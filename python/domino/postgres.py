import os, sys, psutil, shutil
import psycopg2
from psycopg2 import pool
import sqlalchemy
from sqlalchemy import create_engine, String, Integer, SmallInteger, BigInteger, Date, DateTime, Boolean, Numeric, Table, JSON
from sqlalchemy.dialects.postgresql import JSONB, BOOLEAN, NUMERIC, VARCHAR, TEXT, TIMESTAMP, BIGINT, SMALLINT, INTEGER
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


def system(log, cmd):
    if log:
        log(cmd)
    os.system(cmd)

class PostgresTable:

    class Column:
        def __init__(self, table, column, params = None):
            self.table = table
            if isinstance(column, str):
                self.name = column.lower()
                self.params = params.lower() if params else ''
            else:
                self.name = column.name
                column_type = ''
                if isinstance(column.type, (String, VARCHAR, TEXT)):
                    column_type = 'varchar'
                elif isinstance(column.type, (BigInteger, BIGINT)):
                    if column.autoincrement == True:
                        column_type = 'bigserial'
                    else:
                        column_type = 'bigint'
                elif isinstance(column.type, (SmallInteger, SMALLINT)):
                    if column.autoincrement == True:
                        column_type = 'smallserial'
                    else:
                        column_type = 'smallint'
                elif isinstance(column.type, (Integer, INTEGER)):
                    if column.autoincrement == True:
                        column_type = 'serial'
                    else:
                        column_type = 'integer'
                elif isinstance(column.type, Date):
                    column_type = 'date'
                elif isinstance(column.type, (DateTime, TIMESTAMP)):
                    column_type = 'timestamp'
                elif isinstance(column.type, (Boolean, BOOLEAN)):
                    column_type = 'bool'
                elif isinstance(column.type, (Numeric, NUMERIC)):
                    column_type = 'numeric'
                elif isinstance(column.type, (JSONB, JSON)):
                    column_type = 'jsonb'
                else:
                    raise Exception(f'Unknown postgresql type "{column.type}"')
                self.params = column_type

                if not column.nullable:
                    self.params += ' not null'
                if column.primary_key:
                    self.params += ' primary key'

    class Index:
        def __init__(self, table, table_index, *column_names, name = None, unique = False):
            self.column_names = []
            self.table = table
            if table_index is not None:
                self.name = table_index.name
                self.unique = table_index.unique
                for column in table_index.columns:
                    self.column_names.append(f'"{column.name}"')
                if not self.name or not self.name.strip():
                    self.name = f'{self.table.table_name}_on'
                    for column in table_index.columns:
                        self.name += f'_{column.name}'
            else:
                for column_name in column_names:
                    self.column_names.append(f'"{column_name.lower()}"')
                self.name = name.lower() if name else None
                self.unique = unique
                if not self.name:
                    self.name = f'{self.table.table_name}_on_{"_".join(column_names)}'.lower()

        def migrate(self, pg_cursor, existing_indexes = None):
            if existing_indexes is None or self.name not in existing_indexes:
                if self.unique:
                    sql = f'create unique index "{self.name}" on "{self.table.table_name}" ({",".join(self.column_names)})'
                else:
                    sql = f'create index "{self.name}" on "{self.table.table_name}" ({",".join(self.column_names)})'
                self.table.execute(pg_cursor, sql)

    def __init__(self, table):
        self.columns = {}
        self.indexes = {}
        self.msg_log = None
        if isinstance(table, str):
            self.table_name = table.lower()
        elif isinstance(table, sqlalchemy.Table):
            self.table_name = str(table)
            for column in table.columns:
                self.column(column)
            for index in table.indexes:
                table_index = PostgresTable.Index(self, index)
                self.indexes[table_index.name] = table_index
        else:
            raise Exception('Недопустимый тип таблицы')

    def log(self, msg):
        if self.msg_log is not None:
            self.msg_log(msg)
    
    def execute(self, pg_cursor, sql):
        self.log(sql)
        pg_cursor.execute(sql)

    def column(self, column, params = None):
        if isinstance(column, str):
            column_name = column.lower()
        else:
            column_name = column.name
        self.columns[column_name] = PostgresTable.Column(self, column, params)

    def index(self, *column_names, name = None, unique=False):
        index = PostgresTable.Index(self, None, *column_names, name=name, unique=unique)
        self.indexes[index.name] = index

    def table_exists(self, pg_cursor):
        pg_cursor.execute("SELECT count(*) FROM information_schema.tables where table_schema='public' and table_name=%s", [self.table_name])
        return bool(pg_cursor.fetchone()[0])

    def create_table(self, pg_cursor):
        fields = []
        for column in self.columns.values():
            fields.append(f'"{column.name}" {column.params}') 
        fields_clause = ' ,'.join(fields)
        sql = f'create table "{self.table_name}" ({fields_clause})'
        self.execute(pg_cursor, sql)
        for index in self.indexes.values():
            index.migrate(pg_cursor, existing_indexes={})

    def alter_table(self, pg_cursor):
        existing_columns = {}
        sql = "select column_name, data_type from information_schema.columns where table_schema='public' and table_name=%s"
        pg_cursor.execute(sql, [self.table_name])
        for column_name, data_type in pg_cursor:
            existing_columns[column_name] = {'data_type':data_type}
        for column in self.columns.values():
            if column.name not in existing_columns:
                sql = f'alter table "{self.table_name}" add column "{column.name}" {column.params}'
                self.execute(pg_cursor, sql)

        existing_indexes = {}
        pg_cursor.execute("select indexname, indexdef from pg_indexes where tablename=%s", [self.table_name])
        for indexname, indexdef in pg_cursor:
            existing_indexes[indexname] = {'indexdef' : indexdef}
        for index in self.indexes.values():
            index.migrate(pg_cursor, existing_indexes)

    def migrate(self, account_id, msg_log):
        self.msg_log = msg_log
        pg_connection = Postgres.connect(account_id)
        pg_cursor = pg_connection.cursor()
        with pg_connection:
            if not self.table_exists(pg_cursor):
                self.create_table(pg_cursor)
            else:
                self.alter_table(pg_cursor)

