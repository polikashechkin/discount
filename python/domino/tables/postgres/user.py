#import json, datetime, random, arrow, re
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Binary
from domino.core import log
from domino.databases.postgres import Postgres, JSON
from domino.databases.oracle import RawToHex

from sqlalchemy import or_

def on_activate(account_id, msglog):
    postgres = Postgres.Pool().session(account_id)
    any_user = postgres.query(User).get(User.ANY_USER_ID)
    if not any_user:
        postgres.add(User(id=User.ANY_USER_ID, name = 'ANY_USER'))
        msglog(f'add ANY USER')
        postgres.commit()
    postgres.close()

class User(Postgres.Base):

    ANY_USER_ID = ''

    __tablename__ = 'user'

    id          = Column(String, primary_key=True)
    name        = Column(String)
    full_name   = Column(String)
    #sysadmin    = Column(Boolean)
    info        = Column(JSON)
    disabled    = Column(Boolean)
    uid         = Column(Binary)
    
    @property
    def UID(self):
        return RawToHex(self.uid)

    def __repr__(self):
         return f"<User(id={self.id} name='{self.name}')>" 

User.NotDisabled = or_(User.disabled == False, User.disabled == None)
UserTable = User.__table__

Postgres.Table(UserTable)

