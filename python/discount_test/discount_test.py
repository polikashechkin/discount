import os, sys, datetime, pickle, json, uuid, random, time, logging, shutil, platform
from time import sleep
import xml.etree.cElementTree as ET
from multiprocessing import Process, Queue

try:
    import requests
except:
    os.system(f'pip3 install requests')
    import requests

#---------------------------------------------------------
# Domino Core
#---------------------------------------------------------

if platform.system() == 'Windows':
    DOMINO_ROOT = 'C:\\DOMINO'
    IS_WINDOWS = True
    IS_LINUX = False
else:   
    DOMINO_ROOT = '/DOMINO'
    IS_WINDOWS = False
    IS_LINUX = True

DOMINO_LOG = os.path.join(DOMINO_ROOT, 'log')
os.makedirs(DOMINO_LOG, exist_ok=True)

log = logging.getLogger('domino')
hdlr = logging.FileHandler(os.path.join(DOMINO_LOG, 'domino.log'))
formatter = logging.Formatter('%(asctime)s %(levelname)s %(module)s %(message)s')
#formatter = logging.Formatter('%(asctime)s %(levelname)s %(module)s.%(funcName)s %(message)s')
hdlr.setFormatter(formatter)
log.addHandler(hdlr) 
#log.setLevel(logging.INFO)
log.setLevel(logging.DEBUG)

start_log = logging.getLogger('start')
start_hdlr = logging.FileHandler(os.path.join(DOMINO_LOG, 'start.log'))
start_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
#formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
start_hdlr.setFormatter(start_formatter)
start_log.addHandler(start_hdlr) 
#log.setLevel(logging.INFO)
start_log.setLevel(logging.DEBUG)


