import json, datetime, arrow, re
from domino.core import log
from sqlalchemy import Column, Integer, String, JSON, DateTime, Binary
from sqlalchemy import or_, and_
from sqlalchemy.orm import sessionmaker, synonym, aliased
from sqlalchemy.dialects.oracle import RAW, NUMBER
from domino.tables.oracle.DB1_PRODUCT import DB1_PRODUCT
from domino.databases.oracle import Oracle, RawToHex

class Barcode_(DB1_PRODUCT):

    __tablename__ = 'db1_product'
    __table_args__ = {'extend_existing': True}

    product_id = synonym(DB1_PRODUCT.pid)
    qty = Column('f14745601', NUMBER(19,4))

    @property
    def pack_qty(self):
        return f'{self.qty}' if self.qty else None
 
    def __repr__(self):
        return f'<Barcode(code={self.code}, product_id={self.PID}), pack_qty = {self.pack_qty}, pack_name = {self.name})>'

Barcode = aliased(Barcode_, name='barcode')
Barcode.ClassType = and_(Barcode.CLASS == 14745603, or_(Barcode.TYPE == 14745604, Barcode.TYPE ==28835842))
BracodeTable = Barcode_.__table__ 


