import os, sys, datetime, requests, pickle, json, uuid, arrow
import xml.etree.ElementTree as ET
from multiprocessing import Process, Queue
from time import sleep

#DIR = os.path.dirname(os.path.abspath(__file__))
DIR = '/DOMINO/data/test/discount/'
os.makedirs(DIR, exist_ok=True)
VALUES_FILE = os.path.join(DIR, 'calc_emi.def')
VALUES = {}
os.makedirs(os.path.dirname(VALUES_FILE), exist_ok=True)
try:
    with open(os.path.join(VALUES_FILE)) as f:
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
        self.r = requests.post(f'https://{self.server}/discount/active/python/calc', data={'xml_file': self.xml_file})
        self.time_ms = round((datetime.datetime.now() - start).total_seconds() * 1000, 3)

def pos_test(r):
    r.request()
    h('Запрос')
    print(r.url)
    h(f'Ответ : {r.status_code} : {r.time_ms} ms : {len(r.text)}')
    text = r.text.replace('<CHECK>', '<CHECK>\n')
    text = text.replace('<LINES>', '\n<LINES>')
    text = text.replace('</LINES>', '\n</LINES>\n')
    text = text.replace('<COMMENT>', '\n<COMMENT>')
    text = text.replace('</COMMENTS>', '\n</COMMENTS>')
    text = text.replace('<LINE ', '\n<LINE ')
    text = text.replace('</COUPONS>', '\n</COUPONS>')
    text = text.replace('<COUPONS>', '<COUPONS>\n')
    text = text.replace('<COUPON>', '\n<COUPON>')
    text = text.replace('</COUPONS>', '</COUPONS>\n')
    print(text)

if __name__ == "__main__":
    
    server = question('Сервер')
    #account_id = question('Учетная запись')
    check_date = question('Дата чека')
    if check_date == '.':
        check_date = datetime.datetime.now()
    else:
        check_date = arrow.get(check_date).datetime
    print (f'{check_date:%Y-%m-%d %H:%M:%S}')
    filename = question('Имя файла чека')
    file = os.path.join(DIR,'calc', filename + '.xml')
    xml_file_src = open(file).read()
    xml = ET.fromstring(xml_file_src)
    xparams = xml.find('PARAMS')
    account_id = xparams.attrib['ACCOUNT_ID']
    print(f'Учетная запись {account_id}')
    r = PosRequest(server, xml_file_src, check_date)
    h('Чек')
    print(r.xml_file)
    pos_test(r)
    while True:
        print()
        input('Нажмите любую клавишу для повторного теста')
        pos_test(r)
