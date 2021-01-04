import json, sqlite3, datetime, arrow, re, pickle, os, json, time
from domino.core import log, Time, Bool
from discount.core import DISCOUNT_DB, PRODUCT_COLUMNS_FILE
from tables.Good import Good

class ProductSetItem:
    def __init__(self, ID = None, TYPE = 0, product_set=0, code = '', info = {}):
        self.ID = ID
        self.product_set = product_set
        self.TYPE = TYPE # 0 - товар 1 - Группа
        self.info = info
        self.code = str(code)
        #log.debug(f'{self.ID}, TYPE, product_set, code, {self.info}')
    @property
    def код(self):
        return self.info.get('code')
    def __str__(self):
        return f'ProductSetItem({self.ID}, {self.product_set}, {self.TYPE}, {self.code})'
    @property
    def это_товар(self):
        return self.TYPE == 0
    @property
    def это_товарная_группа(self):
        return self.TYPE == 1
    @это_товарная_группа.setter
    def это_товарная_группа(self, value):
        if value:
            self.TYPE = 1
        else:
            self.TYPE = 0

    @property
    def цена(self):
        try:
            return float(self.info.get('price'))
        except:
            return None
    @цена.setter
    def цена(self, value):
        self.info['price'] = value
    
    @property
    def description(self):
        try:
            return self.info.get('description', '')
        except:
            return f'{self.info}'
    @description.setter 
    def description(self, value):
        self.info['description'] = value

    @property
    def наименование(self):
        try:
            return self.info.get('description', '')
        except:
            return f'{self.info}'
    @наименование.setter 
    def наименование(self, value):
        self.info['description'] = value
    
    @staticmethod
    def _from_record(r):
        if r is None:
            return None
        else:
            ID, TYPE, product_set, code, INFO = r
            #log.debug(f'_from_record {ID}, TYPE, product_set, code, {INFO}')
            try:
                info = json.loads(INFO)
            except:
                info = {}
        return ProductSetItem(ID, TYPE, product_set, code, info)

    @staticmethod
    def get(cursor, ID):
        return ProductSetItem.findfirst(cursor, 'ID=?', [int(ID)])

    @staticmethod
    def findfirst(cursor, where_clause, params = []):
        q = f'select ID, TYPE, product_set, code, info from product_set_item where {where_clause}'
        cursor.execute(q, params)
        return ProductSetItem._from_record(cursor.fetchone())

    @staticmethod
    def findall(cursor, where_clause = None, params = []):
        items = []
        if where_clause is None:
            cursor.execute(f'select ID, TYPE, product_set, code, info from product_set_item')
        else:
            cursor.execute(f'select ID, TYPE, product_set, code, info from product_set_item where {where_clause}', params)
        for r in cursor:
            items.append(ProductSetItem._from_record(r))
        return items

    @staticmethod
    def count(cursor, where_clause = None, params = []):
        if where_clause is None:
            cursor.execute(f'select count(*) from product_set_item')
        else:
            cursor.execute(f'select count(*) from product_set_item where {where_clause}', params)
        return cursor.fetchone()[0]

    def create(self, cursor):
        cursor.execute('insert into product_set_item(TYPE, product_set, code, info) values (?,?,?,?)',
            [self.TYPE, self.product_set, str(self.code), json.dumps(self.info, ensure_ascii=False)])
        self.ID = cursor.lastrowid
        return self.ID

    def create_or_replace(self, cursor):
        cursor.execute('insert or replace into product_set_item(TYPE, product_set, code, info) values (?,?,?,?)',
            [self.TYPE, self.product_set, str(self.code), json.dumps(self.info, ensure_ascii=False)])
        self.ID = cursor.lastrowid

    def update(self, cursor):
        cursor.execute('update product_set_item set TYPE=?, product_set=?, code=?, info=? where ID=?',
            [self.TYPE, self.product_set, str(self.code), json.dumps(self.info, ensure_ascii=False), self.ID])

    def delete(self, cursor):
        ProductSetItem.deleteall(cursor, 'ID=?', [self.ID])
    
    @staticmethod
    def deleteall(cursor, where_clause, params=[]):
        #log.debug(f'deleteall(cursor, {where_clause}, {params})')
        cursor.execute(f'delete from product_set_item where {where_clause}', params)

