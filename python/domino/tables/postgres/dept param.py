from sqlalchemy import Column, Integer, BigInteger, String, DateTime, insert, Binary, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from domino.core import log
from domino.databases.postgres import Postgres
from .dictionary import Dictionary

def on_activate(account_id, msglog):
    table =  Postgres.Table(DeptParamTable)
    table.migrate(account_id, msglog)
 
class DeptParam(Postgres.Base):
  
    __tablename__ = 'dept_param'

    id              = Column(String, primary_key=True, nullable=False)
    disabled        = Column(Boolean)
    name            = Column(String)
    info            = Column(JSONB)

    def __repr__(self):
         return f"<DeptParam(id={self.id}, name={self.name})>" 
    
    @staticmethod
    def all(postgres):
        return postgres.query(DeptParam).filter(DeptParam.disabled == False).order_by(DeptParam.name).all()

    def options(self, postgres):
        return postgres.query(Dictionary.id, Dictionary.name)\
            .filter(Dictionary.CLASS == 'dept', Dictionary.TYPE == self.id)\
            .order_by(Dictionary.name)\
             .all()

DeptParamTable = DeptParam.__table__

# schema_id