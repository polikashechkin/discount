# -*- coding: utf-8 -*-
import os, sys, datetime, time, sqlite3, json, re
from domino.jobs import Proc
from domino.core import log, DOMINO_ROOT

from domino.databases.oracle import Databases
from domino.databases.postgres import Postgres

from discount.core import DISCOUNT_DB, PRODUCT_COLUMNS_FILE, DOMINO_LOG
#from discount.product_sets import ProductSet
from tables.Good import Good, QueryColumn
#from discount.user import User
from sqlalchemy.orm import sessionmaker
#import logging
from settings import MODULE_ID
from discount.page import DiscountPage as BasePage

from domino.pages import Title

TIMEOUT = 100
DESCRIPTION = 'Обновление справочников'
MODULE = 'discount'
PROC = 'load.py'

#305[14745604] 0000013100E10004 "Страна производства : Государство"

class ThePage(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.proc = Proc.get(self.account_id, MODULE_ID, PROC)

    def __call__(self):
        self.title(DESCRIPTION)
        p = self.text_block()
        p.text('''
        При импорте справичниов из Домино не всегда необходимо загружать все товары. Справочник в может быть 
        избыточен за счет товаров, потерявших актуальность.
        Для фильтрации таких товаров можно задать шаблон наименования (регулярное выражение) при
        совпадении с которым товар считается выбывшим из ассортимента.
        ''')
        self.print_toolbar()

    def print_toolbar(self):
        toolbar = self.toolbar('toolbar').mt(1)
        toolbar.item().input(label='Шаблон наименования', name='pattern', value=self.proc.info.get('pattern'))\
            .onkeypress(13, '.on_change', forms=[toolbar])

    def on_change(self):
        pattern = self.get('pattern')
        self.proc.info['pattern'] = pattern
        self.proc.save()
        self.print_toolbar()
        self.message(f'Шаблон наименования "{pattern}"')

class TheJob(Proc.Job):
    def __init__(self, ID):
        log.info(f'Запуск задачи {ID} : load')
        super().__init__(ID)
        self.db_connection = None
        self.db_cursor = None
        self.connection = None
        self.cursor = None
        self.database = None

    def __call__(self):
        self.log('НАЧАЛО РАБОТЫ')
        if self.account_id is None:
            self.error(f'Не задано учетной записи')
        self.database = Databases().get_database(self.account_id)
        self.db_connection = self.database.connect()
        self.db_cursor = self.db_connection.cursor()
        self.connection = sqlite3.connect(DISCOUNT_DB(self.account_id))
        self.cursor = self.connection.cursor()
        self.pg_connection = Postgres.connect(self.account_id)
        self.pg_cursor = self.pg_connection.cursor()

        with self.pg_connection:
            self.dowork()

        if self.db_connection is not None:
            self.db_connection.close()
        if self.connection is not None:
            self.connection.close()
        if self.pg_connection is not None:
            self.pg_connection.close()
        self.log('ЗАВЕРШЕНО УСПЕШНО')

    def dowork(self):
        pattern = self.info.get('pattern')
        self.pattern = None
        if pattern:
            self.log(f'Шаблон наименования "{pattern}"')
            self.pattern = re.compile(pattern)

        self.load_products()
        self.check_for_break()
        self.create_goods_json()
        self.check_for_break()
        #self.load_depts()
        #self.check_for_break()
        #self.загрузка_пользователей()
        #self.check_for_break()

    #def load_depts(self):
    #    self.log(f'ОБНОВЛЕНИЕ СПИСКА ПОДРАЗДЕЛЕНИЙ')
    #    sql = '''
    #        select code, name from db1_agent 
    #        where class=2 and type=40566786
    #    '''
    #    self.db_cursor.execute(sql)
    #    DEPTS = self.db_cursor.fetchall()
    #    upsert = '''
    #        insert into dept (ID, NAME)
    #        values (%s, %s)
    #        on conflict (ID)
    #        do update set (ID, NAME) = (%s, %s)
    #        '''
    #    with self.pg_connection:
    #        count = 0
    #        for ID, NAME in DEPTS:
    #            count += 1
    #            try:
    #                self.pg_cursor.execute(upsert, [ID, NAME, ID, NAME])
    #            except BaseException as ex:
    #                self.log(f'{ID}, {NAME} : {ex}')
    #                log.exception(__file__)
    #                self.pg_connection.commit()
    # ``       self.pg_connection.commit()
    #    self.log(f'Обработано {count} подразделений')

    #def add_user(self, ID, NAME, FULL_NAME):
    #    if FULL_NAME is None:
    #        FULL_NAME = ''
    #    FULL_NAME = FULL_NAME.strip()
    #    NAME = NAME.strip()
    #    User.upsert(self.pg_cursor, ID, NAME, FULL_NAME)

    #def загрузка_пользователей(self):
    #    self.log(f'ЗАГРУЗКА ПОЛЬЗОВАТЕЛЕЙ')
    #    sql = '''
    #        select domino.DominoUIDToString(id), name, full_name 
    #        from domino_user
    #        where CLASS = 1 and TYPE=1 and name is not null
    #        '''
    #    self.db_cursor.execute(sql)
    #    count = 0
    #    with self.connection, self.pg_connection:
    #        for ID, NAME, FULL_NAME in self.db_cursor:
    #            self.add_user(ID, NAME, FULL_NAME)
    #            count += 1
    #    self.log(f'Обработано {count} пользователей')
        #self.session.commit()

    def old_name(self, name):
        return self.pattern is not None and self.pattern.match(name) is not None

    def load_products(self):
        # получение обoщего списка полей из БД
        all_db_columns = set()
        sql = "select column_name from user_tab_columns where table_name = 'DB1_PRODUCT' "
        self.db_cursor.execute(sql)
        for column_id, in self.db_cursor:
                all_db_columns.add(column_id.lower())
        
        # выделение из них, тех известны и имеют какие то значения (используются)
        self.columns = [Good.QueryColumn('code'), Good.QueryColumn('name')]
        for column in Good.Columns.values():
            if column.ID in all_db_columns:
                if column.ID != 'code' and column.ID != 'name':
                    self.columns.append(QueryColumn(column))

        for column in self.columns:
            column.create(self.pg_cursor)
            column.load(self.pg_cursor)

        self.log(f'ПОЛУЧЕН СПИСОК ПОЛЕЙ ТОВАРА : {self.columns}')

        self.log(f'ЗАГРУЗКА ТОВАРОВ')

        pg_columns = []
        pg_values = []
        pg_set = []
        db_columns = []
        for column in self.columns:
            pg_values.append('%s') 
            pg_set.append(f'{column.pg_column}=%s') 
            pg_columns.append(column.pg_column)
            db_columns.append(column.db_column)

        db_select = f'select {" ,".join(db_columns)}, domino.DominoUIDToString(p.id) from db1_product p, db1_classif g where p.local_group  = g.id and g.type=14745602'
        pg_update = f'update "good" set {", ".join(pg_set)}, description=%s, modify_time=%s where "e_code"=%s'
        pg_select = f'select {", ".join(pg_columns)} from "good" where "e_code"=%s'
        pg_insert = f'insert into "good" ({", ".join(pg_columns)}, "e_code", description, "modify_time") values ({", ".join(pg_values)}, %s, %s, %s)'
        icols = range(len(self.columns))

        #self.log(f'{db_select}')
        #self.log(f'{pg_select}')
        #self.log(f'{pg_insert}')
        #self.log(f'{pg_update}')

        all_changed = 0
        count = 0
        updated = 0
        created = 0
        old = 0
        select_cursor = self.db_connection.cursor()
        select_cursor.execute(db_select)
        for db_row in select_cursor:
            count += 1
            #if count > 100:
            #    break
            if count % 10000 == 0:
                self.log(f'Обработано "{count}" товаров, обновлено {updated}, создано {created}, устаревших {old} ')
                self.pg_connection.commit()
            # ---------------------------------------------
            e_code = db_row[-1]
            db_row = list(db_row[:-1])
            name = db_row[1]
            #if count < 100:
            #    self.log(f'{name} : {self.old_name(name)}')
            if self.old_name(name):
                # Пометить товар как потерявщий актуальность 
                self.pg_cursor.execute('update good set state=-1 where e_code=%s', [e_code])
                old += 1
                continue
            # формирование словарей (без имен, только значения)
            description = {}
            for i in icols:
                column = self.columns[i]
                code, name = column.get_code_name_by_uid(self.pg_cursor, self.db_cursor, db_row[i])
                if name is not None:
                    description[column.name] = name 
                if code is not None:
                    db_row[i] = code
            description_json = json.dumps(description, ensure_ascii=False)
            #log.debug(f'{db_row} {description_json}')
            modify_time = datetime.datetime.now()
            # ---------------------------------------------
            self.pg_cursor.execute(pg_select, [e_code])
            pg_row = self.pg_cursor.fetchone()
            if pg_row is not None:
                changed = False
                for i in icols:
                    if pg_row[i] != db_row[i]:
                        changed = True
                        break
                if changed:
                    updated += 1
                    self.pg_cursor.execute(pg_update, list(db_row) + [description_json, modify_time, e_code])
            else: 
                created += 1
                #if created < 3:
                #    self.log(f'{pg_insert} {db_row}')
                self.pg_cursor.execute(pg_insert, list(db_row) + [e_code, description_json, modify_time])
        self.log(f'Обработано "{count}" товаров, обновлено {updated}, создано {created}, устаревших {old}')
        all_changed += created
        all_changed += updated
        self.log('СОСТАВ ТОВАРНЫХ СЛОВАРЕЙ')
        for column in self.columns:
            self.log(f'{column.type_id} : {column.name} : {len(column.get_names(self.pg_cursor))}')
        if all_changed:
            self.log('ОБНОВЛЕНИЕ ОПИСАНИЯ ТОВАРОВ')

        self.log('ПРОВЕРКА НА НЕИСПОЛЬЗУЕМЫЕ СПРАВОЧНИКИ')
        for column in Good.Columns.values():
            if column.is_dictionary:
                self.pg_cursor.execute('select count(*) from dictionary where class_id=%s and type_id=%s', ['good', column.ID])
                count = self.pg_cursor.fetchone()[0]
                self.pg_cursor.execute('update dictionary set state=%s where class_id=%s and type_id=%s and code=%s'\
                    ,[0 if count > 0 else 1, 'good', 'column', column.ID])

        #self.log('ОБНОВЛЕНИЕ ЖИВЫХ НАБОРОВ')
        #for живой_набор in ProductSet.findall(self.cursor, 'TYPE=2'):
        #    with self.connection, self.db_connection:
        #        товаров = живой_набор.update_goods_by_query(self.cursor, self.pg_cursor)
        #        self.log(f'{живой_набор.полное_наименование}, товаров {товаров}')

    def create_goods_json(self):
        self.log('ФОРМИРОВАНИЕ JSON ФАЙЛА')
        json_file = os.path.join(DOMINO_ROOT, 'accounts', self.account_id, 'data', 'discount', 'schemas', 'goods.json')
        OLD = None
        if os.path.isfile(json_file):
            with open(json_file) as f:
                OLD = f.read()
            
        rows = {}
        columns = []
        for column in Good.QueryColumns(self.pg_cursor):
            if column.is_dictionary:
                columns.append(column.ID)
        self.pg_cursor.execute(f'select code, {", ".join(columns)} from good where state=0')
        for row in self.pg_cursor:
            code = row[0]
            rows[code] = row[1:]
        goods = {'columns':columns, 'goods': rows}
        NEW = json.dumps(goods, ensure_ascii=False)
        if OLD is None or OLD != NEW:
            os.makedirs(os.path.dirname(json_file), exist_ok=True)
            with open(json_file, 'w') as f:
                f.write(NEW)
            self.log(f'ОБНОВЛЕНИЕ ФАЙЛА ТОВАРОВ {json_file} : {len(rows)}')
        else:
            self.log('ФАЙЛ ТОВАРОВ НЕ ОБНОВЛЕН')

if __name__ == "__main__":
    ID = sys.argv[1]
    try:
        with TheJob(ID) as job:
            job()
    except:
        log.exception(__file__)

