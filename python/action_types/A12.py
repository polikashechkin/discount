import flask, sqlite3, json, datetime
from domino.core import log
#from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
from .action_page import TheActionPage
from .action_base import ActionCalculator
from discount.series import Series, CardType
from discount.cards import Card, CardLog
from discount.checks import Check

ID = 'A12'
CLASS = 1
DESCRIPTION = 'Суммовая скидка за наклпленные баллы по карте'
ABOUT = '''
    Скидка выдается за счет накопленных баллов на карте. Скидка не действует на
    товары с фиксированной ценой (табак, распродажи). Скидка равномерно "размазывается"
    по всем товарам.
    '''

#=============================================
# Description
#=============================================

def is_available():
    return True

def description(**args):
    return DESCRIPTION

def about(page, to_detail = False):
    x = page.text_block('about')
    x.text(ABOUT)
    if to_detail:
        x.href('Подробнее...', 'action_types/{ID}.description_page')
    return x

#=============================================
# Calculator
#=============================================

class Calculator(ActionCalculator):
    def __init__(self, application, cursor, action, LOG, SQLITE):
        super().__init__(application, cursor, action, LOG, SQLITE)

        self.card_type_ID = int(self.action.info.get(Action.ДИСКОНТНАЯ_КАРТА, 0))
        self.card_type = CardType.get(cursor, self.card_type_ID)
        self.max_percent = float(self.action.info.get(Action.МАКСИМАЛЬНО_ОПЛАЧИВАЕМАЯ_СТОИМОСТЬ_ЧЕКА,99))
        self.создать_набор_основных_товаров(SQLITE, LOG)
        self.создать_набор_исключенных_товаров(SQLITE, LOG)

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        USED_POINTS = None
        CARD_POINTS = None
        CARD_INFO = None
        card = None
        for card_info in check.cards.values():
            c = card_info.get(Check.CARD_CARD)
            if c is not None and c.TYPE == self.card_type_ID:
                card = c
                CARD_INFO = card_info
                CARD_POINTS = card.points
                USED_POINTS = card_info.get(Check.CARD_POINTS)
                #self.log(check, f'{card_info}')

        if card is None:
            self.log(check, 'нет карты')
            return

        if self.card_type.это_персональная_карта:
            # для персональной карты следует взять то количество баллов, которое ввел кассар
            if USED_POINTS is None or USED_POINTS <= 0:
                self.log(check, f'карта {card.ID} не задано баллов для использования')
                return
            if CARD_POINTS <= 0:
                self.log(check, f'карта {card.ID} нет баллов')
                return
            if USED_POINTS > CARD_POINTS:
                USED_POINTS = CARD_POINTS
        else:
            # для остальных карт то которое вообще есть на карте
            USED_POINTS = CARD_POINTS
            if USED_POINTS <= 0:
                self.log(check, f'карта {card.ID} нет баллов')
                return 
        #----------------------------
        total = 0.0
        lines = []
        for line in check.lines:
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            total += line.price * line.qty
            lines.append(line)

        if total == 0.0:
           self.log(check, 'нет товаров')
           return
        #----------------------------
        if self.max_percent:
            MAX_POINTS = round(total * self.max_percent / 100)
            if USED_POINTS > MAX_POINTS:
                self.log(check, f'Ограничение {self.max_percent} от {total} => скидка {MAX_POINTS}')
                USED_POINTS = MAX_POINTS
        self.log(check, f'карта {card.ID} всего баллов {CARD_POINTS}, использовать {USED_POINTS} сумма {total} процент {self.max_percent} ')
        #----------------------------
        СКИДКА = round(self.добавить_суммовую_скидку(lines, total, USED_POINTS, card.ID, use_points = True), 2)
        #self.log(check, f'скидка {СКИДКА}')
        ИСПОЛЬЗОВАНО = round(СКИДКА, 0)
        БЫЛО = CARD_POINTS
        ОСТАТОК = round(БЫЛО - ИСПОЛЬЗОВАНО, 2)
        #self.печать_в_чеке(check, ОСТАТОК = ОСТАТОК, БЫЛО = БЫЛО, ИСПОЛЬЗОВАНО = ИСПОЛЬЗОВАНО, СКИДКА = СКИДКА)
        CARD_INFO[Check.CARD_POINTS] = 0

        self.log(check, 
        f'карта {card.ID} скидка {СКИДКА}, использовано {ИСПОЛЬЗОВАНО}, было {БЫЛО}, остаток {ОСТАТОК}, ')

#=============================================
# Settings
#=============================================

#tabs = ActionTabControl()
#tabs.remove('weekdays')

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    #  return param_id in ['description', 'validity', Action.FIXED_PRICE, Action.SUPPLEMENT, Action.АКЦИЯ, Action.МНОЖИТЕЛЬ]
    def param_visible(self, param_id):
        return param_id in [
            'description', 'дисконтная_карта', 'excluded', Action.МАКСИМАЛЬНО_ОПЛАЧИВАЕМАЯ_СТОИМОСТЬ_ЧЕКА, 'validity', 
            Action.ПОДРАЗДЕЛЕНИЕ
            ]

    def наименование_закладки(self, tab_id):
        if tab_id == 'скидка_на_товары':
            return 'Максимальная скидка на товары'

    def tab_visible(self, tab_id):
        return tab_id in ['base_params']

    #def params(self):
    #    return [
    #        ActionParam('series_id', 'Накопительная карта', type = 'select', options=self.get_series())
    #        ]

    #def print_macros(self):
    #    return [
    #        ['СКИДКА', 'скидка по акции'],
    #        ['ИСПОЛЬЗОВАНО', 'количество использованных баллов'],
    #        ['БЫЛО', 'входящий остатк баллов'],
    #        ['ОСТАТОК', 'остаток после выполнения акции']
    #    ]

    def settings_page(self):
        self.print_title()
        about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)

