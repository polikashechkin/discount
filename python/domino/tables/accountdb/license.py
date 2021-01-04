import json
from domino.core import log
from domino.databases.accountdb import Accountdb
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.sqlite import BLOB

def on_install(LOG):
    sql = '''
        create table if not exists license (
            account_id  text not null,
            product_id  text not null,
            object_id   text not null,
            date        text not null,
            info        blob,
            primary key(account_id, product_id, object_id) 
        )
        '''
    accountdb = Accountdb.Pool().session()
    accountdb.execute(sql)

class License(Accountdb.Base):

    __tablename__ = 'license'

    account_id      = Column(String, nullable=False, primary_key=True)
    product_id      = Column(String, nullable=False, primary_key=True)
    object_id       = Column(String, nullable=False, primary_key=True)
    date            = Column(DateTime, nullable=False)
    info            = Column(Accountdb.JSON)

LicenseTable = License.__table__
