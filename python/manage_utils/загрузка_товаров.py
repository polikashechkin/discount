import os, sys, datetime, requests, pickle, json, sqlite3
import xml.etree.ElementTree as ET
python = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(python)

from domino.core import log
from domino.cli  import print_comment, Console, print_header, print_warning
from domino.databases import Databases, table_exists, drop_table
from discount.core import DISCOUNT_DB
from domino.jobs import query_job2, start_job2, JOBS_DB, запустить_задачу

from domino.account import find_account

if __name__ == "__main__":
    console = Console(__file__)
    print_header(F'ЗАГРУЗКА ТОВАРОВ')
    print()
    account_id = console.input('Учетная запись')
    account = find_account(account_id)
    if account is None:
        console.error(f'Нет такой учетной записи')

    ID = запустить_задачу(account_id, 'discount', 'load', description='Загрузка товаров')
    #with sqlite3.connect(JOBS_DB) as connection:
    #    cursor = connection.cursor()
    #    ID = query_job2(cursor, account_id = account_id, product_id = 'discount', program = 'load', argv=[] )
    #    start_job2(cursor, ID)
    print(f'Запущена задача "{ID}"')

    #database = Databases().get_database(account_id)
    #print(database.uri)
    #conn = database.connect()
    #cur = conn.cursor()
    #cur.execute('''
    #    select p.code, p.name, g.name from db1_product p, db1_classif g where p.local_group  = g.id and g.type=14745602
    #    ''')
    #products = cur.fetchall()
    #conn.close()
    #print(len(products))
    #with sqlite3.connect(DISCOUNT_DB(account_id)) as conn:
    #    cur = conn.cursor()
    #    for product in products:
    #        cur.execute(
    #            'insert or replace into products (code, name) values(?,?)',
    #            [product[0], product[1]]
    #        )
