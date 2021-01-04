import datetime
from sqlalchemy import Column, Integer, BigInteger, String, JSON, DateTime, insert, Binary
from domino.core import log
from domino.databases.postgres import Postgres
from .dictionary import Dictionary 
from .dept_param import DeptParam

def on_activate(account_id, msglog):
    table =  Postgres.Table(Dept.__table__)
    table.migrate(account_id, msglog)
    #postgres = Postgres.Pool().session(account_id)
    #try:
    #    dept_param = postgres.query(DeptParam).get('f28835888')
    #    if not dept_param:
    #        dept_param = DeptParam(id='f28835888', name='Ценовой формат', disabled=True)
    #        postgres.add(dept_param)
    #        msglog(f'{dept_param}')
    #        postgres.commit()
    #finally:
    #    postgres.close()

class Dept(Postgres.Base):
  
    __tablename__ = 'dept'

    id              = Column(String, primary_key=True, nullable=False)
    uid             = Column(Binary)
    #e_code          = Column(Binary)
    mtime           = Column('modify_time', DateTime)
    name            = Column(String)
    description     = Column(JSON)
    guid            = Column(String)
    database        = Column(JSON)
    info            = Column(JSON)
    address         = Column(String)
    firm            = Column(String)
    organization_id = Column(BigInteger)

    f28835888       = Column(String) # Ценовой формат

    @property
    def UID(self):
        return self.uid.hex().upper() if self.uid else None

    def __repr__(self):
         return f"<Dept(id={self.id}, name={self.name})>" 

    @staticmethod
    def insert(postgres, values):
        values[DeptTable.c.modify_time] = datetime.datetime.now()
        postgres.execute(insert(DeptTable).values(values))

    @staticmethod
    def query_columns(postgres):
        return postgres.query(Dictionary).filter(Dictionary.CLASS == 'dept', Dictionary.TYPE == 'column')

DeptTable = Dept.__table__

