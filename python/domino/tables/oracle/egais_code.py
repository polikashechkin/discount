import json, datetime, arrow, re
from domino.core import log
from sqlalchemy import Column, Integer, String, JSON, DateTime, Binary
from sqlalchemy import or_, and_
from sqlalchemy.orm import sessionmaker, synonym, aliased
from sqlalchemy.dialects.oracle import RAW, NUMBER
from domino.tables.oracle.DB1_PRODUCT import DB1_PRODUCT
from domino.databases.oracle import Oracle, RawToHex

class EgaisCode_(DB1_PRODUCT):

    __tablename__ = 'db1_product'
    __table_args__ = {'extend_existing': True}

    product_id = synonym(DB1_PRODUCT.pid)

    def __repr__(self):
        return f'<EgaisCode(code={self.code}, product_id={self.PID})>'
EgaisCode = aliased(EgaisCode_, name='egais_code')
EgaisCode.ClassType = and_(EgaisCode.CLASS == 66387969, EgaisCode.TYPE == 66387969)
#EgaisCode.ClassType = and_(EgaisCode.CLASS == 66387969, EgaisCode.TYPE == 66387969)
EgaisCodeTable = EgaisCode.__table__ 


