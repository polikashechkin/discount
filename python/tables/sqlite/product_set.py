import time, json
from sqlalchemy import Column, Index, BigInteger, Integer, String, SmallInteger, DateTime, text as T, or_, and_

from domino.core import log
from domino.databases.sqlite import Sqlite, JSON
from settings import MODULE_ID

#from tables.sqlite.product_set_item import ProductSetItem
#from tables.sqlite.product_set_item import ProductSetItem as PSI
from tables.sqlite.good_set_item import GoodSetItem
from tables.sqlite.complex_good_set_item import ComplexGoodSetItem
from tables.sqlite.complex_good_set_item import ComplexGoodSetItem as CHILD
from tables.Good import Good

from domino.databases.postgres import Postgres

class ГотовыеНаборы:
    def __init__(self, SQLITE, LOG = None, bigsize = None):
        self.SQLITE = SQLITE
        self.LOG = LOG
        self.готовые_наборы = {}
        self.good_set_item = self.SQLITE.execute("select count(*) from sqlite_master where type='table' and name='good_set_item'").fetchone()[0]
        self.product_set_item = self.SQLITE.execute("select count(*) from sqlite_master where type='table' and name='product_set_item'").fetchone()[0]
        self.bigsize = bigsize
        
    def prepeare(self, LOG = None):
        start = time.perf_counter()
        if LOG:
            LOG.header(f'ПОДГОТОВКА ТОВАРНЫХ НАБОРОВ, БОЛЬШОЙ РАЗМЕР {self.bigsize if self.bigsize is not None else "НЕТ"}')
            #log.debug(f'{self.готовые_наборы}')
            for sets, готовый_набор in self.готовые_наборы.items():
                готовый_набор.prepeare(LOG)
        if LOG:
            LOG(f'ПОДГОТОВКА ТОВАРНЫХ НАБОРОВ', start)

    def готовый_набор(self, sets, name=None):
        start = time.perf_counter()
        if isinstance(sets, (list, tuple)):
            sets = tuple(sets)
        else:
            sets = tuple([sets])
        
        готовый_набор = None
        if len(sets):
            готовый_набор = self.готовые_наборы.get(sets)
            if not готовый_набор:
                #готовый_набор = _ГотовыйНабор.create(self, sets, name = f'Набор {sets}')
                готовый_набор = _ГотовыйНабор(self, sets)
            self.готовые_наборы[sets] = готовый_набор

        if self.LOG:
            self.LOG(f'{name} {sets}', start)

        return готовый_набор

class _ГотовыйНабор:
    def __init__(self, готовые_наборы, sets):
        self.готовые_наборы = готовые_наборы
        self.name = f'Набор {sets}'
        self._goods = {}
        self._goods_sets = set()
        self._queries = []
        self._groups = {}
        self._conditions = []
        self.is_bigsize = False
        for set_id in sets:
            self._add(set_id) 

    def __repr__(self):
        return f'{self.name}'

