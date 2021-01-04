# -*- coding: utf-8 -*-
import os, sys, datetime, time, sqlite3, pickle, arrow, shutil, subprocess, psutil, re, glob
from domino.jobs import Proc
from domino.page import Page
from domino.core import log, start_log, DOMINO_ROOT
from domino.databases import Databases
from discount.core import DISCOUNT_DB, PRODUCT_COLUMNS_FILE
#from discount.users import Пользователь
from discount.page import DiscountPage
from domino.page_controls import Кнопка, КраснаяКнопка
from domino.reports import Report
from domino.postgres import Postgres
from domino.page_controls import FormControl
from discount.series import CardType
from discount.cards import Card

TIMEOUT = 100
DESCRIPTION = 'Отчет об использовании карт'
PROC = 'card_report.py'
MODULE = 'discount'
MIN_DAYS = 2

class ThePage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.proc = Proc.get(self.account_id, MODULE, PROC)

    def run(self):
        Proc.start(self.account_id, MODULE, PROC, description=DESCRIPTION)
        self.message(f'Запущена задача')

    def open(self):
        self.title(f'{self.proc.ID}, {DESCRIPTION}')
        p = self.toolbar('about').style('align-items:center')
        t = p.item().text_block()
        t.text('''
        Отчет об использовании карт
        ''') 

TODAY = datetime.date.today()
class CardsStat:
    def __init__(self):
        self.card_types = {}
    def add(self, TYPE, IS_TEST, STATE, EXP_DATE):
        card_type = self.card_types.get(TYPE)
        if card_type is None:
            card_type = CardsStat.CardType()
            self.card_types[TYPE] = card_type
        card_type.add(1, IS_TEST, STATE, EXP_DATE)

    class CardType:
        def __init__(self):
            self.total = 0
            self.active = 0
            self.test = 0
            self.exp = 0
        def add(self, TOTAL, IS_TEST, STATE, EXP):
            self.total += TOTAL
            if IS_TEST:
                self.test += 1
            if STATE == Card.ACTIVE:
                self.active += 1
            self.exp += EXP

class TheJob(Proc.Job):
    def __init__(self, ID):
        log.info(f'Запуск задачи {ID}, card_report')
        super().__init__(ID=ID)

    def get_card_type_name(self, ID):
        card_type = CardType.get(self.cursor, int(ID))
        if card_type:
            return card_type.полное_наименование
        else:
            return f'<{ID}>'

    def __call__(self):
        if self.account_id is None:
            self.error(f'Не задано учетной записи')
        
        self.pg_connection = Postgres.connect(self.account_id)
        self.pg_cursor = self.pg_connection.cursor()

        self.connection = sqlite3.connect(DISCOUNT_DB(self.account_id))
        self.cursor = self.connection.cursor()
        #conn = sqlite3.connect(JOBS_DB)
        #cur = conn.cursor()

        self.check_for_break()
        self.log('ОБРАБОТКА КАРТ')
        report = Report(self.account_id, 'discount', 'Отчет об использовании карт')
        table = report.table('table')
        table.columns = {
            'cardtype': { 'name':'Тип', 'type':'card_type'},
            'total':    { 'name':'Всего', 'type': Report.INTEGER, 'default':0 },
            'test':     { 'name':'Тестовых', 'type': Report.INTEGER, 'default':0 },
            'active':   { 'name':'Активных', 'type': Report.INTEGER, 'default':0},
            'exp':      { 'name':'С истекшим строком', 'type': Report.INTEGER, 'default':0}
            }
        
        stat = CardsStat()

        self.pg_cursor.execute('select TYPE, IS_TEST, STATE, EXP_DATE from discount_card')
        self.check_for_break()
        count = 0
        for TYPE, IS_TEST, STATE, EXP_DATE in self.pg_cursor:
            TYPE = f'{TYPE}'
            count += 1
            EXP = 1 if EXP_DATE and EXP_DATE < TODAY else 0
            stat.add(TYPE, IS_TEST, STATE, EXP)
            if count % 100000 == 0:
                self.log(f'Обработано {count} карт')
                self.check_for_break()
        self.log(f'Всего обработано {count} карт')

        self.log(f'ФОРМИРОВАНИЕ ОТЧЕТА')
        CARD_TYPES = report.create_enum('card_type')
        TOTAL = CardsStat.CardType()
        
        for TYPE, card_type in stat.card_types.items():
            self.check_for_break()
            table.row(TYPE, values=[TYPE, card_type.total, card_type.active, card_type.test, card_type.exp])
            TOTAL.add(card_type.total, card_type.active, card_type.test, card_type.exp)
            NAME = self.get_card_type_name(TYPE)
            CARD_TYPES[TYPE] = NAME
            self.log(f'{TYPE}, {NAME}')

        table.row(Report.TOTAL, values=[Report.TOTAL, TOTAL.total, TOTAL.active, TOTAL.test, TOTAL.exp])
           

#            row = table.row(TYPE)
#            row[0] = TYPE 
#            if row[1] is None:
#                card_type = CardType.get(self.cursor, TYPE)
#                if card_type:
#                   row[1] = card_type.полное_наименование
#               else:
#                    row[1] = f'<{TYPE}>'
#            row[2] += 1
#            if IS_TEST:
#                row[3] += 1
#            if STATE == Card.ACTIVE:
#                row[4] += 1
#            if EXP_DATE and EXP_DATE < TODAY:
#                row[5] += 1
            
        self.log(f'СОХРАНЕНИЕ ОТЧЕТА')
        report.create()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            with TheJob(sys.argv[1]) as job:
                job()
        except BaseException as ex:
            log.exception(__name__)

