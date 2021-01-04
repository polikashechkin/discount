import sqlite3, os, threading, json, time, sys
import barcodenumber
from datetime import datetime
from domino.core import log
from domino.postgres import Postgres
from discount.actions import Action
from discount.series import Series
from discount.core import DISCOUNT_DB, SCHEMES_FOLDER, Engine
#from discount.actions import ActionSetItem
from discount.cards import Card, CardLog 
from discount.checks import Check
from discount.schemas import ДисконтнаяСхема 
from tables.sqlite.schema import Schema
from discount.dept_sets import DeptSetItem
from threading import Lock
#from settings import log as discount_log
from domino.databases.sqlite import Sqlite
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tables.sqlite.product_set import ГотовыеНаборы

UpdateLock = Lock()

СТАНДАРТНАЯ_ОБРАБОТКА_КАРТ = 'A16'

class ErrorCalculator:
    def __init__(self, action_ID, error):
        self.action_ID = action_ID
        self.error = error
        self.сообщение = f'{action_ID} : НЕДОСТУПНА'
    
    def calc(self, курсор, чек):
        чек.write_log(self.сообщение, self.error)

    def accept(self, курсор, чек):
        чек.write_log(self.сообщение, self.error)

    def check_base_conditions(self, check):
        return True

class AccountSchemeWorker:
    #def __init__(self, application, курсор, схема, goods, LOG, SQLITE):
    def __init__(self, application, schema_id, goods, path, bigsize):
        self.application = application
        self.schema_id = schema_id
        self.схема = None
        self.goods = goods
        self.path = path
        self.bigsize = bigsize
        self.opened = False

        self.calulators = [] # Расчетные акцииЮ основной список
        self.after_totals = [] # Расчетные акции, выполняющиеся после подведения итогов по скидкам
        self.for_sale = [] # Список акций, исполняющихся при оценки цен для печати ценников и этикеток
        self.acceptors = [] # Послепродажные действия (акции)
        self.accept_calc = [] # список послепродажных акций, имеющих возможность расчета
        self.before_accept = [] # Послепродажные действия, выполняющихся в первую очередь 
        self.action_names = {} # словать имен акций
        self.готовые_наборы = None
        #self.open(dbpath, LOG)
    @property
    def action_types(self):
        return self.application['action_types']

    @property
    def card_types(self):
        return self.application['card_types']

    def close(self):
        if self.opened:
            self.SQLITE.close()
        self.opened = False

    def open(self, LOG):
        if self.opened: return self
        start = time.perf_counter()
        self.calulators = []    # Расчетные акцииЮ основной список
        self.after_totals = []  # Расчетные акции, выполняющиеся после подведения итогов по скидкам
        self.for_sale = []      # Список акций, исполняющихся при оценки цен для печати ценников и этикеток
        self.acceptors = []     # Послепродажные действия (акции)
        self.accept_calc = []   # список послепродажных акций, имеющих возможность расчета
        self.before_accept = [] # Послепродажные действия, выполняющихся в первую очередь 
        self.action_names = {}  # словать имен акций
        #--------------------------------------------------
        connection = sqlite3.connect(f'file://{self.path}?mode=ro', uri=True)
        ENGINE = create_engine(f'sqlite:///{self.path}')
        Session = sessionmaker(bind=ENGINE)
        self.SQLITE = Session()
        курсор = connection.cursor()
        #--------------------------------------------------
        self.схема = ДисконтнаяСхема.get(курсор, self.schema_id)
        LOG.header(f'{self.схема.наименование}')
        
        #--------------------------------------------------
        self.LOG = LOG
        self.готовые_наборы = ГотовыеНаборы(self.SQLITE, LOG = LOG, bigsize = self.bigsize)
        self.create_actions(LOG, connection)
        self.готовые_наборы.prepeare(LOG = self.LOG)
        self.opened = True
        LOG(f'{self.схема.наименование}', start)
        connection.close()
        return self
    
    def готовый_набор(self, sets, name=None):
        return self.готовые_наборы.готовый_набор(sets, name)
    
    def create_actions(self, LOG, connection):
        #start = time.perf_counter()
        #LOG = self.LOG
        схема = self.схема
        курсор = connection.cursor()
        actions_start = time.perf_counter()
        actions = []
        for action_id in схема.расчетные_акции.список_акций:
            action = Action.get(курсор, action_id)
            if action is None:
                log.error(f'Не найдено описание акции {action_id}')
                LOG(f'error:Не найдено описание акции {action_id}')
                continue
            if action.status < 0:
                LOG(f'error:Акция "{action_id}" недоступна')
                continue
            actions.append(action)
        LOG(f'Получение списка расчетных акций', actions_start)
 
        for action in actions:
            try:
                LOG.header(f'{action.full_name(self.action_types)}({action.id}, {action.type_})')
                action_start = time.perf_counter()
                action_type = self.action_types[action.type]
                calculator = action_type.Calculator(self, курсор, action, LOG, self.SQLITE)
                if calculator.for_sale:
                    self.for_sale.append(calculator)
                if action.type == 'A24' or action.type == 'A26':
                    self.after_totals.append(calculator)
                else:
                    self.calulators.append(calculator)
                self.action_names[f'{action.ID}'] = action.полное_наименование(self.action_types)
                LOG(f'{action.full_name(self.action_types)}({action.id}, {action.type_})', action_start)
            except BaseException as ex:
                LOG(f'error:{ex}')
                log.exception(__file__)
                calculator = ErrorCalculator(action.id, f'{ex}')
                self.calulators.append(calculator)
 
        # СТАНДАРТНАЯ_ОБРАБОТКА_КАРТ
        action_start = time.perf_counter()
        try:
            action_type = self.action_types[СТАНДАРТНАЯ_ОБРАБОТКА_КАРТ]
            self.before_accept.append(action_type.Acceptor(self, курсор, None, self.LOG, self.SQLITE))
        except BaseException as ex:
            log.exception(f'{self} : {СТАНДАРТНАЯ_ОБРАБОТКА_КАРТ} : {ex}')
            LOG(f'{ex}')
        LOG(f'{СТАНДАРТНАЯ_ОБРАБОТКА_КАРТ}', action_start)
        
        actions = []
        actions_start = time.perf_counter()
        for action_id in схема.послепродажные_акции.список_акций:
            action = Action.get(курсор, action_id)
            if action is None:
                log.error(f'Не найдено акции "{action_id}"')
                LOG(f'Не найдено описание акции {action_id}')
                continue
            if action.status < 0:
                LOG(f'Акция {action_id} заблокирована')
                continue
        LOG('Получение списка послепродажных акций', actions_start)

        for акция_ID in схема.послепродажные_акции.список_акций:
            action = Action.get(курсор, акция_ID)
            #LOG(f'{action}')
            if action is None:
                LOG(f'error:Не найдено описание акции "{акция_ID}"')
                continue
            if action.status < 0:
                LOG(f'error:Акция "{акция_ID}" недоступна')
                continue
            actions.append(action)

        for action in actions:
            try:
                LOG(f'{action.full_name(self.action_types)}({action.id}, {action.type_})')
                action_start = time.perf_counter()
                action_type = self.action_types[action.type]
                worker = action_type.Acceptor(self, курсор, action, self.LOG, self.SQLITE)
                self.acceptors.append(worker)
                if hasattr(worker, 'calc'):
                    self.accept_calc.append(worker)
                self.action_names[f'{action.ID}'] = action.полное_наименование(self.action_types)
                LOG(f'{action.full_name(self.action_types)}({action.id}, {action.type_})',action_start)
            except BaseException as ex:
                log.exception(f'{self} : {action} : {ex}')
                LOG(f'error:{ex}')
                calculator = ErrorCalculator(action.id, f'{ex}')
                self.calulators.append(calculator)
        #self.LOG(f'{self}', start)
 
    def __str__(self):
        return  f'AccountSchemeWorker({self.schema_id})'
    def __repr__(self):
        return self.__str__()

    def make_totals(self, check):
        #check.write_log('ПОДСЧЕТ ИТОГОВ')
        totals = {}
        check.points = {}
        for account_id, gift in check.gifts.items():
            totals[account_id] = gift
        for line in check.lines:
            actions = line.actions
            if actions is not None:
                for action in actions:
                    action_id = f'{action[Check.LINE_ACTION_ID]}'
                    #log.debug(f'ACTION {action}, {check.card_id}')
                    #check.write_log(f'Акция {action_id} : {action}')
                    
                    discount = action[Check.LINE_ACTION_DISCOUNT]
                    if discount:
                        discount = int(discount * 100) # в копейках все
                    
                    card_id = action[Check.LINE_ACTION_CARD_ID]
                    if card_id and check.card_id and card_id == check.card_id:
                        points = action[Check.LINE_ACTION_POINTS]
                        if points:
                            points = int(points * 100) # в копейках все
                        #log.debug(f'POINTS = {points}')
                    else:
                        points = 0

                    if discount or points:
                        total = totals.get(action_id)
                        if total:
                            total['d'] = total.get('d', 0) + discount
                            if points:
                                total['p-'] = total.get('p-', 0) + points
                        else:
                            total = {'d':discount}
                            if points:
                                total['p-'] = points
                            totals[action_id] = total

        check.totals = totals
        check.write_log(f'ПОДСЧЕТ ИТОГОВ')

    def calc(self, engine, check, LOG=None):
        engine.pg_connection.autocommit = True
        check.goods = self.goods
        check.params['schema_id'] = self.schema_id
        if check.for_sale:
            for action_worker in self.for_sale:
                try:
                    if action_worker.check_base_conditions(check):
                        action_worker.calc(engine, check)
                except BaseException as ex:
                    log.exception(f'{action_worker}')
                    check.write_log(f'{action_worker} : {ex}')
        else: 
            # поиск и загрузка карт
            msg = []
            for card_ID, card_info in check.cards.items():
                CARD = Card.get(engine, card_ID)
                if CARD:
                    if CARD.TYPE == 0:
                        check.card_id = card_ID
                        if CARD.points:
                            check.card_points = int(CARD.points * 100)
                        else:
                            check.card_points = 0
                    card_info[Check.CARD_CARD] = CARD
                    msg.append(f'карта {card_ID}')
                else:
                    msg.append(f'карта {card_ID} НЕ НАЙДЕНА')
                
            check.write_log('ПОИСК КАРТ', ", ".join(msg))
            #check.find_cards(engine)
            #--------------------------------------
            for action_worker in self.calulators:
                try:
                    if action_worker.check_base_conditions(check):
                        action_worker.calc(engine, check)
                except BaseException as ex:
                    log.exception(f'{action_worker}')
                    check.write_log(f'{action_worker} : {ex}')
            
            check.action_names = self.action_names

            for action_worker in self.accept_calc:
                try:
                    if action_worker.check_base_conditions(check):
                        action_worker.calc(engine, check)
                except BaseException as ex:
                    log.exception(f'{action_worker}')
                    check.write_log(f'{action_worker} : {ex}')

            self.make_totals(check)

            for action_worker in self.after_totals:
                try:
                    if action_worker.check_base_conditions(check):
                        action_worker.calc(engine, check)
                except BaseException as ex:
                    log.exception(f'{action_worker}')
                    check.write_log(f'{action_worker} : {ex}')

    def get_keywords(self, keywords, check, LOG=None):
        check.goods = self.goods
        check.params['schema_id'] = self.schema_id
        for calculator in self.calulators:
            if hasattr(calculator, 'get_keywords'):
                calculator.get_keywords(keywords, check)
                #log.debug(f'{calculator} : {check.keywords}')
 
    def get_prices(self, prices, dept_code, date, LOG=None):
        for calculator in self.calulators:
            if hasattr(calculator, 'get_prices'):
                calculator.get_prices(prices, dept_code, date)

    def find_used_cards(self, engine, чек):
        # добавление в список карт, карт из информации об акциях из строк чека
        # формирование дополнительных данных СКИДКИ и ИСПОЛЬЗОВАННЫЕ БАЛЛЫ 
        for line in чек.lines:
            actions = line.params.get(Check.LINE_CALC_INFO)
            if actions: # есть информация по проведенным акциям
                #log.debug(f'{line.calc_info.actions}')
                for action in actions:
                    скидка = action[Check.LINE_ACTION_DISCOUNT]
                    card_ID = action[Check.LINE_ACTION_CARD_ID]
                    try:
                        points = action[Check.LINE_ACTION_POINTS]
                    except:
                        points = 0
                    if card_ID and card_ID.strip():
                        # есть скидка за карту, вставляем карту в список карт
                        card_info = чек.cards.get(card_ID)
                        if card_info is None:
                            card_info = {}
                            #check_card = CheckCard(card_id)
                            #check_card.card = Card.get(курсор, check_card.id)
                            card_info[Check.CARD_DISCOUNT] = скидка
                            card_info[Check.CARD_POINTS] = points
                            чек.cards[card_ID] = card_info
                            #log.debug(f'create {card_id} {скидка}, {points}')
                            #msg.append(f'"{check_card.id}"')
                        else:
                            DISCOUNT = card_info.get(Check.CARD_DISCOUNT, 0)
                            card_info[Check.CARD_DISCOUNT] = DISCOUNT + скидка
                            POINTS = card_info.get(Check.CARD_POINTS, 0)
                            card_info[Check.CARD_POINTS] = POINTS + points
                            #log.debug(f'append {card_id} {скидка}, {points} => {check_card.discount}, {check_card.points}')

        # собственно поиск карт в базе данных
        msg = []
        for card_ID, card_info in чек.cards.items():
            points = card_info.get(Check.CARD_POINTS)
            if points:
                points = round(points, 2)
                card_info[Check.CARD_POINTS] = points
            msg.append(f'карта {card_ID}')
            if points:
                msg.append(f'использованные баллы {points}')
            card = Card.get(engine, card_ID)
            if card is None:
                msg.append('не найдена')
            else:
                card_info[Check.CARD_CARD] = card
                if card.TYPE == 0:
                    чек.card_id = card_ID
                    msg.append(f'персональная')

        чек.write_log('ПОИСК КАРТ', ", ".join(msg))

    def accept(self, engine, check, LOG=None):
        check.goods = self.goods
        check.params['schema_id'] = self.schema_id
        self.find_used_cards(engine, check)

        for acceptor in self.before_accept:
            try:
                acceptor.accept(engine, check)
            except BaseException as ex:
                log.exception(f'{acceptor}')
                check.write_log(f'{acceptor} : {ex}')

        for acceptor in self.acceptors:
            try:
                if acceptor.check_base_conditions(check):
                    acceptor.accept(engine, check)
            except BaseException as ex:
                log.exception(f'{acceptor}')
                check.write_log(f'{acceptor} : {ex}')

