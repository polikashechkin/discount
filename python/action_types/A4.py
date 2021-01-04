import flask, sqlite3, json, datetime, time
from domino.core import log
from discount.actions import Action
from .action_page import TheActionPage
from .action_base import ActionCalculator 
import discount.series
#from discount.product_sets import ГотовыйНабор
from discount.series import CardType
from tables.sqlite.action_set_item import ActionSetItem
#from tables.sqlite.product_set import ГотовыйНабор

ID = 'A4'
CLASS = 0
#PERCENT = True
DESCRIPTION = 'Процентная скидка на сопутствующие товары'
ABOUT = '''
    При покупке каких то товаров из заданного набора (ОСНОВНЫХ) товаров, на товары
    определяемые набором СОПУТСТВУЮЩИХ товаров выдается процентная скида в соответствие
    с заданным "соотношением основных и сопутствующих товаров".
    Если задан параметр "минимальная цена товаров", то в список ОСНОВНЫХ товаров попадают только те товары
    из набора, для которых розничная цена больше или равна заданной цены.
    '''
IS_AVAILABLE = True
IS_TAX_DISCOUNT = True

SUPPLEMENT = True
FIXED_PRICE = True

#=============================================
# Info
#=============================================

def is_available():
    return True

def description():
    return DESCRIPTION

def about(page, to_datail = False):
    x = page.text_block()
    x.text(ABOUT)
    if to_datail:
        x.href('Подробнее...',f'action_types/{ID}.description_page')
    return x

