import flask, sqlite3, json, datetime
from domino.core import log
from discount.actions import Action
from .action_page import TheActionPage
from .action_base import ActionCalculator
from discount.series import Series

ID = 'A11'
CLASS = 1
IS_AVAILABLE = True
CARD = True
SUPPLEMENT = False
FIXED_PRICE = True
DESCRIPTION = 'Скидка на набор (от позиции товара)'
ABOUT = '''
    Каждый следующий товар из заданного набора получает 
    скидку в зависимости от количества предыдущих проданных товаров.
    Товары упорядочиваются по цене (сначала самые дорогие).
    Вычисляется общая скидка на набор, которая потом распределяется
    по всему набору, пропорционально розничной цены товаров.
    '''

#=============================================
# Calculator
#=============================================

class Calculator(ActionCalculator):
    def __init__(self, application, cursor, action, LOG, SQLITE):
        super().__init__(application, cursor, action, LOG, SQLITE)

        self.discounts = self.action.info.get(Action.ПРОЦЕНТ_ОТ_ПОЗИЦИИ)
        self.default = self.to_float(self.action.info.get(Action.ПРОЦЕНТНАЯ_СКИДКА), 0.0)
        self.count = None
        if self.discounts is not None:
            for pos in reversed(range(len(self.discounts))):
                discount = self.discounts[pos]
                if discount is not None:
                    self.count = pos + 1
                    break
        
        #self.проценты = action.info.get('процент_от_позиции', [])
        #log.debug(f'проценты {self.проценты}')
        self.создать_набор_основных_товаров(SQLITE, LOG)

    def процент_от_позиции(self, pos):
        return self.discounts[pos] if pos < self.count else self.default


    def calc(self, engine, check):
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            return


        if self.набор_товаров is None:
            self.log(check, f'не определен набор товаров')
            return
        if self.count is None:
            self.log(check, f'не определен набор скидок')
            return

        #self.log(check, f'{self.набор_товаров.товары}')
        #if self.проценты is None or len(self.проценты) == 0:
        #    self.log(check, 'не задана шкала процентов')
        #    return

        строки = []
        отобранные_строки = []
        товаров = 0
        сумма_товаров = 0.0
        уникальные_товары = set()
        строк = 0

        for line in check.lines:
            #self.log(check, f'{line.product} {line.count}')
            if line in self.набор_товаров:
                товаров += line.count
                строк += 1
                уникальные_товары.add(line.product)
                сумма_товаров += line.price * line.qty
                строки.append(line)
                for i in range(0, line.count):
                    отобранные_строки.append(line)

        if товаров == 0:
            self.log(check, 'нет товаров')
            return 
        elif self.минимальное_количество_товаров is not None:
            if товаров < self.минимальное_количество_товаров:
                self.log(check, f'недостаточное количество товаров {товаров}')
                return
        elif self.минимальное_количество_уникальных_товаров is not None:
            if len(уникальные_товары) < self.минимальное_количество_уникальных_товаров:
                self.log(check, f'недостаточное количество уникальных товаров  {len(уникальные_товары)}')
                return
        elif self.минимальная_сумма_товаров is not None:
            if сумма_товаров < self.минимальная_сумма_товаров:
                self.log(check, f'недостаточная сумма товаров {сумма}')
                return 

        СКИДКА = 0.0
        msg = []
        скидка_на_последующие_товары = 0.0
        количество_последующих_товаров = 0
        if товаров > 0:
            отобранные_строки = sorted(отобранные_строки, key=lambda line : line.price, reverse = True)
            pos = 0
            for line in отобранные_строки:
                if pos < self.count:
                    процент = self.discounts[pos]
                    скидка_на_товар = line.price * процент / 100.0
                    msg.append(f'{скидка_на_товар}({line.price}x{процент}%)')
                else:
                    процент = self.default
                    скидка_на_товар = line.price * процент / 100.0
                    msg.append(f'{скидка_на_товар}({line.price}x{процент}%)')
                    количество_последующих_товаров += 1
                    скидка_на_последующие_товары += скидка_на_товар
                #СКИДКА += self.применить_скидку(line, процент, None)
                #скидка_на_товар = line.price * процент / 100.0
                СКИДКА += скидка_на_товар
                pos += 1
            #if количество_последующих_товаров > 0:
            #    msg.append(f'{скидка_на_последующие_товары}({количество_последующих_товаров}x ... х {self.default}%)')

        else:
            self.log(check, 'нет товаров')
            return
        
        итоговая_скидка = self.добавить_суммовую_скидку(строки, сумма_товаров, СКИДКА, None)
        разница = round(итоговая_скидка - СКИДКА, 2)

        self.log(check, f'скидка {СКИДКА}+{разница}={итоговая_скидка}, товаров {товаров}, строк {строк}, расчет={" + ".join(msg)}')
        self.print_check_lines(check, values = {f'{{СКИДКА}}':f'{СКИДКА}'})

#=============================================
# Settings
#=============================================

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)
    
    def набор_базовых_параметров(self):
        return [Action.ПОДРАЗДЕЛЕНИЕ,'description', 'validity', 'обязательный_набор_товаров','процент_от_позиции', 'округление_цены']

    def tab_visible(self, tab_id):
        return tab_id in ['base_params', 'print', 'params']

    def набор_дополнительных_условий(self):
        return [Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА,Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ, Action.МИНИМАЛЬНАЯ_СУММА_ЧЕКА]

    def print_macros(self):
        return [
            ['СКИДКА', 'скидка по акции']
        ]

    def settings_page(self):
        self.print_title()
        p = self.text_block('about')
        p.text(ABOUT)
        #p.href(f' Подробнее ...', f'action_types/{ID}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {DESCRIPTION}')
        p = self.text_block('about')
        p.text(ABOUT)