class Goods:
    def __init__(self, account_id):
        self.account_id = account_id
        self.folder = SCHEMES_FOLDER(self.account_id)
        self.GOODS_JSON_FILE = os.path.join(self.folder, 'goods.json')
        self.goods_mtime = None
        self.columns = None
        self.rows = None

    def __str__(self):
        return f'<Goods {self.account_id}>'
    
    def match(self, code, query):
        #log.debug(f'MATCH {code} : {query}')
        try:
            row = self.rows[code]
            #log.debug(f'MATCH COLUMNS : {self.columns}')
            #log.debug(f'MATCH ROW : {row}')
            for column_id, values in query.items():
                column_no = self.columns.index(column_id)
                #log.debug(f'MATCH COLUMN NO : {column_no}')
                if row[column_no] not in values:
                    #log.debug(f'MATCH VALUE : {row[column_no]}')
                    return False
            return True
        except:
            log.exception(__file__)
            return False

    def update(self, LOG):
        if os.path.isfile(self.GOODS_JSON_FILE):
            start = time.perf_counter()
            goods_mtime = os.path.getmtime(self.GOODS_JSON_FILE)
            if self.goods_mtime is None or goods_mtime != self.goods_mtime:
                with open(self.GOODS_JSON_FILE) as f:
                    goods = json.load(f)
                    self.columns = goods['columns']
                    self.rows = goods['goods']
                LOG(f'ОБНОВЛЕНИЕ СПРАВОЧНИКА ТОВАРОВ {self.account_id} ({self.goods_mtime}, {goods_mtime})', start)
                self.goods_mtime = goods_mtime

