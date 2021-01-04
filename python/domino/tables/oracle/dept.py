import json, datetime, arrow, re
from domino.core import log
from sqlalchemy import Column, Integer, String, JSON, DateTime, Binary
from sqlalchemy.dialects.oracle import RAW, NUMBER
from domino.databases.oracle import Oracle, RawToHex, HexToRaw
from domino.tables.oracle.DB1_AGENT import DB1_AGENT

class Dept(DB1_AGENT):

    __tablename__ = 'db1_agent'
    __table_args__ = {'extend_existing': True}

    fsrar_id    = Column('f66387969', RAW(8))
    @property
    def fsrar_ID(self):
        return RawToHex(self.fsrar_id)

    def __repr__(self):
         return f"<Dept(id={self.ID}, name={self.name})>" 

Dept.ClassType = (Dept.CLASS == 2, Dept.TYPE == 40566786)

DeptTable = Dept.__table__
    
#283[43122704] 0000011B02920010 "Образование : Длинная строка (2048)"





