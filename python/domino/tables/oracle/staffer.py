import json, datetime, arrow, re
from domino.core import log
from sqlalchemy import Column, Integer, String, JSON, DateTime, Binary, and_, or_
from sqlalchemy.dialects.oracle import RAW
from domino.databases.oracle import Oracle, RawToHex, HexToRaw

from domino.tables.oracle.DB1_AGENT import DB1_AGENT

class Staffer(DB1_AGENT):

    __tablename__ = 'db1_agent'
    __table_args__ = {'extend_existing': True}

StafferTable = Staffer.__table__
Staffer.ClassType = and_(Staffer.CLASS == 14745603, Staffer.TYPE == 14745623)

   

