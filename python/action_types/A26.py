import flask, sqlite3, json, datetime
from domino.core import log
from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
#from discount.action_page import TheActionPage, ActionParam
from .action_base import ActionCalculator
from .action_page import TheActionPage as BasePage
from discount.checks import TEXT_TEXT, TEXT_BOLD, TEXT_CODE, TEXT_EAN13

#=============================================
# Description
#=============================================

ID = 'A26'
CLASS = 2
DESCRIPTION = 'Печать итогов по взаиморасчетам за баллы'
ABOUT = '''
    Печать в чеке итогов по баллам, использованным и начисленным. Данная акция должна быть расположена 
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
        if self.print_mode == Action.print_mode_HEADER:
            print_place = check.print[0] 
        elif self.print_mode == Action.print_mode_FOOTER:
            print_place = check.print[1]
        elif self.print_mode == Action.print_mode_COUPON:
            print_place = []
            check.print[2].append(print_place)
        else:
            print_place = check.print[1]

        #self.log(check, f'НАЧАЛО')
        points_minus = []
        points_plus = []
        for action_id, total in check.totals.items():
            #self.log(check, f'{action_id} = {total}')
            points = total.get('p-')
            if points:
                points_minus.append([action_id, points])
            points = total.get('p+')
            if points:
                points_plus.append([action_id, points])

        if len(points_minus) or len(points_plus):
            print_place.append([TEXT_TEXT, 'БАЛЛЫ'])
            СТАЛО = БЫЛО = check.card_points
            #headers.append([TEXT_TEXT, f'БЫЛО {self.check_card_points}'])
            for action_id, points in points_minus:
                action_name = check.action_names.get(f'{action_id}', f'акция {action_id}')
                print_place.append([TEXT_TEXT, f'-{round(points/100, 2)} {action_name}'])
                СТАЛО -= points
            for action_id, points in points_plus:
                action_name = check.action_names.get(f'{action_id}', f'акция {action_id}')
                print_place.append([TEXT_TEXT, f'+{round(points/100, 2)} {action_name}'])
                СТАЛО += points
            print_place.append([TEXT_TEXT, f'ИТОГО {round(СТАЛО/100,2)}'])
            self.log(check, f'карта "{check.card_id}" было {БЫЛО}, стало {СТАЛО}')
        else:
            self.log(check, f'Нет операций с баллами')

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
        self.title(f'{ID}. {DESCRIPTION}')
        about(self)



