import os, sys, sqlite3

#----------------------------------
try:
    import barcode
except Exception as ex:
    print(f'{ex}')
    os.system('pip3 -q install python-barcode')
    import barcode
#----------------------------------
try:
    import PIL
except Exception as ex:
    print(f'{ex}')
    os.system('pip3 -q install Pillow')
    import PIL
#----------------------------------
try:
    import barcodenumber
except Exception as ex:
    print(f'{ex}')
    os.system('pip3 -q install barcodenumber')
    import barcodenumber
#----------------------------------

from domino.core import log, Version
from domino.account import Account, find_account

#from domino.databases import Databases, table_exists, drop_table
from domino.cli import print_warning, print_error, print_comment, Console
from domino.jobs import Proc
from domino.server import Server
from discount.core import DISCOUNT_DB, CARDS
from discount.checks import Check
from discount.cards import Card, CardLog
#from discount.depts import Dept
#from discount.product_sets import ProductSet
import discount.actions 

from domino.databases.postgres import Postgres
from domino.databases.sqlite import Sqlite

from tables.Good import Good

import domino.tables.postgres.user
import domino.tables.postgres.grant
import domino.tables.postgres.dept
import domino.tables.postgres.dept_param
import domino.tables.postgres.dictionary
import domino.tables.postgres.request_log

import tables.postgres.protocol
import tables.postgres.schema_dept_order
import domino.tables.postgres.report
#import domino.tables.postgres.report_line

import tables.sqlite.dept_set_item
import tables.sqlite.product_set
import tables.sqlite.action_set_item
#import tables.sqlite.product_set_item
import tables.sqlite.good_set_item
import tables.sqlite.complex_good_set_item

import tables.sqlite.schema

PRODUCT_ID = 'discount'

def msglog(msg) : print(msg)
def print_msg(msg) : print(msg)

def on_activate_log(msg) : print(msg)

def create_structure(account):

    os.makedirs(os.path.dirname(DISCOUNT_DB(account.id)), exist_ok=True)
    
    discount.actions.create_structure(account.id, print_msg)

    with sqlite3.connect(DISCOUNT_DB(account.id)) as conn:

        #ProductSet.create_structure(conn, print)

        conn.executescript('''
        create table if not exists emission(
            id integer not null primary key,
            status integer not null default(-1),
            type not null,
            prefix,
            start,
            end,
            info blob
        );

        insert or ignore into emission (id, type, info)
        values (0, "C04", '{}');

        create table if not exists discount_scheme(
            action_id integer not null primary key, 
            action_type not null, 
            status int not null default(0),
            info blob
            );

        create table if not exists dept_set
        (
            ID integer not null primary key,
            CLASS integer not null default(0),
            TYPE integer not null default(0),
            state integer not null default(0),
            info blob default('{}')
        );
        
        create table if not exists dept_set_item
        (
            ID integer not null primary key,
            TYPE integer not null default(0),
            dept_set integer not null,
            code string not null,
            info blob default('{}')
        );

        create unique index if not exists dept_by_code
        on dept_set_item(TYPE, dept_set, code);

        --create table if not exists schema
        --(
        --    ID integer not null primary key,
        --    TYPE integer not null default(0),
        --    info blob default('{}')
        --);

        -- create table if not exists users
        -- (
        --  ID text not null primary key,
        -- TYPE integer not null default(0),
        --    STATE integer not null default(0),
        --    NAME text not null,
        --    INFO blob default('{}')
        --);

        --create table if not exists test_cards
        --(
        --    CARD_ID text not null primary key
        --);

        --create table if not exists DICTIONARY
        --(
        --    ID integer not null primary key,
        --    PID integer,
        --    STATE integer not null default(0),
        --    CLASS integer not null,
        --    TYPE integer not null,
        --    UID text,
        --    CODE text,
        --    NAME text,
        --    INFO blob default ('{}')
        --);

        --insert or replace into DICTIONARY (ID, CLASS, TYPE, NAME)
        --values (-1, 100, 0, 'Код' );
        --insert or replace into DICTIONARY (ID, CLASS, TYPE, NAME)
        --values (-2, 100, 1, 'Наименование');
        --insert or replace into DICTIONARY (ID, CLASS, TYPE, NAME)
        --values (-3, 100, 2, 'Группа');

        create table if not exists TEST_CHECKS
        (
            ID integer not null primary key,
            STATE integer not null default(0),
            CLASS integer not null default(0),
            TYPE integer not null default(0),
            NAME text,
            INFO blob default ('{}')
        );

        '''
        )
        cur = conn.cursor()

        # Добавление ОСНОВНОЙ_СХЕМЫ если ее нет 
        
        #cur.execute('select count(*) from schema where ID=0;')
        #count = cur.fetchone()[0]
        #if count == 0:
        #    cur.execute(''' 
        #        insert or replace into schema (ID, info) 
        #        values (0, '{"description":"ОСНОВНАЯ СХЕМА"}')
        #        ''')

