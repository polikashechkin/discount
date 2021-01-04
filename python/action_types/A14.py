import flask, sqlite3, json, datetime
from domino.core import log
#from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
from .action_page import TheActionPage
from .action_base import ActionAcceptor
from discount.series import Series
from discount.cards import Card, CardLog
#from discount.product_sets import ГотовыйНабор

ID = 'A14'
#IS_AVAILABLE = False
CLASS = 1
DESCRIPTION = 'Начисление баллов на персональную карту'
ABOUT = ''' 
    Начисление баллов на персональную карту. Начисляются баллы только на товары,
    заданные в "наборе товаров", за исключением "исключенных" товаров. 
    Баллы определяются как заданный процен от фактичской стоимости продажи (с учетом всех скидок).
    Если задано округление до рублей, то округление трактуется в пользу покупателей. 
    Например, если начислено 100 руб 01 коп , то это округлится до 101 руб 00 коп.
    '''

#=============================================
# Description
#=============================================

def is_available():
    return True

def description(**args):
    return DESCRIPTION

def about(page, to_detail = False):
    x = page.text_block('about')
    x.text(ABOUT)
    #if to_detail:
    #    x.href('Подробнее...', 'action_types/{ID}.description_page')
    #return x
 
#=============================================
# Acceptor
#=============================================
class Acceptor(ActionAcceptor):
    def __init__(self, worker, cursor, action, LOG, SQLITE):
        super().__init__(worker, cursor, action, LOG, SQLITE)
        
        percent = self.action.info.get(Action.ПРОЦЕНТ_НАЧИСЛЕНИЯ_БАЛЛОВ, 0.0)
         #log.debug(f'PERCENT = {percent}')
        self.percent = float(percent) / 100.0
        self.round = self.action.info.get(Action.ОКРУГЛЕНИЕ_БОНУСА, 0)
        self.создать_набор_исключенных_товаров(SQLITE, LOG)
        self.создать_набор_основных_товаров(SQLITE, LOG)

    def calc_points(self, check):
        total = 0
        lines = 0
        for line in check.lines:
            if self.исключенные_товары and line in self.исключенные_товары:
                continue
            if self.набор_товаров and line not in self.набор_товаров:
                continue
            total += int(int(line.final_price if line.final_price else line.price * 100) * line.qty)
            lines += 1

        points = int(total *  self.percent)
        if check.TYPE:
            self.log(check, 'ВОЗВРАТ')
            points = - points


        if self.round:
            #self.log(check, f'Округление до {self.round}, points = {points}, total = {total}')
            cents = points % 100
            #self.log(check, f'Копейки {cents}')
            if cents > 0:
                points = int(points / 100) * 100 + 100
                #self.log(check, f'без копеек {points}')


        if lines == 0:
            self.log(check, f'нет товаров')
            return 0

        #elif points == 0:
        #    self.log(check, f'к начислению {round(points/100, 2)} : сумма {round(total/100,2)} : процент {round(self.percent * 100, 2)}%')
        #    return 0
        self.log(check, f'к начислению {points} : сумма {total} : процент {round(self.percent * 100, 2)}%')
        return points

    def calc(self, engine, check):
        card = self.найти_карту_по_типу(check, 0)
        if card is None:
            self.log(check, f'нет карты')
            return
        points = self.calc_points(check)
        if points:
            check.gifts[self.action.id] = {'p+' : points}
            #self.log(check, f'начисленo {round(points/100, 2)} баллов')

    def accept(self, engine, check):
        card = self.найти_карту_по_типу(check, 0)
        if card is None:
            self.log(check, f'нет карты')
            return 
        points = self.calc_points(check)
        баллы = round(points / 100, 2)
        if points:
            БЫЛО = card.points
            card.начислить_баллы(engine, баллы, check)
            СТАЛО = card.points
            self.log(check, f'карта {card.ID} было {БЫЛО} стало {СТАЛО} начислено {баллы}')

#=============================================
# Settings
#=============================================

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.print_tab_exists = False

    def наименование_закладки(self, tab_id):
        if tab_id == 'скидка_на_товары':
            return 'Процент начисленя по наборам товаров'.upper()

    def tab_visible(self, tab_id):
        return tab_id in ['base_params']

    def param_visible(self, param_id):
        return param_id in [Action.ПОДРАЗДЕЛЕНИЕ,'description','validity','набор_товаров','процент_начисления_баллов', 'excluded', Action.ОКРУГЛЕНИЕ_БОНУСА]
    
    def стандартные_наборы_для_товаров_с_процентами(self):
        return [104,105, 102]

    def settings_page(self):
        self.print_title()
        about(self)
        #.href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')
        self.print_tab()

    def description_page(self):
        self.title(f'{ID}. {description()}')
        about(self)

