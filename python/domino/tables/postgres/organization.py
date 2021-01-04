#import json, datetime, random, arrow, re
from sqlalchemy import Column, BigInteger, String, JSON, DateTime, Boolean
from domino.core import log
from domino.databases.postgres import Postgres

def on_activate(account_id, msglog):
    table = Postgres.Table(OrganizationTable)
    table.migrate(account_id, msglog)

class Organization(Postgres.Base):

    __tablename__ = 'organization'

    id          = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True)
    disabled    = Column(Boolean)
    inn         = Column(String)
    name        = Column(String)
    info        = Column(JSON)

    def __repr__(self):
         return f"<Oraganization(id={self.id} name='{self.name}')>" 

OrganizationTable = Organization.__table__
