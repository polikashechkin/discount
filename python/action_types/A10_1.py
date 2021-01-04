import flask, sqlite3, json, datetime, time
from domino.core import log
#from discount.core import DISCOUNT_DB, CARDS
from .action_page import TheActionPage
from .action_base import ActionCalculator
from discount.series import Series
from domino.pages import Text
#from discount.product_sets import ГотовыйРеестрЦен


from discount.actions import Action
from tables.sqlite.action_set_item import ActionSetItem
#from tables.sqlite.product_set import ГотовыйНабор

ID = 'A10_1'
DESCRIPTION = 'Красная цена по купону'
SUPPLEMENT = False
ABOUT = '''
    Для каждого купона заданного типа, определяется специальная цена на одни из товаров
    зананных в товарном наборе. Для каждого купона скидка дается только на один товар
    из набора. 
    '''
FIXED_PRICE = True

#=============================================
# Description
#=============================================

def is_available():
    return True

def description(**args):
    return DESCRIPTION

#def about(page):
#    t = page.text_block('about')
#    t.text(ABOUT)
#    return t

#=============================================
# Calculator
#=============================================
class Calculator(ActionCalculator):
    def __init__(self, worker, cursor, action, LOG, SQLITE):
        super().__init__(worker, cursor, action, LOG, SQLITE)

        sets = ActionSetItem.sets(SQLITE, self.action.id, 0)
        self.prices = worker.готовый_набор(sets, name='Набор товаров и цен')

        self.тип_карты_ID = action[Action.ПОДАРОЧНЫЙ_КУПОН]
        if self.тип_карты_ID and self.тип_карты_ID.strip() != '':
            self.тип_карты_ID = int(self.тип_карты_ID)
        else:
            self.тип_карты_ID = None

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        # проверка наличия подарочный купонов
        coupons = []
        if self.тип_карты_ID is not None:
            for card_info in check.cards.values():
                card = card_info[check.CARD_CARD]
                if card and card.TYPE == self.тип_карты_ID:
                    coupons.append(card.ID)
        else:
            self.log(check, 'Не задан тип подарочныого купона')
            return
        
        if len(coupons) == 0:
            self.log(check, 'Нет ни одного купона')
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
                coupon_id = coupons.pop()
                СКИДКА += self.изменить_цену(line, цена, coupon_id)
                if len(coupons) == 0:
                    break

        if lines != 0:
            self.log(check, f'скидка {СКИДКА}, строк {lines}')
            #self.печать_в_чеке(check, СКИДКА = СКИДКА)
        else:
            self.log(check, f'нет товаров')

#=============================================
# Settings
#=============================================

class Page(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def tab_visible(self, tab_id):
        return tab_id in ['base_params']

    #def набор_дополнительных_условий(self):
    #    return [Action.НАЛИЧИЕ_КАРТЫ_КУПОНА, 'наличие_ключевого_слова', Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ, Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ]
        #return [Action.НАЛИЧИЕ_КАРТЫ_КУПОНА, 'наличие_ключевого_слова']

    def набор_базовых_параметров(self):
        return [Action.ПОДРАЗДЕЛЕНИЕ,'description', 'validity', 'набор_товаров_и_цен', Action.ПОДАРОЧНЫЙ_КУПОН]


    #def print_macros(self):
    #    return [
    #        ['СКИДКА', 'скидка по акции']
    #    ]

    def settings_page(self):
        self.print_title()
        Text(self, 'about').text(ABOUT)
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        Text(self, 'about').text(ABOUT)

