# -*- coding: utf-8 -*-
import os, sys, datetime, time, sqlite3
import xml.etree.cElementTree as ET

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.append(path)

from domino.jobs import Proc
from domino.page import Page
from domino.page_controls import КраснаяКнопка, ПлоскаяТаблица, FormControl
from domino.core import log, start_log
#from domino.databases import Databases
from domino.postgres import Postgres
from discount.core import DISCOUNT_DB, Engine
from discount.product_sets import ProductSet
from discount.series import ТипКарты
from discount.schemas import ДисконтнаяСхема
from discount.cards import Card
from discount.page import DiscountPage
from discount.actions import Action
from settings import MODULE_ID

TIMEOUT = 100
PROC = 'procs/calc_discount.py'
DESCRIPTION = 'Перерасчет персональной процентной скидки'

class Вариант_рачета_процента_скидки(FormControl.Param):
    def __init__(self):
        super().__init__('вариант_расчета_процента_скидки', '', type='select')
        self.options=[
            ['improve', 'Изменить процент скидки ТОЛЬКО ЕСЛИ рачетный процент больше чем существующий'],
            ['change', 'Изменить процент скидки В ЛЮБОМ СЛУЧАЕ, даже если рачетный процент меньше чем существующий']
            ]
    def get_value(self, page):
        return page.proc.info.get(self.ID, 'improve')
    def save(self, page):
        page.proc.info[self.ID] = page.get(self.ID)
        page.proc.save()

ВАРИАНТ_УЧЕТА_ПРОЦЕНТНОЙ_СКИДКИ = Вариант_рачета_процента_скидки()

ПараметрыПроцедуры = FormControl('параметры_процедуры', width=0)
ПараметрыПроцедуры.append(ВАРИАНТ_УЧЕТА_ПРОЦЕНТНОЙ_СКИДКИ)

def find_action_15(cursor):
    action_15 = None
    ОСНОВНАЯ_СХЕМА = ДисконтнаяСхема.get(cursor, 0)
    for action_ID in ОСНОВНАЯ_СХЕМА.послепродажные_акции.список_акций:
        action = Action.get(cursor, action_ID)
        if action.TYPE == 'A15':
            action_15 = action
            break
    return action_15

class CalcDiscountPage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request, controls=[ПараметрыПроцедуры])
        self.proc = Proc.get(self.account_id, MODULE_ID, PROC)

    def запустить(self):
        Proc.start(self.account_id, MODULE_ID, PROC, description=DESCRIPTION)
        self.message(f'Запущена задача')

    def расчет_процентной_скидки(self):
        p = self.text_block().mt(1)
        #p.header('Пересчет процента скидки для персональных карт')
        p.text('''
        Для персональных карт определен показатель
        общей суммы покупок. На основании этого показателя пересчитываются
        проценты скидок по персональным картам. Это делается согласно акции A15 
        "Начисление процентной скидки от суммы покупок", которая должна быть создана в
        ОСНОВНОЙ схеме и нужным образои настроена.
        ''')
        action_15 = find_action_15(self.cursor)
        if action_15 is None:
            p.newline()
            p.text(''' В настоящее время данная акция не обнаружена''')
        else:
            p.newline()
            p.text(''' В настоящее время данная акция имее следующие параметры:''')
            table = ПлоскаяТаблица(self, 'table')
            table.column().text('Сумма покупок')
            table.column().text('Процент скидки')
            percents_of_sum = action_15.percents_of_sum
            dim = percents_of_sum.dim
            for i in range(0, dim):
                row = table.row(i)
                row.cell(width=20).text(percents_of_sum.sum_name(i))
                row.cell(cls='text-left').text(f'{percents_of_sum.get_percent(i)} %')
            ПараметрыПроцедуры(self)
    def open(self):
        self.title(f'{self.proc.ID}, {DESCRIPTION}')
        p = self.toolbar('about').style('align-items:center')
        self.расчет_процентной_скидки()

