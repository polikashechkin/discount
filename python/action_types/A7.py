import sqlite3, json, datetime, re
from domino.core import log
from discount.actions import Action
from .action_page import TheActionPage
from .action_base import ActionCalculator
import discount.actions
import discount.series
#from discount.product_sets import ГотовыйНабор

ID = 'A7'
IS_AVAILABLE = False
CLASS = 1
DESCRIPTION = 'Скидка на набор, один бесплатно'
ABOUT = '''
    Данная акция действует на каждый товар из набора индивидуально.
    Набор товаров определяет список товаров, на которые действует 
    акция. Для КАЖДОГО товара, независимо от остальных, вычисляется количество подарков и в соответствии с этим
    выдается скидка.
    '''

FIXED_PRICE = True

#=============================================
# Description
#=============================================

def is_available():
    return True

def description(**args):
    return DESCRIPTION

def about(page):
    t = page.text_block()
    t.text(ABOUT)
    return t

#=============================================
# Calculator
#=============================================

class Набор:
    def __init__(self, action, размер_набора):
        self.action = action
        self.размер_набора = размер_набора
        self.строки = []
        self.количество_всего = 0
        self.сумма_всего = 0.0
        self.подарки = {}
    
    def добавить(self, строка):
        self.строки.append(строка)
        self.количество_всего += строка.count
        self.сумма_всего += строка.qty * строка.price
   
    def печать_подарков(self):
        msg = []
        for price, count in self.подарки.items():
            msg.append(f'{count}х{price}')
        return ' '.join(msg)
    
    def добавить_подарок(self, price, count):
        self.подарки[price] = self.подарки.get(price, 0) + count

    
    @property
    def всего_подарков(self):
        return int(self.количество_всего / self.размер_набора)
    
    @staticmethod
    def ключ_сортировки(строка):
        return f'{строка.price:010}:{строка.count:010}:{строка.id}'
    
    def строки_в_порядке_раздачи_подарков(self):
        return sorted(self.строки, key = Набор.ключ_сортировки)
    '''
    def выдать_подарки(self):
        общая_скидка = 0.0
        подарков = self.всего_подарков
        if подарков > 0:
            for строка in self.строки_в_порядке_раздачи_подарков():
                #self.log(check, f'подарков "{подарков}" "{строка.count}"')
                if подарков <= 0:
                    break
                if подарков >= строка.count:
                    #self.log(check, f'изменить цену "{подарков}" "{строка.count}"')
                    подарков -= строка.count 
                    общая_скидка += self.action.изменить_цену(строка, 0)
                else:
                    процент_скидки = (подарков / строка.count) * 100.0 
                    #self.log(check, f'изменить скидку "{процент_скидки}" "{строка.count}"')
                    self.action.изменить_скидку(строка, процент_скидки)
                    подарков -= строка.count
        return общая_скидка
    '''
    def суммовая_скидка_на_подарки(self):
        подарков = self.всего_подарков
        общая_скидка = 0.0
        if подарков > 0:
            процент = подарков / self.количество_всего * 100.0
            for строка in self.строки:
                общая_скидка += self.action.добавить_скидку(строка, процент)
        return общая_скидка

    '''
    def расчитать_суммовыю_скидку(self):
        скидка = 0.0
        подарков = self.всего_подарков
        if подарков > 0:
            for строка in self.строки_в_порядке_раздачи_подарков():
                #self.log(check, f'подарков "{подарков}" "{строка.count}"')
                if подарков <= 0:
                    break
                if подарков >= строка.count:
                    #self.log(check, f'изменить цену "{подарков}" "{строка.count}"')
                    подарков -= строка.count 
                    скидка += строка.qty * строка.price
                    self.добавить_подарок(строка.price, строка.count)
                else:
                    скидка += (строка.qty * строка.price) * подарков / строка.count 
                    self.добавить_подарок(строка.price, подарков)
        return скидка

    def суммовая_скидка_на_подарки(self):
        общая_скидка = 0.0
        суммовая_скидка = self.расчитать_суммовыю_скидку()
        процентая_скидка = суммовая_скидка / self.сумма_всего * 100.0
        if процентая_скидка > 0.0:
            for строка in self.строки:
                общая_скидка += self.action.добавить_скидку(строка, процентая_скидка)
        return общая_скидка
    '''


class Calculator(ActionCalculator):
    def __init__(self, application, cursor, action, LOG, SQLITE):
        super().__init__(application, cursor, action, LOG, SQLITE)

        self.count = self.action.формула_вычисления_подарка
        self.создать_набор_основных_товаров(SQLITE, LOG)

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        # Формируем список продуктов (нужных) и их число в штуках
        наборы = {}
        for line in check.lines:
            if self.набор_товаров and line in self.набор_товаров:
                набор = наборы.get(line.product)
                if набор is None:
                    набор = Набор(self, self.count)
                    наборы[line.product] = набор
                набор.добавить(line)
                #self.log(check, f'добавить "{line.product}", {line.count} {набор.строки}')

        общая_скидка = 0.0
        всего_подарков = 0
        количество_всего = 0
        for набор in наборы.values():
            количество_всего += набор.количество_всего
            скидка = набор.суммовая_скидка_на_подарки()
            всего_подарков += набор.всего_подарков
            общая_скидка += скидка
        #for c in counts.values():
        #    check.comment(f'{c.product} : {c.qty}({c.count}-{c.present}), {round(c.sum / c.qty, 2)}, {c.sum} : {round(c.discount * 100,2)}%, {round(c.new_price,2)}')
        if всего_подарков > 0:
            self.печать_в_чеке(check, СКИДКА = общая_скидка)
            self.log(check, f'скидка {общая_скидка}, товаров {количество_всего}, подарков {всего_подарков}')
        else:
            self.log(check,'нет подарков')

#=============================================
# Page
#=============================================
class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def набор_базовых_параметров(self):
        return ['description', 'validity', 'обязательный_набор_товаров','формула_вычисления_подарка', 'округление_цены']

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'print']

    def settings_page(self):
        self.print_title()
        about(self).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)
        p = self.text_block()
        p.header('Алгоритм')
        p.text('''
        Рассматривается наборы товаров. Для каждого набора индивидуально 
        вычисляется количество товаров в подарок. Вычисляется общая суммовая скидка,
        которая "размазывается" по всему набору.
        ''')
        p = self.text_block()
        p.header('Соотношение с другими акциями')
        p.text('''
        Игнорируется вся арифметика процентных акций.  Не имеет значения 
        красные цены.
        Акция всегда прибавляет заданную скидку. 
        ''')


