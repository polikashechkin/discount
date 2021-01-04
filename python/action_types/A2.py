from .action_page import TheActionPage
from .action_base import ActionCalculator

from domino.core import log
from discount.actions import Action
import discount.actions
from discount.series import Series, ТипКарты
from discount.checks import TEXT_TEXT, TEXT_BOLD, TEXT_CODE
from discount.cards import Card, CardLog

ID = 'A2'
CLASS = 1
DESCRIPTION = 'Выдача подарочного купона'
ABOUT = '''
    Задается список товаров, участвующих в акции. Собственно премия (купон) 
    выдается в том случае, если общее количество (штук) проданных товаров из списка 
    превышает или равно заданному количеству (штук)
    '''

DEFAULT_PRINT_LINES = 5
SERIES_PARAM_ID = 'series_id'
COUNT_PARAM_ID = 'count'
SUMMA_PARAM_ID = 'summa'

#=============================================
# Description
#=============================================

def is_available():
    return True

def description():
    return DESCRIPTION

def about(page, to_detail = False):
    x = page.text_block()
    x.text(ABOUT)
    if to_detail:
        x.href('Подробнее ...', f'action_types/{ID}.description_page')
    return x

#=============================================
# Calculator
#=============================================

class Calculator(ActionCalculator):
    def __init__(self, application, cursor, action, LOG, SQLITE):
        super().__init__(application, cursor, action, LOG, SQLITE)
 
        if self.action.подарочный_купон is None:
            raise Exception(f'Не задан тип подарочного купона')

        self.тип_купона = ТипКарты.get(cursor, self.action.подарочный_купон)
        if self.тип_купона is None:
            raise Exception(f'Неизвестный тип подарочного купона "{self.action.подарочный_купон}"')
        self.наименование_купона = self.тип_купона.наименование
        self.класс_купона = self.card_types[self.тип_купона.type]

        self.создать_набор_исключенных_товаров(SQLITE, LOG)
        self.создать_набор_основных_товаров(SQLITE, LOG)

    def создать_и_активировать_купон(self, engine, card_type, check):
        card = Card.создать_подарочный_купон(engine, card_type, check = check)
        card.активировать(engine, card_type, check = check)
        return card

    def print_coupon(self, engine, check):
        action_info = check.processing.actions_info.get(self.action.id, {})
        coupon_id = action_info.get('coupon_id')
        if coupon_id is None:
            try:
                купон = self.создать_и_активировать_купон(engine, self.тип_купона, check)
                action_info['coupon_id'] = купон.ID
                check.processing.actions_info[self.action.id] = action_info
                self.print_check_lines(check, {f'{{КУПОН}}':купон.ID})
                self.log(check, f'выдача купона "{купон.ID}" {self.наименование_купона}')
            except BaseException as ex:
                log.exception(__name__)
                self.log(check, f'{ex}')
        else:
            #log.debug(f'self.print_check_lines')
            self.print_check_lines(check, {f'{{КУПОН}}':coupon_id})
            self.log(check, f'Повторная выдача купона "{coupon_id}"')
    
    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        # формирование набора товаров
        строки = []
        количество_товаров = 0
        уникальные_товары = set()
        сумма_товаров = 0.0
        for line in check.lines:
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            if not self.набор_товаров or line in self.набор_товаров: 
                строки.append(line)
                количество_товаров += line.count
                сумма_товаров += line.qty * line.price
                уникальные_товары.add(line.product)

        if len(строки) == 0:
            self.log(check, f'нет товаров')
            return
            
        # проверка дополнительных условий
        if self.минимальное_количество_товаров:
            if self.минимальное_количество_товаров > количество_товаров:
                self.log(check, f'недостаточное количество товаров')
                return
        if self.минимальная_сумма_товаров:
            if self.минимальная_сумма_товаров > сумма_товаров:
                self.log(check, f'недостаточная сумма товаров')
                return
        if self.минимальное_количество_уникальных_товаров:
            if self.минимальное_количество_уникальных_товаров > len(уникальные_товары):
                self.log(check, f'недостаточное количество уникальных товаров')
                return

        self.print_coupon(engine, check)

#=============================================
# Settings
#=============================================

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'params', 'weekdays', 'print']

    def набор_базовых_параметров(self):
        return [Action.ПОДРАЗДЕЛЕНИЕ,'description', 'validity', 'подарочный_купон', 'набор_товаров', 'excluded']

    def набор_дополнительных_условий(self):
        return [Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА,Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ, Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ЧЕКА]
    
    def print_macros(self):
        return [
            ['КУПОН', 'номер купона']
        ]

    def settings_page(self):
        self.print_title()
        about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)
        x = self.text_block().margin(1)
        x.header('Весовые и штучные товары')
        x.text('''
        Товары могут быть как весовыми, так и штучными. Понятие количество (штук) для них различаются.
        Для штучных товаров количество (штук) равно количесту в чеке. Например, если в чеке стоит
        товар = ЛОЖКА и количество = 5, то количество (штук) и есть 5.
        ''')
        x.newline()
        x.text('''Для весовых товаров - по другому.
        Каждая строка в чеке - одна позиция, вне зависимости от количества в чеке. Например, если в чеке 
        стоит товар = МОРКОВКА и количество = 5.340, то это количество (штук) равно 1
        ''')
        x = self.text_block().margin(1)
        x.header('Выделение весовых товаров')
        x.text('''Различаются весовые товары (товарные позиции) от штучных на основании 
        анализа значения количества в чеке. Если количество - целое чисто, то предполагается, что
        товар штучный, если нет - то весовой. 
        ''')

