from sqlalchemy import Column, Index, BigInteger, Integer, String, JSON, DateTime, Boolean, and_, or_

from domino.core import log
from domino.databases.postgres import Postgres

def on_activate(account_id, msglog):
    table = Postgres.Table(Dictionary.__tablename__)
    table.column('row_id','bigserial not null primary key')
    table.column('state','integer not null default 0')
    table.column('class_id','varchar')
    table.column('type_id','varchar')
    table.column('e_code','varchar')
    table.column('code','varchar')
    table.column('name','varchar')
    table.column('info','jsonb')
    table.column('disabled', 'bool')

    table.index('class_id', 'type_id', 'name')
    table.index('class_id', 'type_id', 'e_code')

    table.migrate(account_id, msglog)

class Dictionary(Postgres.Base):

    __tablename__ = 'dictionary'.lower()

    id          = Column('row_id', BigInteger, primary_key=True, nullable=False, autoincrement=True)
    disabled    = Column(Boolean)
    state       = Column(Integer, default=0)
    CLASS       = Column('class_id', String)
    TYPE        = Column('type_id', String)
    e_code      = Column(String)
    code        = Column(String)
    name        = Column(String)
    info        = Column(JSON)

    Index('', CLASS, TYPE, name)
    Index('', CLASS, TYPE, e_code)

DictionaryTable = Dictionary.__table__
Dictionary.DeptColumns = and_(Dictionary.CLASS == 'dept', Dictionary.TYPE == 'column')

Postgres.Table(DictionaryTable)