#---------------------------------------------------------
# PosCheck
#---------------------------------------------------------
class PosCheck:
    class Responce:
        def __init__(self, r = None):
            self.error = True
            self.message = ''
            self.status_code = 0
            self.text = ''
            self.xml = None
            self.ms = 0
            self.url = ''

        def check_xml(self):
            if self.status_code != 200:
                self.error = True
                self.message = f'ОШИБКА ДОСТУПА К СЕРВЕРУ : {self.status_code}'
            else:
                self.xml = ET.fromstring(self.text)
                xstatus = self.xml.find('status')
                if xstatus is None:
                    self.error = True
                    self.message = f'ОШИБКА ДОСТУПА К СЕРВЕРУ : НЕПРАВИЛЬНЫЙ ОТВЕТ : {self.text}'
                elif xstatus.text == 'exception':
                    self.error = True
                    xmessage = self.xml.find('message')
                    self.message = f'exception {xmessage.text}' if xmessage is not None else f'ОШИБКА ДОСТУПА К СЕРВЕРУ : {self.text}'
                elif xstatus.text != 'success':
                    self.error = True
                    xmessage = self.xml.find('message')
                    self.message = xmessage.text if xmessage else f'ОШИБКА ДОСТУПА К СЕРВЕРУ '

    class Card:
        def __init__(self):
            self.ID = None
            self.TYPE = None 
            self.name = None
            self.cash = 0.0
            self.reusable = False
            self.points = 0.0
            self.used_points = 0.0

        def to_js(self):
            return [self.ID, self.TYPE, self.name, self.cash, self.reusable, self.points, self.used_points]
        def from_js(self, value):
            self.ID, self.TYPE, self.name, self.cash, self.reusable, self.points, self.used_points = value

    class Line:
        def __init__(self,):
            self.product = None
            self.price = 0.0
            self.qty = 0.0
            self.product_type = ''
            self.barcode = None
            self.group = None
            self.final_price = 0.0
            self.fixed_price = False
            self.calc_info = None
            self.enable = True
            self.params = {}

        def __str__(self):
            return f'<PosCheck.Line {self.ID}>'

        def to_js(self):
            return [self.ID, self.product, self.price, self.qty, self.product_type, self.barcode, self.group, self.final_price, self.calc_info, self.enable, self.params]
        def from_js(self, value):
            self.ID, self.product, self.price, self.qty, self.product_type, self.barcode, self.group, self.final_price, self.calc_info, self.enable, self.params = value

    def __init__(self, account_id, ID, schema_id = 0):
        self.account_id = account_id
        self.ID = ID                # внутренний идентификатор чека "ID"
        self.name = f'Чек {ID}'     # наименование чека
        self.TYPE = 0               # 0 продажа, 1 возврат
        self.test_mode = 0          # 0 проверка 1 проверка после утверждения 3 реальный чек
        self.GUID = uuid.uuid4()    # GUID внешний идентификатор
        self.date = None            # дата чека 
        self.dept_code = None       # код подразделения 
        self.pos_id = None          # Номер фискального регистратора 
        self.session_id = None      # Номер смены  фр 
        self.session_date = None    # Дата сеанса фр 
        self.check_no = None        # Номер чека 
        self.schema_id = schema_id  # Дисконтная схема при последней обработке чека 
        self.next = 0               # нумерантор строк чека
        self.keyword = ''           # ключевое слово
        self.keywords = []          # список допустимых ключевых слов
        self.protocol = False       # печатаь протокол при вызове операций 
        self.timeout = 60           # timeout (c) 
        self.server = 'localhost'   # сервер
        self.cards = {}             # карты в чеке "CARDS"
        self.lines = {}             # строки чека "LINES"
        self.totals = None          # скидки и подарки в результате расчета (calc)

    def __str__(self):
        return f'<PosCheck {self.ID}>'
    
    def total(self):
        total = 0
        for line in self.lines.values():
            if line.enable:
                try:
                    total += (line.final_price if line.final_price else line.price) * line.qty
                except:
                    log.exception('')
        return total

    @staticmethod
    def get_folder(account_id):
        folder = os.path.join(DOMINO_ROOT, 'accounts', account_id, 'data', 'discount', 'test')
        os.makedirs(folder, exist_ok=True)
        return folder

    def save(self):
        FOLDER = PosCheck.get_folder(self.account_id)
        with open(os.path.join(FOLDER, f'{self.ID}.json'), 'w') as f:
            json.dump(self.to_js(), f, ensure_ascii=False)
        #log.debug(f'SAVE {self.to_js()}')

    def add_line(self, product_code, price, qty, product_type='', barcode=None, group=None, fixed_price = None, enable=True):
        line = PosCheck.Line()
        line.product = product_code
        line.price = price 
        line.qty = qty 
        line.product_type = product_type
        line.barcode = barcode
        line.group = group 
        line.fixed_price = fixed_price
        line.enable = enable
        self.next += 1
        line.ID = f'{self.next:03}'
        self.lines[line.ID] = line
        return line

    def add_card(self, ID, TYPE, name, cash = 0.0, reusable = False, points = 0.0, used_points = 0.0):
        card = PosCheck.Card()
        card.ID = ID
        card.TYPE = TYPE
        card.name = name
        card.cash = cash
        card.reusable = reusable
        card.points = points
        card.used_points = used_points
        self.cards[card.ID] = card
        return card

    @staticmethod
    def load(account_id, ID):
        check = PosCheck(account_id, ID)
        try:
            FOLDER = PosCheck.get_folder(account_id)
            file = os.path.join(FOLDER, f'{ID}.json')
            if os.path.isfile(file):
                with open(file) as f:
                    check.from_js(json.load(f))
        except:
            log.exception(__name__)
        return check

    def to_js(self):
        DATE = self.date.strftime('%Y-%m-%d %H:%M:%S') if self.date is not None else None
        SESSION_DATE = self.session_date.strftime('%Y-%m-%d %H:%M:%S') if self.session_date else None
        GUID = str(self.GUID) if self.GUID else None 
        CARDS = []    
        for card in self.cards.values():
            CARDS.append(card.to_js())
        LINES = []
        for line in self.lines.values():
            LINES.append(line.to_js())
        return [ \
        self.account_id, self.ID, self.name, self.TYPE, self.test_mode, GUID, \
        DATE, self.dept_code, self.pos_id, self.session_id, SESSION_DATE, \
        self.check_no, self.schema_id, self.next, self.keyword, self.protocol, \
        self.timeout, self.server, self.keywords, \
        CARDS, LINES \
        ]

    def from_js(self, value):
        try:
            self.account_id, self.ID, self.name, self.TYPE, self.test_mode, self.GUID, \
            DATE, self.dept_code, self.pos_id, self.session_id, SESSION_DATE, \
            self.check_no, self.schema_id, self.next, self.keyword, self.protocol, \
            self.timeout, self.server, self.keywords, \
            CARDS, LINES = value
            #DATE = self.date.strftime('%Y-%m-%d %H:%M:%S') if self.date else None
            #SESSION_DATE = self.session_date.strftime('%Y-%m-%d %H:%M:%S') if self.session_date else None
            self.date = datetime.datetime.strptime(DATE, '%Y-%m-%d %H:%M:%S') if DATE else None
            self.session_date = datetime.datetime.strptime(SESSION_DATE, '%Y-%m-%d %H:%M:%S') if SESSION_DATE else None
            for CARD in CARDS:
                card = PosCheck.Card()
                card.from_js(CARD)
                self.cards[card.ID] = card
            for LINE in LINES:
                line = PosCheck.Line()
                line.from_js(LINE)
                self.lines[line.ID] = line
        except:
            log.exception(__name__)

    def to_json(self):
    
        return json.dumps(self.to_js(), ensure_ascii=False)

    def from_json(self, dump):
        self.from_js(json.loads(dump))

    def clear_keyword(self):
        self.keyword = ''
        self.keywords = []
    def calc_clear(self):
        self.totals = None
        for line in self.lines.values():
            line.final_price = None
            line.calc_info = None

    def next_check(self):
        self.GUID = uuid.uuid4()
        if self.check_no is not None:
            self.check_no += 1
        else:
            self.check_no = 1
        self.calc_clear()

    def create_accept_xml_file(self, CHECK_DATE):
        xml = ET.fromstring('<CHECK/>')
        attrib = {}
        attrib['TEST'] = 'TRUE'
        attrib['ACCOUNT_ID'] = f'{self.account_id}'
        attrib['CHECK_GUID'] = f'{self.GUID}'
        attrib['CHECK_DATE'] = f'{CHECK_DATE:%Y-%m-%d %H:%M:%S}'
        attrib['CHECK_DEPT_CODE'] = f'{self.dept_code}'
        attrib['POS_ID'] = f'{self.pos_id}'
        attrib['SESSION_ID'] = f'{self.session_id}'
        attrib['SESSION_DATE'] = f'{CHECK_DATE:%Y-%m-%d %H:%M:%S}'
        attrib['CHECK_ID'] = f'{self.check_no}'
        attrib['TYPE'] = 'R' if self.TYPE else 'S'
        xparams = ET.SubElement(xml, 'PARAMS', attrib = attrib)
        xlines = ET.SubElement(xml, 'LINES')
        total = 0.0
        for line in self.lines.values():
            if line.enable:
                attrib = {}
                attrib['LINE_ID'] = f'{line.ID}'
                if line.barcode:
                    attrib['CODE'] = f'{line.barcode}'
                attrib['PRODUCT_CODE'] = f'{line.product}'
                attrib['GROUP'] = f'{line.group}'
                if line.product_type:
                    attrib['PRODUCT_TYPE'] = f'{line.product_type}'
                attrib['PRICE'] = f'{line.price}'
                final_price = line.final_price if line.final_price is not None else line.price
                attrib['FINAL_PRICE'] = f'{final_price}'
                attrib['QTY'] = f'{line.qty}'
                if line.calc_info is not None:
                    attrib['CALC_INFO'] = line.calc_info
                try:
                    total += round(final_price * line.qty, 2)
                except:
                    log.exception('create_accept_xml_file')
                ET.SubElement(xlines, 'LINE', attrib = attrib)
                if line.product_type == 'CARD':
                    line.enable = False

        xcards = ET.SubElement(xml, 'CARDS')
        for card_ID in self.cards:
            ET.SubElement(xcards, 'CARD').text = card_ID

        xparams.attrib['TOTAL'] = f'{total}'
        xpayments = ET.SubElement(xml, 'PAYMENTS')
        for card_ID, card_info in self.cards.items():
            if total <= 0.0:
                break
            if card_info.TYPE == 'gift':
                # ОПЛАТА ПОДАРОЧНОЙ КАРТОЙ
                cash = card_info.cash
                if not cash:
                    continue
                if cash >= total:
                    ET.SubElement(xpayments, 'GIFT', attrib = {'ID':card_ID, 'TOTAL':f'{total}'})
                    total = 0
                else:
                    ET.SubElement(xpayments, 'GIFT', attrib = {'ID':card_ID, 'TOTAL':f'{cash}'})
                    total -= cash
        if total > 0.0:
            ET.SubElement(xpayments, 'CASH', attrib = {'TOTAL':f'{total}'})

        xml_file = ET.tostring(xml, encoding='utf-8')
        #self.save_check()
        return xml_file

    def create_calc_xml_file(self, CHECK_DATE):
        xml = ET.fromstring('<CHECK/>')
        attrib = {}
        attrib['TEST'] = 'TRUE'
        attrib['ACCOUNT_ID'] = f'{self.account_id}'
        attrib['CHECK_GUID'] = f'{self.GUID}'
        attrib['CHECK_DATE'] = f'{CHECK_DATE:%Y-%m-%d %H:%M:%S}'
        attrib['CHECK_DEPT_CODE'] = f'{self.dept_code}'
        attrib['TYPE'] = 'R' if self.TYPE else 'S'
        #attrib['CHECK_ID'] = f'{self.номер_чека}'
        if self.keyword and self.keyword.strip():
            attrib['KEYWORD'] = f'{self.keyword}'

        ET.SubElement(xml, 'PARAMS', attrib = attrib)
        xlines = ET.SubElement(xml, 'LINES')
        for line in self.lines.values():
            if line.enable:
                attrib = {}
                attrib['LINE_ID'] = f'{line.ID}'
                attrib['PRODUCT_CODE'] = f'{line.product}'
                attrib['GROUP'] = f'{line.group}'
                if line.product_type:
                    attrib['PRODUCT_TYPE'] = f'{line.product_type}'
                attrib['GROUP'] = f'{line.group}'
                if line.barcode:
                    attrib['CODE'] = f'{line.barcode}'
                attrib['PRICE'] = f'{line.price}'
                attrib['QTY'] = f'{line.qty}'
                ET.SubElement(xlines, 'LINE', attrib = attrib)
        
        xcards = ET.SubElement(xml, 'CARDS')
        for card_ID, card_info in self.cards.items():
            attrib={}
            if card_info.used_points:
                attrib['POINTS'] = f'{card_info.used_points}'
            ET.SubElement(xcards, 'CARD', attrib = attrib).text = card_ID

        xml_file = ET.tostring(xml,encoding='utf-8')
        return xml_file

    def POST(self, q, xml_file, x):
        q = f'http://{self.server}/{q}'
        if self.test_mode == 0:
            q += '?test=1'
        r = PosCheck.Responce()
        r.error = False
        r.url = q

        try:
            start = time.perf_counter()
            if self.server == 'localhost':
                rr = requests.post(q, data={'xml_file': xml_file}, verify=False, timeout = self.timeout)
            else:
                rr = requests.post(q, data={'xml_file': xml_file}, verify=True, timeout = self.timeout)
            end = time.perf_counter()
            r.status_code = rr.status_code
            r.text = rr.text
            r.error = False
        except BaseException as ex:
            end = time.perf_counter()
            r.error = True
            r.message = f'{ex}'
        r.ms = round((end - start) * 1000.0, 3)
        if r.error:
            self.print_error(x, r.message)
        #else:
        #    self.print_comment(x, f'{r.url} : {r.status_code}')
            #self.print_comment(x, f'{xml_file}')
            #self.print_comment(x, f'{r.text}')
        return r

    def GET(self, q, params, x):
        q = f'http://{self.server}/{q}'
        r = PosCheck.Responce()
        r.url = q
        if self.test_mode == 0:
            params['test']='1'

        start = time.perf_counter()
        try:
            if self.server == 'localhost':
                rr = requests.get(q, params = params , verify=False, timeout = self.timeout)
            else:
                rr = requests.get(q, params = params , verify=True, timeout = self.timeout)
            r.status_code = rr.status_code
            r.text = rr.text
            r.url = rr.url
            r.error = False
        except BaseException as ex:
            r.error = True
            r.message = f'{ex}'
            log.exception(f'{q}')
        end = time.perf_counter()
        r.ms = round((end - start) * 1000.0, 3)
        if r.error:
            self.print_error(x, f'{r.url} : {r.status_code}')
            #self.print_comment(x, f'{r.text}')
        #else:
            #self.print_error(x, f'{r.message}')
        return r
    
    def calc(self, x = None):
        self.calc_clear()
        #if not self.TYPE:
        #    self.print_header(x, f'Возвратный чек не расчитывается'.upper())
        #    return
        xml_file = self.create_calc_xml_file(self.CHECK_DATE)
        r = self.POST(f'discount/active/python/calc', xml_file, x)
        if r.error:
            return r
        r.check_xml()
        if r.error:
            return r
        xlines = r.xml.find('LINES')
        if xlines is not None:
            for xline in xlines.findall('LINE'):
                line_id = xline.attrib['LINE_ID']
                line = self.lines.get(line_id)
                if line:
                    line.final_price = float(xline.attrib['FINAL_PRICE'])
                    line.calc_info = xline.attrib['CALC_INFO']
                    self.print_header(x, f'{line.product} : {line.final_price}')
                else:
                    self.print_error(x, f'НЕИЗВЕСТНАЯ СТРОКА {line_id} {self.lines}')
                    r.Error = True
                    r.message = f'НЕИЗВЕСТНАЯ СТРОКА {line_id}'
        xtotals = r.xml.find('TOTALS')
        if xtotals:
            self.totals = {}
            for xaction in xtotals.findall('ACTION'):
                ID = xaction.attrib['ID']
                NAME = xaction.attrib['NAME']
                DISCOUNT = xaction.attrib.get('SUM', 0)
                MARK = xaction.attrib.get('MARK', 0)
                total = {'n':NAME, 'd':DISCOUNT, 'm' : MARK}
                self.totals[ID] = total

        self.save()
        if not r.error:
            self.print_header(x, f'Расчет успешно выполенен за {r.ms} мс'.upper())
        return r

    def accept(self, x = None):
        xml_file = self.create_accept_xml_file(self.CHECK_DATE)
        r = self.POST(f'discount/active/python/accept', xml_file, x)
        if r.error:
            return r
        r.check_xml()
        if not r.error:
            self.print_header(x, f'Чек успешно отправлен за {r.ms} мc'.upper())
        return r

    def check_card(self, input_line, x):
        input_line = input_line.strip()

        q = f'discount/active/python/check_card'
        params = {
            'account_id':self.account_id, 
            'card_id':input_line, 
            'dept_code':f'{self.dept_code}',
            'date': f'{self.CHECK_DATE:%Y-%m-%d %H:%M:%S}',
            'check_guid' : self.GUID
            }
        r = self.GET(q, params, x)
        if r.error:
            self.print_error(x, r.message)
            return r
        r.check_xml()
        if r.error:
            self.print_error(x, r.message)
            return r

        #xml = ET.fromstring(r.text)
        xcard = r.xml.find('card')
        name = xcard.attrib['name']
        card_id = xcard.attrib.get('id')
        if not card_id:
            card_id = input_line
        self.print_header(x, name)

        xtype = xcard.attrib['type']
        if xtype == 'discount-sale':
            price = xcard.attrib['price']
            product_code = xcard.attrib['product_code']
            self.add_line(product_code, price , 1, barcode = input_line, product_type='CARD')
            r.message = f'Добавляет в чек по цене "{price}" товар "{product_code}"'

        elif xtype == 'gift-sale':
            price = float(xcard.attrib['price'])
            product_code = xcard.attrib['product_code']
            self.add_line(product_code, price , 1, barcode = input_line, product_type='CARD')
            r.message = f'Добавляет в чек по цене "{price}" товар "{product_code}"'

        elif xtype == 'gift':
            #card_ID = input_line
            cash = float(xcard.attrib['cash'])
            reusable = xcard.attrib['reusable'] == '1'
            self.add_card(card_id, 'gift',  name, cash = cash, reusable=reusable)
            r.message = f'Добавляет в чек подарочную карту {card_id}, с отатком {cash}, многоразовая {reusable}'

        elif xtype == 'coupon':
            #card_ID = input_line
            self.add_card(card_id, 'coupon', name)
            r.message = f'Добавляет в чек купон {card_id}'

        elif xtype == 'discount':
            #card_ID = input_line
            try:
                points = xcard.attrib['points']
            except:
                points = 0
            self.add_card(card_id, 'discount', name, points=points)
            r.message = f'Добавляет в чек персональную карту {card_id}'

        else:
            r.error = True
            r.message = f'Неизвестный тип карты "{xtype}"'
            self.print_error(x, r.message)
            return r

        self.print_header(x, r.message)
        return r

    def print_header(self, log, text):
        pass
        #print(text)
    def print_comment(self, log, text):
        pass
        #print(text)
    def print_error(self, log, text):
        print(text)

    @property
    def CHECK_DATE(self):
        return self.date if self.date else datetime.datetime.now()

    def get_keywords(self, x):
        self.print_header(x, 'КАССА ВЫДАЕТ ЗАПРОС СЕРВЕРУ')
        xml_file = self.create_calc_xml_file(self.CHECK_DATE)
        r = self.POST(f'discount/active/python/get_keywords', xml_file, x)
        if r.error:
            return r
        if r.status_code != 200:
            r.error = True
            r.message = f'ОШИБКА "{r.status_code}" ДОСТУПА К СЕРВЕРУ {self.server}'
            self.print_error(x, r.message)
            return r
        xml = ET.fromstring(r.text)
        self.print_header(x, 'КАССА ВЫВОДИТ СПИСОК ПОЛУЧЕННЫХ СЛОВ')
        self.keywords = []
        for keyword in xml.findall('KEYWORD'):
            self.print_header(x, keyword.text)
            self.keywords.append(keyword.text) 
        self.print_header(x, f'Операция успешно выполнена за {r.ms} мс'.upper())
        r.error = False
        return r