class AccountDeptWorker:
    def __init__(self, application, account_id, dept_code, LOG):
        start = time.perf_counter()
        self.application = application
        self.account_id = account_id
        self.dept_code = dept_code
        self.goods = Goods(account_id)
        try:
            LOG(f'{self}')
            SQLITE = Sqlite.Pool().session(account_id, 'discount')
            conn = sqlite3.connect(DISCOUNT_DB(account_id))
            cursor = conn.cursor()
            self.schema = None
            base_schema = None
            for schema in ДисконтнаяСхема.findall(cursor):
                if schema.это_основная_схема:
                    base_schema = schema
                else:
                    sql = f'select info from dept_set_item where dept_set=?'
                    params = [schema.набор_подразделений_ID]
                    cursor.execute(sql, params)
                    for INFO, in cursor:
                        info = json.loads(INFO)
                        code = info['code']
                        #discount_log.worning(f'схема {self.schema} : подразделение {code}')         
                        if code == dept_code:
                            self.schema = schema
                            break
                if self.schema is not None:
                    break
            if self.schema is None:
                self.schema = base_schema
            # --------------------------------
            self.goods.update(LOG)
            #LOG(f'{self.schema} : {self.schema.полное_наименование}')
            self.worker = AccountSchemeWorker(self.application, self.schema.ID, self.goods, path=DISCOUNT_DB(account_id), bigsize=0)
            self.worker.open(LOG) 
            LOG(f'{self} : {self.schema}', start)
        except Exception as ex:
            LOG(f'{self} : {ex}')
            log.exception(__file__)
        finally:
            SQLITE.close()
            conn.close()

    def close(self):
        self.worker.close()

    def calc(self, check, LOG, POSTGRES):
        if self.worker is None:
            check.write_log(f'ПОЛУЧЕНИЕ РАСЧЕТНЫХ АКЦИЙ', f'НЕТ НИ ОДНОЙ АКЦИИ')
        else:
            pg_connection = Postgres.connect(self.account_id)
            with pg_connection:
                engine = Engine(None, pg_connection)
                check.write_log(f'ОТКРЫТИЕ СОЕДИНЕНИЯ С БД')
                self.worker.calc(engine, check, LOG)
                engine.close()
        xml = check.xml()
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml.decode("utf-8")
        #check.dump()
        check.save_xml_file(xml, 'calc.r.xml')
        return xml

    def get_keywords(self, keywords, check, LOG, POSTGRES):
        self.worker.get_keywords(keywords, check, LOG)

    def accept(self, check, LOG, POSTGRES):
        if self.worker is None:
            check.write_log(f'НЕТ НИ ОДНОЙ АКЦИИ')
        else:
            pg_connection = Postgres.connect(self.account_id)
            with pg_connection:
                engine = Engine(None, pg_connection)
                check.write_log(f'ОТКРЫТИЕ СОЕДИНЕНИЯ С БД')
                self.worker.accept(engine, check, LOG)
                check.create(engine)
                engine.close()
            check.write_log(f'ЗАКРЫТИЕ СОЕДИНЕНИЯ С БД')

    def get_prices(self, dept_code, date, LOG, POSTGRES):
        prices = {}
        self.worker.get_prices(prices, dept_code, date, LOG)
        return prices

    def __str__(self):
        return f'<AccountDeptWorker {self.account_id} {self.dept_code}>'

    def __repr__(self):
        return self.__str__()
 
