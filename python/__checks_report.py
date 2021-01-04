# -*- coding: utf-8 -*-
import os, sys, datetime, time, sqlite3, pickle, arrow, shutil, subprocess, psutil, re, glob, json
from domino.jobs import Proc
from domino.page import Page
from domino.core import log, start_log, DOMINO_ROOT
from domino.databases import Databases
from discount.core import DISCOUNT_DB, PRODUCT_COLUMNS_FILE
#from discount.users import Пользователь
from discount.page import DiscountPage
from domino.page_controls import Кнопка, КраснаяКнопка
#from domino.crontab import CronJob, JOBS_DB
from domino.reports import Report
from domino.postgres import Postgres
from domino.page_controls import FormControl
from discount.series import CardType
from discount.cards import Card
from discount.checks import Check
from discount.actions import Action
from discount.action_types import ActionTypes
from domino.application import Application

application = Application(os.path.abspath(__file__))

TIMEOUT = 100
DESCRIPTION = 'Отчет за текущий месяц'
PROC = 'checks_report.py'
MODULE = 'discount'
MIN_DAYS = 2

class ThePage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.proc = Proc.get(self.account_id, MODULE, PROC)

    def on_run(self):
        YEAR = int(self.get('year'))
        MONTH = int(self.get('month'))
        Proc.start(self.account_id, MODULE, PROC, description=DESCRIPTION, info={'year':YEAR, 'month':MONTH})
        self.message(f'Запущена задача, год {YEAR}, месяц {MONTH}')

    def open(self):
        self.title(f'{self.proc.ID}, {DESCRIPTION}')
        #p = self.toolbar('about').style('align-items:center')
        # f_value, d_dept, (f_value * 100) as e_dwddwd from reports {} r_checks201601_d_wddwd r_checks2016_c_base      
        #t = p.item().text_block()
        #t.text(DESCRIPTION)
        t = self.text_block()
        t.text('''
        По умолчанию и автоматически, отчет запускается за текущий месяц. 
        Но для одноразового запуска можно указать конкретный месяц, за который
        рассчитать отчет.
        ''')
        p = self.toolbar('params').style('align-items:flex-end')
        select = p.item().mr(1).select(label='Год', name = 'year')
        YEAR = datetime.date.today().year
        for year in [YEAR, YEAR - 1, YEAR -2]:
            select.option(year, year)

        select = p.item().mr(1).select(label='Месяц', name = 'month')
        for month in range(1,13):
            select.option(month, month)
        КраснаяКнопка(p.item(), 'запустить').onclick('.on_run', forms=[p])

class DeptStat:
    def __init__(self, code):
        self.code = code
        self.выручка = 0
        self.чеков = 0
        self.возвратов = 0
        self.сумма_возвратов = 0
        self.чеков_со_скидкой = 0
        self.скидка = 0
        #self.розничная_стоимость_чеков_со_скидкой = 0

    def check(self, TYPE, TOTAL, DISCOUNT):
        total = float(TOTAL)
        if TYPE == 0:
            self.выручка += total
            self.чеков += 1
            if DISCOUNT > 0:
                self.чеков_со_скидкой += 1
                self.скидка += DISCOUNT
        else:
            self.возвратов += 1
            self.сумма_возвратов += total

