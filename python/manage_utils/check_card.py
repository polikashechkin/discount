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
    def __init__(self, server, account_id, card_id):
        self.server = server
        self.account_id = account_id
        self.card_id = card_id
        
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
        data = {'account_id': self.account_id, 'card_id':self.card_id}
        self.r = requests.get(f'https://{self.server}/discount/active/python/check_card',  params=data)
        self.time_ms = round((datetime.datetime.now() - start).total_seconds() * 1000, 3)

def pos_test(r):
    r.request()
    h('Запрос')
    print(r.url)
    h(f'Ответ : {r.status_code} : {r.time_ms} ms : {len(r.text)}')
    print(r.text)

if __name__ == "__main__":
    
    server = question('Сервер')
    account_id = question('Учетная запись')
    card_id = question('Номер карты')

    r = PosRequest(server, account_id, card_id)
    pos_test(r)