class CalcDiscountJob(Proc.Job):

    def __init__(self, ID):
        super().__init__(ID)
        #log.info(f'Запуск задачи {ID} : load')
        #self.connection = None
        #self.cursor = None
       # self.pg_connection = None
        #self.engine = None
        #self.остатки = {}
        self.change_discount = False
        self.persent_of_sum = None
        
    def __call__(self):
        #self.start_and_stop_previous('discount_load')
        if self.account_id is None:
            self.error(f'Не задано учетной записи')
        
        #self.database = Databases().get_database(self.account_id)
        #self.db_connection = self.database.connect()
        #self.db_cursor = self.db_connection.cursor()
        self.pg_connection = Postgres.connect(self.account_id)
        self.pg_cursor = self.pg_connection.cursor()
        #self.engine = Engine(None, self.pg_connection)
        self.connection = sqlite3.connect(DISCOUNT_DB(self.account_id))
        self.cursor = self.connection.cursor()
        
        self.change_discount = self.info.get(ВАРИАНТ_УЧЕТА_ПРОЦЕНТНОЙ_СКИДКИ.ID, 'improve') == 'change'
        if self.change_discount:
            self.log(f'УСТАНОВЛЕН РЕЖИМ ЗАМЕЩЕНИЯ ПРОЦЕНТНОЙ СКИДКИ')
        else:
            self.log(f'УСТАНОВЛЕН РЕЖИМ УЛУЧШЕНИЯ ПРОЦЕНТНОЙ СКИДКИ')

        action_15 = find_action_15(self.cursor)
        if action_15:
            self.persent_of_sum = action_15.percents_of_sum
        if self.persent_of_sum is not None:
            self.calc_discounts()
        else:
            self.log('НЕ НАЙДЕНО АКЦИИ ДЛЯ РАСЧЕТА СКИДКИ')

    def calc_discounts(self):
        self.xml = ET.fromstring('<card_discounts/>')
        sql = 'select id, discount, total from discount_card where type=0 and (total>0 or discount>0)'
        self.pg_cursor.execute(sql)
        cards = self.pg_cursor.fetchall()
        self.log(f'ЗАГРУЗКА ДИСКОНТЫХ КАРТ, всего {len(cards)}')
        discounts = []
        for ID, discount, total in cards:
            new_discount = self.новый_процент(discount, total)
            if new_discount is not None:
                discounts.append([new_discount, ID])
                #ET.SubElement(self.xml, 'card', attrib={'id':ID, 'old':f'{discount}', 'new':f'{new_discount}'})
        #with open(os.path.join(self.folder, 'card_discounts.xml'), 'w') as f:
        #    f.write(str(ET.tostring(self.xml, encoding='utf-8')))
        self.log(f'ФОРМИРОВАНИЕ СПИСКА НОВЫХ СКИДОК, всего {len(discounts)}')
        sql = 'update discount_card set discount = %s where id = %s'
        with self.pg_connection:
            #for discount, ID in discounts:
            #    self.log(f'{ID}, {discount}')
                #sql = f'update discount_card set discount={discount} where id="{ID}"'
                #self.pg_cursor.execute(sql, [discount, ID])
            self.pg_cursor.executemany(sql, discounts)
        self.log(f'ОБНОВЛЕНИЕ ДИСКОНТНЫХ КАРТ')

    def новый_процент(self, CARD_DISCOUNT, CARD_TOTAL):
        новый_процент = self.persent_of_sum.find_percent(CARD_TOTAL if CARD_TOTAL else 0) 
        #log.debug(f'новый процент {процент} {новый_процент}') total checks i_total i_checks 
        if CARD_DISCOUNT is None:
            return новый_процент
        elif новый_процент == CARD_DISCOUNT:
            return None 
        elif новый_процент > CARD_DISCOUNT:
            return новый_процент
        else:
            #log.debug(f'новый процент меньше {процент} {новый_процент} {self.change_discount}')
            if self.change_discount:
                #log.debug(f'изменить процент {новый_процент}')
                return новый_процент
            else:
                return None

if __name__ == "__main__":
    try:
        with CalcDiscountJob(sys.argv[1]) as job:
            job()
    except:
        log.exception(__file__)

