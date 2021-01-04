from .action_page import TheActionPage, ActionTabControl
from .action_base import ActionCalculator

from domino.core import log
from discount.actions import Action, ActionSetItem
from discount.series import Series, ТипКарты
from discount.product_sets import ProductSet

#=============================================
# Description
#=============================================

ID = 'A31'
PERCENT = True
DESCRIPTION = 'Суммовая скидка'
ABOUT = '''
    Формирование суммовой скидки на список товаров, заданный при настройке акции.
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

        self.суммовая_скидка = float(self.action.info.get(Action.СУММОВАЯ_СКИДКА, 0.0))

        self.тип_карты_ID = action[Action.НАЛИЧИЕ_КАРТЫ_КУПОНА]
        if self.тип_карты_ID is not None and self.тип_карты_ID.strip() != '':
            self.тип_карты_ID = int(self.тип_карты_ID)
        else:
            self.тип_карты_ID = None

        self.создать_набор_исключенных_товаров(SQLITE, LOG)
        self.создать_набор_основных_товаров(SQLITE, LOG)
        #log.debug(f'{self} : НАБОР_ТОВАРОВ {self.набор_товаров}')

    def calc(self, engine, чек):
        if чек.TYPE:
            self.log(чек, 'ВОЗВРАТ')
            return
        # проверка на наличие типа карты
        карта_ID = None
        if self.тип_карты_ID is not None:
            карта = self.найти_первую_карту_по_типу(чек, self.тип_карты_ID)
            if карта is None:
                self.log(чек, 'нет карты')
                return
            else:
                карта_ID = карта.ID

        # формирование набора товаров
        строки = []
        количество_товаров = 0
        уникальные_товары = set()
        сумма_товаров = 0.0
        for line in чек.lines:
            if line.fixed_price:
                continue
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            #self.log(чек, f'{self.набор_товаров}')
            if not self.набор_товаров or line in self.набор_товаров:
                строки.append(line)
                количество_товаров += line.count
                сумма_товаров += line.qty * line.price
                уникальные_товары.add(line.product)

        # проверка дополнительных условий
        if self.минимальное_количество_товаров:
            if self.минимальное_количество_товаров > количество_товаров:
                self.log(чек, f'недостаточное количество товаров')
                return
        if self.минимальная_сумма_товаров:
            if self.минимальная_сумма_товаров > сумма_товаров:
                self.log(чек, f'недостаточная сумма товаров')
                return
        if self.минимальное_количество_уникальных_товаров:
            if self.минимальное_количество_уникальных_товаров > len(уникальные_товары):
                self.log(чек, f'недостаточное количество уникальных товаров')
                return

        if len(строки) == 0:
            self.log(чек, f'нет товаров')
            return

        # расчет скидки
        скидка_всего = round(self.добавить_суммовую_скидку(строки, сумма_товаров, self.суммовая_скидка, None), 2)

        self.log(чек, f'строк {len(строки)}, скидка {скидка_всего}')

#=============================================
# Page
#=============================================
 
class Page(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def набор_базовых_параметров(self):
        return ['description', 'validity', 
            Action.ПОДРАЗДЕЛЕНИЕ,
            Action.СУММОВАЯ_СКИДКА, 'набор_товаров', 
            'excluded', 'округление_цены'
            ]

    def набор_дополнительных_условий(self):
        return [Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА, Action.НАЛИЧИЕ_КАРТЫ_КУПОНА, 'наличие_ключевого_слова', Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ, Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ЧЕКА]

    def tab_visible(self, tab_id):
        return tab_id in ['base_params','params', 'weekdays']

    #def print_macros(self):
    #    return [
    #        ['СКИДКА', 'скидка по акции']
    #    ]

    def settings_page(self):
        self.print_title()
        about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        #self.print_base_params()
        #self.print_tab()
        self.print_tabs()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)
