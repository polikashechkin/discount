import json, datetime, os, sys
from sqlalchemy import Column, Index, BigInteger, Integer, String, JSON, Boolean, DateTime, text as T, or_, and_

from domino.core import log
from domino.databases.postgres import Postgres
from domino.tables.postgres.dictionary import Dictionary

class GoodParam(Postgres.Base):

    __tablename__ = 'good_param'

    column_id       = Column(String, primary_key=True, nullable=False)
    disabled        = Column(Boolean)
    name            = Column(String)
    info            = Column(JSON)

    def items(self, postgres):
        return postgres.query(Dictionary.code, Dictionary.name)\
            .filter(Dictionary.CLASS == 'good', Dictionary.TYPE == self.column_id)\
            .order_by(Dictionary.name).all()
    
GoodParamTable = GoodParam.__table__

Postgres.Table(GoodParamTable)

