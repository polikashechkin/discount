import sqlite3, os, datetime, re, arrow, math, time
from domino.core import log
from discount.actions import Action, ДеньНедели
from discount.series import Series, ТипКарты
from discount.core import DISCOUNT_DB, SCHEMES_FOLDER
from discount.checks import TEXT_TEXT
from discount.checks import Check

#from discount.product_sets import ГотовыйНабор, ProductSetItem, ProductSet
from tables.sqlite.product_set import ProductSet
#from tables.sqlite.product_set import ГотовыйНабор, ProductSet
from tables.sqlite.action_set_item import ActionSetItem

class PrintLineFormatter:
    def __init__(self, values = {}):
        self.r = re.compile('|'.join(values))
        self.values = values

    def _sub(self, match):
        return self.values.get(match.group(0))

    def format(self, text):
        return self.r.sub(self._sub, text)
class _PrintLineFormatter:
    def __init__(self, values = {}):
        self.values = values

    def format(self, text):
        for name, value in self.values.items():
            text = text.replace(name, value)
        return text
class PrintLine:
    def __init__(self, action, line):
        self.type = action.info.get(f'line_type_{line}', TEXT_TEXT)
        self.text = action.info.get(f'line_text_{line}', '')

class ActionCalculator:
    def __init__(self, worker, cursor, action, LOG, SQLITE):
        self.worker = worker
        self.action = action
        self.card_types = worker.card_types
        self.action_types = worker.action_types
        self.for_sale = False
        self.dept_code = self.action.info.get(Action.ПОДРАЗДЕЛЕНИЕ)
        self.start_date = self.action.start_date
        self.end_date = self.action.end_date

        self.print_lines_count = self.action.print_lines_count
        self.print_mode = self.action.print_mode
        self.print_lines = []
        for line in range(0, self.print_lines_count):
            self.print_lines.append(PrintLine(self.action, line))

        self.ограничение_по_дням_недели = self.action.ограничение_по_дням_недели
        self.fixed_price = self.action.fixed_price
        #self.дополнительная_скидка = self.action.supplement
        self.supplement = self.action.supplement
        self.округление = self.action.округление

        self.минимальная_сумма_чека = float(self.action.info.get(Action.МИНИМАЛЬНАЯ_СУММА_ЧЕКА, 0.0)) 
        if self.минимальная_сумма_чека <= 0.0 :
            self.минимальная_сумма_чека = None
        self.способ_вычисления_суммы_чека = self.action.info.get(Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА)

        self.минимальное_количество_товаров = float(self.action.info.get(Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ, 0.0)) 
        if self.минимальное_количество_товаров <= 0.0 :
            self.минимальное_количество_товаров = None

        self.минимальное_количество_уникальных_товаров = float(self.action.info.get(Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ, 0.0)) 
        if self.минимальное_количество_уникальных_товаров <= 0.0 :
            self.минимальное_количество_уникальных_товаров = None

        self.минимальная_сумма_товаров = float(self.action.info.get(Action.МИНИМАЛЬНАЯ_СУММА_ТОВАРОВ, 0.0))
        if self.минимальная_сумма_товаров <= 0.0:
            self.минимальная_сумма_товаров = None

        self.минимальная_цена_товаров = float(self.action.info.get('минимальная_цена_товаров', 0.0))
        if self.минимальная_цена_товаров <= 0.0:
            self.минимальная_цена_товаров = None

        #self.создать_набор_исключенных_товаров(cursor, LOG)
        #self.создать_набор_основных_товаров(cursor, LOG)
        
        self.наличие_карты_купона = self.action.info.get(Action.НАЛИЧИЕ_КАРТЫ_КУПОНА)
        if self.наличие_карты_купона is not None:
            try:
                self.наличие_карты_купона = ТипКарты.get(cursor, int(self.наличие_карты_купона))
            except:
                log.exception('НАЛИЧИЕ КАРТЫ КУПОНА')
                self.наличие_карты_купона = None
        
        self.ключевое_слово = self.action.info.get(Action.КЛЮЧЕВОЕ_СЛОВО)
        if self.ключевое_слово is not None:
            self.ключевое_слово = self.ключевое_слово.strip().upper()
            if self.ключевое_слово == '':
                self.ключевое_слово = None
        self.ШАБЛОН_QR_КОДА = self.action.info.get(Action.ШАБЛОН_QR_КОДА)
        if self.ШАБЛОН_QR_КОДА:
            self.шаблон_QR_кода = re.compile(self.ШАБЛОН_QR_КОДА, flags=re.IGNORECASE)
        else:
            self.шаблон_QR_кода = None
    
        self.исключенные_товары = None
        self.набор_товаров = None
        self.сопутствующие_товары = None

    def создать_набор_исключенных_товаров(self, SQLITE, LOG):
        sets = ActionSetItem.sets(SQLITE, self.action.ID, ActionSetItem.ИСКЛЮЧЕННЫЕ_ТОВАРЫ)
        sets.append(ProductSet.ПОСТОЯННО_ИСКЛЮЧЕННЫЕ_ТОВАРЫ_ID)
        self.исключенные_товары = self.worker.готовый_набор(sets, name = 'Исключенные товары')
        return self.исключенные_товары

    def создать_набор_основных_товаров(self, SQLITE, LOG):
        sets = ActionSetItem.sets(SQLITE, self.action.ID, ActionSetItem.ОСНОВНЫЕ_ТОВАРЫ)
        self.набор_товаров = self.worker.готовый_набор(sets, name = 'Основные товары')
        return self.набор_товаров

    def создать_набор_сопутствующих_товаров(self, SQLITE):
        sets = ActionSetItem.sets(SQLITE, self.action.id, ActionSetItem.СОПУТСТВУЮЩИЕ_ТОВАРЫ)
        self.сопутствующие_товары = self.worker.готовый_набор(sets, name='Сопутствующие товары')
        return self.сопутствующие_товары

    def проверка_QR_кода(self, line):
        if self.шаблон_QR_кода is None:
            self.log(line.check, f'проверка_QR_кода : True')
            return True
        if line.barcode is None:
            self.log(line.check, f'проверка_QR_кода : False')
            return False
        r = bool(self.шаблон_QR_кода.search(line.barcode))
        self.log(line.check, f'проврка_QR_кода : {r} : "{line.barcode}" : "{self.ШАБЛОН_QR_КОДА}"')
        return r

    def to_float(self, value, default = None):
        try:
            return float(value)
        except:
            return default
    def to_int(self,value, default = None):
        try:
            return int(value)
        except:
            return default
    def найти_первую_карту_по_типу(self, check, TYPE):
        if TYPE is not None:
            for card_info in check.cards.values():
                card = card_info.get(Check.CARD_CARD)
                if card and card.TYPE == TYPE:
                    return card
        return None
    def найти_карту_по_типу(self, чек, тип_карты_ID):
        return self.найти_первую_карту_по_типу(чек, тип_карты_ID)
    def log(self, check, msg = ''):
        #check.log.write(self.action.id, msg)
        check.write_log(self.action.id, msg)

    def добавить_суммовую_скидку(self, строки, сумма, скидка, card_ID, use_points = False):
        процент = скидка / сумма * 100.0
        итоговая_скидка = 0.0
        for строка in строки:
            итоговая_скидка += self.добавить_скидку(строка, процент, card_ID, use_points)
        return итоговая_скидка

    def умножить_скидку(self, строка, action_id, коэффициент):
        if not строка.actions_exists: 
            return 0.0
        action = строка.get_action(action_id)
        if action is None:
            return 0.0

        текущая_скидка_по_акции = action[Check.LINE_ACTION_DISCOUNT]
        уменьшение_цены = round(текущая_скидка_по_акции / строка.qty * (коэффициент - 1.0), 2)
        новая_цена = строка.final_price - уменьшение_цены
        
        if новая_цена < строка.min_price:
            новая_цена = строка.min_price
        if новая_цена >= строка.final_price:
            return 0.0
        выданная_скидка = (строка.final_price - новая_цена) * строка.qty
        строка.final_price = новая_цена
        action[Check.LINE_ACTION_DISCOUNT] += выданная_скидка
        return выданная_скидка

    def применить_скидку(self, строка, процент_скидки, card_id= None):
        if self.supplement:
            return self.добавить_скидку(строка, процент_скидки, card_id)
        else:
            return self.изменить_скидку(строка, процент_скидки, card_id)

    def добавить_скидку(self, строка, процент_скидки, card_id= None, use_points = False):
        if not строка.actions_exists:
            return self.изменить_скидку(строка, процент_скидки, card_id, use_points)
        else:
            #уменьшение_цены = round(строка.price * процент_скидки / 100.0, 2)
            уменьшение_цены = строка.price * процент_скидки / 100.0
            новая_цена = self.округлить(строка.final_price - уменьшение_цены)
            if новая_цена < строка.min_price:
                новая_цена = строка.min_price

            реальное_уменьшение_цены = round(строка.final_price - новая_цена, 2)
            if реальное_уменьшение_цены > 0.0:
                выданная_скидка = реальное_уменьшение_цены * строка.qty
                строка.final_price = новая_цена
                строка.add_discount(self.action.id, round(выданная_скидка,2), card_id, use_points)
                return выданная_скидка
            else:
                return 0.0

    def изменить_скидку(self, строка, размер_скидки, card_id = None, use_points = False):
        if not размер_скидки:
           размер_скидки = 0.0 
        if размер_скидки < 0.0 : 
            размер_скидки = 0.0
        if размер_скидки > 100.0 : 
            размер_скидки = 100.0
        #новая_цена = round(строка.price * (1 - размер_скидки / 100.0), 2)
        PRICE = int(строка.price * 100)
        NEW_PRICE = int(self.округлить(строка.price * (1 - размер_скидки / 100.0))*100)
        #log.debug(f'изменить_скидку({PRICE} * {размер_скидки} = {NEW_PRICE})')
        return self.изменить_цену_I(строка, NEW_PRICE, card_id, use_points)
  
    def __изменить_скидку(self, строка, размер_скидки, card_id = None, use_points = False):
        if размер_скидки < 0.0 : 
            размер_скидки = 0.0
        if размер_скидки > 100.0 : 
            размер_скидки = 100.0
        #новая_цена = round(строка.price * (1 - размер_скидки / 100.0), 2)
        новая_цена = self.округлить(строка.price * (1 - размер_скидки / 100.0))
        return self.изменить_цену(строка, новая_цена, card_id, use_points)
 
    def округлить_в_копейках(self, x):
        if self.округление == 10000: # до рублей
            return int(x/100) * 100
        elif self.округление == 100000: # до 10 рублей
            return int(x/1000) * 10000
        elif self.округление == 1000000: # до 100 рублей
            return int(x/10000) * 10000
        else: # до копеек
            return x

    def округлить(self, x):
        if self.округление == 10000:
            return math.floor(x)
        elif self.округление == 100000:
            return math.floor(x/10) * 10
        elif self.округление == 1000000:
            return math.floor(x/100) * 100
        else:
            return int(x * 100) / 100.0

    def изменить_цену_I(self, строка, NEW_PRICE, card_id = None, use_points = False):
        PRICE = int(строка.price * 100)
        FINAL_PRICE = int(строка.final_price * 100) if строка.final_price else 0
        #log.debug(f'изменить_цену_I(PRICE={PRICE}, NEW_PRICE={NEW_PRICE}, FINAL_PRICE={FINAL_PRICE}')

        строка.fixed_price = self.fixed_price
        # Нельзя уменьшать уже выданную скидку (увеличить цену)
        if FINAL_PRICE and NEW_PRICE >= FINAL_PRICE:
            return 0
        FINAL_PRICE = NEW_PRICE
        DISCOUNT = int(строка.qty * (PRICE - FINAL_PRICE))
        #log.debug(f'DISCOUNT = {DISCOUNT}')
        строка.final_price = round(FINAL_PRICE/100, 2)
        скидка = round(DISCOUNT / 100, 2)

        #log.debug(f'скидка = {скидка} строка.final_price = {строка.final_price}')
        строка.change_discount(self.action.id, скидка, card_id, use_points)
        return скидка

    def изменить_цену(self, строка, новая_цена, card_id = None, use_points = False):
        строка.fixed_price = self.fixed_price

        # Нельзя уменьшать уже выданную скидку (увеличить цену)
        if строка.final_price is not None and новая_цена >= строка.final_price: 
            return 0.0
        строка.final_price = новая_цена

        скидка = round(строка.qty * (строка.price - строка.final_price), 2)
        строка.change_discount(self.action.id, скидка, card_id, use_points)
        return скидка

    def проверка_периода_действия(self, date, check = None):
        date = arrow.get(date)
        if self.start_date:
            if date < self.start_date:
                if check:
                    self.log(check, f'Раньше начала действия акции')
                return False
        if self.end_date:
            if self.end_date.hour == 0 and self.end_date.minute == 0:
                if date.date() > self.end_date.date():
                    if check:
                        self.log(check, f'Позже окончания действия акции')
                    return False
            else:
                if date > self.end_date:
                    if check:
                        self.log(check, f'Позже окончания действия акции')
                    return False
        return True

    def check_base_conditions(self, check):
        if self.dept_code:
            if self.dept_code != check.dept_code:
                self.log(check, f'не то подразделение')
                return False
        date = check.date
        if not self.проверка_периода_действия(date, check):
            return False

        if self.ограничение_по_дням_недели.есть:
            день = date.weekday()
            наименование = ДеньНедели.наименование(день)
            день_недели = self.ограничение_по_дням_недели[день]
            if день_недели is None:
                self.log(check, f'Недопустимый деь недели "{наименование}"')
                return False
            else:
                if день_недели.начало.defined:
                    if date.time() < день_недели.начало.time():
                        self.log(check, f'Раньше времени "{наименование}" "{день_недели.начало}"')
                        return False
                if день_недели.окончание.defined:
                    if date.time() > день_недели.окончание.time():
                        self.log(check, f'Позже времени "{наименование}" "{день_недели.окончание}"')
                        return False
        
        if self.минимальная_сумма_чека is not None:
            сумма_чека = 0
            if self.способ_вычисления_суммы_чека == '+E':
                for line in check.lines:
                    if self.сопутствующие_товары and line in self.сопутствующие_товары:
                        continue
                    сумма_чека += (line.qty * line.price)
            elif self.способ_вычисления_суммы_чека == 'D':
                for line in check.lines:
                    if self.исключенные_товары and line in self.исключенные_товары:
                        continue
                    if self.сопутствующие_товары and line in self.сопутствующие_товары:
                        continue
                    сумма_чека += (line.qty * (line.final_price if line.final_price else line.price))
            elif self.способ_вычисления_суммы_чека == 'D+E':
                for line in check.lines:
                    if self.сопутствующие_товары and line in self.сопутствующие_товары:
                        continue
                    сумма_чека += (line.qty * (line.final_price if line.final_price else line.price))
            else:
                for line in check.lines:
                    if self.исключенные_товары and line in self.исключенные_товары:
                        continue
                    if self.сопутствующие_товары and line in self.сопутствующие_товары:
                        continue
                    сумма_чека += (line.qty * line.price)

                #self.log(check, f'{сумма_чека} += ({line.qty} * {line.price}) {line.product}')
            #self.log(check, f'минимально необходимая рзничная сумма чека : {self.минимальная_сумма_чека} : {сумма_чека}')

            if сумма_чека < self.минимальная_сумма_чека :
                self.log(check, f'недостаточная сумма чека {сумма_чека}, нужно {self.минимальная_сумма_чека}')
                return False

        if self.наличие_карты_купона is not None:
            for card_info in check.cards.values():
                card = card_info.get(Check.CARD_CARD)
                if card is not None and card.TYPE == self.наличие_карты_купона.ID:
                    break
            else:
                self.log(check, f'нет карты {self.наличие_карты_купона.полное_наименование}')
                return False
        # проверка на наличие ключевого слова
        if self.ключевое_слово:
            if not check.keyword or self.ключевое_слово != check.keyword:
                self.log(check, f'отсутствует ключевое слово "{self.ключевое_слово}"')
                return False
        #
        return True
    def печать_в_чеке(self, check, **kwargs):
        values = {}
        for key, value in kwargs.items():
            values[f'{{{key}}}'] = f'{value}'
        self.print_check_lines(check, values)
    def print_check_lines(self, check, values = {}):
        formatter = PrintLineFormatter(values)
        if len(self.print_lines) > 0:
            if self.print_mode == Action.print_mode_HEADER:
                headers = check.print[0] 
                for line in self.print_lines:
                    TYPE = line.type
                    TEXT = formatter.format(line.text)
                    headers.append([TYPE, TEXT])
            elif self.print_mode == Action.print_mode_FOOTER:
                footers = check.print[1]
                for line in self.print_lines:
                    TEXT = formatter.format(line.text)
                    TYPE = line.type
                    footers.append([TYPE, TEXT])
            elif self.print_mode == Action.print_mode_COUPON:
                coupon = []
                check.print[2].append(coupon)
                for line in self.print_lines:
                    TEXT = formatter.format(line.text)
                    TYPE = line.type
                    coupon.append([TYPE, TEXT])
        return len(self.print_lines)
    def calc(self, cur, check):
        pass
    def get_keywords(self, keywords, check):
        if self.ключевое_слово:
            keywords.append(self.ключевое_слово)
    def __str__(self):
        return f'<ActionWorker {self.action.type},{self.action.id}>'

