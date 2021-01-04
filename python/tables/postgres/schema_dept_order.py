#import json, datetime, random, arrow, re
from domino.core import log
from sqlalchemy import Column, Index, String, BigInteger, DateTime, insert, Integer
from sqlalchemy.dialects.postgresql import JSONB
from domino.databases.postgres import Postgres
from .schema_dept_order_line import on_activate as schema_dept_order_line_on_activate

def on_activate(account_id, msglog):
    table = Postgres.Table(SchemaDeptOrderTable)
    table.migrate(account_id, msglog)
    schema_dept_order_line_on_activate(account_id, msglog)

class SchemaDeptOrder(Postgres.Base):

    __tablename__ = 'schema_dept_order'

    id              = Column(BigInteger, primary_key=True, autoincrement = True, nullable =False)
    schema_id       = Column(Integer, nullable =False)
    info            = Column(JSONB)
    Index('', schema_id, unique=True)

    def __repr__(self):
        return f'<SchemaDeptOrder(id={self.id}, schema_id={self.schema_id})>'

SchemaDeptOrderTable = SchemaDeptOrder.__table__


