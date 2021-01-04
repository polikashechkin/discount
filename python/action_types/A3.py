import flask, sqlite3, json, datetime
from domino.core import log
from discount.actions import Action
from .action_base import ActionCalculator
from .action_page import TheActionPage, ActionTabControl
from .action_page import CheckButton, EditButton, CancelButton, SaveButton
#import discount.actions
#import discount.series
#from discount.product_sets import ГотовыйНабор

ID = 'A3'
PERCENT = True
CLASS = 1
DESCRIPTION = 'Процентная скидка от суммы чека'
ABOUT = '''
    Под суммой чека понимается изначальная сумма чека в розничных ценах.
    Скидка выдается на все товары в чеке, кроме тех, которые 
    определены в списке исключенных товаров и тех, которые на момент применения 
    скидки, имеют окончательную цену.
    '''
SUPPLEMENT = True
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
        self.процент_от_суммы = self.action.percents_of_sum

        self.создать_набор_исключенных_товаров(SQLITE, LOG)
#        self.создать_набор_основных_товаров(cursor, LOG)


    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        сумма_чека = 0
        for line in check.lines:
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            сумма_чека += line.price * line.qty
            # TOTAL += int(line.price * line.qty)

        #msg = []
        if self.процент_от_суммы.dim > 0:
            процент_скидки = self.процент_от_суммы.find_percent(сумма_чека)
            #msg.append(f'сумма чека {сумма_чека}')
            строк = 0
            количество_товаров = 0
            СКИДКА = 0.0
            if процент_скидки > 0.0:
                for line in check.lines:
                    if line.fixed_price:
                        continue
                    if self.исключенные_товары and line in self.исключенные_товары:
                        continue
                    строк += 1
                    количество_товаров += line.count
                    СКИДКА += self.применить_скидку(line, процент_скидки)
            self.log(check, f'сумма чека {сумма_чека} процент {процент_скидки}% строк {строк}  товаров {количество_товаров} cкидка {СКИДКА}')
            self.печать_в_чеке(check, СКИДКА = round(СКИДКА,0))

            #msg.append(f'строк {строк} cкидка {СКИДКА}, процент {процент_скидки}%')
            #self.log(check, ', '.join(msg))
        else:
            self.log(check, f'не задан прцент от суммы')
        


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
        return param_id in ['description', 'validity']

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'percent_of_sum', Action.ПОДРАЗДЕЛЕНИЕ]
        
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
