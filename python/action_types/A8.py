import flask, sqlite3, json, datetime
from domino.core import log
#from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
from .action_page import TheActionPage
from .action_base import ActionCalculator
from discount.series import Series, ТипКарты
#from discount.product_sets import ГотовыйНабор

ID = 'A8'
PERCENT = True
CARD = True
DESCRIPTION = 'Процентная скидка по дисконтной карте / купону'
ABOUT = '''
    Скидка применяется только при предъявлении дисконтной карты или купона.
    Процент скидки устанавливается для дисконтной карты. 
    По умолчанию, скидка выдается на все товары. Можно указать 
    конкретный список товаров, на которые скидка не распространяется.
    '''

SUPPLEMENT = True
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
    def __init__(self, application, cursor, action, LOG, SQLITE):
        super().__init__(application, cursor, action, LOG, SQLITE)

        self.card_type_ID = self.action.info.get(Action.ДИСКОНТНАЯ_КАРТА, 0)
        try:
            self.card_type_ID = int(self.card_type_ID)
            self.дисконтная_карта = ТипКарты.get(cursor, self.card_type_ID)
        except:
            log.exception(f'{self}.__init__')
            raise Exception(f'недопустимый тип карты "{self.card_type_ID}"')
        #self.used_cards = self.action.used_cards

        #self.искюченные_товары = ГотовыйНабор()
        #for набор in self.action.sets.findall('искюченные_товары'):
        #    self.искюченные_товары.добавить(cursor, набор.set_id, True)
        self.создать_набор_исключенных_товаров(SQLITE, LOG)
        self.создать_набор_основных_товаров(SQLITE, LOG)

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        card = self.найти_первую_карту_по_типу(check, self.card_type_ID)
        if card is None:
            self.log(check, f'нет карты "{self.дисконтная_карта.полное_наименование}" {self.card_type_ID}')
            return

        процент = card.discount

        СКИДКА = 0.0
        lines = 0
        for line in check.lines:
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            if self.набор_товаров and line not in self.набор_товаров:
                continue

            #if not line.fixed_price:
            #    if self.искюченные_товары.найти(line, False):
                #if self.products_2 is not None and line.product in self.products_2:
            #        continue
                #if self.products is None or line.product in self.products:
            СКИДКА += self.применить_скидку(line, процент, card.ID)
            lines += 1

        if lines == 0:
            self.log(check, f'нет товаров')
        else:
            self.log(check, f'карта {card.ID} процент {процент}% строк {lines} cкидка {СКИДКА}')
            self.печать_в_чеке(check, СКИДКА = СКИДКА)

#=============================================
# Page
#=============================================


#COUNT_PARAM = ActionParam('count', 'Количество товаров в наборе, при котором действует скидка', type='number', min=2)
#DISCOUNT_PARAM = ActionParam(Action.DISCOUNT, 'Процентная скидка', type='number', min=0, max=100, undefined='НЕТ')
#PRODUCTS_PARAM = ActionParam('products', 'Товары, на которые выдается скидка', type='set', set_id=0, undefined='ВСЕ') 
#PRODUCTS_PARAM_2 = ActionParam('products', 'Товары, на которые скидка НЕ выдается', type='set', set_id=2, undefined='НЕТ') 
#SERIES_PARAM = ActionParam('series_id', 'Карта/Купон', type='select', options=[

#from discount.action_page import ActionTabControl

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def набор_базовых_параметров(self):
        return ['description', 'validity', 'дисконтная_карта', 'набор_товаров', 'excluded','округление_цены']

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'print']
    
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

