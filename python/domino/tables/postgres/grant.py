from domino.core import log
from domino.databases.postgres import Postgres
from sqlalchemy import Column, Index, Integer, BigInteger, String, DateTime, Date, or_, and_
from sqlalchemy.dialects.postgresql import JSONB

def on_activate(account_id, on_activate_log):
    on_activate_log(f'УСТАРЕВШИЙ ВЫЗОВ Grant.on_activate()')

class Grant(Postgres.Base):

    NOOBJECT = ' '

    SYSADMIN            = 1
    MANAGER             = 2
    
    __grant_names__ = {
        1 : 'Системный администратор',
        2 : 'Управляющий'
    }
    
    __tablename__ = 'grant'

    id          = Column(Integer, primary_key = True, nullable=False, autoincrement=True)
    module_id   = Column(String, nullable=False)
    user_id     = Column(String, nullable=False)
    grant_id    = Column(Integer, nullable=False)
    object_id   = Column(String)
    info        = Column(JSONB)
    Index('' , module_id, user_id, grant_id, object_id, unique=True)

    @staticmethod
    def grant_name(grant_id):
        #log.debug(f'{grant_id}')
        return Grant.__grant_names__.get(grant_id, f'{grant_id}')

def __repr__(self):
    return f'<Grant(id={self.id}, module_id={self.module_id}, grant_id={self.grant_id}, user_id={self.user_id})>'

Grant.NoObject = or_(Grant.object_id == '', Grant.object_id == ' ')
GrantTable = Grant.__table__

Postgres.Table(GrantTable)


