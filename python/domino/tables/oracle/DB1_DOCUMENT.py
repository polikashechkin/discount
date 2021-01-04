import json, datetime, arrow, re
from domino.core import log
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime, Date
from sqlalchemy.dialects.oracle import RAW, NUMBER
from domino.databases.oracle import Oracle, RawToHex, HexToRaw

class DB1_DOCUMENT(Oracle.Base):

    __tablename__ = 'db1_document'
    __table_args__ = {'extend_existing': True}
    
    id              = Column('id', RAW(8), primary_key=True, nullable=False)
    pid             = Column('pid', RAW(8))
    CLASS           = Column('class', NUMBER(10,0), nullable=False)
    TYPE            = Column('type', NUMBER(10,0), nullable=False)
    disabled        = Column(NUMBER(10,0), nullable=False)
    state           = Column(NUMBER(10,0), nullable=False)
    name            = Column(String)
    code            = Column(String)
    date            = Column('doc_date', Date, nullable=False)
    dept_id         = Column('department', RAW(8), nullable=False)
    partner_id      = Column('partner', RAW(8))
    partner_doc     = Column('partn_doc', String)
    partner_date    = Column('partn_date', Date)

    @property
    def ID(self):
        return RawToHex(self.id)
    @property
    def PID(self):
        return RawToHex(self.pid)
    @property
    def dept_ID(self):
        return RawToHex(self.dept_id)
    @property
    def partner_ID(self):
        return RawToHex(self.partner_id)

    def __repr__(self):
        return f'<DB1_DOCUMENT(id={self.id}, class={self.CLASS}, type={self.TYPE}>'
