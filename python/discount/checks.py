import sys, os, datetime, pickle, arrow, json, binascii
import barcode
#import xml.etree.cElementTree as ET
from lxml import etree as ET

from domino.core import log, DOMINO_ROOT
from domino.databases.postgres import Postgres
from discount.cards import Card
from settings import PostgresTable
from sqlalchemy import Column, String, Integer, SmallInteger, DateTime, Date, JSON, Boolean, DECIMAL

CHECKS = 'DISCOUNT#CHECKS'
TEXT_TEXT = 'TEXT'
TEXT_BOLD = 'BOLD'
TEXT_CODE = 'CODE'
TEXT_EAN13 = 'EAN13'


class CheckLine:
    #line_actions
    ACTION_ID = 0
    ACTION_DISCOUNT = 1
    ACTION_CARD_ID = 2
    ACTION_POINTS = 3
    #line
    ACTIONS = 0
    LINE_ID = 1
    PRODUCT_CODE = 2
    #PRODUCT_UID = 
    PRODUCT_TYPE = 3
    BARCODE = 4
    GROUP = 5
    PRICE = 6
    FINAL_PRICE = 7
    MIN_PRICE = 8
    FIXED_PRICE = 9
    QTY = 10
    RESERVE = 11

    def __init__(self, check, PARAMS = None):
        self.check = check
        self.params = PARAMS if PARAMS else {}
        self.js = [None, None, None, None, None, None, 0, None, 0, False, 1.0, None]

    def to_js(self):
        self.actions_to_i_actions()
        return self.js
    
    def from_xml(self, xml):
        if xml is not None:
            for name, value in xml.attrib.items():
                name = name.upper()
                if name == 'LINE_ID':
                    self.params[Check.LINE_ID] = value
                    self.js[CheckLine.LINE_ID] = value
                elif name == 'PRODUCT_CODE':
                    self.params[Check.LINE_PRODUCT_CODE] = value
                    self.js[CheckLine.PRODUCT_CODE] = value
                elif name == 'CODE':
                    self.params[Check.LINE_BARCODE] = value
                    self.js[CheckLine.BARCODE] = value
                elif name == 'PRODUCT_TYPE':
                    self.params[Check.LINE_PRODUCT_TYPE] = value.strip()
                    self.js[CheckLine.PRODUCT_TYPE] = value.strip()
                elif name == 'GROUP':
                    self.params[Check.LINE_GROUP] = value.strip()
                    self.js[CheckLine.GROUP] = value.strip()
                    #self.group = value
                elif name == 'QTY':
                    if value and value.strip():
                        self.params[Check.LINE_QTY] = float(value)
                        self.js[CheckLine.QTY] = float(value)
                    #self.qty = float(value)
                elif name == 'PRICE':
                    if value and value.strip():
                        self.params[Check.LINE_PRICE] = float(value)
                        self.js[CheckLine.PRICE] = int(float(value)*100)
                    #self.price = float(value)
                elif name == 'FINAL_PRICE':
                    if value and value.strip():
                        self.params[Check.LINE_FINAL_PRICE] = float(value)
                        self.js[CheckLine.FINAL_PRICE] = int(float(value)*100)
                    #self.final_price = float(value)
                elif name == 'FIXED_PRICE':
                    self.params[Check.LINE_FIXED_PRICE] = (value == '1')
                    self.js[CheckLine.FIXED_PRICE] = (value == '1')
                elif name == 'MIN_PRICE':
                    if value and value.strip():
                        self.params[Check.LINE_MIN_PRICE] = float(value)
                        self.js[CheckLine.MIN_PRICE] = int(float(value)*100)
                elif name == 'CALC_INFO':
                    self.actions_from_string(value)
                else:
                    self.params[name] = value
        #log.debug(f'product_code : {self.product}, price : {self.price}, qty : {self.qty}')
                    #self.set_param(name, value)
        #self.product = None         # идентификатор продуктв "PI"
        #self.group = None           # идентифкатор нруппы продукта "GI" 
        #self.qty = 0                # количестов "Q"
        #self.price = 0              # цена товара "P"
        #self.fixed_price = False    # фиксированная цена "FX"
        #self.final_price = None     # окончательная цена "PF"
        #self.минимальная_розничная_цена = 0.0 # минимальная цена "MP"
        # __getattriute__() name == 
    
    @property
    def min_price(self):
        return self.params.get(Check.LINE_MIN_PRICE, 0)

    @property
    def fixed_price(self):
        return self.params.get(Check.LINE_FIXED_PRICE)
    @fixed_price.setter
    def fixed_price(self, value):
        self.params[Check.LINE_FIXED_PRICE] = bool(value)
        self.js[CheckLine.FIXED_PRICE] = bool(value)

    @property
    def final_price(self):
        return self.params.get(Check.LINE_FINAL_PRICE)
    @final_price.setter
    def final_price(self, value):
        self.params[Check.LINE_FINAL_PRICE] = float(value)
        self.js[CheckLine.FINAL_PRICE] = int(float(value)*100)

    @property
    def product(self):
        return self.params.get(Check.LINE_PRODUCT_CODE)

    @property
    def group(self):
        return self.params.get(Check.LINE_GROUP)

    @property
    def qty(self):
        return self.params.get(Check.LINE_QTY)

    @property
    def price(self):
        return self.params.get(Check.LINE_PRICE)
    
    @property
    def actions(self):
        return self.params.get(Check.LINE_ACTIONS)
    
    def clear_actions(self):
        if Check.LINE_ACTIONS in self.params:
            del self.params[Check.LINE_ACTIONS]

    def get_action(self, action_id):
        actions = self.params.get(Check.LINE_ACTIONS)
        if actions:
            for action in actions:
                if action[Check.LINE_ACTION_ID] == action_id:
                    return action
        return None

    def append_action(self, action_id, discount, card_id, points):
        actions = self.actions
        if actions is None:
            actions = []
            self.params[Check.LINE_ACTIONS] = actions
        actions.append([action_id, discount, card_id, points])

    def add_discount(self, action_id, discount, card_id = None, use_points = False):
        discount = round(discount, 2)
        if use_points:
            points = discount
        else:
            points = 0
        action = self.get_action(action_id)
        if action:
            action[Check.LINE_ACTION_DISCOUNT] += discount
            action[Check.LINE_ACTION_CARD_ID] = card_id
            action[Check.LINE_ACTION_POINTS] += points
        else:
            self.append_action(action_id, discount, card_id, points)

    def change_discount(self, action_id, discount, card_id = None, use_points = False):
        discount = round(discount,2)
        if use_points:
            points = discount
        else:
            points = 0
        self.clear_actions()
        self.append_action(action_id, discount, card_id, points)
    @property
    def actions_exists(self):
        return Check.LINE_ACTIONS in self.params
    def actions_to_string(self):
        if self.actions_exists:
            return json.dumps(self.params[Check.LINE_ACTIONS])
        else:
            return ''
    def actions_to_i_actions(self):
        actions = self.params.get(Check.LINE_ACTIONS)
        if actions is not None:
            self.js[CheckLine.ACTIONS] = []
            for action in actions:
                points = action[Check.LINE_ACTION_POINTS]
                discount = action[Check.LINE_ACTION_DISCOUNT]
                self.js[CheckLine.ACTIONS].append([
                    action[Check.LINE_ACTION_ID], 
                    int (discount*100) if discount else 0,
                    action[Check.LINE_ACTION_CARD_ID],
                    int(points*100) if points else 0,
                    ])

    def actions_from_string(self, s):
        try:
            self.params[Check.LINE_ACTIONS] = json.loads(s)
            self.js[CheckLine.ACTIONS] = []
        except:
            pass

    @property
    def summa(self):
        return self.price * self.qty

    @property
    def ID(self):
        return self.params.get(Check.LINE_ID)

    @property
    def barcode(self):
        return self.params.get(Check.LINE_BARCODE)

    @property
    def product_type(self):
        return self.params.get(Check.LINE_PRODUCT_TYPE)

    def __str__(self):
        return f'CheckLine({self.product},{self.qty},{self.count})'

    @property
    def count(self):
        return int(self.qty) if float.is_integer(self.qty) else 1

