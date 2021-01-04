import json, datetime
from domino.core import log
from sqlalchemy import Column, Integer, String, JSON, DateTime, and_, or_
from sqlalchemy.dialects.oracle import RAW, NUMBER
from domino.databases.oracle import Oracle, RawToHex

class DominoUser(Oracle.Base):

    __tablename__ = 'domino_user'
    
    id          = Column(RAW(8), primary_key=True)
    pid         = Column(RAW(8))
    CLASS       = Column('class', NUMBER(10,0))
    TYPE        = Column('type', NUMBER(10,0))
    disabled    = Column(NUMBER(10,0))
    name        = Column(String)
    full_name   = Column(String)
    staffer_id  = Column('f15859713', RAW(8)) # Сотрудник

    @property
    def ID(self):
        return RawToHex(self.id)
    
    @property
    def PID(self):
        return RawToHex(self.pid)

    @property
    def staffer_ID(self):
        return RawToHex(self.staffer_id)
         
    def __repr__(self):
        return f'<DominoUser(id={self.id}, class={self.CLASS}, type={self.TYPE}, name={self.name}>'

DominoUserTable = DominoUser.__table__
DominoUser.ClassType = and_(DominoUser.CLASS == 1, DominoUser.TYPE == 1)