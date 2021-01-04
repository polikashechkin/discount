import flask, sqlite3, json, datetime
from domino.core import log
#from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action, ActionSetItem
from .action_page import TheActionPage
#from discount.action_page import Наличие_карты_купона, Минимальное_количество_товаров
#from discount.action_page import Минимальная_сумма_чека

from .action_base import ActionCalculator
from discount.series import Series, ТипКарты
from discount.product_sets import ProductSet

#=============================================
# Description
#=============================================

ID = 'A19'
PERCENT = True
DESCRIPTION = 'Скидка по срокам годности'
ABOUT = '''
    На упакове товара может быть нанесен как штриховой код, так и QR код.
    Касса в любом случае "выуживает" из кода штриховой код и производит 
    поиск и идентификацию товара. Т.е. работа кассы не зависит от того, какой 
    код нанесен на упаковке. Но в отличие от штрихового кода (который сам по себе не несет смысловой нагрузки),
    QR код может иметь некоторое смысловое содержание. На основе анализа этого 
    содержания
    и формируется данная скидка.
    '''
SUPPLEMENT = False
FIXED_PRICE = True
       
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

        self.процент_скидки = float(self.action.info.get(Action.ПРОЦЕНТНАЯ_СКИДКА, 0.0))
        self.создать_набор_исключенных_товаров(SQLITE, LOG)
        self.создать_набор_основных_товаров(SQLITE, LOG)


    def calc(self, engine, чек):
        if чек.TYPE:
            self.log(чек, 'ВОЗВРАТ')
            return

        if self.шаблон_QR_кода is None:
            self.log(чек, f'не задан шаблон QR кода')
            return
        # формирование набора товаров
        строки = []
        for line in чек.lines:
            #log.debug(f'{self} {line.__dict__}')
            #log.debug(f'строка {строка.product} {строка.fixed_price}')
            if line.fixed_price:
                continue
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            # проверка на шаблон QR кода
            if not self.проверка_QR_кода(line): 
                continue

            if self.набор_товаров is None or line in self.набор_товаров: 
                строки.append(line)

        if len(строки) == 0:
            self.log(чек, f'нет товаров')
            return

        # расчет скидки
        скидка_всего = 0.0
        for строка in строки:
            скидка_всего += self.применить_скидку(строка, self.процент_скидки, None)

        self.печать_в_чеке(чек, СКИДКА = скидка_всего)
        self.log(чек, f'строк {len(строки)}, скидка {скидка_всего}')

#=============================================
# Page
#=============================================
 
class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def набор_базовых_параметров(self):
        return [Action.ШАБЛОН_QR_КОДА, 'description', 'validity', Action.ПРОЦЕНТНАЯ_СКИДКА, 'набор_товаров','excluded', 'округление_цены']

    def набор_дополнительных_условий(self):
        return []

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'print']

    def print_macros(self):
        return [
            ['СКИДКА', 'скидка по акции']
        ]

    def settings_page(self):
        self.print_title()
        about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tabs()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)
