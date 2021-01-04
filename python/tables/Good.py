import json, datetime, arrow, os, sys
from domino.core import log, DOMINO_ROOT
from domino.postgres import Postgres
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime, text as T, or_, and_

E_CODE = 0
CODE = 1
NAME = 2
ROW_ID = 3

class QueryColumn:
    def __init__(self, base_column):
        self.base_column = base_column
        self.by_code = {}
        self.by_uid = {}
        self.max_code = 0

    def create(self, pg_cursor):
        pg_cursor.execute('select row_id from dictionary where class_id=%s and type_id=%s and e_code=%s', [self.class_id, 'column', self.type_id]) 
        r = pg_cursor.fetchone()
        if r is None:
            sql = 'insert into dictionary (class_id, type_id, e_code, code, name) values(%s, %s,%s, %s, %s)'
            pg_cursor.execute(sql, [self.class_id, 'column', self.type_id, self.type_id, self.name])

    @property
    def width(self):
        return self.base_column.width
    @property
    def is_dictionary(self):
        return self.base_column.is_dictionary
    @property
    def ID(self):
        return self.base_column.ID
    @property
    def name(self):
        return self.base_column.name
    @property
    def class_id(self):
        return 'good'
    @property
    def type_id(self):
        return self.base_column.ID
    @property
    def pg_column(self):
        return self.base_column.ID
    @property
    def db_column(self):
        return self.base_column.db_column

    def get_names(self, pg_cursor):
        names = {}
        pg_cursor.execute('select code, name from dictionary where class_id=%s and type_id=%s order by name', [self.class_id, self.type_id])
        for code, name in pg_cursor:
            names[code] = name
        return names
    
    def insert_into(self, pg_cursor, uid, code, name):
        sql = 'insert into "dictionary" (class_id, type_id, e_code, code, "name") values (%s, %s, %s, %s, %s) RETURNING "row_id"'
        pg_cursor.execute(sql, [self.class_id, self.type_id, uid, code, name])
        return pg_cursor.fetchone()[0]

    def load_row(self, e_code, code, name, row_id):
        icode = int(code)
        if icode > self.max_code:
            self.max_code = icode
        row = [e_code, code, name, row_id]
        self.by_code[code] = row
        self.by_uid[e_code] = row

    def load(self, pg_cursor):
        sql = 'select "row_id", "e_code", "code", "name" from dictionary where class_id=%s and type_id=%s'
        pg_cursor.execute(sql, ['good', self.base_column.ID])
        for row_id, uid, code, name in pg_cursor:
            self.load_row(uid, code, name, row_id)

    def get_code_name_by_uid(self, pg_cursor, db_cursor, e_code):
        code = None
        name = None
        row = self.by_uid.get(e_code)
        if row is not None:
            code = row[CODE]
            name = row[NAME]
        else:
            name = self.base_column.get_db_name(db_cursor, e_code)
            if name is not None:
                self.max_code += 1
                code = self.max_code
                row_id = self.insert_into(pg_cursor, e_code, code, name)
                self.load_row(e_code, code, name, row_id)
        return code, name

    def where(self, where_clauses, params, values):
        if values is not None:
            if self.ID == 'code':
                if values:
                    value = values
                    where_clauses.append(f'"{self.ID}" ilike %s')
                    params.append(f'{value}%')
            elif self.ID == 'name':
                if values:
                    value = values
                    where_clauses.append(f'"{self.ID}" ilike %s')
                    params.append(f'%{value}%')
            elif isinstance(values, (list, tuple)):
                if len(values) == 1:
                    value = values[0]
                    if value:
                        where_clauses.append(f'"{self.ID}" = %s')
                        params.append(value)
                elif len(values) > 1:
                    where_clauses.append(f'"{self.ID}" in {tuple(values)}')
            else:
                if values:
                    value = values
                    where_clauses.append(f'"{self.ID}" = %s')
                    params.append(value)

class ProductColumn:
    def __init__(self, ID, name, width = None):
        self.ID = ID.lower()
        self.name = name
        self.width = width
        self.is_dictionary = False
    
    @property
    def db_column(self):
        return f'p.{self.ID}'
    def get_db_name(self, db_cursor, uid):
        return None
    
    def __str__(self):
        return f'<Column {self.ID} {self.name}>'
    def __repr__(self):
        return f'<Column {self.ID} {self.name}>'

