import flask, sqlite3, json, datetime
from domino.core import log
from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action, ActionSetItem
#from discount.action_page import TheActionPage, ActionParam
from .action_base import ActionCalculator
from .action_page import TheActionPage as BasePage
from discount.checks import TEXT_TEXT, TEXT_BOLD, TEXT_CODE, TEXT_EAN13

#=============================================
# Description
#=============================================

ID = 'A24'
CLASS = 2
DESCRIPTION = 'Печать итогов по скидкам'
ABOUT = '''
    Печать в чеке итогов по полученным скидкам в результате проведения акций. Данная акция должна быть расположена 
    в конце списка акций.
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

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        if self.print_mode == Action.print_mode_HEADER:
            print_place = check.print[0] 
        elif self.print_mode == Action.print_mode_FOOTER:
            print_place = check.print[1]
        elif self.print_mode == Action.print_mode_COUPON:
            print_place = []
            check.print[2].append(print_place)
        else:
            print_place = check.print[1]

        DISCOUNT = 0
        DISCOUNT_LINES = []
        POINTS = 0
        POINTS_LINES = []
        MARKS = 0
        MARKS_LINES = []
        for action_id, total in check.totals.items():
            name = check.action_names.get(f'{action_id}', f'акция {action_id}')
            discount = total.get('d')
            if discount:
                DISCOUNT += discount
                discount = round(discount/100, 2)
                DISCOUNT_LINES.append([name, discount])
            points = total.get('p-')
            if points:
                POINTS += points
                points = round(points/100, 2)
                POINTS_LINES.append([name, points])
            marks = total.get('m')
            if marks:
                MARKS += marks
                MARKS_LINES.append([name, marks])

        if DISCOUNT > 0:
            DISCOUNT = round(DISCOUNT/100, 2)
            print_place.append([TEXT_TEXT, 'СКИДКИ'])
            for name, discount in DISCOUNT_LINES:
                print_place.append([TEXT_TEXT, f'{discount} {name}'])
            print_place.append([TEXT_TEXT, f'ИТОГО {DISCOUNT}'])
        
        #if POINTS:
        #    headers.append([TEXT_TEXT, 'БАЛЛЫ'])
        #    БЫЛО = check.card_points
        #    #headers.append([TEXT_TEXT, f'БЫЛО {self.check_card_points}'])
        #    for name, points in POINTS_LINES:
        #        headers.append([TEXT_TEXT, f'-{points} {name}'])
        #    СТАЛО = БЫЛО - POINTS
        #    headers.append([TEXT_TEXT, f'ИТОГО {round(СТАЛО/100,2)}'])
        #    self.log(check, f'карта "{check.card_id}" баллов {СТАЛО} = {БЫЛО} - {POINTS}')

        if MARKS:
            print_place.append([TEXT_TEXT, 'ПОДАРОЧНЫЕ МАРКИ'])
            for name, marks in MARKS_LINES:
                print_place.append([TEXT_TEXT, f'{marks} {name}'])
            print_place.append([TEXT_TEXT, f'ИТОГО {MARKS}'])
        
        self.log(check, f'скидка {DISCOUNT} акций {len(DISCOUNT_LINES)} карта "{check.card_id}"')

#=============================================
# ThePage
#=============================================

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def tab_visible(self, tab_id):
        return tab_id in ['base_params']

    def набор_базовых_параметров(self):
        return [Action.PRINT_MODE]

    def settings_page(self):
        self.print_title()
        p = about(self)
        #p.href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {DESCRIPTION}')
        about(self)