class ActionAcceptor:
    def __init__(self, worker, cursor, action, LOG, SQLITE):
        self.worker = worker
        self.action = action
        #LOG(f'{self}')
        self.card_types = worker.card_types
        self.action_types = worker.action_types

        self.dept_code = self.action.info.get(Action.ПОДРАЗДЕЛЕНИЕ)

        self.start_date = self.action.start_date
        self.end_date = self.action.end_date

        self.набор_товаров = None
        self.исключенные_товары = None
        self.сопутствующие_товары = None

    def создать_набор_исключенных_товаров(self, SQLITE, LOG):
        sets = ActionSetItem.sets(SQLITE, self.action.ID, ActionSetItem.ИСКЛЮЧЕННЫЕ_ТОВАРЫ)
        sets.append(ProductSet.ПОСТОЯННО_ИСКЛЮЧЕННЫЕ_ТОВАРЫ_ID)
        self.исключенные_товары = self.worker.готовый_набор(sets, name='Исключенные товары')
        return self.исключенные_товары

    def создать_набор_основных_товаров(self, SQLITE, LOG):
        sets = ActionSetItem.sets(SQLITE, self.action.ID, ActionSetItem.ОСНОВНЫЕ_ТОВАРЫ)
        self.набор_товаров = self.worker.готовый_набор(sets, name='Основные товары')
        return self.набор_товаров
    def создать_набор_сопутствующих_товаров(self, SQLITE):
        sets = ActionSetItem.sets(SQLITE, self.action.id, ActionSetItem.СОПУТСТВУЮЩИЕ_ТОВАРЫ)
        self.сопутствующие_товары = self.worker.готовый_набор(sets, name='Сопутствующие товары')
        return self.сопутствующие_товары
 
    def log(self, check, msg):
        check.write_log(self.action.id, msg)

    def check_base_conditions(self, check):
        if self.dept_code:
            if self.dept_code != check.dept_code:
                self.log(check, f'не то подразделение')
                return False

        if self.start_date is not None:
            if check.date.date() < self.start_date:
                check.log.write(self.action.id, f'{check.date} меньше чем {self.start_date}')
            return False
        if self.end_date is not None:
            if check.date.date() > self.end_date:
                check.log.write(self.action.id, f'{check.date} больше чем {self.end_date}')
            return False
        return True

    def найти_карту_по_типу(self, check, TYPE):
        for card_info in check.cards.values():
            card = card_info.get(Check.CARD_CARD)
            if card and card.TYPE == TYPE:
                return card
        return None

    def __str__(self):
        return f'<ActionWorker {self.action.type},{self.action.id}>'

