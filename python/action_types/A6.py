import json, datetime
from domino.core import log
from discount.actions import Action
from .action_base import ActionCalculator
from .action_page import TheActionPage
#from discount.product_sets import ГотовыйНабор


ID = 'A6'
#IS_AVAILABLE = False
CLASS = 1
DESCRIPTION = 'Скидка на набор по типу N+1 (один в подарок)'
ABOUT = '''
    Просматривается чек, все товары сортируются по цене. 
    Просматриваются товары, начиная с самых дорогих и разбиваются на группы по N товаров.
    Каждая группа обрабатывается отдельно.
    Для каждой группы скидка (суммовая) равна стоимости самого дешевого товара.
    Скидка равномерно распределяется по всем товарам в группе сокруглением в пользу 
    покупателя с точностью до копеек
    '''
FIXED_PRICE = True

#=============================================
# Calculator
#=============================================

class Набор:
    def __init__(self, action, check, размер_набора):
        self.action = action
        self.check = check
        self.размер_набора = размер_набора
        self.строки = []
        self.количество_всего = 0
        self.сумма_всего = 0.0
        self.подарки = {}

    def log(self, msg):
        self.action.log(self.check, msg)
    
    def печать_подарков(self):
        msg = []
        for price, count in self.подарки.items():
            msg.append(f'{count}х{price}')
        return ' '.join(msg)
    
    def добавить(self, строка):
        self.строки.append(строка)
        self.количество_всего += строка.count
        self.сумма_всего += строка.qty * строка.price

    def добавить_подарок(self, price, count):
        self.подарки[price] = self.подарки.get(price, 0) + count

    
    @property
    def всего_подарков(self):
        return int(self.количество_всего / self.размер_набора)
    
    @staticmethod
    def ключ_сортировки(строка):
        return f'{строка.price:010}:{строка.count:010}:{строка.ID}'
    
    def строки_в_порядке_раздачи_подарков(self):
        return sorted(self.строки, key = Набор.ключ_сортировки, reverse=False)

    def выдать_подарки(self):
        выданная_скидка = 0.0
        подарков = self.всего_подарков
        if подарков > 0:
            for строка in self.строки_в_порядке_раздачи_подарков():
                #self.log(f'продукт "{строка.product}", количество "{строка.count}" цена "{строка.price}", подарков "{подарков}"')
                if подарков <= 0:
                    break
                if подарков >= строка.count:
                    процентая_скидка = подарков / строка.count * 100.0
                    выданная_скидка += self.action.добавить_скидку(строка, процентая_скидка)
                    #self.log(f'{выданная_скидка} = {процентая_скидка}')
                else:
                    процентая_скидка = (подарков / строка.count) * 100.0 
                    выданная_скидка += self.action.добавить_скидку(строка, процентая_скидка)
                    #self.log(f'{выданная_скидка} = {процентая_скидка}')
                    подарков -= строка.count
        return выданная_скидка

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
                    break
        return скидка

    def сделать_суммовую_скидку(self, суммовая_скидка):
        общая_скидка = 0.0
        #суммовая_скидка = self.расчитать_суммовыю_скидку()
        процентая_скидка = суммовая_скидка / self.сумма_всего * 100.0
        if процентая_скидка > 0.0:
            for строка in self.строки:
                общая_скидка += self.action.добавить_скидку(строка, процентая_скидка)
        return общая_скидка

class Calculator(ActionCalculator):
    def __init__(self, application, cursor, action, LOG, SQLITE):
        super().__init__(application, cursor, action, LOG, SQLITE)
        self.count = self.action.формула_вычисления_подарка
        self.создать_набор_основных_товаров(SQLITE, LOG)

    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return

        if self.набор_товаров is None:
            self.log(check, f'не определен набор товаров')
            return 

        # Формируем список продуктов (нужных) и их число в штуках
        набор = Набор(self, check, self.count)

        #product_lines = [] # строки с нужными товарами
        #product_count = 0 # количество товаров
        #gifts = 0 # количество подарков
        #gifts_sum = 0 # общая сумма подарков

        for line in check.lines:
            if line in self.набор_товаров:
                #product_lines.append(line)
                #product_count += line.count
                набор.добавить(line)
                #self.log(check, f'добавить "{line.product}", {line.count} {набор.строки} {набор.сумма_всего}')

        всего_подарков = набор.всего_подарков
        if всего_подарков > 0:
            общая_суммовая_скидка = набор.расчитать_суммовыю_скидку()
            #self.log(check, f'общая_суммовая_скидка = {общая_суммовая_скидка}')
            #выданная_скидка_1 = набор.выдать_подарки()
            #self.log(check, f'выданная_скидка = {выданная_скидка}')
            #остаточная_суммовая_скидка = общая_суммовая_скидка - выданная_скидка_1
            #self.log(check, f'остаточная_суммовая_скидка = {остаточная_суммовая_скидка}')
            выданная_скидка = набор.сделать_суммовую_скидку(общая_суммовая_скидка)
            #выданная_скидка = выданная_скидка_1 + выданная_скидка_2
            #self.log(check, f'выданная_скидка = {выданная_скидка}')
        #for c in counts.values(]'):
        #    check.comment(f'{c.product} : {c.qty}({c.count}-{c.present}), {round(c.sum / c.qty, 2)}, {c.sum} : {round(c.discount * 100,2)}%, {round(c.new_price,2)}')
            #self.print_check_lines(check, {'{СКИДКА}':str(общая_скидка)})
            self.log(check, f'скидка {round(выданная_скидка,2)}, товаров {набор.количество_всего}, подарков {всего_подарков} ({набор.печать_подарков()})')
        else:
            self.log(check,'нет подарков')

#=============================================
# Settings
#=============================================

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def набор_базовых_параметров(self):
        return [Action.ПОДРАЗДЕЛЕНИЕ,'description', 'validity', 'обязательный_набор_товаров', 'формула_вычисления_подарка', 'округление_цены']

    def tab_visible(self, tab_id):
        return tab_id in ['base_params','params']

    def settings_page(self):
        self.print_title()
        x = self.text_block('about')
        x.text(ABOUT)
        x.href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {DESCRIPTION}')
        x = self.text_block('about')
        x.text(ABOUT)

