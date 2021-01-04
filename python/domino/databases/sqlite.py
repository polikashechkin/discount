import os, sys, json, sqlite3
from domino.core import log, DOMINO_ROOT
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import String

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

class Sqlite:
    Base = declarative_base()
    engine_name = 'sqlite'
    class Pool:
        class Item:
            def __init__(self, account_id, module_id):
                self.account_id = account_id
                path = os.path.join(DOMINO_ROOT, 'accounts', account_id, 'data', f'{module_id}.db')
                #log.debug(f'sqlite:///{path}')
                self.engine = create_engine(f'sqlite:///{path}')
                self.Session = sessionmaker(bind = self.engine)
            def session(self):
                return self.Session()

        def __init__(self, module_id = None, name=None):
            self.module_id = module_id
            if name:
                self.engine_name = name
            else:
                self.engine_name = Sqlite.engine_name
            self.items = {}

        def session(self, account_id, module_id, **kwargs):
            if self.module_id:
                module_id = self.module_id
            item = self.items.get((account_id, module_id))
            if item is None:
                item = Sqlite.Pool.Item(account_id, module_id)
                self.items[(account_id, module_id)] = item
            return item.session()

    class Table:
        def __init__(self, table):
            self.columns = {}
            self.indexes = {}

