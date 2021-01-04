#import json, datetime, random, arrow, re
from domino.core import log
import datetime
from sqlalchemy import Column, Index, String, BigInteger, DateTime, insert, Integer
from sqlalchemy.dialects.postgresql import JSONB
from domino.postgres import Postgres
from settings import MODULE_ID

def on_activate(account_id, msglog):
    table = Postgres.Table(ProtocolTable)
    table.migrate(account_id, msglog)

class Protocol(Postgres.Base):

    __tablename__ = 'protocol'

    id              = Column(BigInteger, primary_key=True, autoincrement = True, nullable =False)
    ctime           = Column(DateTime, nullable=False)
    description     = Column(JSONB)
    info            = Column(JSONB)
    user_id         = Column(String)
    module_id       = Column(String)
    schema_id       = Column(Integer)
    schema_name     = Column(String)
    Index('', ctime)
    Index('', user_id, ctime)
    Index('',module_id, user_id, ctime)

    @staticmethod
    def create(postgres, user_id, description, schema_id = None, info = None, module_id=MODULE_ID):
        protocol = Protocol(user_id = user_id, description=description, info=info if info else {}, schema_id = schema_id, ctime = datetime.datetime.now(), module_id = module_id)
        postgres.add(protocol)
        return protocol

    @staticmethod
    def insert(values):
        values[Protocol.ctime] = datetime.datetime.now()
        values[Protocol.module_id] = MODULE_ID
        return insert(ProtocolTable, values)

ProtocolTable = Protocol.__table__