#----------------------------------------------------------------
DOMINO_ROOT = '/DOMINO'
VALUES_FILE = os.path.join(DOMINO_ROOT, 'data','discount.def')
os.makedirs(os.path.dirname(VALUES_FILE), exist_ok=True)
VALUES = {}
try:
    with open(VALUES_FILE) as f:
        VALUES = json.load(f)
except:
    pass
def question(q):
    old_value = VALUES.get(q, '')
    new_value = input(f'{q} [{old_value}] ? ')
    if new_value != '':
        VALUES[q] = new_value
        with open(VALUES_FILE, 'w') as f:
            json.dump(VALUES, f)
        return new_value
    else:
        return old_value
#----------------------------------------------------------------

def h(text):
    print()
    print(text.upper())
    d = ('-'* len(text))
    print(d)

class PosRequest:
    def __init__(self, server, xml_file_src, check_date):
        self.server = server
        self.xml_file_src = xml_file_src
        self.check_date = check_date
        
        self.r = None
        self.time_ms = 0

    @property
    def xml_file(self):
        return self.xml_file_src.format(GUID=uuid.uuid4(), DATE=self.check_date.strftime('%Y-%m-%d %H:%M:%S'))
    
    @property
    def url(self):
        return self.r.url if self.r is not None else ''

    @property
    def status_code(self):
        return self.r.status_code if self.r is not None else ''

    @property
    def text(self):
        return self.r.text if self.r is not None else ''

    def request(self):
        start = datetime.datetime.now()
        self.r = requests.post(f'http://{self.server}/discount/active/python/calc', data={'xml_file': self.xml_file})
        self.time_ms = round((datetime.datetime.now() - start).total_seconds() * 1000, 3)

