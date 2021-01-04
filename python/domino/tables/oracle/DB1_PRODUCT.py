import json, datetime, arrow, re
from domino.core import log
from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.dialects.oracle import RAW, NUMBER
from domino.databases.oracle import Oracle, RawToHex, HexToRaw

class DB1_PRODUCT(Oracle.Base):

    __tablename__ = 'db1_product'
    __table_args__ = {'extend_existing': True}
    
    id = Column('id', RAW(8), primary_key=True)
    pid = Column('pid', RAW(8))
    CLASS = Column('class', Integer)
    TYPE = Column('type', Integer)
    name = Column(String)
    code = Column(String)

    @property
    def ID(self):
        return RawToHex(self.id)
    @property
    def PID(self):
        return RawToHex(self.pid)

    def __repr__(self):
        return f'<DB1_PRODUCT(id={self.id}, class={self.CLASS}, type={self.TYPE}, name={self.name}>'