#=============================================
# Calculator
#=============================================
class Calculator(ActionCalculator): 
    def __init__(self, worker, cursor, action, LOG, SQLITE):
        super().__init__(worker, cursor, action, LOG, SQLITE)

        self.процент = float(self.action.info.get(Action.ПРОЦЕНТНАЯ_СКИДКА, 0.0))

        self.создать_набор_основных_товаров(SQLITE, LOG)
        self.создать_набор_исключенных_товаров(SQLITE, LOG)
        self.создать_набор_сопутствующих_товаров(SQLITE)

        #sets = ActionSetItem.sets(SQLITE, self.action.id, ActionSetItem.СОПУТСТВУЮЩИЕ_ТОВАРЫ)
        #self.сопутствующие_товары = self.worker.готовый_набор(sets, name='Сопутствующие товары')
        #self.сопутствующие_товары = ГотовыйНабор.create(SQLITE, sets, LOG=LOG, name='Сопутствующие товары')
        #LOG(f'{self}.сопутствующие_товары', start)

        self.ОСНОВНЫХ_ТОВАРОВ = 1
        self.СОПУСТВТВУЮЩИХ_ТОВАРОВ = None
        self.соотношение_основных_и_сопутствующих = self.action.info.get(Action.КОЛИЧЕСТВО_СОПУТСТВУЮЩИХ_ТОВАРОВ, 0)
        if self.соотношение_основных_и_сопутствующих:
            if self.соотношение_основных_и_сопутствующих > 0:
                self.ОСНОВНЫХ_ТОВАРОВ = 1
                self.СОПУСТВТВУЮЩИХ_ТОВАРОВ = self.соотношение_основных_и_сопутствующих
            else:
                self.ОСНОВНЫХ_ТОВАРОВ = -1 * self.соотношение_основных_и_сопутствующих
                self.СОПУСТВТВУЮЩИХ_ТОВАРОВ = 1

        #self.минимальная_цена_товаров = float(self.action.info.get('минимальная_цена_товаров', 0))


    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        #self.log(check, f'Минимальная сумма чека : {self.минимальная_сумма_чека}')
        if self.сопутствующие_товары is None:
            self.log(check, 'не заданы сопутствующие товары')
            return
        
        # проверка наличия основных товаров
        количество_основных_товаров = 0
        уникальные_товары = set()
        сумма_товаров = 0.0
        for line in check.lines:
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            if self.набор_товаров and line not in self.набор_товаров:
                continue
            #if self.минимальная_цена_товаров:
            #    #self.log(check, f'{line.price} < {self.минимальная_цена_товаров} = {line.price < self.минимальная_цена_товаров}')
            #    if line.price < self.минимальная_цена_товаров:
            #        continue
            количество_основных_товаров += line.count
            сумма_товаров += line.qty * line.price
            уникальные_товары.add(line.product)

        if количество_основных_товаров == 0:
            self.log(check, f'нет основных товаров')
            return

        # проверка дополнительных условий
        if self.минимальное_количество_товаров:
            if self.минимальное_количество_товаров > количество_основных_товаров:
                self.log(check, f'недостаточное количество основных товаров {количество_основных_товаров} нужно {self.минимальное_количество_товаров}')
                return
        if self.минимальная_сумма_товаров:
            if self.минимальная_сумма_товаров > сумма_товаров:
                self.log(check, f'недостаточная сумма основных товаров')
                return
        if self.минимальное_количество_уникальных_товаров:
            if self.минимальное_количество_уникальных_товаров > len(уникальные_товары):
                self.log(check, f'недостаточное количество уникальных основных товаров {len(уникальные_товары)} нужно {self.минимальное_количество_уникальных_товаров}')
                return
        # получаем количество сопутствующих товаров
        if self.СОПУСТВТВУЮЩИХ_ТОВАРОВ:
            максимальное_количество_сопутствующих_товаров = int (количество_основных_товаров / self.ОСНОВНЫХ_ТОВАРОВ) * self.СОПУСТВТВУЮЩИХ_ТОВАРОВ
            #self.log(check, f'{максимальное_количество_сопутствующих_товаров} = int ({количество_основных_товаров} / {self.ОСНОВНЫХ_ТОВАРОВ}) * {self.СОПУСТВТВУЮЩИХ_ТОВАРОВ}')
        else:
            максимальное_количество_сопутствующих_товаров = None
        # список строки, содержащих сопутствующие товары
        lines = []
        for line in check.lines:
            if line.fixed_price:
                continue
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            if line not in self.сопутствующие_товары:
                continue
            lines.append(line)
        
        if len(lines) == 0:
            self.log(check, f'нет сопутствующих товаров')
            return

        # применить скидку {процент} 
        СКИДКА = 0.0
        сопутствующих = 0
        if self.СОПУСТВТВУЮЩИХ_ТОВАРОВ:
            count = максимальное_количество_сопутствующих_товаров
            for line in lines:
                if line.count <= count:
                    сопутствующих += line.count
                    СКИДКА += self.применить_скидку(line, self.процент, None)
                    count -= line.count
                    if count == 0:
                        break 
                else:
                    сопутствующих += count
                    процент_на_строку = self.процент * count / line.count
                    СКИДКА += self.применить_скидку(line, процент_на_строку, None)
                    break
        else:
            for line in lines:
                сопутствующих += line.count
                СКИДКА += self.применить_скидку(line, self.процент, None)
        
        # печать результатов
        self.log(check, f'основных {количество_основных_товаров} => сопутствующих {максимальное_количество_сопутствующих_товаров} из ({len(lines)}) : строк {сопутствующих} скидка {СКИДКА} {self.процент}%')
        self.печать_в_чеке(check, СКИДКА=СКИДКА)

#=============================================
# Page
#=============================================

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)
    def набор_базовых_параметров(self):
        return [Action.ПОДРАЗДЕЛЕНИЕ, Action.КОЛИЧЕСТВО_СОПУТСТВУЮЩИХ_ТОВАРОВ, 'description', 'validity', 'основные_товары', 'excluded', 'сопутствующие_товары', Action.ПРОЦЕНТНАЯ_СКИДКА, 'округление_цены']
    def набор_дополнительных_условий(self):
        return [Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА,Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ, Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА, Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ЧЕКА, Action.МИНИМАЛЬНАЯ_СУММА_ТОВАРОВ]
        #return ['-минимальная_цена_товаров', Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ, Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ЧЕКА]
    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'params', 'weekdays']
    def print_macros(self):
        return [
            ['СКИДКА', 'размер скидки']
        ]
    def settings_page(self):
        self.print_title()
        about(self, False)
        #self.print_base_params()
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)
