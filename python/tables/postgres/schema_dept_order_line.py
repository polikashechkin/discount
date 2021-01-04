#import json, datetime, random, arrow, re
from domino.core import log
from sqlalchemy import Column, Index, String, BigInteger, DateTime, insert, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from domino.databases.postgres import Postgres

def on_activate(account_id, msglog):
    table = Postgres.Table(SchemaDeptOrderLineTable)
    table.migrate(account_id, msglog)

class SchemaDeptOrderLine(Postgres.Base):

    __tablename__ = 'schema_dept_order_line2'

    id              = Column(BigInteger, primary_key=True, autoincrement = True, nullable =False)
    order_id        = Column(BigInteger, nullable=False)
    dept_id         = Column(String, nullable=False)
    sign            = Column(Boolean)
    Index('', order_id, dept_id, unique=True)    

SchemaDeptOrderLineTable = SchemaDeptOrderLine.__table__


