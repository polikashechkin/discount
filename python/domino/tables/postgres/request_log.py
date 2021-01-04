import json, datetime, os
from domino.core import log
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON, Float, Boolean
from domino.databases.postgres import Postgres

class RequestLog(Postgres.Base):
   
    __tablename__ = 'request_log'

    id              = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True)
    fixed           = Column(Boolean)
    is_test         = Column(Boolean)
    module_id       = Column(String)
    path            = Column(String)
    url             = Column(String)
    dept_code       = Column(String)
    user_id         = Column(String)
    status_code     = Column(Integer)
    ctime           = Column(DateTime)
    response_text   = Column(String)
    response_type   = Column(String)
    info            = Column(JSON)
    duration        = Column(Float)
    xml_file        = Column(String)
    guid            = Column(String)
    comment         = Column(String)

    def __init__(self, module_id, url):
        self.module_id = module_id
        self.ctime = datetime.datetime.now()
        self.url = url
        args_pos = url.find('?')
        if args_pos != -1:
            self.path = os.path.basename(url[:args_pos])
        else:
            self.path = os.path.basename(url)

    def __repr__(self):
         return f"<RequestLog(id={self.id}, url={self.url}'>" 
    
RequestLogTable = RequestLog.__table__
Postgres.Table(RequestLogTable)
        