if __name__ == "__main__":
    try:
        account_id = sys.argv[1]
    except: 
        print(f'НЕ ЗАДАНА УЧЕТНАЯ ЗАПИСЬ')
        sys.exit(1)

    account = find_account(account_id)
    if account is None:
        error = f'Не найдена учетная запись'
        print(error)
        sys.exit(1)

    #Postgres.create_database(account_id, print)
    Postgres.on_activate(account_id, print)

    Check.on_activate(account_id, print)
    Good.on_activate(account_id, print)
    Card.on_activate(account_id, print)
    CardLog.on_activate(account_id, print)

    domino.tables.postgres.user.on_activate(account_id, on_activate_log)
    domino.tables.postgres.grant.on_activate(account_id, on_activate_log)
    domino.tables.postgres.dept_param.on_activate(account_id, on_activate_log)
    domino.tables.postgres.dept.on_activate(account_id, on_activate_log)
    domino.tables.postgres.dictionary.on_activate(account_id, on_activate_log)
    #domino.tables.postgres.request_log.on_activate(account_id, on_activate_log)
    #domino.tables.postgres.report.on_activate(account_id, on_activate_log)
    #domino.tables.postgres.report_line.on_activate(account_id, on_activate_log)

    tables.postgres.protocol.on_activate(account_id, on_activate_log)
    tables.postgres.schema_dept_order.on_activate(account_id, on_activate_log)

    tables.sqlite.schema.on_activate(account_id, on_activate_log)
    tables.sqlite.product_set.on_activate(account_id, on_activate_log)
    #tables.sqlite.product_set_item.on_activate(account_id, on_activate_log)
    tables.sqlite.action_set_item.on_activate(account_id, on_activate_log)
    tables.sqlite.good_set_item.on_activate(account_id, on_activate_log)

    tables.sqlite.complex_good_set_item.on_activate(account_id, on_activate_log)

    import procs.calc_discount 
    import export_cards
    import procs.cleaning

    procs.cleaning.on_activate(account_id, on_activate_log)

    Proc.create(account_id, PRODUCT_ID, 'load.py', description='Обновление справочников', url='load')
    Proc.create(account_id, PRODUCT_ID, procs.calc_discount.PROC, description=procs.calc_discount.DESCRIPTION, url='calc_discount')
    Proc.create(account_id, PRODUCT_ID, 'remove_checks.py', description='Удаление чеков', url='remove_checks')
    export_cards.on_activate(account_id, print)

    #Proc.create(account.id, PRODUCT_ID, 'export_cards.py', description='Выгрузка карт', url='export_cards')

    Proc.delete(account_id, PRODUCT_ID, 'cleaning.py')
    Proc.delete(account_id, PRODUCT_ID, 'procs/load_cards.py')
    Proc.delete(account_id, PRODUCT_ID, 'load_cards.py')
    Proc.delete(account_id, PRODUCT_ID, 'card_report.py')
    Proc.delete(account_id, PRODUCT_ID, 'checks_report.py')
    #Proc.create(account.id, PRODUCT_ID, 'checks_report.py', description='Отчет за текущий месяц', url='checks_report')

    create_structure(account)

    # -----------------------------------------------
    from tables.sqlite.product_set import ProductSet
    #POSTGRES = Postgres.Pool().session(account_id)
    SQLITE = Sqlite.Pool().session(account_id, module_id='discount')
    for ps in SQLITE.query(ProductSet).filter(ProductSet.type_ == ProductSet.TYPE_GROUPS):
        print(f'{ps.id} : {ps.name} : {ps.type_name} : {ps.group_query} : {ps.query}')
        ps.info['query'] = {'local_group' : list(ps.group_query.values())}
        ps.type_ = ProductSet.ТОВАРНЫЙ_ЗАПРОС
    SQLITE.commit()
    
