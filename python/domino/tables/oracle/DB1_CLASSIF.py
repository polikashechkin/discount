import json, datetime, arrow, re
from domino.core import log
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.dialects.oracle import RAW, NUMBER
from domino.databases.oracle import Oracle, RawToHex

class DB1_CLASSIF(Oracle.Base):

    __tablename__ = 'db1_classif'
    
    id          = Column('id', RAW(8), primary_key=True)
    @property
    def ID(self):
        return RawToHex(self.id)
    pid         = Column('pid', RAW(8))
    @property
    def PID(self):
        return RawToHex(self.pid)
    
    CLASS       = Column('class', NUMBER(10,0))
    TYPE        = Column('type', NUMBER(10,0))
    disabled    = Column(NUMBER(10,0))
    name        = Column(String)
    code        = Column(String)

    def __repr__(self):
        return f'<DB1_CLASSIF(id={self.ID}, class={self.CLASS}, type={self.TYPE}>'
