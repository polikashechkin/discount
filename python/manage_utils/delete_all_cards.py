import os, sys, datetime, requests, pickle, json, sqlite3
import xml.etree.ElementTree as ET
python = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(python)

from domino.core import log
from domino.cli  import print_comment, Console, print_header, print_warning
from domino.databases import Databases, table_exists, drop_table
from domino.account import find_account
from discount.core import DISCOUNT_DB, CARDS, CARDS_LOG

if __name__ == "__main__":
    console = Console(__file__)
    print()
    print('УДАЛЕНИЕ ВСЕХ КАРТ')
    print()
    account_id = console.input('Учетная запись')
    account = find_account(account_id)
    if account is None:
        console.error(f'Нет такой учетной записи')

    database = Databases().get_database(account.id)
    conn = database.connect()
    with conn:
        cur = conn.cursor()
        cur.execute(f'delete from {CARDS}')
        cur.execute(f'delete from {CARDS_LOG}')
    conn.close()