class PosgresMirgation:
    def __init__(self, account_id, msg_log = None):
        self.account_id = account_id
        self.msg_log = msg_log
        self.operations = []

    def create_table(self, tablename, *columns):
        tablename = tablename.lower()
        sql = []
        for column in columns:
            column_name, column_def = column.split(' ', 1)
            sql.append(f'"{column_name.lower()}" {column_def}')
        tablecolumns = ','.join(sql)
        self.operations.append(f'create table if not exists "{tablename}" ({tablecolumns})')

    def create_index(self, tablename, *columns):
        indexname = f'"{tablename}_on_{"_".join(columns)}"'.lower()
        tablename = f'"{tablename.lower()}"'
        column_names = []
        for column in columns:
            column_names.append(f'"{column.lower()}"')
        self.operations.append(f'create index if not exists {indexname} on {tablename}({",".join(column_names)})')

    def create_unique_index(self, tablename, *columns, **kwargs):
        indexname = kwargs.get('name')
        if indexname is None:
            indexname = f'"{tablename}_on_{"_".join(columns)}"'.lower()
        tablename = f'"{tablename.lower()}"'
        column_names = []
        for column in columns:
            column_names.append(f'"{column.lower()}"')
        self.operations.append(f'create unique index if not exists {indexname} on {tablename}({",".join(column_names)})')

    def add_columns(self, tablename, *columns):
        tablename = tablename.lower()
        for column in columns:
            column_name, column_def = column.split(' ', 1)
            self.operations.append(f'alter table "{tablename}" add column if not exists "{column_name.lower()}" {column_def}')

    def migrate(self):
        conn = Postgres.connect(self.account_id)
        with conn:
            cur = conn.cursor()
            for operation in self.operations:
                if self.msg_log is not None:
                    self.msg_log(operation)
                cur.execute(operation)
                conn.commit()
        conn.close()