class CheckProcessing:
    def __init__(self):
        self.count = 0
        self.actions_info = {}
        self.card_info = {}
        self.info = {}

class Check(Postgres.Base):

    __tablename__ = 'discount_check'
    
    ID              = Column('id', String, primary_key=True)
    CLASS           = Column('class', SmallInteger, nullable=False)
    TYPE            = Column('type', SmallInteger, nullable = False)
    STATE           = Column('state', SmallInteger, nullable=False)
    creation_date   = Column(DateTime)
    dept_code       = Column(String)
    is_test         = Column(Boolean)
    check_date      = Column(DateTime)
    card_id         = Column(String)
    pos_id          = Column(String)
    session_id      = Column(String)
    session_date    = Column(Date)
    check_no        = Column(String)
    total           = Column(DECIMAL)
    params          = Column(JSON)
    lines           = Column(JSON)
    cards           = Column(JSON)
    payments        = Column(JSON)
    bookmark        = Column(Boolean)

    @staticmethod
    def on_activate(account_id, msg_log):
        table = Postgres.Table('discount_check')
        table.column('ID', 'VARCHAR NOT NULL PRIMARY KEY')
        table.column('CLASS','SMALLINT DEFAULT 0 NOT NULL')
        table.column('TYPE','SMALLINT DEFAULT 0 NOT NULL')
        table.column('STATE','SMALLINT DEFAULT 0 NOT NULL')
        table.column('CREATION_DATE','TIMESTAMP')
        table.column('DEPT_CODE','VARCHAR')
        table.column('IS_TEST','BOOL')
        table.column('CHECK_DATE','TIMESTAMP')
        table.column('CARD_ID','VARCHAR')
        table.column('POS_ID','VARCHAR')
        table.column('SESSION_ID','VARCHAR')
        table.column('SESSION_DATE','DATE')
        table.column('CHECK_NO','VARCHAR')
        table.column('TOTAL','DECIMAL')
        table.column('PARAMS','JSONB')
        table.column('lines','jsonb')
        table.column('cards','jsonb')
        table.column('payments','jsonb')
        table.column('bookmark','bool')

        table.index('CREATION_DATE')
        table.index('CHECK_DATE')
        table.index('CARD_ID', 'CHECK_DATE')

        table.migrate(account_id, msg_log)
    #line_actions
    LINE_ACTIONS = 'CI'
    LINE_ACTION_ID = 0
    LINE_ACTION_DISCOUNT = 1
    LINE_ACTION_CARD_ID = 2
    LINE_ACTION_POINTS = 3
    #line
    LINE_ID = 'ID'
    LINE_PRODUCT_CODE = 'PC'
    LINE_PRODUCT_UID = 'PU'
    LINE_PRODUCT_TYPE = 'PT'
    LINE_BARCODE = 'BC'
    LINE_GROUP = 'G'
    LINE_PRICE = 'P'
    LINE_FINAL_PRICE = 'FP'
    LINE_MIN_PRICE = 'MP'
    LINE_FIXED_PRICE = 'FX'
    LINE_QTY = 'Q'
    LINE_CALC_INFO = 'CI'
    # card
    CARD_POINTS = 'P'
    CARD_DISCOUNT = 'D'
    CARD_CARD = 'CARD'
    CARD_TYPE = 'T'

    # print
    PRINT_FOOTERS = 'F'
    PRINT_HEADERS = 'H'
    PRINT_COUPONS = 'C'
    PRINT_TEXT = 'TEXT'
    PRINT_BOLD = 'BOLD'
    PRINT_CODE = 'CODE'
    PRINT_EAN13 = 'EAN13'
        
    # payments
    PAYMENT_TYPE = 'T'
    PAYMENT_CASH = 'CASH'
    PAYMENT_GIFT = 'GIFT'
    PAYMENT_CARD = 'CARD'

    PAYMENT_CARD_ID = 'ID'
    PAYMENT_TERMINAL_ID = 'TID'
    PAYMENT_SYSTEM = 'PS'
    PAYMENT_ORD_ID = 'OID'
    PAYMENT_TRANS_ID = 'TRID'
    PAYMENT_STORNO_TRANS_ID = 'SRID'

    # operations
    LOAD = -1
    RESTORE_PROCESSING = -2
    STORE_PROCESSING = -3
    CREATE_RESPONCE = -4
    FIND_CARDS = -5
    DATE = 'DT'
    
    # params
    PARAMS = 'PARAMS'
    CHECK_GUID = 'ID'
    CALC_GUID = 'CID'
    DEPT_CODE = 'DC'
    POS_ID = 'FR'
    SESSION_ID = 'FRS'
    SESSION_DATE = 'FRD'
    CHECK_NO = 'FRN'
    SCHEMA = 'SH'
    VERSION = 'V'
    TOTAL = 'TТ'
    KEYWORD = 'KW'
    ERROR = 'ERROR'
    VERSION = 'V'
    SCHEMA = 'SH'

    def __init__(self, CLASS = 0):
        self.CLASS = CLASS          # 0: фискальный чек 1: расчетный чек 
        self.TYPE = 0               # 0: продажа 1: возврат
        self.start = datetime.datetime.now() # время начала обработки чека
        self.creation_date = None     # время создания записи - коней обработки чека
        
        self.account_id = None

        self.log = []               # протокол "LOG"

        # params
        #self.date = None            # дата чека "DATE"
        self.check_date = None      # дата чека "DATE"
        self.dept_code = None       # код подразделения "DEPT_CODE"
        self.ID = None              # Идентификатор чека "ID"
        #self.summa = 0.0
        self.is_test = None         # Тестовый чек "IS_TEST"
        self.for_sale = False       # Режим оценки цен для печати ценников и этикеток
        self.pid = None             # Родителький чек (для возврата) "PID"
                                    # чек расчета "CID"
        self.pos_id = None          # Номер фискального регистратора "FR"
        self.session_id = None      # Номер смены  фр "FRS"
        self.session_date = None    # Дата сеанса фр "FRD"
        self.check_no = None        # Номер чека фр FRN
        self.scheme = None          # Дисконтная схема при последней обработке чека "DS"
        self.total = 0
        
        self.params = {}            # Параметры чека "PARAMS"
        self.cards = {}             # карты в чеке "CARDS"
        self.lines = []             # строки чека "LINES"
        self.payments = []          # Платежи "PAYMENTS"
        
        self._processing = None
        
        self.print = [[], [], []] # печать в чеке print[0] - headers print[1] - footers print[2] купоны

        self.card_id = None # ID персональной карты (если есть в чеке) "CARD_ID"
        self.card_points = 0 # Начальное количество баллов на персональной карте
        self.card_used_points = 0 # Использованное количество баллов в результате скидок
        self.gifts = {} # список подарков по акциям
        self.totals = None # Скидки, подарки
        self.action_names = {} # словарь имен акций
    
    @property
    def date(self):
        return self.check_date
    @date.setter
    def date(self, value):
        self.check_date = value    

    def __str__(self):
        return f'<Check {self.ID}>'
    
    @property
    def summa(self):
        return self.total

    @property
    def keyword(self):
        return self.params.get(Check.KEYWORD)
    @property
    def calc_check_id(self):
        '''
        Возвращает идентификатор (guid) расчета, в случае собственно расчета
        возвращает сам себя. Также и для случаев, когда идентификатор чека
        не меняется при пробитии (нет нескольких фискальных чеков)
        '''
        guid = self.params.get(Check.CALC_GUID)
        return guid if guid is not None else self.ID

    def write_log(self, operation, msg=''):
        log_record = [str(datetime.datetime.now()), operation, msg]
        self.log.append(log_record)
    
    @staticmethod
    def operation_name(operation):
        if operation == Check.LOAD: 
            return 'Анализ запроса'
        elif operation == Check.RESTORE_PROCESSING:
            return 'Восстановление РН'
        elif operation == Check.STORE_PROCESSING:
            return 'Сохраение'
        elif operation == Check.CREATE_RESPONCE:
            return 'Формирование ответа'
        elif operation == Check.FIND_CARDS:
            return 'Анализ карт'
        else:
            return operation
    
    @staticmethod
    def read_log_record(log_record):
        dt = datetime.datetime.strptime(log_record[0], "%Y-%m-%d %H:%M:%S.%f")
        operation = log_record[1]
        msg = log_record[2]
        return dt, operation, msg

    @staticmethod
    def make_folder(account_id, date, dept_code, CLASS = 0):
        DATA = os.path.join(DOMINO_ROOT, 'accounts', account_id, 'data', 'discount', 'checks')
        folder = os.path.join(DATA, f'{date.year}/{date.month:02}/{date.day:02}/{dept_code}')
        os.makedirs(folder, exist_ok=True)
        return folder

    @staticmethod
    def make_work_folder(account_id, date, dept_code, CLASS = 0):
        DATA = os.path.join(DOMINO_ROOT, 'accounts', account_id, 'data', 'discount', 'calc')
        folder = os.path.join(DATA, f'{date.year}/{date.month:02}/{date.day:02}/{dept_code}')
        os.makedirs(folder, exist_ok=True)
        return folder

    @property
    def folder(self):
        return Check.make_folder(self.account_id, self.date, self.dept_code, self.CLASS)

    @property
    def work_folder(self):
        return Check.make_work_folder(self.account_id, self.date, self.dept_code, self.CLASS)
    
    def get_start_stop(self, account_id = None, calc = False):
        folder = Check.make_work_folder(account_id if account_id else self.account_id, self.check_date, self.dept_code)
        stop = 'calc.stop' if calc else 'accept.stop'
        stop_file = os.path.join(folder, f'{self.ID}.{stop}')
        if os.path.isfile(stop_file):
            with open(stop_file, 'r') as f:
                START, STOP = f.read().split(',')
            return datetime.datetime.strptime(START, "%Y-%m-%d %H:%M:%S.%f"),\
                datetime.datetime.strptime(STOP, "%Y-%m-%d %H:%M:%S.%f")
        return None, None

    @staticmethod
    def xml_file(account_id, date, dept_code, guid, ext):
        folder = Check.make_work_folder(account_id, date, dept_code)
        return os.path.join(folder, f'{guid}.{ext}')

    def save_xml_file(self, xml, ext):
        file = Check.xml_file(self.account_id, self.date, self.dept_code, self.ID, ext)
        with open(file, 'w') as f:
            f.write(xml)

    @property
    def processing(self):
        if self._processing is None:
            self._processing = CheckProcessing()
        return self._processing
    def load_processing(self):
        file = os.path.join(self.work_folder, f'{self.ID}.ctx')
        if os.path.isfile(file):
            with open(file, 'rb') as f:
                self._processing = pickle.load(f)

    #def find_cards(self, engine):
    #    msg = []
    #    for card_ID, card_info in self.cards.items():
    #        CARD = Card.get(engine, card_ID)
    #        if CARD:
    #            if CARD.TYPE == 0:
    #                self.card_id = card_ID
    #                if CARD.points:
    #                    self.card_points = int(CARD.points * 100)
    #                else:
    #                    self.card_points = 0
    #            card_info[Check.CARD_CARD] = CARD
    #            msg.append(f'карта {card_ID}')
    #        else:
    #            msg.append(f'карта {card_ID} НЕ НАЙДЕНА')
    #        
    #    self.write_log('ПОИСК КАРТ', ", ".join(msg))
    
    def set_param(self, name, value):
        name = name.upper()
        if name == 'ACCOUNT_ID':
            self.account_id = value
        elif name == 'CALC_GUID':
            self.params[Check.CALC_GUID] = value
        elif name == 'CHECK_DATE':
            #self.info[Check.DATE] = value
            self.date = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        elif name == 'DATE':
            if value.strip():
                self.date = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        elif name == 'CHECK_GUID':
            #self.params[Check.CHECK_GUID] = value
            self.ID = value
        elif name == 'INITIAL_GUID':
            self.params['PID'] = value
        elif name == 'CHECK_DEPT_CODE':
            #self.params[Check.DEPT_CODE] = value
            self.dept_code = value
        elif name == 'KEYWORD':
            self.params[Check.KEYWORD] = value.strip()
            #self.keywords.add(value.strip())
        elif name == 'POS_ID':
            #self.params[Check.POS_ID] = value.strip()
            self.pos_id = value
        elif name == 'SESSION_ID':
            #self.params[Check.SESSION_ID] = value.strip()
            self.session_id = value
        elif name == 'SESSION_DATE':
            #self.params[Check.SESSION_DATE] = value.strip()
            self.session_date = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        elif name == 'CHECK_ID':
            #self.params[Check.CHECK_NO] = value.strip()
            self.check_no = value.strip()
        elif name == 'TEST':
            self.is_test = True
        elif name == 'CALC_PRICE':
            self.for_sale = True
        
        elif name == 'TYPE':
            if value.upper() == 'R':
                self.TYPE = 1
        elif name == 'TOTAL':
            self.total = float(value)
        else:
            self.params[name] = value

        # не фискальный чек, дату чека берем как дату сесии
        if not self.date:
            self.date = self.session_date

    def load_for_calc(self, xml_file):
        xml = ET.fromstring(xml_file)
        self.load_from_xml(xml)
        self.total = 0
        for line in self.lines:
            self.total += (line.qty * line.price)
        self.total = round(self.total, 2) 
        self.load_processing()
        self.save_xml_file(xml_file, ext='calc.xml')
        self.write_log('РАЗБОР ЗАПРОСА')

    def load_for_accept(self, xml_file):

        parser = ET.XMLParser(recover=True)
        xml  = ET.fromstring(xml_file, parser=parser)

        self.load_from_xml(xml)
        self.save_xml_file(xml_file, ext='accept.xml')
        self.write_log('РАЗБОР ЗАПРОСА')

    def load_from_xml(self, xml):

        xparams = xml.find('PARAMS')
        for name, value in xparams.attrib.items():
            self.set_param(name, value)

        xcards = xml.find('CARDS')
        if xcards is not None:
            for xcard in xcards.findall('CARD'):
                info = {}
                card_ID = xcard.text
                for name, value in xcard.attrib.items():
                    try:
                        if name == 'POINTS' and value:
                            info[Check.CARD_POINTS] = float(value)
                    except:
                        log.exception(__file__)
                self.cards[card_ID] = info

        xlines = xml.find('LINES')
        if xlines:
            for xline in xlines.findall('LINE'):
                line = CheckLine(self)
                line.from_xml(xline)
                self.lines.append(line)

        xpayments = xml.find('PAYMENTS')
        if xpayments is not None:
            for xpayment in xpayments.findall("*"):
                payment = {}
                payment[Check.PAYMENT_TYPE] = xpayment.tag.upper()
                for name, value in xpayment.attrib.items():
                    name = name.upper()
                    if name == 'ID':
                        payment[Check.PAYMENT_CARD_ID] = value
                    elif name == 'PAYMENT_SYSTEM':
                        payment[Check.PAYMENT_SYSTEM] = value
                    elif name == 'ORG_ID':
                        payment[Check.PAYMENT_ORD_ID] = value
                    elif name == 'TERMINAL_ID':
                        payment[Check.PAYMENT_TERMINAL_ID] = value
                    elif name == 'TOTAL':
                        payment[Check.TOTAL] = value
                    elif name == 'TRANS_ID':
                        payment[Check.PAYMENT_TRANS_ID] = value
                    elif name == 'CLIENT_ID':
                        payment[Check.PAYMENT_CARD_ID] = value
                    elif name == 'STORNO_TRANS_ID':
                        payment[Check.PAYMENT_STORNO_TRANS_ID] = value
                self.payments.append(payment)

    def append_print_line(self, xlines, TYPE, TEXT):
        if TYPE == TEXT_EAN13:
            #log.debug(f'"{TYPE}" : "{TEXT}"')
            try:
                ean13 = barcode.get('ean13', TEXT)
                ET.SubElement(xlines, TYPE).text = f'{ean13}'
            except:
                #log.exception(__file__)
                ET.SubElement(xlines, TEXT_TEXT).text = f'?{TEXT}?'
        else:
            ET.SubElement(xlines, TYPE).text = TEXT

    def xml(self):
        xml = ET.fromstring('<CHECK/>')
        ET.SubElement(xml, 'status').text = 'success'

        if len(self.lines) > 0:
            xlines = ET.SubElement(xml, 'LINES')
            for line in self.lines:
                if line.actions_exists:
                    attrib = {'LINE_ID':line.ID, 'FINAL_PRICE':f'{line.final_price}'}
                    attrib['CALC_INFO'] = line.actions_to_string()
                    if hasattr(line, 'SALE_PRICE'):
                        attrib['SALE_PRICE'] = f'{round(line.SALE_PRICE / 100, 2)}'
                    if hasattr(line, 'VIP_PRICE'):
                        attrib['VIP_PRICE'] = f'{round(line.VIP_PRICE / 100, 2)}'
                    ET.SubElement(xlines, 'LINE', attrib=attrib)

        headers = self.print[0]
        if len(headers) > 0:
            xlines = ET.SubElement(xml, 'HEADER')
            for TYPE, TEXT in headers:
                self.append_print_line(xlines, TYPE, TEXT)

        footers = self.print[1]
        if len(footers) > 0:
            xlines = ET.SubElement(xml, 'FOOTER')
            for TYPE, TEXT in footers:
                self.append_print_line(xlines, TYPE, TEXT)

        coupons = self.print[2]
        if len(coupons) > 0:
            xcoupons = ET.SubElement(xml, 'COUPONS')
            for coupon in coupons:
                xcoupon = ET.SubElement(xcoupons, 'COUPON')
                for TYPE, TEXT in coupon:
                    self.append_print_line(xcoupon, TYPE, TEXT)

        if self.totals is not None:
            xtotals = ET.SubElement(xml, 'TOTALS')
            for action_id, total in self.totals.items():
                discount = total.get('d', 0)
                marks = total.get('m', 0)
                attrib = {'ID' : f'{action_id}'}
                attrib['NAME'] = self.action_names.get(action_id,'')
                if discount:
                    attrib['SUM'] = str(round(discount / 100, 2))
                if marks:
                    attrib['MARK'] = str(marks)
                ET.SubElement(xtotals, 'ACTION', attrib = attrib)

        xml = ET.tostring(xml, encoding='utf-8')
        
        self.write_log(Check.CREATE_RESPONCE)
        return xml
    
    def create(self, engine):
        self.pg_create(engine.pg_cursor)
    
    def pg_create(self, pg_cursor):
        sql = '''
            insert into DISCOUNT_CHECK 
            (ID, CLASS, TYPE, CHECK_DATE, DEPT_CODE, POS_ID, SESSION_ID, SESSION_DATE, 
            CHECK_NO, CREATION_DATE, PARAMS, IS_TEST, CARD_ID, TOTAL, LINES, CARDS, PAYMENTS)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
        PARAMS = json.dumps(self.params, ensure_ascii=False)
        #cards
        # 0 - ID
        # 1 - CLASS
        # 2 - TYPE
        # 3 - DISCOUNT
        # 4 - POINTS 
        for card_info in self.cards.values():
            if Check.CARD_CARD in card_info:
                del card_info[Check.CARD_CARD]
        CARDS_DUMP = json.dumps(self.cards, ensure_ascii=False)

        #payments
        if self.payments and len(self.payments) > 0:
            PAYMENTS_DUMP = json.dumps(self.payments, ensure_ascii=False)
        else:
            PAYMENTS_DUMP = None
        #lines
        LINES = []
        for line in self.lines:
            LINES.append(line.to_js())
        LINES_DUMP = json.dumps(LINES, ensure_ascii=False) 
        #
        params = [self.ID, self.CLASS, self.TYPE, self.date, self.dept_code, self.pos_id, self.session_id, self.session_date,
                self.check_no, datetime.datetime.now(), PARAMS, 
                self.is_test, self.card_id, self.total, LINES_DUMP, CARDS_DUMP, PAYMENTS_DUMP]
        pg_cursor.execute(sql, params)
    
    __FIELDS__ = 'ID, CLASS, TYPE, CHECK_DATE, DEPT_CODE, POS_ID, SESSION_ID, SESSION_DATE'\
        ',CHECK_NO, IS_TEST, CARD_ID, TOTAL, PARAMS'

    @staticmethod
    def _LOAD_FROM_RECORD(r):
        if r is None:
            return None
        c = Check()
        c.ID = r[0]
        c.CLASS = r[1]
        c.TYPE = r[2]
        c.date = r[3]
        c.dept_code = r[4]
        c.pos_id = r[5]
        c.session_id = r[6]
        c.session_date  = r[7]
        c.check_no  = r[8]
        c.is_test = r[9]
        c.card_id = r[10]
        c.total = r[11]
        c.params = r[12]
        #if PARAMS:
        #    c.params = json.loads(PARAMS)
        return c

    @staticmethod
    def pg_get(pg_cursor, account_id, ID):
        try:
            sql = f'''select {Check.__FIELDS__} from DISCOUNT_CHECK where ID = %s'''
            pg_cursor.execute(sql, [ID])
            r = pg_cursor.fetchone()
            check = Check._LOAD_FROM_RECORD(r)
            check.account_id = account_id
            #if check:
            #    check.load_from_dump()
            return check
        except:
            log.exception('Check.pg_get')

    @staticmethod
    def pg_findall(pg_cursor, where_clause, params = [], order_by = ''):
        checks = []

        if where_clause and where_clause.strip():
            sql = f'select {Check.__FIELDS__} from DISCOUNT_CHECK where {where_clause} {order_by}'
        else:
            sql = f'select {Check.__FIELDS__} from DISCOUNT_CHECK {order_by}'
        pg_cursor.execute(sql, params)
        for r in pg_cursor:
            checks.append(Check._LOAD_FROM_RECORD(r))
        return checks

