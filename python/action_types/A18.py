import flask, sqlite3, json, datetime, time
from domino.core import log
#from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
from .action_page import TheActionPage
from .action_base import ActionCalculator
from discount.series import Series
#from discount.product_sets import ГотовыйРеестрЦен
from tables.sqlite.action_set_item import ActionSetItem
#from tables.sqlite.product_set import ГотовыйНабор

ID = 'A18'
DESCRIPTION = 'Распродажа'
SUPPLEMENT = False
ABOUT = '''
    Определяет список товаров и для каждого товара задает цену,
    по которой он будет продаватся в период действия акции.
    '''

FIXED_PRICE = True
FOR_SALE = True

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
        self.for_sale = True

        #start = time.perf_counter()
        #self.prices = ГотовыйРеестрЦен()
        #for ps in ActionSetItem.findall(cursor, 'TYPE=0 and action_id=?', [self.action.ID]):
        #    self.prices.добавить(cursor, ps.set_id)
        #LOG(f'{self}.набор_товаров_и_цен', start)
        sets = ActionSetItem.sets(SQLITE, self.action.id, 0)
        self.prices = worker.готовый_набор(sets, name='Набор товаров и цен')

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return 

        СКИДКА = 0.0
        lines = 0
        for line in check.lines:
            if line.fixed_price:
                continue
            цена = self.prices.get(line)
            log.debug(f'{self.prices}')
            log.debug(f'{цена} = self.prices.get({line.product})')
            if цена is not None:
                lines += 1
                СКИДКА += self.изменить_цену(line, цена, None)
        
        if lines != 0:
            self.log(check, f'скидка {СКИДКА}, строк {lines}')
            self.печать_в_чеке(check, СКИДКА = СКИДКА)
        else:
            self.log(check, f'нет товаров')

    def get_prices(self, prices, dept_code, date):
        if self.проверка_периода_действия(date):
            for uid, price in self.prices.items():
                prices[uid] = price

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
        return tab_id in ['base_params']

    def набор_базовых_параметров(self):
        return [Action.ПОДРАЗДЕЛЕНИЕ,'description', 'период_действия_упрощенный', 'набор_товаров_и_цен']

    def print_macros(self):
        return [
            ['СКИДКА', 'скидка по акции']
        ]

    def settings_page(self):
        self.print_title()
        about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)

