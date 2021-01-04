#import flask, sqlite3, json, datetime
from discount.page import DiscountPage as BasePage
from domino.page_controls import TabControl
#from domino.core import log

#from discount.card_types import CARD_TYPES
#from discount.action_types import ActionTypes

#def DISCOUNT_DB(account_id):
#    return f'/DOMINO/accounts/{account_id}/data/discount.db'
 
ACTION_TABS = TabControl('action_tabs')
ACTION_TABS.append('print_calc_actions', 'Расчетные акции', 'print_calc_actions')
ACTION_TABS.append('print_accept_actions', 'Послепродажные акции (действия)', 'print_accept_actions')

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request, controls = [ACTION_TABS])
        self.action_types = self.application['action_types']

    def print_calc_actions(self):
        self.print_actions(True)

    def print_accept_actions(self):
        self.print_actions(False)
    
    def print_actions(self, is_calc = True):
        x = self.text_block('types').mt(1)
        for action_type in sorted(self.action_types.types(), key = lambda a : a.description()):
            if not action_type.IS_AVAILABLE:
                continue
            if not action_type.hasAcceptor and not is_calc:
                continue
            if not action_type.hasCalculator and is_calc:
                continue
            x.newline(css='h5 mt-3')
            x.text(action_type.description())

            #x.href(action_type.description(), f'action_types/{action_type.id}.description_page')
            x.newline()
            x.text(action_type.about)
            #x.href(' Подробнее...', f'action_types/{action_type.id}.description_page')
        x.newline(css='mb-3')
        x.text('')

    def __call__(self):
        self.title(f'Типы акций')
        ACTION_TABS.print(self)
