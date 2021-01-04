import os, sys, json, sqlite3
from domino.core import log, DOMINO_ROOT
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import json
from sqlalchemy.types import TypeDecorator
from sqlalchemy.ext.mutable import MutableDict

class JSONEncodedDict(TypeDecorator):

    impl = String

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value, ensure_ascii=False)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        else:
            value = dict()
        return value

JSON = MutableDict.as_mutable(JSONEncodedDict)

class Jobs:
    Base = declarative_base()
    class Pool:
        def __init__(self):
            self.engine_name = 'jobs'
            path = os.path.join(DOMINO_ROOT, 'data', 'jobs.db')
            self.engine = create_engine(f'sqlite:///{path}')
            self.Session = sessionmaker(bind = self.engine)

        def session(self, **kwargs):
            return self.Session()

