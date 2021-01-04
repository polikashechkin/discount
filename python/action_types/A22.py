import flask, sqlite3, json, datetime, arrow
from domino.core import log
from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action, ActionSetItem
from .action_page import TheActionPage as BasePage
#from discount.action_page import TheActionPage, ActionParam, ActionTabControl
#from discount.action_page import Наличие_карты_купона, Минимальное_количество_товаров
#from discount.action_page import Минимальная_сумма_чека

from .action_base import ActionCalculator
from discount.series import Series, ТипКарты
from discount.product_sets import ProductSet

#=============================================
# Description
#=============================================

ID = 'A22'
CLASS = 1
DESCRIPTION = 'Выдача подарочных марок от набора товаров'
ABOUT = '''
    В зависимости от количества купленных товаров из определенного набора определяется количество
    выданных марок. Задается количество товаров за которое выдается одна марка.
    Количество марок округляется в меньшую сторону. Например, если количество товаров 3, 
    а одна марка вдается за 2, то марок будет выдано 1, если количество 1, то марок 0.
    '''
#PERCENT = False
#SUPPLEMENT = False
#FIXED_PRICE = False
       
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
    def __init__(self, application, cursor, action, LOG, SQLITE):
        super().__init__(application, cursor, action, LOG, SQLITE)
        self.количество_товаров_для_получения_подарочной_марки = self.action.info.get(Action.КОЛИЧЕСТВО_ТОВАРОВ_ДЛЯ_ПОЛУЧЕНИЯ_ПОДАРОЧНОЙ_МАРКИ, 0)
        if self.количество_товаров_для_получения_подарочной_марки < 0:
            self.количество_товаров_для_получения_подарочной_марки = 0
        self.создать_набор_исключенных_товаров(SQLITE, LOG)
        self.создать_набор_основных_товаров(SQLITE, LOG)

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        # формирование набора товаров
        if not self.количество_товаров_для_получения_подарочной_марки:
            self.log(check, f'не задано количество товаров')
            return

        количество_товаров = 0
        уникальные_товары = set()
        сумма_товаров = 0.0
        for line in check.lines:
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            if self.набор_товаров and line in self.набор_товаров:
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
        количество_марок = int(количество_товаров / self.количество_товаров_для_получения_подарочной_марки)
        if количество_марок:
            check.gifts[f'{self.action.id}'] = {"m":количество_марок}
        self.log(check, f'марок {количество_марок}, товаров {количество_товаров}, стоимость марки {self.количество_товаров_для_получения_подарочной_марки}')

#=============================================
# Page
#=============================================
 
class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def набор_базовых_параметров(self):
        return [
            'description', 'validity', 'excluded', 'набор_товаров', Action.КОЛИЧЕСТВО_ТОВАРОВ_ДЛЯ_ПОЛУЧЕНИЯ_ПОДАРОЧНОЙ_МАРКИ
            ]

    def набор_дополнительных_условий(self):
        return []

    def tab_visible(self, tab_id):
        return tab_id in ['base_params']

    #def print_macros(self):
    #    return [
    #        ['СКИДКА', 'скидка по акции']
    #    ]

    def settings_page(self):
        self.print_title()
        #about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        about(self)
        #self.print_base_params()
        #self.print_tab()
        self.print_tabs()

    def description_page(self):
        self.title(f'{ID}. {DESCRIPTION}')
        about(self)
