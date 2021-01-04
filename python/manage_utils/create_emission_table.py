import os, sys, datetime, requests, pickle, json, uuid, sqlite3
import xml.etree.ElementTree as ET
from multiprocessing import Process, Queue
from time import sleep

python = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(python)

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

from discount.core import DISCOUNT_DB


if __name__ == "__main__":
    h('пересоздание таблицы emission')
    account_id = question('Учетная запись')
    with sqlite3.connect(DISCOUNT_DB(account_id)) as conn:
        #conn.executescript('drop table emission;')

        conn.executescript('''
        create table emission(
            id integer not null primary key,
            status integer not null default(-1),
            type not null,
            prefix,
            start,
            end,
            info blob
        );
        ''')
    