class CodifColumn(ProductColumn):
    def __init__(self, ID, name, кодификатор):
        super().__init__(ID, name)
        self.кодификатор = кодификатор
        self.is_dictionary = True
    @property
    def db_column(self):
        return f'rawtohex(p.{self.ID})'
    def get_db_name(self, db_cursor, e_code):
        name = self.кодификатор.get(e_code)
        return name

class ClassifColumn(ProductColumn):
    def __init__(self, ID, name):
        super().__init__(ID, name)
        self.is_dictionary = True
    @property
    def db_column(self):
        return f'domino.DominoUIDToString(p.{self.ID})'
    def get_db_name(self, db_cursor, uid):
        sql = 'select code, name from db1_classif where id = domino.StringToDominoUID(:0)'
        db_cursor.execute(sql, [uid])
        r = db_cursor.fetchone()
        if r is None : return None
        code, name = r
        if self.ID == 'f61669377' : # Старый поставщик
            return f'{code} {name}'
        else:
            return name

class GroupColumn(ProductColumn):
    def __init__(self, ID, name):
        super().__init__(ID, name)
        self.is_dictionary = True
    @property
    def db_column(self):
        return f'domino.DominoUIDToString(p.{self.ID})'
    def get_db_name(self, db_cursor, uid):
        sql = 'select c.name, g.name from db1_classif c, db1_classif g where c.pid = g.id and c.id=domino.StringToDominoUID(:0)'
        db_cursor.execute(sql, [uid])
        r = db_cursor.fetchone()
        return f'{r[0]} : {r[1]}' if r is not None else None

COLUMNS = [
    {"id" : "code",         "name" : "Код",             'width':15},
    {"id" : "name",         "name" : "Наименование",    'width':20},
    {'id' : 'local_group',  'name' : 'Категория',       'type':"group"},
    {"id" : "f2818049",     "name" : 'Торговая марка',  'type':"classif"},
    {"id" : 'f28835913',    "name" : 'Ценовая ниша',    'type':"classif"},
    {"id" : 'f15073289',    "name" : 'Уценка',          'type':"codif", 'codif': {'07D2000307D20001': 'Нет', '07D2000307D20002': 'Да'} },
    {"id" : 'f42401855',    "name" : 'Основной цвет',   'type':"classif"},
    {"id" : 'f15073282',    "name" : 'Основной материал изготовления',   'type':"classif"},
    {"id" : 'f42401857',    "name" : 'Размер',   'type':"classif"},
    {"id" : 'f62455820',    "name" : 'Гендер',   'type':"classif"},
    {"id" : 'f62455821',    "name" : 'Целевая аудитория',   'type':"classif"},
    {"id" : 'f62455822',    "name" : 'Назначение',   'type':"classif"},
    {"id" : 'f61931523',    "name" : 'Категория для интернет магазина',   'type':"classif"},
    {"id" : 'f61669377',    "name" : 'Старый постащик',   'type':"classif"}
]

Base = declarative_base()

class Dictionary(Base):
    @staticmethod
    def on_activate(account_id, msg_log):
        table = Postgres.Table(Disctionary.__tablename__)
        table.column('row_id','bigserial not null primary key')
        table.column('state','integer not null default 0')
        table.column('class_id','varchar')
        table.column('type_id','varchar')
        table.column('e_code','varchar')
        table.column('code','varchar')
        table.column('name','varchar')
        table.column('info','jsonb')

        table.index('class_id', 'type_id', 'name')
        table.index('class_id', 'type_id', 'e_code')

        table.migrate(account_id, msg_log)
    '''
    @staticmethod
    def migrate(account_id, msg_log):
        m = Postgres.Migration(account_id, msg_log)
        m.create_table(Disctionary.__tablename__, 
        'row_id bigserial not null primary key',
        'state integer not null default 0',
        'class_id varchar',
        'type_id varchar',
        'e_code varchar',
        'code varchar',
        'name varchar',
        'info jsonb'
        )
        m.create_index(Disctionary.__tablename__, 'class_id', 'type_id', 'name')
        m.create_index(Disctionary.__tablename__, 'class_id', 'type_id', 'e_code')
        m.migrate()
    '''
    __tablename__ = 'Dictionary'.lower()
    row_id = Column(Integer, primary_key=True)
    state = Column(Integer)
    type_id = Column(String)
    class_id = Column(String)
    code = Column(String)
    name = Column(String)
    description = Column(JSON)
    info = Column(JSON)
    
