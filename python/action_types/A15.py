import flask, sqlite3, json, datetime
from domino.core import log
from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
from .action_base import ActionAcceptor
from .action_page import TheActionPage
from discount.series import Series
from discount.cards import Card, CardLog
from discount.checks import Check

ID = 'A15'
CLASS = 1
DESCRIPTION = 'Начисление процентной скидки от суммы покупок'
ABOUT = '''
    Расчет размера процентной скидки по по персональной карте 
    в зависимости от общей суммы совершенных покупок. 
    Процент не уменьшает существующий процент скидки, а только увеличивает его.
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
# Acceptor
#=============================================

class Acceptor(ActionAcceptor):
    def __init__(self, application, cursor, action, LOG, SQLITE):
        super().__init__(application, cursor, action, LOG, SQLITE)

        self.persent_of_sum = self.action.percents_of_sum
        #self.тип_карты_ID = int(self.action.info.get(Action.ДИСКОНТНАЯ_КАРТА))
        #self.тип_карты = ТипКарты.get(cursor, self.тип_карты_ID)
        #self.used_cards = self.action.used_cards

    def accept(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')

        cursor = engine.cursor
        msg = []
        for card_info in check.cards.values():
            card = card_info.get(Check.CARD_CARD)
            if card:
                if card.TYPE == 0:
                    total = card.total 
                    if total is None:
                        total = 0
                    percent = self.persent_of_sum.find_percent(total) 
                    if card.изменить_скидку(engine, percent, check):
                    #if card.discount is None or percent > card.discount:
                    #    card.change_discount(percent, check)
                    #    card_log = CardLog(card_id = card.ID)
                    #    card_log.operation = CardLog.CHANGE_PARAM
                    #    card_log.msg = f'сумма покупок {total}, установлен процент {percent}%  вместо {card.discount}%'
                        msg.append(f'карта {card.ID}, процент {card.discount}%, сумма покупок {total} : установлен процент {percent}%')
                    #    card.discount = percent
                    #    card.update(engine)
                    #    card_log.create(engine)
                    else:
                        msg.append(f'карта {card.ID}, процент {card.discount}% , сумма покупок {total} : процент не изменен')

        self.log(check, ', '.join(msg))

#=============================================
# Settings
#=============================================
 

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'percent_of_sum']

    def param_visible(self, param_id):
        return param_id in ['description']

    def card_type_visible(self, card_type):
        return True
    
    def params(self):
        return []

    def settings_page(self):
        self.print_title()
        about(self).margin(1).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)

