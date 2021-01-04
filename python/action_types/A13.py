import flask, sqlite3, json, datetime
from domino.core import log
#from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
from .action_base import ActionCalculator
from .action_page import TheActionPage
from .action_page import CheckButton, EditButton, CancelButton, SaveButton
#import discount.actions
#import discount.series
#from discount.product_sets import ГотовыйНабор

ID = 'A13'
DESCRIPTION = 'Процентная скидка от количества товаров в чеке'
ABOUT = '''
    В зависимости от количества товаров в чеке 
    определяется процент скидки. 
    Скидка выдается на все товары в чеке, кроме тех, которые 
    определены в списке исключенных товаров и тех, которые на момент применения 
    скидки, имеют окончательную цену.
    '''
FIXED_PRICE = True

def description():
    return DESCRIPTION

def is_available():
    return True

def about(page, detail=False):
    t = page.text_block('about')
    t.text(ABOUT)
    return t
#=============================================
# Calculator
#=============================================

class Calculator(ActionCalculator):
    def __init__(self, application, cursor, action, LOG, SQLITE):
        super().__init__(application, cursor, action, LOG, SQLITE)
        self.процент_от_количества = self.action.percents_of_sum
        self.создать_набор_исключенных_товаров(SQLITE, LOG)

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        if self.процент_от_количества.dim > 0:
            количество_товаров = 0
            for line in check.lines:
                if self.исключенные_товары and line in self.исключенные_товары:
                    continue
                количество_товаров += line.count

            процент_скидки = self.процент_от_количества.find_percent(количество_товаров)
            СКИДКА = 0.0
            if процент_скидки > 0.0:
                for line in check.lines:
                    if line.fixed_price:
                        continue
                    if self.исключенные_товары and line in self.исключенные_товары:
                        continue
                    СКИДКА += self.применить_скидку(line, процент_скидки)
            self.log(check, f'товаров в чеке {количество_товаров} процент {процент_скидки}% скидка {СКИДКА}')
            self.печать_в_чеке(check, СКИДКА=СКИДКА)
        else:
            self.log(check, f'не задана шкала процентов')

#=============================================
# Settings
#=============================================
#PRODUCTS_PARAM = ActionParam('products', 'Товары, на которые выдается скидка', type='set', set_id=0, undefined='ВСЕ') 
#PRODUCTS_PARAM_2 = ActionParam('products', 'Товары, на которые скидка НЕ выдается', type='set', set_id=2, undefined='НЕТ') 

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    #  return param_id in ['description', 'validity', Action.FIXED_PRICE, Action.SUPPLEMENT, Action.АКЦИЯ, Action.МНОЖИТЕЛЬ]
    def param_visible(self, param_id):
        return param_id in [Action.ПОДРАЗДЕЛЕНИЕ,'description', 'validity', 'excluded']

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'percent_of_sum', 'params']

    def наименование_закладки(self, id):
        if id == 'percent_of_sum':
            return 'ПРОЦЕНТ ОТ КОЛИЧЕСТВА ТОВАРОВ'
        return None

    def набор_дополнительных_условий(self):
        return [Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА, Action.НАЛИЧИЕ_КАРТЫ_КУПОНА, 'наличие_ключевого_слова', Action.МИНИМАЛЬНАЯ_СУММА_ЧЕКА]

        
    def params(self):
        return [
            #PRODUCTS_PARAM, 
            #PRODUCTS_PARAM_2, 
            ]

    def print_macros(self):
        return [
            ['СКИДКА', 'размер скидки']
        ]
   
    def settings_page(self):
        self.print_title()
        about(self, True)
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)
