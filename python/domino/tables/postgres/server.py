from sqlalchemy import Column, Integer, String, DateTime, insert
from sqlalchemy.dialects.postgresql import JSONB
from domino.core import log
from domino.databases.postgres import Postgres

def on_activate(account_id, msg_log = None):
    table = Postgres.Table(Server.__table__)
    table.migrate(account_id, msg_log)
    postgres = Postgres.Pool().session(account_id)
    try:
        server = postgres.query(Server).get('localhost')
        if not server:
            values = {
                'id' : 'localhost',
                'name' : 'ОСНОВНОЙ СЕРВЕР'
            }
            sql = insert(Server, values = values)
            postgres.execute(sql)
            msg_log(sql)
        postgres.commit()
    finally:
        postgres.close()
    
class Server(Postgres.Base):

    __tablename__ = 'server'

    id      = Column(String, primary_key=True, nullable=False)
    name    = Column(String)
    info    = Column(JSONB)

    def __repr__(self):
         return f"<Server(id={self.id})>" 