class Postgres:
    Base = declarative_base()
    engine_name = 'postgres'

    def __init__(self, engine_name = None):
        self.engine_name = engine_name if engine_name else 'postgres'
        self.databases = {}

    def session(self, account_id, **kwargs):
        database = self.databases.get(account_id)
        if not database:
            engine = create_engine('postgresql+psycopg2://', creator = Postgres.ConnectionCreator(account_id))
            database = {'session' : sessionmaker(bind=engine)}
            self.databases[account_id] = database
        return database['session']()
    
    def __repr__(self):
        return f'<Postgres({self.engine_name}, databases = {len(self.databases)})>'

    class Pool:

        def __init__(self, name = None):
            self.items = {}
            self.engine_name = name if name else 'postgres'

        def session(self, account_id, **kwargs):
            if account_id is None:
                return None
            item = self.items.get(account_id)
            if not item:
                engine = create_engine('postgresql+psycopg2://', creator = Postgres.ConnectionCreator(account_id))
                item = {'session' : sessionmaker(bind=engine)}
                self.items[account_id] = item
            return item['session']()
        
        def __repr__(self):
            return f'<Postgres.Pool(name={self.engine_name}, size={len(self.items)})>'

    class ConnectionCreator:
        def __init__(self, account_id):
            self.account_id = account_id
        def __call__(self):
            return Postgres.connect(self.account_id)

    @staticmethod
    def create_engine(account_id):
        #return create_engine('postgres', creator = Postgres.ConnectionCreator(account_id))
        return create_engine('postgresql+psycopg2://', creator = Postgres.ConnectionCreator(account_id))
        #return create_engine(f'postgresql+psycopg2://u{account_id}:{ljvbyj}@localhost/d{account_id}')

    STD_PASSWORD = 'ljvbyj'

    @staticmethod
    def Table(table_name):
        return PostgresTable(table_name)

    @staticmethod
    def Migration(account_id, msg_log):
        return PosgresMirgation(account_id, msg_log)
    @staticmethod
    def tables(cur):
        tables = set()
        cur.execute('select tablename from pg_tables')
        for tablename, in cur:
            tables.add(tablename.upper()) 
        return tables

    @staticmethod
    def execute(cur, sql, log):
        if log:
            log(sql.upper())
        cur.execute(sql)

    @staticmethod
    def exists_database(account_id):
        location = f'/DOMINO/accounts/{account_id}/data/postgres'
        return os.path.exists(location)
    
    @staticmethod
    def create_connection_pool(account_id, min_connection=1, max_connection=10):
        user = f'u{account_id}'
        dbname = f'd{account_id}'
        pool = psycopg2.pool.ThreadedConnectionPool(min_connection, max_connection, dbname=dbname, user=user)
        return pool
        
    @staticmethod
    def version():
        return psycopg2.__version__

    @staticmethod
    def connect(account_id):
        user = f'u{account_id}'
        dbname = f'd{account_id}'
        #return psycopg2.connect(dbname=dbname, host='127.0.0.1', user=user, password=Postgres.STD_PASSWORD)
        connection = psycopg2.connect(dbname=dbname, user=user, password=Postgres.STD_PASSWORD)
        return connection

    @staticmethod
    def create_database(account_id, log = None):
        location = f'/DOMINO/accounts/{account_id}/data/postgres'
        user = f'u{account_id}'
        tablespace = f't{account_id}'
        dbname = f'd{account_id}'
        if os.path.exists(location):
            #if log:
            #    log(f'База данных postgres для учетной записи "{account_id}" уже существует')
            return
        
        os.makedirs(location, exist_ok=True)
        system(log, f'sudo chown -R postgres:postgres {location}')
        system(log, f'''sudo -u postgres psql -c "CREATE USER {user} WITH password '{Postgres.STD_PASSWORD}';"''')
        system(log, f'''sudo -u postgres psql -c "CREATE TABLESPACE {tablespace} OWNER {user} LOCATION '{location}';"''')
        system(log, f'''sudo -u postgres psql -c "CREATE DATABASE {dbname} OWNER {user} TABLESPACE {tablespace};"''')
        if log:
            log(f'База данных postgres для учетной записи "{account_id}" создана')
    
    @staticmethod
    def drop_database(account_id, log=None):
        location = f'/DOMINO/accounts/{account_id}/data/postgres'
        user = f'u{account_id}'
        tablespace = f't{account_id}'
        dbname = f'd{account_id}'
        if not os.path.exists(location):
            print(f'База данных для учетной записи "{account_id}" еще не создана')
            return 
            
        system(log, f'''sudo -u postgres psql -c "DROP DATABASE {dbname};"''')
        system(log, f'''sudo -u postgres psql -c "DROP TABLESPACE {tablespace};"''')
        system(log, f'''sudo -u postgres psql -c "DROP USER {user}";''')
        system(log, f'''rm -R -d {location}''')
        
