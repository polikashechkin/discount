import flask, sqlite3, json, datetime, time
from domino.core import log
#from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
from .action_page import TheActionPage
from .action_base import ActionCalculator
from discount.series import Series

from tables.sqlite.action_set_item import ActionSetItem
#from tables.sqlite.product_set import ГотовыйНабор

ID = 'A29'
DESCRIPTION = 'Персональная цена'
SUPPLEMENT = False
ABOUT = '''
    Основное назначение данной акции - это задавать персональные цены для владельцев 
    персональных карт. Цена не зависит от состава чека. 
    Соответственно согласно данным ценам можно  печатать ценники и этикетки на товар. 
    Диапазон действия скидки задается без времени.    '''

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
        sets = ActionSetItem.sets(SQLITE, self.action.ID, 0)
        #self.prices = ГотовыйНабор.create(SQLITE, sets, LOG=LOG, name='Набор персональных цен')
        self.prices = worker.готовый_набор(sets, name='Набор персональных цен')

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        if not check.for_sale:
            if not self.найти_первую_карту_по_типу(check, 0):
                self.log(check, 'нет карты')
                return

        СКИДКА = 0.0
        lines = 0
        for line in check.lines:
            if line.fixed_price:
                continue
            цена = self.prices.get(line)
            #log.debug(f'{цена} = self.цены.найти({line.product})')
            if цена is not None:
                lines += 1
                СКИДКА += self.изменить_цену(line, цена, None)
                VIP_PRICE = self.округлить_в_копейках(int(цена * 100))
                if hasattr(line, 'VIP_PRICE'):
                    line.VIP_PRICE = min(line.VIP_PRICE, VIP_PRICE)
                else:
                    line.VIP_PRICE = VIP_PRICE
        
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

class Page(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def tab_visible(self, tab_id):
        return tab_id in ['base_params']

    def набор_базовых_параметров(self):
        return [Action.ПОДРАЗДЕЛЕНИЕ,'description', 'период_действия_упрощенный', 'набор_товаров_и_цен']

    def settings_page(self):
        self.print_title()
        about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)

