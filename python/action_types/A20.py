import flask, sqlite3, json, datetime, arrow, time
from domino.core import log
from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action, ActionSetItem
from .action_page import TheActionPage
#from discount.action_page import Наличие_карты_купона, Минимальное_количество_товаров
#from discount.action_page import Минимальная_сумма_чека

from .action_base import ActionCalculator
from discount.series import Series, ТипКарты
from discount.product_sets import ProductSet

#=============================================
# Description
#=============================================

ID = 'A20'
PERCENT = True
DESCRIPTION = 'Скидка на день рождения'
ABOUT = '''
    Скидка применяется только при предъявлении персоналоной карты.
    В карте обязательно должна быть определена дата рождения.
    При попадании даты чека в диапозон, определенный в акции, выдается процентная скидка
    на перечень определенных в акции товаров.
    '''
SUPPLEMENT = True
FIXED_PRICE = True
       
def is_available():
    return True
def description(**args):
    return DESCRIPTION
def about(page):
    t = page.text_block('about')
    t.text(ABOUT)
    return t

SERIES_PARAM_ID = 'series_id'

#=============================================
# Calculator
#=============================================
class Calculator(ActionCalculator):
    def __init__(self, application, cursor, action, LOG, SQLITE):
        super().__init__(application, cursor, action, LOG, SQLITE)

        self.процент_скидки = float(self.action.info.get(Action.ПРОЦЕНТНАЯ_СКИДКА, 0.0))
        self.start_day = int(self.action.info.get(Action.КОЛИЧЕСТВО_ДНЕЙ_ДО_ДНЯ_РОЖДЕНИЯ, 0))
        self.end_day = int(self.action.info.get(Action.КОЛИЧЕСТВО_ДНЕЙ_ПОСЛЕ_ДНЯ_РОЖДЕНИЯ, 0))
        self.создать_набор_исключенных_товаров(SQLITE, LOG)
        self.создать_набор_основных_товаров(SQLITE, LOG)

    def calc(self, engine, чек):
        if чек.TYPE:
            self.log(чек, 'ВОЗВРАТ')
            return

        pg_cursor = engine.pg_cursor
        # проверка на наличие типа карты
        карта = self.найти_первую_карту_по_типу(чек, 0)
        if карта is None:
            self.log(чек, 'нет карты')
            return
        else:
            карта_ID = карта.ID
        #получаем дату рождения
        pg_cursor.execute('select day from discount_card where ID=%s', [карта_ID])
        DAY = pg_cursor.fetchone()[0]
        if DAY is None:
            self.log(чек, f'карта "{карта_ID}" не задан день рождения')
            return

        CHECK_DATE  = чек.date.date()
        
        # день рождения в текущем году
        if DAY.month == 2 and DAY.day == 29:
            try:
                DAY = arrow.get(CHECK_DATE.year, 2, 29)
            except:
                DAY = arrow.get(CHECK_DATE.year, 2, 28)
        else:
            DAY = arrow.get(CHECK_DATE.year, DAY.month, DAY.day)

        if self.start_day == 0:
            START_DATE = DAY.date()
        elif self.start_day == 100:
            START_DATE = DAY.shift(days =- DAY.weekday()).date()
        else:
            START_DATE = DAY.shift(days=-self.start_day).date()

        if self.end_day == 0:
            END_DATE = DAY.date()
        elif self.end_day == 100:
            END_DATE = DAY.shift(weekday=6).date()
        else:
            END_DATE = DAY.shift(days=self.end_day).date()
        
        self.log(чек, f'Текущий день рождения {DAY.date()}, акция действует с {START_DATE} по {END_DATE} включительно')

        if CHECK_DATE < START_DATE:
            self.log(чек, f'{CHECK_DATE} < {START_DATE} : до дня рождения')
            return
        if CHECK_DATE > END_DATE:
            self.log(чек, f'{CHECK_DATE} > {END_DATE} : после дня рождения')
            return

        # формирование набора товаров
        строки = []
        количество_товаров = 0
        уникальные_товары = set()
        сумма_товаров = 0.0
        for line in чек.lines:
            #log.debug(f'{self} {line.__dict__}')
            #log.debug(f'строка {строка.product} {строка.fixed_price}')
            if line.fixed_price:
                continue
            if self.исключенные_товары and line in self.исключенные_товары:
                continue

            if self.набор_товаров is None or line in self.набор_товаров: 
                строки.append(line)
                количество_товаров += line.count
                сумма_товаров += line.qty * line.price
                уникальные_товары.add(line.product)

        # проверка дополнительных условий
        #if self.минимальное_количество_товаров:
        #    if self.минимальное_количество_товаров > количество_товаров:
        #        self.log(чек, f'недостаточное количество товаров')
        #        return
        #if self.минимальная_сумма_товаров:
        #    if self.минимальная_сумма_товаров > сумма_товаров:
        #        self.log(чек, f'недостаточная сумма товаров')
        #        return
        #if self.минимальное_количество_уникальных_товаров:
        #    if self.минимальное_количество_уникальных_товаров > len(уникальные_товары):
        #        self.log(чек, f'недостаточное количество уникальных товаров')
        #        return

        if len(строки) == 0:
            self.log(чек, f'нет товаров')
            return

        # расчет скидки
        скидка_всего = 0.0
        for строка in строки:
            скидка_всего += self.применить_скидку(строка, self.процент_скидки, карта_ID)

        self.печать_в_чеке(чек, СКИДКА = скидка_всего)
        self.log(чек, f'карта "{карта_ID}" строк {len(строки)}, скидка {скидка_всего}, день рождения {DAY.date()} : {START_DATE} : {END_DATE}')

#=============================================
# Page
#=============================================
 
class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def набор_базовых_параметров(self):
        return [
            'description', 'validity', Action.ПРОЦЕНТНАЯ_СКИДКА, 'набор_товаров', 
            'excluded', 'округление_цены',
            Action.КОЛИЧЕСТВО_ДНЕЙ_ДО_ДНЯ_РОЖДЕНИЯ,
            Action.КОЛИЧЕСТВО_ДНЕЙ_ПОСЛЕ_ДНЯ_РОЖДЕНИЯ
            ]

    def набор_дополнительных_условий(self):
        return []

    def tab_visible(self, tab_id):
        return tab_id in ['base_params','print']

    def print_macros(self):
        return [
            ['СКИДКА', 'скидка по акции']
        ]

    def settings_page(self):
        self.print_title()
        #about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        about(self)
        #self.print_base_params()
        #self.print_tab()
        self.print_tabs()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)
