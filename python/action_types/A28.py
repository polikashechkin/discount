import flask, sqlite3, json, datetime
from domino.core import log
from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action, ActionSetItem
from .action_page import TheActionPage, ActionTabControl
#from discount.action_page import Наличие_карты_купона, Минимальное_количество_товаров
#from discount.action_page import Минимальная_сумма_чека

from .action_base import ActionCalculator
from discount.series import Series, ТипКарты
from discount.product_sets import ProductSet

#=============================================
# Description
#=============================================

ID = 'A28'
PERCENT = True
DESCRIPTION = 'Постоянная процентная скидка'
ABOUT = '''
    Основное назначение данной акции - это задавать “долгоиграющие” процентные скидки, 
    которые можно трактовать как своеобразную распродажу товаров.Скидка задается 
    на подразделение и товар, и не зависит от состава чека. 
    Соответственно согласно данным скидкам можно  печатать ценники и этикетки на товар. 
    Диапазон действия скидки задается без времени.
    '''
SUPPLEMENT = False
FIXED_PRICE = True
FOR_SALE = True
       
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
        self.for_sale = True
        self.создать_набор_основных_товаров(SQLITE, LOG)
        self.создать_набор_исключенных_товаров(SQLITE, LOG)

    def calc(self, engine, чек):
        if чек.TYPE:
            self.log(чек, 'ВОЗВРАТ')
            return

        # формирование набора товаров
        lines = []
        for line in чек.lines:
            if line.fixed_price:
                continue
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            if self.набор_товаров is None or line in self.набор_товаров: 
                lines.append(line)

        if len(lines) == 0:
            self.log(чек, f'нет товаров')
            return

        # расчет скидки
        скидка_всего = 0.0
        for line in lines:
            скидка_всего += self.применить_скидку(line, self.процент_скидки, None)
            SALE_PRICE = self.округлить_в_копейках(int(line.price * (100 - self.процент_скидки)))
            if hasattr(line, 'SALE_PRICE'):
                line.SALE_PRICE = min(line.SALE_PRICE, SALE_PRICE)
            else:
                line.SALE_PRICE = SALE_PRICE

        #self.печать_в_чеке(чек, СКИДКА = скидка_всего)
        self.log(чек, f'строк {len(lines)}, скидка {скидка_всего}')

#=============================================
# Page
#=============================================
 
class Page(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def набор_базовых_параметров(self):
        return ['description', 'период_действия_упрощенный', Action.ПОДРАЗДЕЛЕНИЕ, Action.ПРОЦЕНТНАЯ_СКИДКА, 'набор_товаров', 
            'excluded', 'округление_цены'
            ]

    def набор_дополнительных_условий(self):
        return [Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА, Action.НАЛИЧИЕ_КАРТЫ_КУПОНА, 'наличие_ключевого_слова', Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ, Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ЧЕКА]

    def tab_visible(self, tab_id):
        return tab_id in ['base_params']

    def settings_page(self):
        self.print_title()
        about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        #self.print_base_params()
        #self.print_tab()
        self.print_tabs()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)
