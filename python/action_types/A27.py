import flask, sqlite3, json, datetime, time
from domino.core import log
#from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
from .action_page import TheActionPage
#from discount.action_page import Наличие_карты_купона, Минимальное_количество_товаров
#from discount.action_page import Минимальная_сумма_чека
from domino.databases.sqlite import Sqlite 

from .action_base import ActionCalculator
from discount.series import Series, ТипКарты

from tables.sqlite.action_set_item import ActionSetItem
#from tables.sqlite.product_set import ГотовыйНабор

#=============================================
# Description
#=============================================

ID = 'A27'
PERCENT = True
SUPPLEMENT = True
FIXED_PRICE = True
DESCRIPTION = 'Скидка на комплексный набор (комплексный обед)'
ABOUT = '''
    Определяются список товарных наборов. Скидка начисляется на группу товаров
    при условии, что каждый товар входит в один из заданных товарных наборов.
    Это примерно так, как комплексный обед, когда скидка выдается если взяли 
    по одной позиции каждого блюда, входящего в комплексный обед.
    '''
       
def is_available():
    return True
def description(**args):
    return DESCRIPTION
def about(page):
    t = page.text_block('about')
    t.text(ABOUT)
    return t

class Комплексный_обед:
    class Item:
        def __init__(self, schema_worker, set_id):
            self.набор_товаров = schema_worker.готовый_набор(set_id)
        def __repr__(self):
            return f'{self.набор_товаров}'
    
    class Worker:
        class Item:
            def __init__(self, c_item):
                self.c_item = c_item
                self.counter = 0
                self.lines = []
                self.discount = 0
        
        def __init__(self, complex, discount):
            self.items = []
            self.discount = discount
            for c_item in complex.items:
                self.items.append(Комплексный_обед.Worker.Item(c_item))

        def __repr__(self):
            n = 0
            r = []
            for item in self.items:
                n += 1
                r.append(f'{n}:{len(item.lines)}:{item.counter}:{item.discount}')
            return ', '.join(r)

        def check_line(self, line):
            for item in self.items:
                if line in item.c_item.набор_товаров:
                    item.counter += line.count
                    item.lines.append(line)
                    return True
            return False

        def calc_discount(self):
            self.count = None
            for item in self.items:
                if self.count is None:
                    self.count = item.counter
                else:
                    self.count = min(self.count, item.counter)
            if self.count:
                for item in self.items:
                    item.discount = (self.count / item.counter) * self.discount

    def __init__(self, schema_worker, discount):
        self.schema_worker = schema_worker
        self.items = []
        self.discount = discount

    def append(self, set_id):
        self.items.append(Комплексный_обед.Item(self.schema_worker, set_id))

    def worker(self):
        return Комплексный_обед.Worker(self, self.discount)

    def __repr__(self):
        r = [f'КОМПЛЕКСНЫЙ НАБОР ИЗ {len(self.items)} БЛЮД :']
        for i in range(len(self.items)):
            r.append(f'{i} : {self.items[i]}')
        return ', '.join(r)

#=============================================
# Calculator
#=============================================

class Calculator(ActionCalculator):
    def __init__(self, worker, cursor, action, LOG, SQLITE):
        super().__init__(worker, cursor, action, LOG, SQLITE)
        self.процент_скидки = float(self.action.info.get(Action.ПРОЦЕНТНАЯ_СКИДКА, 0.0))

        self.complex = Комплексный_обед(self.worker, self.процент_скидки)

        sets = ActionSetItem.sets(SQLITE, self.action.id, ActionSetItem.ОСНОВНЫЕ_ТОВАРЫ)
        for set_id in sets:
            self.complex.append(set_id)

        #sql = "select set_id from action_set_item where action_id=? and type=?"
        #cursor.execute(sql, [self.action.ID, ActionSetItem.ОСНОВНЫЕ_ТОВАРЫ])
        #for set_id, in cursor.fetchall():
            #log.debug(f'КОМПЛЕКС {set_id}')
            #start = time.perf_counter()
            #self.complex.append(cursor, set_id)
            #LOG(f'{self}.набор {set_id}', start)

        self.создать_набор_исключенных_товаров(SQLITE, LOG)
        #self.создать_набор_основных_товаров(cursor, LOG)


        #log.debug(f'{self.complex}')
        
    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        complex = self.complex.worker()
 
        # формирование набора товаров
        for line in check.lines:
            if line.fixed_price:
                continue
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            complex.check_line(line)

        complex.calc_discount()

        #self.log(check, f'{complex}')

        if not complex.count:
            self.log(check, f'не найдено ни одного комплекс')
            return

        скидка_всего = 0
        count = 0
        for item in complex.items:
            for line in item.lines:
                count += 1
                скидка_всего += self.применить_скидку(line, item.discount, None)

        self.log(check, f'строк {count}, комплексов {complex.count}, скидка {скидка_всего}')

#=============================================
# Page
#=============================================
 
class Page(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def набор_базовых_параметров(self):
        return ['description', 'validity', 
            Action.ПОДРАЗДЕЛЕНИЕ,
            Action.ПРОЦЕНТНАЯ_СКИДКА,
            'excluded', 'округление_цены'
            ]

    def набор_дополнительных_условий(self):
        return [Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА, Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ, Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ЧЕКА]

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'weekdays', 'основные_товары']

    def settings_page(self):
        self.print_title()
        about(self)
        #self.print_base_params()
        #self.print_tab()
        self.print_tabs()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)

