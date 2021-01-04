import json, datetime, arrow, re
from domino.core import log
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.dialects.oracle import RAW, NUMBER
from domino.databases.oracle import Oracle, RawToHex, HexToRaw

class DB1_AGENT(Oracle.Base):

    __tablename__ = 'db1_agent'
    __table_args__ = {'extend_existing': True}

    id          = Column('id', RAW(8), primary_key=True, nullable=False)
    pid         = Column('pid', RAW(8))
    CLASS       = Column('class', NUMBER(10,0), nullable=False)
    TYPE        = Column('type', NUMBER(10,0), nullable=False)
    disabled    = Column(NUMBER(10,0), nullable=False)
    name        = Column(String)
    code        = Column(String)

    @property
    def ID(self):
        return RawToHex(self.id)
    @property
    def PID(self):
        return RawToHex(self.pid)

    def __str__(self):
        return f'<DB1_AGENT(id={self.id}, class={self.CLASS}, type={self.TYPE}>'
