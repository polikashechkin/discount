import os, sys, datetime, requests, pickle, json, uuid
import xml.etree.ElementTree as ET
from multiprocessing import Process, Queue
from time import sleep

DIR = os.path.dirname(os.path.abspath(__file__))
VALUES_FILE = 'calc_emi.def'
VALUES = {}

try:
    with open(os.path.join(DIR, VALUES_FILE)) as f:
        VALUES = json.load(f)
except:
    pass

def question(q):
    old_value = VALUES.get(q, '')
    new_value = input(f'{q} [{old_value}] ? ')
    if new_value != '':
        VALUES[q] = new_value
        with open(os.path.join(DIR, VALUES_FILE), 'w') as f:
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
    def __init__(self, server, xml_file):
        self.server = server
        self.xml_file = xml_file
        
        self.r = None
        self.time_ms = 0

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
        data = {'xml_file': self.xml_file}
        self.r = requests.post(f'https://{self.server}/discount/active/python/get_keywords',  data=data)
        self.time_ms = round((datetime.datetime.now() - start).total_seconds() * 1000, 3)

def pos_test(r):
    r.request()
    h('Запрос')
    print(r.url)
    h(f'Ответ : {r.status_code} : {r.time_ms} ms : {len(r.text)}')
    text = r.text.replace('<KEYWORD>', '\n<KEYWORD>')
    text = text.replace('</KEYWORDS>', '\n</KEYWORDS>')
    print(text)

if __name__ == "__main__":
    
    server = question('Сервер')
    account_id = question('Учетная запись')
    check_date = question('Дата чека')
    check_dept_code = question('Подразделение')

    xml = ET.fromstring('<CHECK/>')
    xparams = ET.SubElement(xml, 'PARAMS')
    xparams.attrib['ACCOUNT_ID'] = account_id
    xparams.attrib['CHECK_DATE'] = check_date
    xparams.attrib['CHECK_DEPT_CODE'] = check_dept_code
    xml_file_src = ET.tostring(xml, encoding='utf-8').decode('utf-8')

    r = PosRequest(server, xml_file_src)
    h('Чек')
    print(r.xml_file)
    pos_test(r)
