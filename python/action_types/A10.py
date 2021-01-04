import flask, sqlite3, json, datetime, time
from domino.core import log
#from discount.core import DISCOUNT_DB, CARDS
from .action_page import TheActionPage
from .action_base import ActionCalculator
from discount.series import Series
#from discount.product_sets import ГотовыйРеестрЦен

from discount.actions import Action
from tables.sqlite.action_set_item import ActionSetItem
#from tables.sqlite.product_set import ГотовыйНабор


ID = 'A10'
DESCRIPTION = 'Красная цена'
SUPPLEMENT = False
ABOUT = '''
    Определяет список товаров и для каждого товара задает цену,
    по которой он будет продаватся в период действия акции.
    '''

FIXED_PRICE = True

#=============================================
# Description
#=============================================

def is_available():
    return True

def description(**args):
    return DESCRIPTION

def about(page):
    t = page.text_block('about')
    t.text(ABOUT)
    return t

#=============================================
# Calculator
#=============================================
class Calculator(ActionCalculator):
    def __init__(self, worker, cursor, action, LOG, SQLITE):
        super().__init__(worker, cursor, action, LOG, SQLITE)

        sets = ActionSetItem.sets(SQLITE, self.action.id, 0)
        self.prices = worker.готовый_набор(sets, name='Набор товаров и цен')

        self.тип_карты_ID = action[Action.НАЛИЧИЕ_КАРТЫ_КУПОНА]
        if self.тип_карты_ID and self.тип_карты_ID.strip() != '':
            self.тип_карты_ID = int(self.тип_карты_ID)
        else:
            self.тип_карты_ID = None


    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        # проверка наличия карты, купона
        карта_ID = None
        if self.тип_карты_ID is not None:
            карта = self.найти_первую_карту_по_типу(check, self.тип_карты_ID)
            if карта is None:
                self.log(check, 'нет карты')
                return
            else:
                карта_ID = карта.ID

        # проверка дополнительных условий
        количество_товаров = 0
        уникальные_товары = set()
        for line in check.lines:
            if line.fixed_price:
                continue
            #if self.исключенные_товары and line in self.исключенные_товары:
            #    continue
            if line in self.prices:
                количество_товаров += line.count
                уникальные_товары.add(line.product)

        # проверка дополнительных условий
        if self.минимальное_количество_товаров:
            if self.минимальное_количество_товаров > количество_товаров:
                self.log(check, f'недостаточное количество товаров')
                return
        if self.минимальное_количество_уникальных_товаров:
            if self.минимальное_количество_уникальных_товаров > len(уникальные_товары):
                self.log(check, f'недостаточное количество уникальных товаров')
                return

        # формирование скидки
        СКИДКА = 0.0
        lines = 0
        for line in check.lines:
            if line.fixed_price:
                continue
            цена = self.prices.get(line)
            #log.debug(f'{цена} = self.цены.найти({line.product})')
            if цена is not None:
                lines += 1
                СКИДКА += self.изменить_цену(line, цена, карта_ID)
        if lines != 0:
            self.log(check, f'скидка {СКИДКА}, строк {lines}')
            #self.печать_в_чеке(check, СКИДКА = СКИДКА)
        else:
            self.log(check, f'нет товаров')

#=============================================
# Settings
#=============================================

#PRODUCTS_PARAM = ActionParam('products', 'Список товаров, на которые действует данная акция', type='set', set_id=0, set_price=True) 
#from discount.action_page import ActionTabControl

#SERIES_PARAM_ID = 'series_id'

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'params']

    def набор_дополнительных_условий(self):
        return [Action.НАЛИЧИЕ_КАРТЫ_КУПОНА, 'наличие_ключевого_слова', Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ, Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ]
        #return [Action.НАЛИЧИЕ_КАРТЫ_КУПОНА, 'наличие_ключевого_слова']

    def набор_базовых_параметров(self):
        return [Action.ПОДРАЗДЕЛЕНИЕ,'description', 'validity', 'набор_товаров_и_цен']


    #def print_macros(self):
    #    return [
    #        ['СКИДКА', 'скидка по акции']
    #    ]

    def settings_page(self):
        self.print_title()
        about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)