class AccountWorker:
    def __init__(self, application, account_id):
        self.application = application
        self.account_id = account_id
        self.goods = Goods(account_id)
        self.folder = SCHEMES_FOLDER(self.account_id)
        #self.основной_калькулятор = None
        #self.калькулятор_подразделения = {}
        self.worker_of_scheme = {}
        self.scheme_of_dept = {}

        self.VERSION = ''
        self.VERSION_FILE = os.path.join(self.folder, 'VERSION')
        self.connection_pool = Postgres.create_connection_pool(account_id, 1, 10)
        log.info(f'СОЗДАНИЕ ПУЛА СОЕДИНЕНИЙ 1 10')
        
        #self.scheme_workers = {}
        #self.default_worker
        #self.scheme_worker_of_dept.get(dept_code)  = 1 
    
    def close(self):
        for worker in self.worker_of_scheme.values():
            worker.close()
        self.worker_of_scheme = {}
        self.scheme_of_dept = {}

    def update(self, LOG):
        with UpdateLock:
            self.goods.update(LOG)
            with open(self.VERSION_FILE) as f:
                VERSION = f.read()
            
            if self.VERSION != VERSION:
                start = time.perf_counter()
                LOG(f'{self} ({self.VERSION}, {VERSION})')
                self.VERSION = VERSION
                #----------------------------------
                self.close()
                #self.основнай_калькулятор = None
                #self.калькулятор_подразделения = {}

                #-----------------------------------------
                # ПОЛУЧЕНИЕ СПИСКА ДИСКОНТНЫХ СХЕМ И ПОДРАЗДЕЛЕНИЙ
                #-----------------------------------------
                for schema_id in os.listdir(self.folder):
                    if schema_id.isdigit():
                        schema_id = int(schema_id)

                        path = os.path.join(self.folder, str(schema_id))
                        ENGINE = create_engine(f'sqlite:///{path}')
                        Session = sessionmaker(bind=ENGINE)
                        SQLITE = Session()
                        try:
                            # корректирровка для старых версий
                            bigsize_exists = False
                            cur = SQLITE.execute(f'pragma table_info(schema)').fetchall()
                            for column in cur:
                                if column[1] == 'bigsize':
                                    bigsize_exists = True
                                    break
                            if not bigsize_exists:
                                sql = 'alter table schema add column bigsize integer'
                                log.debug(sql)
                                SQLITE.execute(sql)
                                SQLITE.commit()
                            # -----------------------------
                            schema = SQLITE.query(Schema).get(schema_id)
                            #conn = sqlite3.connect(f'file://{path}?mode=ro',uri=True)
                            #cursor = conn.cursor()
                            #schema = ДисконтнаяСхема.get(cursor, schema_id)
                            #INFO = SQLITE.execute(f'select INFO from schema where id = {schema_id}').fetchone()[0]
                            #try:
                            #    bigsize = SQLITE.execute(f'select bigsize from schema where id = {schema_id}').fetchone()[0]
                            #except:
                            #    bigsize = None
                            codes = []
                            #LOG(f'{path} {schema.наименование}')
                            if schema_id == 0:
                                worker = AccountSchemeWorker(self.application, schema_id, self.goods, path=path, bigsize = schema.bigsize)
                                self.worker_of_scheme[schema_id] = worker
                                #self.основной_калькулятор = worker
                            else:
                                worker = AccountSchemeWorker(self.application, schema_id, self.goods, path=path, bigsize = schema.bigsize)
                                self.worker_of_scheme[schema_id] = worker
                                codes = schema.get_dept_codes(SQLITE)
                                #for item in DeptSetItem.findall(cursor, 'dept_set=?', [schema.набор_подразделений_ID]):
                                #    codes.append(item.info['code'])
                                for code in codes:
                                    self.scheme_of_dept[code] = schema_id
                            LOG(f'{path} {schema.наименование} {codes}')
                        except Exception as ex:
                            log.exception(__file__)
                            LOG.error(ex)
                        finally:
                            SQLITE.close()
                            #if conn:
                            #    conn.close()
                LOG(f'Распределение дисконтных схем'.upper(), start)
                LOG(f'{self.worker_of_scheme}')
                LOG(f'{self.scheme_of_dept}')
                #-----------------------------------------
                # ПОСТРОЕНИЕ ОБРАБОТЧИКОВ ДИСКОНТНЫХ СХЕМ
                #-----------------------------------------
                #LOG(f'Построение обработчиков'.upper())
                #for schema_id, scheme_worker in self.worker_of_scheme.items():
                #    scheme_worker.open(LOG)
                # ------------------------------------------------
    
    def get_worker(self, dept_code, LOG):
        self.update(LOG)
        schema_id = self.scheme_of_dept.get(dept_code, 0)
        worker = self.worker_of_scheme.get(schema_id)
        worker.open(LOG)
        #return self.калькулятор_подразделения.get(dept_code, self.основной_калькулятор)
        return worker

    def calc(self, check, LOG, POSTGRES):
        калькулятор = self.get_worker(check.dept_code, LOG)
        check.params[Check.VERSION] = self.VERSION

        if калькулятор is None:
            check.write_log(f'ПОЛУЧЕНИЕ РАСЧЕТНЫХ АКЦИЙ', f'НЕТ НИ ОДНОЙ АКЦИИ')
        else:
            check.write_log(f'ПОЛУЧЕНИЕ РАСЧЕТНЫХ АКЦИЙ')
            
            #conn = self.application.account_database_connect(self.account_id)
            pg_connection = None
            try:
                #pg_connection = Postgres.connect(self.account_id)
                pg_connection = self.connection_pool.getconn()
                with pg_connection:
                    engine = Engine(None, pg_connection)
                    check.write_log(f'ОТКРЫТИЕ СОЕДИНЕНИЯ С БД')
                    калькулятор.calc(engine, check, LOG)
                    engine.close()
                self.connection_pool.putconn(pg_connection)
                check.write_log(f'ЗАКРЫТИЕ СОЕДИНЕНИЯ С БД')
            except BaseException as ex: 
                log.exception(f'{self}.calc')
                if pg_connection:
                    self.connection_pool.putconn(pg_connection)
                raise Exception(f'{ex}')

        xml = check.xml()
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml.decode("utf-8")
        #check.dump()
        check.save_xml_file(xml, 'calc.r.xml')
        return xml

    def get_keywords(self, keywords, check, LOG, POSTGRES):
        worker = self.get_worker(check.dept_code, LOG)
        check.params[Check.VERSION] = self.VERSION
        worker.get_keywords(keywords, check, LOG)

    def accept(self, check, LOG, POSTGRES):
        калькулятор = self.get_worker(check.dept_code, LOG)
        check.params[Check.VERSION] = self.VERSION
        if калькулятор is None:
            check.write_log(f'ПОЛУЧЕНИЕ ПОСЛЕПРОДАЖНЫХ АКЦИЙ', 'НЕТ НИ ОДНОЙ АКЦИИ')
        else:
            check.write_log(f'ПОЛУЧЕНИЕ ПОСЛЕПРОДАЖНЫХ АКЦИЙ')
            #conn = self.application.account_database_connect(self.account_id)
            pg_connection = None
            try:
                #pg_connection = Postgres.connect(self.account_id)
                pg_connection = self.connection_pool.getconn()
                with pg_connection:
                    engine = Engine(None, pg_connection)
                    check.write_log(f'ОТКРЫТИЕ СОЕДИНЕНИЯ С БД')
                    калькулятор.accept(engine, check, LOG)
                    check.create(engine)
                    engine.close()
                self.connection_pool.putconn(pg_connection)
                check.write_log(f'ЗАКРЫТИЕ СОЕДИНЕНИЯ С БД')
                #try:
                #    check.dump()
                #except BaseException as ex:
                #    log.exception(f'save')
                    #check.params[Check.ERROR] = f'{ex}'
            except BaseException as ex: 
                log.exception(f'{self}.calc')
                if pg_connection:
                    self.connection_pool.putconn(pg_connection)
                raise Exception(f'{ex}')

    def get_prices(self, dept_code, date, LOG, POSTGRES):
        prices = {}
        worker = self.get_worker(dept_code, LOG)
        worker.get_prices(prices, dept_code, date, LOG)
        return prices

    def __str__(self):
        return f'<AccountWorker {self.account_id}>'

    def __repr__(self):
        return self.__str__()

class Calculator:
    def __init__(self, application):
        self.application = application
        self.workers = {}

    def account_worker(self, account_id, LOG):
        worker = self.workers.get(account_id)
        if worker is None:
            worker = AccountWorker(self.application, account_id)
            self.workers[account_id] = worker
        return worker
        
    def calc(self, check, LOG, POSTGRES):
        return self.account_worker(check.account_id, LOG).calc(check, LOG, POSTGRES)

    def get_keywords(self, keywords, check, LOG, POSTGRES):
        self.account_worker(check.account_id, LOG).get_keywords(keywords, check, LOG)

    def accept(self, check, LOG, POSTGRES):
        self.account_worker(check.account_id, LOG).accept(check, LOG, POSTGRES)

    def get_prices(self, account_id, dept_code, date, LOG, POSTGRES):
        return self.account_worker(account_id, LOG).get_prices(dept_code, date, LOG)

    def __str__(self):
        return f'Calculator()'