Disctionary = Dictionary

class Good(Base):

    Columns = {}   
    for c in COLUMNS:
        ID = c.get('id') 
        TYPE = c.get('type')  
        name = c.get('name')
        width = c.get('width')
        codif = c.get('codif')
        if TYPE is None:
            Columns[ID] = ProductColumn(ID, name, width=width)
        elif TYPE == 'group':
            Columns[ID] = GroupColumn(ID, name)
        elif TYPE == 'classif':
            Columns[ID] = ClassifColumn(ID, name)
        elif TYPE == 'codif':
            Columns[ID] = CodifColumn(ID, name, кодификатор = codif)
    
    @staticmethod
    def QueryColumns(pg_cursor):
        columns = []
        pg_cursor.execute('select code from dictionary where class_id=%s and type_id=%s and state=0',
            ['good', 'column'])
        codes = set()
        for code, in pg_cursor:
            codes.add(code) 
        for column in Good.Columns.values():
            if column.is_dictionary:
                if column.ID in codes:
                    columns.append(QueryColumn(column))    
            else:
                columns.append(QueryColumn(column))
        return columns
    
    @staticmethod
    def QueryColumn(column_id):
        column = Good.Columns.get(column_id.lower())
        return QueryColumn(column) if column is not None else None

    @staticmethod
    def on_activate(account_id, msg_log):
        table = Postgres.Table(Good.__tablename__)
        table.column('row_id','bigserial not null primary key')
        table.column('state','integer not null default 0')
        table.column('e_code','varchar')
        table.column('code','varchar')
        table.column('name','varchar')
        table.column('description','jsonb')
        table.column('info','jsonb')
        table.column('modify_time','timestamp')

        for column_name in Good.Columns:
            if column_name != 'code' and column_name != 'name':
                table.column(column_name, 'varchar')

        table.index('e_code')
        table.index('code')
        table.migrate(account_id, msg_log)
        Dictionary.on_activate(account_id, msg_log)

    __tablename__ = 'good'

    row_id          = Column(Integer, primary_key=True)
    state           = Column(Integer)
    e_code          = Column(String)
    code            = Column(String)
    name            = Column(String)
    description     = Column(JSON)
    modify_time     = Column(DateTime)
    info            = Column(JSON)
    
    local_group     = Column(String) #',    'name' : 'Категория',       'type':"group"},
    f2818049        = Column(String) #",    "name" : 'Торговая марка',  'type':"classif"},
    f28835913       = Column(String) #',    "name" : 'Ценовая ниша',    'type':"classif"},
    f15073289       = Column(String) #',    "name" : 'Уценка',          'type':"codif", 'codif': {'07D2000307D20001': 'Нет', '07D2000307D20002': 'Да'} },
    f42401855       = Column(String) #',    "name" : 'Основной цвет',   'type':"classif"},
    f15073282       = Column(String) #',    "name" : 'Основной материал изготовления',   'type':"classif"},
    f42401857       = Column(String) #',    "name" : 'Размер',   'type':"classif"},
    f62455820       = Column(String) #',    "name" : 'Гендер',   'type':"classif"},
    f62455821       = Column(String) #',    "name" : 'Целевая аудитория',   'type':"classif"},
    f62455822       = Column(String) #',    "name" : 'Назначение',   'type':"classif"},
    f61931523       = Column(String) #',    "name" : 'Категория для интернет магазина',   'type':"classif"},
    f61669377       = Column(String) #',    "name" : 'Старый постащик',   'type':"classif"}

    @staticmethod
    def filter(_query):
        if len(_query) == 0:
            return None
        q = []
        for column_id, values in _query.items():
            if column_id in ['code', 'name'] : continue
            if not values: continue
            column = getattr(Good, column_id, None)
            if column is None: continue
            if isinstance(values, (list, tuple)):
                if len(values) == 1:
                    q.append(column == values[0])
                elif len(values) > 1:
                    q.append(column.in_(values))
            else:
                q.append(column == values)
        return and_(*q)

    @staticmethod
    def query(postgres, _query):
        return postgres.query(Good).filter(Good.filter(_query))