class ГотовыйРеестрЦен:
    def __init__(self):
        self.goods = {}

    def items(self):
        return self.goods.items()

    def add(self, курсор, набор_ID):
        for item in ProductSetItem.findall(курсор, 'product_set=?', [набор_ID]):
            if item.это_товар:
                self.goods[item.код] = item.цена

    def добавить(self, курсор, набор_ID):
        for item in ProductSetItem.findall(курсор, 'product_set=?', [набор_ID]):
            if item.это_товар:
                self.goods[item.код] = item.цена
    
    def найти(self, строка):
        return self.goods.get(строка.product)

    def get(self, line):
        return self.goods.get(line.product)
    
    def __str__(self):
        return f'<ГотовыйРеестрЦен()>'

    def __contains__(self, line):
        return line.product in self.goods

class ГотовыйНабор:
    def __init__(self):
        self.goods = None
        self.groups = None
        self.queries = None

    @staticmethod
    def create(cursor, sets, value, LOG):
        start = time.pref_counter()
        for set_id in sets:
            if готовый_набор is None:
                готовый_набор = ГотовыйНабор()
            готовый_набор.add(cursor, set_id) 
        if LOG:
            LOG(f'<Набор {sets}>', start)

    def добавить(self, cursor, product_set_id, value = True):
        self.add(cursor, product_set_id, value)

    def add(self, cursor, product_set_id, value = True):
        ps = ProductSet.get(cursor, product_set_id)
        if product_set_id == ProductSet.ПОСТОЯННО_ИСКЛЮЧЕННЫЕ_ТОВАРЫ_ID:
            if self.goods is None:
                self.goods = {}
            cursor.execute(f'select info from product_set_item where product_set=?', [product_set_id])
            for INFO, in cursor:
                info = json.loads(INFO)
                code = info['code']
                self.goods[code] = value
        elif ps.TYPE == ProductSet.TYPE_PRODUCTS:
            if self.goods is None:
                self.goods = {}
            cursor.execute(f'select info from product_set_item where TYPE = 0 and product_set=?', [product_set_id])
            for INFO, in cursor:
                info = json.loads(INFO)
                code = info['code']
                self.goods[code] = value
        elif ps.TYPE == ProductSet.TYPE_PRODUCTS_AND_PRIRCES:
            if self.goods is None:
                self.goods = {}
            cursor.execute(f'select info from product_set_item where TYPE = 0 and product_set=?', [product_set_id])
            for INFO, in cursor:
                info = json.loads(INFO)
                code = info['code']
                price = info.get('price',0)
                self.goods[code] = price
        elif ps.TYPE == ProductSet.TYPE_GROUPS:
            if self.groups is None:
                self.groups = {}
            for e_code in ps.group_query:
                self.groups[e_code] = value
        elif ps.TYPE == ProductSet.TYPE_LIVE_PRODUCTS:
            if self.queries is None:
                self.queries = []
            query = {}
            for column_id, values in ps.query.items():
                if values is not None:
                    if isinstance(values, list):
                        query[column_id] = values
                    elif values:
                        query[column_id] = [values]
            self.queries.append([query, value])
            #log.debug(f'QUERIES {self.queries}')
    
    def __contains__(self, line):
        if self.goods is not None and line.product in self.goods:
            return True
        if self.groups is not None and line.group in self.groups:
            return True
        if self.queries is not None:
            for query, value in self.queries:
                if line.check.goods.match(line.product, query):
                    return True
        #log.debug(f'Готовый набор: {line.product} => FALSE ({self.goods})')
        return False

    def get(self, line, default = None):
        if self.goods is not None:
            value = self.goods.get(line.product)
            if value is not None: 
                return value
        if self.groups is not None:
            value = self.groups.get(line.group)
            if value is not None: 
                return value
        if self.queries is not None:
            for query, value in self.queries:
                if line.check.goods.match(line.product, query):
                    return value
        return default

