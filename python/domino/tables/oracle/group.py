import json, datetime, arrow, re
from domino.core import log, RawToHex, HexToRaw
from sqlalchemy import Column, Integer, String, JSON, DateTime, Binary
from sqlalchemy.dialects.oracle import RAW, NUMBER, DATE
#from domino.databases.oracle import Oracle
from sqlalchemy.orm import synonym, aliased
from sqlalchemy.types import TypeDecorator

from domino.tables.oracle.DB1_CLASSIF import DB1_CLASSIF

#class UNIT(TypeDecorator):
#    impl = RAW(8)
#    def process_bind_param(self, value, dialect):
#        return value.uid if value else None
#    def process_result_value(self, value, dialect):
#        return Unit.get(value)

class Group(DB1_CLASSIF):
    
    __tablename__ = 'db1_classif'
    __table_args__ = {'extend_existing': True}
    
    good_type_id = Column('f69009409', RAW(8))

    def __repr__(self):
        return f'<Group(id={self.ID}, class={self.CLASS}, type={self.TYPE}, name={self.name})>'

