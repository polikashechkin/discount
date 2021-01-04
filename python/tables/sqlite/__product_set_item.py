import json
from sqlalchemy import text as T
from domino.databases.sqlite import Sqlite, JSON
from sqlalchemy import Column, Index, BigInteger, Integer, String, SmallInteger, DateTime, text as T
from settings import MODULE_ID

def on_activate(account_id, on_activate_log):
    SQLITE = Sqlite.Pool().session(account_id, module_id=MODULE_ID)
    sql = '''
        create table if not exists product_set_item
        (
            ID integer not null primary key,
            TYPE integer not null default(0),
            product_set integer not null,
            code text not null,
            info blob default('{}')
        )
    '''
    #on_activate_log(sql)
    SQLITE.execute(T(sql))
    sql = '''
        create index if not exists product_set_item_on_product_set on product_set_item(product_set);
    '''
    #on_activate_log(sql)
    SQLITE.execute(T(sql))

    names = []
    for info in SQLITE.execute(T('pragma table_info("PRODUCT_SET_ITEM")')):
        names.append(info[1])

class ProductSetItem(Sqlite.Base):

    __tablename__ = 'product_set_item'

    id              = Column(Integer, nullable=False, primary_key=True)
    set_id          = Column('product_set', Integer, nullable=False)
    #type_           = Column('type', Integer)
    e_code          = Column('code', String)
    info            = Column(JSON)

    def __init__(self, set_id, e_code, good_code, price = None):
        self.set_id = set_id
        self.e_code = e_code
        self.type_ = 0
        self.info = {'code':good_code}
        if price:
            self.info['price'] = price

    @property
    def code(self):
        return self.info.get('code') 
    #@good_code.setter
    #def good_code(self, value):
    #    self.info['code'] = value

    @property
    def price(self):
        try:
            return float(self.info.get('price'))
        except:
            return None
    @price.setter
    def price(self, value):
        self.info['price'] = value
    
    @staticmethod
    def add(SQLITE, set_id, e_code, code, price = None):
        info = {'code':code}
        if price:
            info['price'] = price
        INFO = json.dumps(info)
        sql = T('insert or ignore into product_set_item (product_set, code, info) values (:set_id, :e_code, :info)')
        params = {'set_id':set_id, 'e_code':e_code, 'info':INFO}
        #r = SQLITE.execute(sql, {'set_id':set_id, 'info':INFO, 'e_code':e_code})
        return SQLITE.execute(sql, params).rowcount
