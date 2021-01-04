import flask, sqlite3, json, datetime
from domino.core import log
from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
#from discount.action_page import TheActionPage, ActionParam
from .action_base import ActionCalculator
from .action_page import TheActionPage as BasePage
from discount.checks import TEXT_TEXT, TEXT_BOLD, TEXT_CODE, TEXT_EAN13
from discount.series import Series, ТипКарты

#=============================================
# Description
#=============================================

ID = 'A30'
CLASS = 2
DESCRIPTION = 'Печать подарочного купона'
ABOUT = '''
    Печать в чеке информации по выданным в процессе выполнения акций подарочным купонам.
    Печаются все купоны, задонного вида. Если не создано ни одного подарочного купона, то
    ничего не печатается.
    '''
def is_available():
    return True

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
        #if self.action.подарочный_купон is None:
        #    raise Exception(f'Не задан тип подарочного купона')

        #self.тип_купона = ТипКарты.get(cursor, self.action.подарочный_купон)
        #if self.тип_купона is None:
        #    raise Exception(f'Неизвестный тип подарочного купона "{self.action.подарочный_купон}"')
        #self.наименование_купона = self.тип_купона.наименование
        #self.класс_купона = self.card_types[self.тип_купона.type]

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        for action_id, action_info in check.processing.actions_info.items():
            coupon_id = action_info.get('coupon_id')
            if coupon_id:
                self.print_check_lines(check, {f'{{КУПОН}}':coupon_id})
                self.log(check, f'Печать купона "{coupon_id}"')

#=============================================
# ThePage
#=============================================

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'print']

    def набор_базовых_параметров(self):
        return [Action.ПОДРАЗДЕЛЕНИЕ,'description', 'validity', '-подарочный_купон']

    def print_macros(self):
        return [
            ['КУПОН', 'номер купона']
        ]

    def settings_page(self):
        self.print_title()
        about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {DESCRIPTION}')
        about(self)
