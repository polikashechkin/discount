import sqlite3

from settings import DATABASE_DB
from discount.schemas import ДисконтнаяСхема

class Schema:
    def __init__(self, account_id):
        conn = sqlite3.connect(DATABASE_DB(account_id))
        cur = conn.cursor()
        self.names = {}
        for schema in ДисконтнаяСхема.findall(cur):
            self.names[schema.ID] = schema.наименование

    def get_name(self, id, default=None):
        return self.names.get(id, default)

    def options(self):
        return self.names.items()




