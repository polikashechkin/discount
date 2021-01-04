import os, sys, json, cx_Oracle, sqlite3
from domino.core import log, DOMINO_ROOT

DATABASES_DB = '/DOMINO/data/account.db'
FIRST_USER = '8400000000000001'

def domino_login(conn, user_id = None):
   if user_id is None:
      user_id = FIRST_USER
   cur = conn.cursor()
   cur.execute("begin domino.login(hextoraw('{0}')); end;".format(user_id))
   cur.close()

def table_exists(conn, table_name):
    cur = conn.cursor()
    cur.execute('select count(*) from tab where tname=:0',[table_name.upper()])
    count = cur.fetchone()[0]
    cur.close()
    return count > 0 

def drop_table(conn, table_name):
    cur = conn.cursor()
    cur.execute(f'drop table {table_name.upper()}')
    cur.close()

class Database:
    def __init__(self, scheme, host, port = 1521, service_name='orcl'):
        self.scheme = scheme
        self.host = host
        self.port = port
        self.service_name = service_name
        self.session_pool = None
    @property
    def dsn(self):
        return f'{self.host}:{self.port}/{self.service_name}'
    @property
    def uri(self):
        return f'{self.scheme}@{self.dsn}'

    def connect(self):
        return cx_Oracle.connect(user = self.scheme, password = self.scheme, dsn= self.dsn, encoding = "UTF-8", nencoding = "UTF-8") 

    def connect_sysdba(self, user, password):
        return cx_Oracle.connect(user = user, password = password, dsn= self.dsn, encoding = "UTF-8", nencoding = "UTF-8", mode=cx_Oracle.SYSDBA) 

    def acquire(self):
        if self.session_pool is None:
            self.session_pool = cx_Oracle.SessionPool(dsn = self.dsn, 
                user = self.scheme, password= self.scheme,
                homogeneous = True, min=1, increment=10, max = 100, threaded = True, 
                encoding = "UTF-8" , nencoding = "UTF-8"
                )
            conn = self.session_pool.acquire()
            #log.debug('domino_login')
            domino_login(conn)
            return conn
        else:
            return self.session_pool.acquire()

    def get_revision(self):
        revision = None
        conn = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute("select cfg_value from domino_cfg where cfg_name='Revision'")
            revision = cur.fetchone()[0]
            cur.close()
            conn.close()
            conn = None
        finally:
            if conn is not None:
                conn.close()
        return revision
    def __str__(self):
        return f'Database({self.uri})'

    @staticmethod
    def parse(uri):
        try:
            service_name = 'orcl'
            port = 1521
            scheme, host = uri.split('@')
            #print(scheme, host, port, service_name)
            if host.find('/') != -1:
                host, service_name = host.split('/')
            #print(scheme, host, port, service_name)
            if host.find(':') != -1:
                host, port = host.split(':')
                port = int(port)
            #print(scheme, host, port, service_name)
            return Database(scheme.upper(), host, port, service_name)
        except:
            log.exception(f'database.parse({uri})')
            return None

