import json, datetime, arrow, re
from domino.core import log
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime, Date
from sqlalchemy.dialects.oracle import RAW, NUMBER
from domino.databases.oracle import Oracle, HexToRaw, RawToHex

class DB1_LINE(Oracle.Base):

    __tablename__ = 'db1_line'
    __table_args__ = {'extend_existing': True}

    id          = Column('id', RAW(8), primary_key=True)
    pid         = Column('pid', RAW(8))
    CLASS       = Column('class', NUMBER(10,0))
    TYPE        = Column('type', NUMBER(10,0))
    product_id  = Column('product', RAW(8))
    party_id    = Column('f12', RAW(8))
    document_id = Column('document', RAW(8))
    date        = Column('line_date', Date)

    @property
    def ID(self):
        return RawToHex(self.id)
    @property
    def PID(self):
        return RawToHex(self.pid)
    @property
    def product_ID(self):
        return RawToHex(self.product_id)
    @property
    def document_ID(self):
        return RawToHex(self.document_id)

    def __init__(self, document_id, pid = None, CLASS = None, TYPE = None, product_id = None, date = None):
        self.pid = pid
        self.CLASS = CLASS
        self.TYPE = TYPE
        self.product_id = product_id
        self.document_id = document_id
        self.date = date
        if not self.date:
            self.date = datetime.date.today()

    def __repr__(self):
        return f'<DB1_LINE(id={self.ID}, class={self.CLASS}, type={self.TYPE}>'