class ActionStats:
    def __init__(self, job):
        self.job = job
        self.total = ActionStats.Action(self, Report.TOTAL)
        self.actions = { Report.TOTAL :self.total}

    def add(self, action_ID, dept_ID, group_ID, discount, sum):
        values = [discount, sum]
        action = self.actions.get(action_ID)
        if action is None:
            action = ActionStats.Action(self, action_ID)
            self.actions[action_ID] = action
        action.add(dept_ID, group_ID, values)
        self.total.add(dept_ID, group_ID, values)

    class Action:
        def __init__(self, stats, ID):
            self.stats = stats
            self.ID = ID
            self.total = ActionStats.Action.Dept(self, Report.TOTAL)
            self.depts = {Report.TOTAL:self.total}
        def add(self, dept_ID, group_ID, values):
            dept = self.depts.get(dept_ID)
            if dept is None:
                dept = ActionStats.Action.Dept(self, dept_ID)
                self.depts[dept_ID] = dept
            dept.add(group_ID, values)
            self.total.add(group_ID, values)

        class Dept:
            def __init__(self, action, ID):
                self.action = action
                self.ID = ID
                self.total = ActionStats.Action.Dept.Group(self, Report.TOTAL)
                self.groups = {Report.TOTAL:self.total}
            def add(self, group_ID, values):
                group = self.groups.get(group_ID)
                if group is None:
                    group = ActionStats.Action.Dept.Group(self, group_ID)
                    self.groups[group_ID] = group
                group.add(values)
                self.total.add(values)
           
            class Group:
                def __init__(self, dept, ID):
                    self.ID = ID
                    self.dept = dept
                    self.checks = 0
                    self.discount = 0
                    self.sum = 0
                def add(self, values):
                    self.checks += 1
                    self.discount += values[0]
                    self.sum += values[1]

                    action_ID = self.dept.action.ID
                    dept_ID = self.dept.ID
                    ID = self.ID
                    if action_ID != Report.TOTAL and dept_ID != Report.TOTAL and ID != Report.TOTAL:
                        job = self.dept.action.stats.job
                        job.log(f'{action_ID:10}:{dept_ID:10}:{ID:10}  {self.checks:10} {self.discount} {self.sum}')

class ActionStat:
    actions = {}
    def __init__(self, action_id, dept_code, group): 
        self.action_id = action_id
        self.dept_code = dept_code
        self.group = group
        self.checks = 0
        self.discount = 0
        self.total = 0
        self.depts = {}
    def add(self, discount, total):
        self.checks += 1
        self.discount += discount
        self.total += total
    @staticmethod
    def KEY(action_id, dept_code, group):
        return f'{action_id}:{dept_code}:{group}'
    #@staticmethod
    #def KEYS(action_id, dept_code, group):
    #    return [
    #        ActionStat.KEY(action_id, dept_code, group),
    #        ActionStat.KEY(action_id, dept_code, 'TOTAL'),
    #        ActionStat.KEY(action_id, 'TOTAL', group),
    #        ActionStat.KEY(action_id, 'TOTAL', 'TOTAL'),
    #        ActionStat.KEY('TOTAL', dept_code, group),
    #       ActionStat.KEY('TOTAL' dept_code, 'TOTAL'),
    #       ActionStat.KEY('TOTAL', 'TOTAL', group),
    #       ActionStat.KEY('TOTAL' 'TOTAL', 'TOTAL'),
    #    ] 

    @staticmethod
    def add_action(action_id, dept_code, group, discount, total):

        KEY = ActionStat.KEY(action_id, dept_code, group)
        action = ActionStat.actions.get(KEY)
        if action is None:
            action = ActionStat(action_id, dept_code, group)
            ActionStat.actions[KEY] = action
        action.add(discount, total)

