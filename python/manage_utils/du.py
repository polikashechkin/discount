import os, sys, datetime, requests, pickle, json, sqlite3, arrow, subprocess
import xml.etree.ElementTree as ET
python = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(python)

from domino.core import log
from domino.cli  import print_comment, Console, print_header, print_warning
from domino.databases import Databases, table_exists, drop_table
from domino.account import find_account
from discount.core import DISCOUNT_DB, CARDS, CARDS_LOG
from discount.series import ТипКарты
from discount.cards import Card


def print_output(stdout):
    output = stdout.decode('utf-8')
    for s in output.split('\n'):
        try:
            size, folder = s.split('\t')
            print(f'{size:10} {folder}')
        except:
            pass


if __name__ == "__main__":
    console = Console(__file__)
    account_id = console.input('Учетная запись')
    account = find_account(account_id)
    if account is None:
        console.error(f'Нет такой учетной записи')
    print(f'{account.id}, {account.alias}, "{account.description}"')
    p = subprocess.run('du -d 0 -h /', shell=True, stdout=subprocess.PIPE, stderr=None)
    print_output(p.stdout)
    p = subprocess.run('du -d 0 -h /DOMINO', shell=True, stdout=subprocess.PIPE)
    print_output(p.stdout)
    p = subprocess.run(f'du -d 0 -h /DOMINO/accounts/{account.id}', shell=True, stdout=subprocess.PIPE)
    print_output(p.stdout)
    p = subprocess.run(f'du -d 0 -h /DOMINO/accounts/{account.id}/data/postgres', shell=True, stdout=subprocess.PIPE)
    print_output(p.stdout)
    p = subprocess.run(f'du -d 0 -h /DOMINO/accounts/{account.id}/data/discount', shell=True, stdout=subprocess.PIPE)
    print_output(p.stdout)
    p = subprocess.run(f'du -d 3 -h /DOMINO/accounts/{account.id}/data/discount/calc', shell=True, stdout=subprocess.PIPE)
    print_output(p.stdout)
    p = subprocess.run(f'du -d 3 -h /DOMINO/accounts/{account.id}/data/discount/checks', shell=True, stdout=subprocess.PIPE)
    print_output(p.stdout)


