import os, datetime, sqlite3
from domino.core import log
from domino.page import Page, Filter
from domino.postgres import Postgres
from discount.core import DISCOUNT_DB, Engine, MODULE_ID
from grants import Grants

POSTGRES = Postgres.Pool()

class DiscountPage(Page):
    def __init__(self, application, request, controls=[]):
        super().__init__(application, request, controls = controls)
        self.account_id = self.request.account_id()
        #self._db_connection = None
        #self._db_cursor = None
        self._connection = None
        self._cursor = None
        self.card_types = self.application['card_types']
        self.action_types = self.application['action_types']
        self._grants = None
    
    @property
    def grants(self):
        if self._grants is None:
            self._grants = Grants(self.account_id, self.request.user_id)
        return self._grants

    
    def __getattr__(self, name):
        if name == 'pg_connection':
            value = Postgres.connect(self.account_id)
        elif name == 'pg_cursor':
            value = self.pg_connection.cursor()
        elif name == 'engine':
            #value = Engine(self.db_connection, self.pg_connection)
            value = Engine(None, self.pg_connection)
        else:
            raise AttributeError(name)
        self.__dict__[name] = value
        return value

    def get_product_name(self, code):
        try:
            self.pg_cursor.execute('select "name" from "good" where "code"=%s limit 1', [code])
            r = self.pg_cursor.fetchone()
            return r[0] if r is not None else f'<{code}>'
        except:
            log.exception(__file__)
            return f'?{code}?'

    #@property
    #def права(self):
    #    if self._права is None:
    #        self._права = Права(self.account_id, self.request.user_id)
    #    return self._права

    def close(self):
        if self._connection is not None:
            self._connection.close()
        #if self._db_connection is not None:
        #    self._db_connection.close()

    def _create_connection(self):
        return sqlite3.connect(DISCOUNT_DB(self.account_id))

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self._create_connection()
        return self._connection
    @property
    def cursor(self):
        if self._cursor is None:
            self._cursor = self.connection.cursor()
        return self._cursor
    #@property
    #def db_connection(self):
    #    if self._db_connection is None:
    #        self._db_connection = self.application.account_database_connect(self.account_id)
    #    return self._db_connection
    #@property
    #def db_cursor(self):
    #    if self._db_cursor is None:
    #        self._db_cursor = self.db_connection.cursor()
    #    return self._db_cursor
