import json
from domino.core import log
from domino.databases.jobs import Jobs
from sqlalchemy import Column, Index, String, DateTime, Integer, BLOB

def on_install(on_install_log):
    pass

class Proc(Jobs.Base):

    __tablename__ = 'procs'

    id          = Column(Integer, primary_key=True, nullable=False)
    class_      = Column('class', Integer, nullable=False, default=0)
    type_       = Column('type', Integer, nullable=False, default=0)
    state       = Column(Integer, nullable=False, default=0)
    account_id  = Column(String)
    module_id   = Column('module', String, nullable=False)
    proc_id     = Column('proc', String, nullable=False)
    params      = Column(BLOB, default='{}') 
    info        = Column(BLOB, default='{}') 
    inst        = Column(Integer, nullable=False, default=1)
    autorestart = Column(Integer, nullable=False, default=0)

    Index('', account_id, module_id, proc_id, unique=True)

ProcTable = Proc.__table__