#    @staticmethod
#    def create(готовые_наборы, sets):
#        #start = time.perf_counter()
#        готовый_набор = None
#        if isinstance(sets, (list, tuple)):
#            for set_id in sets:
#                if готовый_набор is None:
#                    готовый_набор = _ГотовыйНабор(готовые_наборы, name)
#                готовый_набор._add(set_id) 
#        else:
#            if готовый_набор is None:
#                готовый_набор = _ГотовыйНабор(готовые_наборы, name)
#            готовый_набор._add(sets) 
#        return готовый_набор

    def _add(self, set_id):
        SQLITE = self.готовые_наборы.SQLITE
        set_id = int(set_id)
        ps = SQLITE.query(ProductSet).get(set_id)

        ps_type = ps.type_ if set_id >= 0 else ProductSet.ТОВАРНЫЙ_НАБОР

        if ps_type == ProductSet.ТОВАРНЫЙ_НАБОР:
            self._goods_sets.add(set_id)

        elif ps_type == ProductSet.ТОВАРНЫЙ_НАБОР_С_ЦЕНАМИ:
            self._goods_sets.add(set_id)

        elif ps_type == ProductSet.TYPE_GROUPS:
            for e_code, code in ps.group_query.items():
                self._groups[e_code] = code
 
        elif ps_type == ProductSet.ТОВАРНЫЙ_ЗАПРОС:
            self._queries.append(ps.query)

        elif ps_type == ProductSet.КОМПЛЕКСНЫЙ_НАБОР:
            childs = ComplexGoodSetItem.childs(SQLITE, set_id)
            for child_id in childs:
                self._add(child_id)

        elif ps_type == ProductSet.ВИРТУАЛЬНЫЙ_НАБОР:
            self._conditions.append(ps.condition)

    def prepeare(self, LOG = None):
        start = time.perf_counter()
        SQLITE = self.готовые_наборы.SQLITE
        if len(self._goods_sets):
            self.SETS = ','.join(map(str, self._goods_sets))
            #LOG(SETS)
            if self.готовые_наборы.good_set_item:
                start = time.perf_counter()
                count = SQLITE.execute(f'select count(*) from good_set_item where set_id in ({self.SETS})').fetchone()[0]
                #if LOG:
                #    LOG(f'найдено {count} товаров', start)
                if self.готовые_наборы.bigsize is not None:
                    if count > self.готовые_наборы.bigsize:
                        self.is_bigsize = True
                if LOG:
                    LOG(f'{self.name} : ({self.SETS}) товаров {count} {"БОЛЬШОЙ" if self.is_bigsize else ""}', start)
                if not self.is_bigsize:
                    #--------------------------------------------------
                    start = time.perf_counter()
                    cur = SQLITE.execute(f'select code, price from good_set_item where set_id in ({self.SETS})')
                    for code, price in cur:
                        PRICE = round(price/100,2) if price else None
                        self._goods[code] = PRICE
                    if LOG:
                        LOG(f'загружено {len(self._goods)} товаров', start)

            elif self.готовые_наборы.product_set_item:
                cur = SQLITE.execute(f'select info from product_set_item where product_set in ({self.SETS})')
                for INFO, in cur:
                    info = json.loads(INFO)
                    code = info.get('code')
                    price = info.get('price')
                    self._goods[code] = price
                if LOG:
                    LOG(f'{self.name} : {self._goods_sets}, загружено товаров {len(self._goods)}', start)

    def condition_match(self, condition, line):
        #log.debug(f'CONDITION {condition} {line.price}')
        price_digit = condition.get('price_format') # Совпадение формата цена
        #no_price_format = condition.get('no_price_format')
        #qrcode_format = condition.get('qrcode_format')
        exists = False
        if price_digit:
            exists = True
            digit = int(line.price) % 10
            if str(digit) == price_digit:
                #log.debug(f'return TRUE')
                return True

        #log.debug(f'return {not exists}')
        return not exists

    def __contains__(self, line):
        #log.debug(f'{line.product} {self.name} : {self._goods} : {self._queries} : {self._conditions}')
        #log.debug(f'{line.product} in {self._goods}')
        if self.is_bigsize:
            #start = time.perf_counter()
            sql = f"select count(*) from good_set_item where code='{line.product}' and set_id in ({self.SETS})"
            count = self.готовые_наборы.SQLITE.execute(sql).fetchone()[0]
            #log.debug(f'{count} = {sql}')
            if count:
                return True
        #start = time.perf_counter()        
        #ok = (line.product in self._goods)
        #end = time.perf_counter()
        #ms = round((end-start)*1000,2)
        #log.debug(f'{ms}')
        elif line.product in self._goods:
            #log.debug('True') 
            return True
        #log.debug(f'{line.group} in {self._groups}')
        if line.group in self._groups:
            #log.debug('True')
            return True
        for _query in self._queries:
            #log.debug(f'{line.product} in {_query}')
            if line.check.goods.match(line.product, _query):
                #log.debug('True')
                return True
        
        for condition in self._conditions:
            if self.condition_match(condition, line):
                return True
        #log.debug(f'Готовый набор: {line.product} => FALSE ({self.goods})')
        #log.debug('False')
        return False

    def get(self, line):
        if self.is_bigsize:
            sql = f"select price from good_set_item where code='{line.product}' and set_id in ({self.SETS})"
            r = self.готовые_наборы.SQLITE.execute(sql).fetchone()
            if r:
                return round(r[0]/100, 2)
            else:
                return None
        else:
            return self._goods.get(line.product)

    def filter(self):
        ff = [Good.code.in_(self._goods)]
        # --------------------------------
        ff.append(Good.local_group.in_(self._groups.values()))
        # --------------------------------
        for _query in self._queries:
            ff.append(Good.filter(_query))
        return or_(*ff)

    def query(self, postgres):
        return postgres.query(Good).filter(self.filter())

