import json, datetime, arrow, re
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime, Binary
from sqlalchemy.dialects.oracle import RAW, NUMBER
from sqlalchemy import or_, and_
#from dicts.yes_no import YES

from domino.core import log
from domino.databases.oracle import Oracle, HexToRaw
from domino.tables.oracle.DB1_CLASSIF import DB1_CLASSIF

class AlcoType(DB1_CLASSIF):

    __tablename__ = 'db1_classif'
    __table_args__ = {'extend_existing': True}

    помарочный_учет = Column('f3342343', Oracle.YES_NO)
    
    #@property
    #def помарочный_учет(self):
    #    return self.f3342343 is not None and self.f3342343 == YES

    def __repr__(self):
        return f'<AcloType(id={self.ID})>'

AlcoType.ClassType = and_(AlcoType.CLASS == 1572865, AlcoType.TYPE == 54525954)
#AlcoType.ClassType = and_(AlcoType.CLASS == 28835869, AlcoType.TYPE == 43122699)

AlcoTypeTable = AlcoType.__table__ 