class Databases:

    def __init__(self):
        #self.conn = sqlite3.connect('/DOMINO/data/account.db')
        self.databases = {}
    
    @staticmethod
    def database_pool_key(account_id, database_id):
        return f'{account_id}.{database_id}'

    def get_database_from_pool(self, account_id, database_id = None):
        return self.databases.get(Databases.database_pool_key(account_id, database_id))

    def pool_database(self, account_id, database_id = None):
        key = Databases.database_pool_key(account_id, database_id)
        database = self.databases.get(key)
        if database is None:
            database = self.get_database(account_id, database_id)
            if database is None:
                raise Exception(f'Не определена база данных "{key}" ')
            self.databases[key] = database
        return database
   
    def acquire(self, account_id, database_id = None):
        #key = Databases.database_pool_key(account_id, database_id)
        #database = self.databases.get(key)
        #if database is None:
        #    database = self.get_database(account_id, database_id)
        #    if database is None:
        #        raise Exception(f'Не определена база данных "{key}" ')
        #   self.databases[key] = database
        return self.pool_database(account_id, database_id).acquire()
 
    def print(self):
        with sqlite3.connect(DATABASES_DB) as conn:
            cur = conn.cursor()
            cur.execute('select account_id, id, scheme, host, port, service_name from databases')
            for account_id, id, scheme, host, port, service_name in cur :
                name = account_id + '.' + id
                print(f'{name:15} {scheme}@{host}:{port}/{service_name}')

    def _get_database(self, cur, account_id, dept_id = ''):
        if not dept_id:
            dept_id = ''
        cur.execute('select scheme, host, port, service_name from databases where account_id=? and id=?', [account_id, dept_id])
        row = cur.fetchone()
        if row is None:
            return None
        scheme, host, port, service_name = row
        return Database(scheme, host, port, service_name)

    def get_database(self, account_id, dept_id = None):
        if account_id is None:
            account_id = ''
           
        account_db = os.path.join(DOMINO_ROOT, 'data', 'account.db')
        with sqlite3.connect(account_db) as conn:
            cur = conn.cursor()

            if dept_id: # какое то подразделение задано
                # тупо поиск базы данных по заданным параметром
                database = self._get_database(cur, account_id, dept_id)
                if database is not None:
                    return database

                # Возможно задано не dept_guid но dept_code
                cur.execute('select guid from depts where account_id=? and code=?', [account_id, dept_id])
                r = cur.fetchone()
                if r is not None:
                    guid = r[0]
                    database = self._get_database(cur, account_id, guid)
                    if database is not None:
                        return database

            # не задано подразделение или нет отдельной БД для подразделения
            return self._get_database(cur, account_id)

    def set_database(self, database, account_id, id = ''):
        self.add_database(database.scheme,database.host, database.port, database.service_name, account_id, id)

    def connect(self, account_id = '', id = ''):
        database = self.get_database(account_id, id)
        if database is None:
            return None
        return database.connect()
        
    @staticmethod
    def parse(connection_string):
        try:
            scheme, host = connection_string.split('@')
            if host.find('/') != -1:
                host, service_name = host.sptit('/')
            else:
                service_name = 'orcl'
            if host.find(':') != -1:
                host, port = host.split(':')
                port = int(port)
            else:
                port = 1521
            return scheme.upper(), host, port, service_name
        except:
            raise Exception(f'Ошибка в описании соединения "{connection_string}"')

    @staticmethod
    def combine(scheme, host, port, service_name):
        return f'{scheme}@{host}:{port}/{service_name}'

    def add(self, account_id, id, connection_string):
        with sqlite3.connect(DATABASES_DB) as conn:
            cur = conn.cursor()
            scheme, host, port, service_name = Databases.parse(connection_string)
            s = 'insert or replace into databases (account_id, id, scheme, host, port, service_name) values (:0, :1, :2, :3, :4, :5);'
            cur.execute(s, [account_id, id, scheme, host, port, service_name])
            cur.close()

    def add_database(self, scheme, host, port, service_name, account_id, id = ''):
        with sqlite3.connect(DATABASES_DB) as conn:
            s = 'insert or replace into databases (account_id, id, scheme, host, port, service_name) values (:0, :1, :2, :3, :4, :5);'
            conn.execute(s, [account_id, id, scheme, host, port, service_name])

    def remove(self, account_id, id):
        with sqlite3.connect(DATABASES_DB) as conn:
            s = 'delete from databases where account_id=:0 and id=:1;'
            conn.execute(s, [account_id, id])

    @staticmethod
    def combine_desc(scheme, host, port, service_name):
        desc = f'{scheme}@{host}'
        if str(port) != '1521':
            desc += f':{port}'
        if service_name != 'orcl':
            desc += f'/{port}'
        return desc

    @staticmethod
    def test_connection(database):
        try:
            scheme, host, port, service_name = Databases.parse(database)
        except: 
            return None
        connection_string = f'{scheme}/{scheme}@{host}:{port}/{service_name}'
        try:
            conn = cx_Oracle.connect(connection_string)
            cur = conn.cursor()
            cur.execute("select cfg_value from domino_cfg where cfg_name='Revision'")
            revision = cur.fetchone()[0]
            #print(f'База данных "{database}" доступна и имеет версию {revision}')
            conn.close()
            return revision
        except:
            return None

    def test(self, account_id, id):
        with sqlite3.connect(DATABASES_DB) as conn:
            cur = conn.cursor()
            s = 'select scheme, host, port, service_name from databases where account_id=:0 and id=:1;'
            cur.execute(s, [account_id, id])
            row = cur.fetchone()
        if row is None:
            return False
        scheme, host, port, service_name = row
        connection_string = f'{scheme}/{scheme}@{host}:{port}/{service_name}'
        desc = Databases.combine_desc(scheme, host, port, service_name)
        #print(connection_string)
        try:
            conn = cx_Oracle.connect(connection_string)
            cur = conn.cursor()
            cur.execute("select cfg_value from domino_cfg where cfg_name='Revision'")
            revision = cur.fetchone()[0]
            print(f'База данных "{desc}" доступна и имеет версию {revision}')
            conn.close()
            return True
        except:
            log.exception()
            return False

    @staticmethod
    def find(host, pwd):
        owners = []
        conn = cx_Oracle.connect(f"SYSTEM/{pwd}@{host}/orcl")
        cur = conn.cursor()
        cur.execute("select owner from all_tables where table_name='DOMINO_CFG'")
        for row in cur:
            owners.append(row[0])
        return owners

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class Oracle:
    engine_name = 'oracle'
    class Pool:
        class Item:
            def __init__(self, account_id, dept_id = None):
                self.account_id = account_id
                self.dept_id = dept_id
                self.engine = Oracle.create_engine(account_id, dept_id)
                self.Session = sessionmaker(bind = self.engine)
            def session(self):
                return self.Session()
        
        def __init__(self):
            self.items = {}
            self.engine_name = 'oracle'
        
        def session(self, account_id, dept_id = None, **kwargs):
            #if account_id is None:
            #    return None
            key = f'{account_id}/{dept_id}'
            item = self.items.get(key)
            if item is None:
                item = Oracle.Pool.Item(account_id, dept_id)
                self.items[key] = item
            return item.session()

    class ConnectionCreator:
        def __init__(self, database):
            self.database = database
        def __call__(self):
            log.debug(f'CONNECT TO {self.database.uri}')
            connection = self.database.connect()
            domino_login(connection)
            return connection

    @staticmethod
    def create_engine(account_id, dept_id):
        database = DATABASES.get_database(account_id, dept_id)
        return create_engine('oracle://', creator = Oracle.ConnectionCreator(database))

    @staticmethod
    def session(account_id, dept_id, **kwargs):
        engine = Oracle.create_engine(account_id, dept_id)
        Session = sessionmaker(bind = engine)
        return Session()

DATABASES = Databases()

        