def on_activate(account_id, on_activate_log):
    SQLITE = Sqlite.Pool().session(account_id, module_id=MODULE_ID)
    sql = '''
    create table if not exists product_set
    (
        ID      integer not null primary key,
        CLASS   integer not null default(0),
        TYPE    integer not null default(0),
        state   integer not null default(0),
        info    blob default('{}')
    );
    '''
    #on_activate_log(sql)
    SQLITE.execute(T(sql))
    sql= '''
    insert or replace into product_set (ID, CLASS, TYPE, info)
    values (-4, 2, 104, '{"description":"ПОДАРОЧНЫЕ КАРТЫ"}');
    '''
    #on_activate_log(sql)
    SQLITE.execute(T(sql))
    sql = '''
    insert or replace into product_set (ID, CLASS, TYPE, info)
    values (-5, 2, 105, '{"description":"ДИСКОНТНЫЕ КАРТЫ"}');
    '''
    #on_activate_log(sql)
    SQLITE.execute(T(sql))
    sql = '''
    insert or replace into product_set (ID, CLASS, TYPE, info)
    values (-6, 2, 106, '{"description":"ПОСТОЯННО ИСКЛЮЧЕННЫЕ ТОВАРЫ"}');
    '''
    #on_activate_log(sql)
    SQLITE.execute(T(sql))

    names = []
    for info in SQLITE.execute(T('pragma table_info("PRODUCT_SET")')):
        names.append(info[1].upper())

    if 'SCHEMA_ID' not in names:
        sql = 'alter table PRODUCT_SET add SCHEMA_ID integer'
        SQLITE.execute(T(sql))
        on_activate_log(sql)
        sql = 'create index if not exists BY_SCHEMA on PRODUCT_SET(SCHEMA_ID);'
        SQLITE.execute(T(sql))
        on_activate_log(sql)

    SQLITE.query(ProductSet).filter(ProductSet.schema_id == None).update({ProductSet.schema_id : 0})        
    SQLITE.commit()

class ProductSet(Sqlite.Base):

    __tablename__ = 'product_set'

    ОБЩИЙ_НАБОР          = 0
    ИНДИВИДУАЛЬНЫЙ_НАБОР = 1

    ТОВАРНЫЙ_НАБОР = 0
    ТОВАРНЫЙ_НАБОР_С_ЦЕНАМИ = 1
    ТОВАРНЫЙ_ЗАПРОС = 2
    КОМПЛЕКСНЫЙ_НАБОР = 3
    TYPE_GROUPS = 4
    ВИРТУАЛЬНЫЙ_НАБОР = 5
    # парамтеры дополнительных учловий
    PRICE_FORMAT = 'price_format'
    NO_PRICE_FORMAT = 'no_price_format'
    QRCODE_FORMAT = 'qrcode_format'

    TYPE_NAMES = [
        'Товарный набор',
        'Набор товаров и цен',
        'Товарный запрос',
        'Комплексный набор',
        'Набор категорий',
        'Виртуальный набор'
    ]

    ДИСКОНТНЫЕ_КАРТЫ_ID = -5    
    ПОДАРОЧНЫЕ_КАРТЫ_ID = -4   
    ПОСТОЯННО_ИСКЛЮЧЕННЫЕ_ТОВАРЫ_ID = -6   
    DESCRIPTION = 'descripti on'
 
    id          = Column(Integer, nullable=False, primary_key=True)
    class_      = Column('class', Integer)
    type_       = Column('type', Integer)
    #state       = Column(Integer)
    schema_id   = Column(Integer)
    info        = Column(JSON)

    @staticmethod
    def TYPE_NAME(type_):
        try:
            return ProductSet.TYPE_NAMES[int(type_)]
        except:
            return f'{type_}' if type_ else ''

    @property
    def type_name(self):
        try:
            return ProductSet.TYPE_NAMES[int(self.type_)]
        except:
            return f'{self.type_}' if self.type_ else ''
    
    @property
    def condition(self):
        condition = self.info.get('condition')
        if condition is None:
            condition = {}
            self.info['condition'] = condition
        return condition

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

    def __repr__(self):
        return f'ProductSet({self.id}, {self.type_name}, query={self.query}'

    @property
    def name(self):
        return self.info.get('description', '')
    @name.setter
    def name(self, value):
        if self.info is not None:
            self.info['description'] = value
        else:
            self.info = {'description':value}

    def clean(self, SQLITE):
        #self.info = {}
        SQLITE.query(ComplexGoodSetItem).filter(ComplexGoodSetItem.set_id == self.id).delete()
        #SQLITE.query(ProductSetItem).filter(ProductSetItem.set_id == self.id).delete()
    @staticmethod
    def delete(SQLITE, set_id):
        SQLITE.execute(f'delete from good_set_item where set_id={set_id}')
        SQLITE.query(CHILD).filter(CHILD.set_id == set_id).delete()
        SQLITE.query(ProductSet).filter(ProductSet.id == set_id).delete()
        SQLITE.commit()