def pos_single_test(r):
    r.request()
    h('Запрос')
    print(r.url)
    h(f'Ответ : {r.status_code} : {r.time_ms} ms : {len(r.text)}')
    text = r.text.replace('<CHECK>', '<CHECK>\n')
    text = text.replace('<LINES>', '\n<LINES>')
    text = text.replace('</LINES>', '\n</LINES>\n')
    text = text.replace('<COMMENT>', '\n<COMMENT>')
    text = text.replace('<LINE ', '\n<LINE ')
    text = text.replace('</COUPONS>', '\n</COUPONS>')
    text = text.replace('<COUPONS>', '<COUPONS>\n')
    text = text.replace('<COUPON>', '\n<COUPON>')
    text = text.replace('</COUPONS>', '</COUPONS>\n')
    print(text)

#-----------------------------------------------------------------------
def pos_test(q, pos, check, CHECK_COUNT, CHECK_TIMEOUT, SERVER, LONG):
    print(f'pos {pos:3} : start {os.getpid()}')
    #checks = 0
    #errors = 0
    #max_time = None
    #min_time = None
    #total_time = 0
    #avg_time = 0

    calc_max = 0
    calc_min = None
    calc_time = 0
    calc_count = 0
    calc_error = 0
    calc_long = 0

    accept_min = None
    accept_max = 0
    accept_time = 0
    accept_count = 0
    accept_error = 0
    accept_long = 0

    pos = int(pos)
    for i in range(0, CHECK_COUNT):
        timeout = random.randrange(1, CHECK_TIMEOUT)
        sleep(timeout)
        #---------------------------------------
        check.next_check()
        r = check.calc()
        ms = r.ms
        calc_time += ms
        calc_count += 1
        if ms > calc_max:
            calc_max = ms
        if calc_min is None or ms < calc_min:
            calc_min = ms
        if ms > LONG:
            calc_long += 1
        if r.error:
            calc_error += 1
            print(f'CALC_ERROR pos {pos:3} : check {i:3} : {ms} ms')
        else:
            r = check.accept()
            accept_count += 1
            accept_time += r.ms
            if r.ms > accept_max:
                accept_max = r.ms
            if accept_min is None or r.ms < accept_min:
                accept_min = r.ms
            if r.ms > LONG:
                accept_long += 1
            if r.error:
                accept_error += 1
                print(f'ACCEPT_ERROR pos {pos:3} : check {i:3} : {r.ms + ms} ms')
            else:
                print(f'pos {pos:3} : check {i:3} : {round(ms, 3)} mс, {round(r.ms, 3)} мс')

    res = {}
    res['pos'] = pos
    res['calc_count'] = calc_count
    res['calc_time'] = calc_time
    res['calc_min'] = calc_min
    res['calc_max'] = calc_max
    res['calc_long'] = calc_long
    res['calc_error'] = calc_error

    res['accept_count'] = accept_count
    res['accept_time'] = accept_time
    res['accept_min'] = accept_min
    res['accept_max'] = accept_max
    res['accept_long'] = accept_long
    res['accept_error'] = accept_error

    q.put(res)
    print(f'pos {pos:3} : end')