class TheJob(Proc.Job):
    def __init__(self, ID):
        super().__init__(ID)
        self.proc = Proc.get(self.account_id, MODULE, PROC)
        log.info(f'Запуск задачи {ID}, card_report')

    def load_dictionaries(self):
        self.group_of_product_code = {}
        self.group_name = {}
        self.dept_name = {}
        sql = 'select p.code, g.name, domino.DominoUIDToString(g.id) from db1_product p, db1_classif g where p.local_group  = g.id and g.type=14745602'
        self.db_cursor.execute(sql)
        for p_code, g_name, g_uid in self.db_cursor:
            self.group_of_product_code[p_code] = g_uid
            self.group_name[g_uid] = g_name
        self.log(f'Загрузка справочника товаров ({len(self.group_of_product_code)}) и групп ({len(self.group_name)})')
        #sql = 'select code, name from db1_agent where type=4653058'
        sql = 'select code, name from db1_agent where class=2 and type=40566786'
        self.db_cursor.execute(sql)
        for code, name in self.db_cursor:
            self.dept_name[code] = name
        self.log(f'Загрузка справочника подразделений ({len(self.dept_name)})')
    

    def get_dept_name(self, dept_code):
        return self.dept_name.get(dept_code, 'None')

    def __call__(self):
        if self.account_id is None:
            self.error(f'Не задано учетной записи')
        self.action_types = ActionTypes(application)

        try:
            self.database = Databases().get_database(self.account_id)
            self.db_connection = self.database.connect()
            self.db_cursor = self.db_connection.cursor()
        except BaseException as ex:
            log.exception('')
            self.log(f'{ex}')
        
        self.pg_connection = Postgres.connect(self.account_id)
        self.pg_cursor = self.pg_connection.cursor()

        self.connection = sqlite3.connect(DISCOUNT_DB(self.account_id))
        self.cursor = self.connection.cursor()
        #conn = sqlite3.connect(JOBS_DB)
        #cur = conn.cursor()

        self.load_dictionaries()

        self.check_for_break()

        YEAR = self.job_info.get('year')
        MONTH = self.job_info.get('month')
        if not YEAR or not MONTH:
            TODAY = datetime.date.today()
            YEAR =  TODAY.year
            MONTH = TODAY.month

        DATE = datetime.date(year=YEAR, month=MONTH, day=1)
        if MONTH == 12:
            NEXT_DATE = datetime.date(year = YEAR + 1, month=1, day=1)
        else:
            NEXT_DATE = datetime.date(year = YEAR, month=MONTH + 1, day=1)

        self.log(f'ФОРМИРОВАНИЕ ОТЧЕТА ЗА {DATE.year:04}-{DATE.month:02}')
        self.log(f'c {DATE} по {NEXT_DATE} исключительно ')

        report = Report(self.account_id, 'discount', f'Отчет за {DATE.year:04}-{DATE.month:02}', year=DATE.year, month=DATE.month)

        self.pg_cursor.execute('select ID, CLASS, TYPE, CHECK_DATE, DEPT_CODE, POS_ID, SESSION_ID, SESSION_DATE, CHECK_NO, IS_TEST, TOTAL from discount_check where check_date >=%s and check_date <%s', [DATE, NEXT_DATE])
        
        count = 0
        sum = 0.0

        records = self.pg_cursor.fetchmany(10000)
        pos = set()
        depts = {}
        days = set()
        groups = {}
        #actions = {}
        errors = 0
        DEPT_CODES = set()
        GROUPS = set()
        ACTIONS = set()
        action_stats = ActionStats(self)
        while records is not None and len(records) > 0:
            self.check_for_break()
            for ID, CLASS, TYPE, CHECK_DATE, DEPT_CODE, POS_ID, SESSION_ID, SESSION_DATE, CHECK_NO, IS_TEST, TOTAL in records:
                DEPT_CODES.add(DEPT_CODE)
                total = float(TOTAL) 
                DISCOUNT = 0

                count += 1
                sum += total
                pos.add(POS_ID)
                days.add(CHECK_DATE.date())
                
                folder = Check.make_folder(self.account_id, CHECK_DATE, DEPT_CODE)
                try:
                    with open(os.path.join(folder, f'{ID}.json')) as f:
                        check = json.load(f)
                except BaseException as ex:
                    errors += 1
                    self.log(f'Чек {POS_ID}/{SESSION_ID}/{CHECK_NO} от {CHECK_DATE} подразделение {DEPT_CODE} : {ex}')
                    continue
                    
                lines = check['LINES']
                check_actions = {}
                for line in lines:
                    product_code = line[Check.LINE_PRODUCT_CODE]
                    qty = line[Check.LINE_QTY]
                    price = line[Check.LINE_PRICE]
                    final_price = line[Check.LINE_FINAL_PRICE]
                    line_roz = qty * price

                    # ПО ГРУППАМ 
                    group_ID = self.group_of_product_code.get(product_code, 'None')
                    GROUPS.add(group_ID)
                    group = groups.get(group_ID)
                    if group is None:
                        group = [self.group_name.get(group_ID, 'None'), 0, 0]
                        groups[group_ID] = group
                    group[1] += 1
                    group[2] += total

                    # ПО АКЦИЯМ 
                    line_actions = line.get(Check.LINE_CALC_INFO)
                    if line_actions is not None:
                        for line_action in line_actions:
                            action_ID = line_action[Check.LINE_ACTION_ID] 
                            discount = line_action[Check.LINE_ACTION_DISCOUNT]
                            DISCOUNT += discount
                            ACTIONS.add(action_ID)
                            check_action = check_actions.get(action_ID)
                            if check_action is None:
                                check_action = [0.0, 0.0]
                                check_actions[action_ID] = check_action
                            check_action[0] += discount
                            check_action[1] += line_roz
                            

                    #ActionStat.add_action(action_ID, DEPT_CODE, group_ID, discount, qty*price )

                #if count <= 100:
                #self.log(f'CHECK {check_actions}')
                for action_ID, check_action in check_actions.items():
                    action_stats.add(action_ID, DEPT_CODE, group_ID, discount, qty*price )
                    
                # ПО ПОДРАЗДЕЛЕНИЯМ
                dept = depts.get(DEPT_CODE)
                if dept is None:
                    dept = DeptStat(DEPT_CODE)
                    depts[DEPT_CODE] = dept
                dept.check(TYPE, TOTAL, DISCOUNT)

            self.log(f'Обработано {count} чеков на сумму {sum}, ошибок {errors}')
            records = self.pg_cursor.fetchmany(10000)

        self.log(f'СОХРАНЕНИЕ ОТЧЕТА')

        report.tab(Report.DEFAULT_TABLE, name = 'Общие показатели')
        report.tab('depts', name = 'По подразделениям')

        table = report.table(Report.DEFAULT_TABLE, name = 'Общие показатели')
        table.columns = {
            'name' : {},
            'value' : {'type' : 'integer'}
        }
        #table.column()
        #table.column(type='integer', default=0)

        table.row('days', values=['Дней', len(days)])
        table.row('checks', values=['Чеков', count])
        if len(days):
            table.row('check_per_day', VALUES=['Среднее количество чеков в день', int(count / len(days))])
        table.row('2', values=['Выручка', sum])
        if count:
            table.row('3', values=['Средний чек', round(sum / count, 2)])
        table.row('4', values=['Подразделений', len(depts)])
        table.row('5', values=['Фискальных регистраторов', len(pos)])
        if len(pos):
            table.row('checks_per_pos', values=['Количество чеков на один фискальный регистратор', int(count/len(pos))])

        # ПО ПОДРАЗДЕЛЕНИЯМ
        table = report.table('depts', name='По подразделениям')
        table.columns = {
            'dept'  : {'name':'Подразделение', 'type':'dept'},
            's1'    : {'name':'Чеков', 'type':'integer', 'default':0},
            's2'    : {'name':'Выручка', 'type':'integer', 'defaul':0},
            's3'    : {'name':'Средний чек', 'type':'integer', 'default':0},
            's4'    : {'name':'Чеков со скидками', 'type':'integer', 'defaul':0},
            's5'    : {'name':'Скидка', 'type':'integer', 'default':0},
            's6'    : {'name':'Возвратов', 'type':'integer', 'default':0},
            's7'    : {'name':'Сумма возвратов', 'type':'integer', 'default':0}
        }

        #table.column(ID='dept', name='Подразделение', type='dept')
        #table.column(name='Чеков', type='integer', default=0)
        #table.column(name='Выручка', type='integer', default=0)
        #table.column(name='Средний чек', type='integer', default=0)
        #table.column(name='Чеков со скидками', type='integer', default=0)
        #table.column(name='Скидка', type='integer', default=0)
        #table.column(name='Возвратов', type='integer', default=0)
        #table.column(name='Сумма возвратов', type='integer', default=0)
        for dept in depts.values():
            row = table.row(dept.code,
                values=[
                    dept.code,
                    dept.чеков,
                    round(dept.выручка, 2), # Выручка
                    round(dept.выручка / dept.чеков, 2) if dept.чеков else 0 ,# Средний чек
                    dept.чеков_со_скидкой, #  Количество чеков со скидками
                    round(dept.скидка,2), # Общая сумма скидок
                    dept.возвратов, # Возвратов
                    dept.сумма_возвратов # Сумма возвратов
                    ])
            #row[0] = dept.code
            #row[1] = dept.чеков # Чеков
            #row[2] = round(dept.выручка, 2) # Выручка
            #if dept.чеков:
            #    row[3] = round(dept.выручка / dept.чеков, 2) # Средний чек
            #row[4] = dept.чеков_со_скидкой #  Количество чеков со скидками
            #ow[5] = round(dept.скидка,2) # Общая сумма скидок
            #row[6] = dept.возвратов # Возвратов
            #ow[7] = dept.сумма_возвратов # Сумма возвратов
            # - Число касс 
            # - Количество чеков с персона картами

        # ПО АКЦИЯМ  IntegerColumn(default=0) 
        #report.tab('actions', name = 'По акциям')
        #table = report.table('actions', name='По акциям')
        #table.column(ID='action', name='Акция', type='action')
        #table.column(ID='dept', name='Подразделение', type='dept')
        #table.column(ID='group', name='Категория', type='group')
        #table.column(name='Чеков', type='integer', default=0)
        #table.column(name='Скидка', type='integer', default=0)
        #table.column(name='Розница', type='integer', default=0)
        #table.column(name='%', type='integer', default=0)
        #for KEY, action in ActionStat.actions.items():
        #    row = table.row(KEY)
        #    row[0] = action.action_id  # Акция (наименование)
        #    row[1] = action.dept_code # подразделение
        #    row[2] = action.group # категория
        #    row[3] = action.checks # чеков - Количество чеков в которых применена данная акция
        #    row[4] = round(action.discount, 2)  # Скидка - Общая сумма скидки по данной акции
        #    row[5] = round(action.total, 2) # Розничная сумма - Розеничная сумма товаров для которых применена данная акция
            # без учета дополнительных скидок
        #    row[6] = round((action.discount / action.total) * 100, 2) #  () Процент - Отношение Сидки к Розничной сумме
            # -Доля -  Отношение выручке за товары (для которых применена акция) к ощей выручке 

        report.tab('actions2', name = 'По акциям')
        table = report.table('actions2', name = 'По акциям')
        table.columns = {
            'action' :  { 'name':'Акция', 'type':'action'},
            'dept':     { 'name':'Подразделение', 'type':'dept'},
            'group':    { 'name':'Категория', 'type':'group'},
            'checks':   { 'name':'Чеков', 'type':'integer', 'default':0, 'desc': 'Количество чеков в которых применена акция'},
            'discount': { 'name':'Скидка', 'type':'integer', 'default':0, 'desc' : 'Общая сумма скидки по акции'},
            'sum':      {'name':'Розница', 'type':'integer', 'default':0, 'desc' : 'Розеничная сумма товаров для которых применена акция'},
            'percent':  { 'name' : '%', 'type' : 'integer', 'default':0, 'desc' : 'Отношение Сидки к Розничной сумме'}
            }
        #table.column(ID='action', name='Акция', type='action')
        ##able.column(ID='dept', name='Подразделение', type='dept')
        #table.column(ID='group', name='Категория', type='group')
        #table.column(name='Чеков', type='integer', default=0)
        #table.column(name='Скидка', type='integer', default=0)
        #table.column(name='Розница', type='integer', default=0)
        #table.column(name='%', type='integer', default=0)
        for action_ID, action in action_stats.actions.items():
            for dept_ID, dept in action.depts.items():
                for group_ID, group in dept.groups.items():
                    if group.sum:
                        percent = round((group.discount / group.sum) * 100, 2)
                    else:
                        percent = 0
                    row = table.row(f'{action_ID}:{dept_ID}:{group_ID}', 
                        values=[
                            action_ID,
                            dept_ID,
                            group_ID,
                            group.checks, # чеков - Количество чеков в которых применена акция
                            round(group.discount, 2),  # Скидка - Общая сумма скидки по данной акции
                            round(group.sum, 2), # Розничная сумма - Розеничная сумма товаров для которых применена данная акция
                            percent #  () Процент - Отношение Сидки к Розничной сумме
                        ])

        # ПО КАТЕГОРИЯМ
        # ПО КАРТАМ
            # Тип карты
            # Количество чеков
            # Количество активированных
            # Количество погашенных
            # С итекшем сроком действия
            # + Баллов нарастилос (денежных средств)
            # - Баллов 
            # + ДС
            # - ДС          

        # create enums
        enum = report.create_enum('dept')
        for DEPT_CODE in DEPT_CODES:
            enum[DEPT_CODE] = self.dept_name.get(DEPT_CODE,DEPT_CODE)
        enum = report.create_enum('group')
        for GROUP in GROUPS:
            enum[GROUP] = self.group_name.get(GROUP,GROUP)
        enum = report.create_enum('action')
        for ACTION in ACTIONS:
            a = Action.get(self.cursor, ACTION)
            enum[ACTION] = a.полное_наименование(self.action_types)
        #self.log(f'{enum}')

        report.create()

if __name__ == "__main__":
    log.debug(f'{__name__} {sys.argv}')
    try:
        with TheJob(sys.argv[1]) as job:
            job()
    except BaseException as ex:
        log.exception(__name__)

