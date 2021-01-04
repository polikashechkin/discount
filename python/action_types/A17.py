import flask, sqlite3, json, datetime
from domino.core import log
from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
from .action_page import TheActionPage
from .action_base import ActionCalculator
from discount.series import Series

#=============================================
# Общее описание
#=============================================

ID = 'A17'
PERCENT = True
CLASS = 0
DESCRIPTION = 'Улучшение процентной скидки'
ABOUT = '''
    Самостоятельно акция не применяется. Она усиливает действие других процентных акций.
    Соответственно, данная акция должна выполняться после расчета акций действие которых 
    усиливает. Список акций задается.
    '''

FIXED_PRICE = True

#def is_available():
#    return True
#def description(**args):
#    return DESCRIPTION

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
        self.множитель = self.action.множитель
        self.action_ID = self.action.акция

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return 

        total_discount = 0.0
        lines = 0
        for line in check.lines:
            if line.get_action(self.action_ID) is not None:
                lines += 1
                total_discount += self.умножить_скидку(line, self.action_ID, self.множитель)
        if lines > 0:
            self.log(check, f'акция {self.action_ID} дополнительная скидка {total_discount}, cтрок {lines}')
        else:
            self.log(check, f'нет строк по акции {self.action_ID}')
          
#=============================================
# Page
#=============================================

#DISCOUNT_PARAM = ActionParam('discount', 'Коэффициент умножения', type='number', min=1, max=10)

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'weekdays']

    def param_visible(self, param_id):
        return param_id in ['description', 'validity', Action.АКЦИЯ, Action.МНОЖИТЕЛЬ]

    def settings_page(self):
        self.print_title()
        about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tabs()

    def description_page(self):
        self.title(f'{ID}. {DESCRIPTION}')
        about(self)
