import flask, sqlite3, json, datetime
from domino.core import log
#from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
from .action_page import TheActionPage
from .action_base import ActionCalculator

#=============================================
# Description
#=============================================

ID = 'A9'
CLASS = 1
DESCRIPTION = 'Промо'
ABOUT = '''
    Суть данной акции это распечатаь в чеке каки либо рекламные предложения
    покупателю.
    '''
def is_available():
    return True

def description(**args):
    return 'Промо'

def about(page):
    t = page.text_block('about')
    t.text(ABOUT)
    return t

#=============================================
# Calculator
#=============================================

class Calculator(ActionCalculator):
    def __init__(self, application, cursor, action, LOG, SQLITE):
        super().__init__(application, cursor, action, LOG, SQLITE)
        self.создать_набор_основных_товаров(SQLITE, LOG)

    def calc(self, engine, check):
        # проверка на наличие необходимый товаров
        if self.набор_товаров:
            количество_товаров = 0
            уникальные_товары = set()
            сумма_товаров = 0.0
            for line in check.lines:
                if not self.набор_товаров or line in self.набор_товаров: 
                    количество_товаров += line.count
                    сумма_товаров += line.qty * line.price
                    уникальные_товары.add(line.product)

            if количество_товаров == 0:
                self.log(check, f'нет товаров')
                return
            
            # проверка дополнительных условий
            if self.минимальное_количество_товаров:
                if self.минимальное_количество_товаров > количество_товаров:
                    self.log(check, f'недостаточное количество товаров')
                    return
            if self.минимальная_сумма_товаров:
                if self.минимальная_сумма_товаров > сумма_товаров:
                    self.log(check, f'недостаточная сумма товаров')
                    return
            if self.минимальное_количество_уникальных_товаров:
                if self.минимальное_количество_уникальных_товаров > len(уникальные_товары):
                    self.log(check, f'недостаточное количество уникальных товаров')
                    return

        lines = self.print_check_lines(check)
        self.log(check, f'напечатано {lines}')

#=============================================
# ThePage
#=============================================

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'params', 'weekdays', 'print']

    def набор_базовых_параметров(self):
        return [Action.ПОДРАЗДЕЛЕНИЕ,'description', 'validity', 'необходимый_набор_товаров']

    def набор_дополнительных_условий(self):
        return [Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА,Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ, Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ЧЕКА]
    
    #def print_macros(self):
    #    return [
    #        ['КУПОН', 'номер купона']
    #    ]

    def settings_page(self):
        self.print_title()
        p = about(self)
        #p.href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)