class ProductSet:
    @staticmethod
    def create_structure(conn, log):
        cur = conn.cursor()
        sql = '''
        create table if not exists product_set
        (
            ID      integer not null primary key,
            CLASS   integer not null default(0),
            TYPE    integer not null default(0),
            state   integer not null default(0),
            info    blob default('{}')
        );

        -- insert or replace into product_set (ID, CLASS, TYPE, info)
        -- values (-1, 2, 101, '{"description":"КАРТЫ"}');

        --insert or replace into product_set (ID, CLASS, TYPE, info)
        --values (-2, 2, 102, '{"description":"АЛКОГОЛЬ"}');

        -- insert or replace into product_set (ID, CLASS, TYPE, info)
        -- values (-3, 2, 103, '{"description":"ТОВАРЫ С КРАСНОЙ ЦЕНОЙ"}');

        insert or replace into product_set (ID, CLASS, TYPE, info)
        values (-4, 2, 104, '{"description":"ПОДАРОЧНЫЕ КАРТЫ"}');

        insert or replace into product_set (ID, CLASS, TYPE, info)
        values (-5, 2, 105, '{"description":"ДИСКОНТНЫЕ КАРТЫ"}');

        insert or replace into product_set (ID, CLASS, TYPE, info)
        values (-6, 2, 106, '{"description":"ПОСТОЯННО ИСКЛЮЧЕННЫЕ ТОВАРЫ"}');

        -- insert or replace into product_set (ID, CLASS, TYPE, info)
        -- values (-20, 2, 120, '{"description":"ВСЕ ТОВАРЫ"}');

        create table if not exists product_set_item
        (
            ID integer not null primary key,
            TYPE integer not null default(0),
            product_set integer not null,
            code text not null,
            info blob default('{}')
        );
        create index if not exists product_set_item_on_product_set on product_set_item(product_set);
        '''
        conn.executescript(sql)
        names = []
        cur.execute('pragma table_info("PRODUCT_SET")')
        for info in cur:
            names.append(info[1].upper())
        if 'SCHEMA_ID' not in names:
            sql = 'alter table PRODUCT_SET add SCHEMA_ID integer'
            cur.execute(sql)
            log(sql)
            sql = 'create index if not exists BY_SCHEMA on PRODUCT_SET(SCHEMA_ID);'
            cur.execute(sql)
            log(sql)
        with conn:
            sql = 'update PRODUCT_SET set SCHEMA_ID = 0 where SCHEMA_ID is null'
            #log(sql)
            cur.execute(sql)

    TYPE_PRODUCTS = 0
    TYPE_PRODUCTS_AND_PRIRCES = 1
    TYPE_LIVE_PRODUCTS = 2
    TYPE_VIRTUAL_PRODUCTS = 3
    КОМПЛЕКСНЫЙ_НАБОР = 3
    TYPE_GROUPS = 4

    TYPE_NAMES = [
        'Товарный набор',
        'Набор товаров и цен',
        'Товарный запрос',
        'Комплексный набор',
        'Набор категорий'
    ]

    ДИСКОНТНЫЕ_КАРТЫ_ID = -5    
    ПОДАРОЧНЫЕ_КАРТЫ_ID = -4   
    ПОСТОЯННО_ИСКЛЮЧЕННЫЕ_ТОВАРЫ_ID = -6   
    
    DESCRIPTION = 'description'
    def __init__(self, ID = None, CLASS = 0, TYPE = 0, state=0, info = {}, schema_id = None):
        self.ID = ID
        self.CLASS = CLASS
        self.TYPE = int(TYPE)
        self.state = state
        self.schema_id = schema_id
        self.info = info
        #self._запрос = None

    @property
    def type_name(self):
        try:
            return ProductSet.TYPE_NAMES[self.TYPE] 
        except:
            return f'{self.TYPE}'
    @property
    def query(self):
        query = self.info.get('query')
        if query is None:
            query = {}
            self.info['query'] = query
        return query
    
    @property
    def group_query(self):
        query = self.info.get('group_query')
        if query is None:
            query = {}
            self.info['group_query'] = query
        return query

    def __str__(self):
        return f'ProductSet({self.ID})'

    def удалить_все_товары(self, курсор):
        ProductSetItem.deleteall(курсор, 'product_set=? and TYPE=?', [self.ID, 0])

    def update_goods_by_query(self, cursor, pg_cursor):
        self.удалить_все_товары(cursor)
        return self.add_goods_by_query(cursor, pg_cursor)

    def добавить_товар(self, курсор, e_code, code, name, теги, цена = None):
        item = ProductSetItem()
        item.product_set = self.ID
        item.info = {'code' : code, 'uid' : e_code, 'description' : name, 'теги' : теги}
        if цена is not None:
            item.цена = цена
        item.code = e_code
        try:
            item.create_or_replace(курсор)
            return 1
        except:
            return 0

    def add_good_by_code(self, cursor, pg_cursor, code, price = None):
        sql = f'select e_code, name, description from good where code = %s'
        pg_cursor.execute(sql, [code])
        added = 0
        for e_code, name, description in pg_cursor:
            added += self.добавить_товар(cursor, e_code, code, name, description, price)
        return added
    
    def select_goods_by_query(self, pg_cursor, order_by = 'order by name', limit = 200, good_code=None, good_name=None):
        where_claues = []
        params = []
        #---------------------------
        if self.TYPE == ProductSet.TYPE_GROUPS:
            query = {'local_group' : list(self.group_query.values())}
        else:
            query = self.query
        #---------------------------
        if good_name:
            query['name'] = good_name
        if good_code:
            query['code'] = good_code
        for column_id, value in query.items():
            column = Good.QueryColumn(column_id)
            if column is not None:
                column.where(where_claues, params, value)
                #log.debug(f'{column_id} {value} {where_claues} {params}')
        #---------------------------
        if len(where_claues) > 0:
            sql = f'select code, e_code, name, description from good where {" and".join(where_claues)} {order_by} limit {limit}'
        else:
            sql = f'select code, e_code, name, description from good {order_by} limit {limit}'
        #---------------------------
        pg_cursor.execute(sql, params)
        return pg_cursor.fetchall()

    def add_goods_by_query(self, cursor, pg_cursor):
        query = self.query
        added = 0
        #---------------------------
        where_claues = []
        params = []
        for column_id, value in query.items():
            column = Good.QueryColumn(column_id)
            if column is not None:
                column.where(where_claues, params, value)
        if len(where_claues) > 0:
            sql = f'select code, e_code, name, description from good where {" and ".join(where_claues)} '
        else:
            return 0
            #sql = f'select code, e_code, name, description from good'
        #---------------------------
        pg_cursor.execute(sql, params)
        for code, e_code, name, description in pg_cursor:
            added += self.добавить_товар(cursor, e_code, code, name, description)
        return added

    @property
    def это_персональный_набор(self):
        return self.CLASS == 1
    @property
    def это_реестр_цен(self):
        return self.TYPE == 1
    @property
    def это_живой_набор(self):
        return self.TYPE == 2
    
    @property
    def description(self):
        return self.info.get(ProductSet.DESCRIPTION, '')

    @property
    def наименование(self):
        return self.info.get(ProductSet.DESCRIPTION, '')
    @наименование.setter
    def наименование(self, value):
        self.info[ProductSet.DESCRIPTION] = value

    def get_type_name(self):
        name = ''
        if self.CLASS == 0:
            if self.TYPE == 0:
                name = 'Товарный набор'
            elif self.TYPE == 1:
                name = 'Товарный набор с ценами'
            elif self.TYPE == 2:
                name = 'Живой набор'
            else:
                name = f'<{self.TYPE}>'
        return name

    @property
    def полное_наименование(self):
        description = self.info.get(ProductSet.DESCRIPTION)
        if description and description.strip():
            return description
        else:
            return f'{self.get_type_name()} {self.ID}'
    
    @staticmethod
    def _from_record(r):
        if r is None:
            return None
        else:
            ID, CLASS, TYPE, state, INFO, schema_id = r
            try:
                info = json.loads(INFO)
            except:
                info = {}
        return ProductSet(ID, CLASS, TYPE, state, info, schema_id)

    @staticmethod
    def get(cursor, ID):
        return ProductSet.findfirst(cursor, 'ID=?', [int(ID)])

    @staticmethod
    def findfirst(cursor, where_clause, params = []):
        #log.debug(f'findfirst(cursor, {where_clause}, {params})')
        q = f'select ID, CLASS, TYPE, state, info, schema_id from product_set where {where_clause}'
        cursor.execute(q, params)
        return ProductSet._from_record(cursor.fetchone())

    @staticmethod
    def findall(cursor, where_clause = None, params = []):
        items = []

        if where_clause is None:
            sql = f'select ID, CLASS, TYPE, state, info, schema_id from product_set'
            cursor.execute(sql)
        else:
            sql = f'select ID, CLASS, TYPE, state, info, schema_id from product_set where {where_clause}'
            #log.debug(f'{sql} {params}')
            cursor.execute(sql, params)
        
        for r in cursor:
            items.append(ProductSet._from_record(r))
        return items

    @staticmethod
    def count(cursor, where_clause = None, params = []):
        if where_clause is None:
            cursor.execute(f'select count(*) from product_set')
        else:
            cursor.execute(f'select count(*) from product_set where {where_clause}', params)
        return cursor.fetchone()[0]


    def create(self, cursor):
        cursor.execute('insert into product_set(CLASS, TYPE, state, INFO, schema_id) values (?,?,?,?,?)',
            [self.CLASS, self.TYPE, self.state, json.dumps(self.info, ensure_ascii=False), self.schema_id])
        self.ID = cursor.lastrowid

    def update(self, cursor):
        cursor.execute('update product_set set CLASS=?, TYPE=?, state=?, info=?, schema_id=? where ID=?',
            [self.CLASS, self.TYPE, self.state, json.dumps(self.info, ensure_ascii=False), self.schema_id, self.ID])

    def delete(self, cursor):
        ProductSet.deleteall(cursor, 'ID=?', [self.ID])

    @staticmethod
    def deleteall(cursor, where_clause, params):
        cursor.execute(f'delete from product_set where {where_clause}', params)

ТоварныйНабор = ProductSet