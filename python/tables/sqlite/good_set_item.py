import json
from sqlalchemy import text as T
from domino.databases.sqlite import Sqlite, JSON
from sqlalchemy import Column, Index, BigInteger, Integer, String, SmallInteger, DateTime, text as T
from settings import MODULE_ID
from domino.core import log

def on_activate(account_id, on_activate_log):
    LOG = on_activate_log
    SQLITE = Sqlite.Pool().session(account_id, module_id=MODULE_ID)

    #has_table = SQLITE.get_bind().has_table('good_set_item')
    #LOG(table_esists)
    sql = '''
        create table if not exists good_set_item
        (
            id integer not null primary key,
            set_id integer not null,
            code text not null,
            price integer 
        )
    '''
    #LOG(sql)
    SQLITE.execute(T(sql))
    SQLITE.commit()
    sql = '''
        create unique index if not exists good_set_item_on_set_id_code on good_set_item(set_id, code);
    '''
    #LOG(sql)
    SQLITE.execute(T(sql))

    cur = SQLITE.execute('pragma table_info("good_set_item")')
    #LOG(f'{cur}')
    names = []
    for info in cur:
        names.append(info[1])
    
    # ПРЕОБРАЗОВАНИЕ
    exists = SQLITE.execute("select 1 from sqlite_master where type='table' AND name='product_set_item'").fetchone()
    if exists:
        exists = SQLITE.execute('select 1 from good_set_item limit 1').fetchone()
        if not exists:
            # еще нет ни обной записи в таблице
            count = 0 
            product_set_items = SQLITE.execute('select product_set, info from product_set_item').fetchall()
            #LOG(len(product_set_items))
            for set_id, INFO in product_set_items:
                #LOG(len(product_set_items))
                info = json.loads(INFO)
                code = info.get('code')
                PRICE = info.get('price')
                try:
                    price = int(PRICE*100) if PRICE else None
                except:
                    log.exception(__file__)
                    price = None
                if price:
                    if price < 0:
                        price = None
                    if price > 10_000_000_00:
                        price = 10_000_000_00
                count += SQLITE.execute(
                    'insert or ignore into good_set_item (set_id, code, price) values(:set_id, :code, :price)', 
                    {'set_id':set_id, 'code':code, 'price':price}
                    ).rowcount
            on_activate_log(f'good_set_item : Конвертировано {count} записей')
            SQLITE.commit()

class GoodSetItem(Sqlite.Base):

    __tablename__ = 'good_set_item'

    id              = Column(Integer, nullable=False, primary_key=True)
    set_id          = Column(Integer, nullable=False)
    code            = Column(String, nullable=False)
    price           = Column(Integer)

    #def __init__(self, set_id, e_code, good_code, price = None):
    #    self.set_id = set_id
    #    self.e_code = e_code
    #    self.type_ = 0
    #    self.info = {'code':good_code}
    #    if price:
    #        self.info['price'] = price

    #@property
    #def code(self):
    #    return self.info.get('code') 
    #@good_code.setter
    #def good_code(self, value):
    #    self.info['code'] = value

    @property
    def PRICE(self):
        return round(self.price / 100.0, 2) if self.price is not None else None
    @PRICE.setter
    def PRICE(self, value):
        self.price = int(value*100) if value is not None else None
    
    @staticmethod
    def add(SQLITE, set_id, code, price = None):
        sql = T('insert or replace into good_set_item (set_id, code, price) values (:set_id, :code, :price)')
        params = {'set_id':set_id, 'code':code, 'price':price}
        return SQLITE.execute(sql, params).rowcount