if __name__ == "__main__":
    QUEUE = []
    LONG = 200

    server = question('Сервер')
    account_id = question('Учетная запись')

    try:
        r = requests.get(f'http://{server}/discount/active/python/get_test_checks?account_id={account_id}')
        checks = r.json()
    except BaseException as ex:
        print(f'{ex}')
        sys.exit(1)
    
    for ID, name in checks:
        print(ID, name)

    ID = int(question('Номер чека'))

    CHECK = PosCheck(account_id, ID)
    #r = requests.get(f'https://{server}/discount/active/python/get_test_check?account_id={account_id}&id={ID}', stream=True)
    r = requests.get(f'http://{server}/discount/active/python/get_test_check?account_id={account_id}&id={ID}')
    if r.status_code != 200:
        print(f'{r.status_code} {r.text}')
        sys.exit(1)
    CHECK.from_js(r.json())
    CHECK.server = server
    CHECK.test_mode = 1
    #r.raw.decode_content = True
    #dump = r.raw.read()
    #CHECK = pickle.loads(dump)
    print(f'{CHECK}')
    #--------------------------------------
    CHECK.next_check()
    r = CHECK.calc()

    if r.error:
        print(f'ОШИБКА : {r.message}')
        sys.exit(1)
    r = CHECK.accept()
    if r.error:
        print(f'ОШИБКА {r.message}')
        sys.exit(1)

    DATE = question('Дата чека (текущая дата ".")')
    if DATE and DATE.strip() and DATE.strip() != '.':
        CHECK.date = datetime.datetime.strptime(DATE, '%Y-%m-%d')
    else:
        CHECK.date = None
    POS_COUNT = int(question('Количество кассовых аппаратов'))
    CHECK_COUNT = int(question('Количество чеков'))
    CHECK_TIMEOUT = int(question('Среднее время на чек (с)'))

    start = datetime.datetime.now()
    process = []
    for pos in range(0, POS_COUNT):
        q = Queue()
        QUEUE.append(q)
        p = Process(target=pos_test, args=(q, pos, CHECK, CHECK_COUNT, CHECK_TIMEOUT, server, LONG))
        p.start()
        process.append(p)

    for p in process:
        p.join()
    end = datetime.datetime.now()

    #count = POS_COUNT * CHECK_COUNT

    #time_ms = (end - start).total_seconds() * 1000 

    total_calc_min = 0
    total_calc_max = 0
    total_calc_time = 0
    total_calc_count = 0
    total_calc_error = 0
    total_calc_long = 0

    total_accept_min = 0
    total_accept_max = 0
    total_accept_time = 0
    total_accept_count = 0
    total_accept_error = 0
    total_accept_long = 0

    for q in QUEUE:
        res = q.get()
        pos = res['pos']

        calc_min = res['calc_min']
        calc_max = res['calc_max']
        calc_long = res['calc_long']
        calc_time = res['calc_time']
        calc_count = res['calc_count']
        calc_error = res['calc_error']

        accept_min = res['accept_min']
        accept_max = res['accept_max']
        accept_long = res['accept_long']
        accept_time = res['accept_time']
        accept_count = res['accept_count']
        accept_error = res['accept_error']

        if calc_min > total_calc_min:
            total_calc_min = calc_min
        if calc_max > total_calc_max:
            total_calc_max = calc_max
        total_calc_count += calc_count
        total_calc_time += calc_time
        total_calc_error += calc_error
        total_calc_long += calc_long

        if accept_min > total_accept_min:
            total_accept_min = accept_min
        if accept_max > total_accept_max:
            total_accept_max = accept_max
        total_accept_count += accept_count
        total_accept_time += accept_time
        total_accept_error += accept_error
        total_accept_long += accept_long

    h('РЕЗУЛЬТАТ')
    print()
    print('РАСЧЕТЫ')
    print(f'Общее количество        {total_calc_count}')
    print(f'Долгие                  {total_calc_long} (более {LONG} мс)')
    print(f'Общее всемя             {total_calc_time} мс')
    print(f'Минимальное время       {total_calc_min} мс')
    print(f'Максимальное время      {total_calc_max} мс')
    print(f'Среднее время           {round(total_calc_time / total_calc_count, 3)}')
    print(f'Количество ошибок       {total_calc_error}')
    print()
    print('ПОСЛЕПРОДАЖНАЯ ОБРАБОТКА')
    print(f'Общее количество        {total_accept_count}')
    print(f'Долгие                  {total_accept_long} (более {LONG} мс)')
    print(f'Общее всемя             {total_accept_time} мс')
    print(f'Минимальное время       {total_accept_min} мс')
    print(f'Максимальное время      {total_accept_max} мс')
    print(f'Среднее время           {round(total_accept_time / total_accept_count, 3)}')
    print(f'Количество ошибок       {total_accept_error}')
    print()
    print('ОБЩИЕ ИТОГИ')
    print(f'Количество чеков        {total_accept_count}')
    print(f'Количество ошибок       {total_accept_error + total_calc_error}')
    print(f'Начало теста            {start}')
    print(f'Окончание теста         {end}')
    print(f'Продолжительность       {end - start}')
    print(f'Интенсивность           {round( total_accept_count / (end - start).total_seconds()  * 60, 6)} чек/мин')

    input()

