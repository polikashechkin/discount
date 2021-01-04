import json, datetime, os, sys
from sqlalchemy import Column, Index, BigInteger, Binary, Integer, String, JSON, DateTime, text as T, or_, and_
from sqlalchemy.dialects.postgresql import VARCHAR
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import synonym
from domino.core import log
from domino.databases.postgres import Postgres
from domino.tables.postgres.good_param import GoodParam
from domino.enums.unit import Unit 
from domino.enums.country import Country

class UNIT(TypeDecorator):
    impl = VARCHAR
    def process_bind_param(self, value, dialect):
        return value.name if value is not None else None
    def process_result_value(self, value, dialect):
        return Unit.get(value) if value is not None else None

class COUNTRY(TypeDecorator):
    impl = VARCHAR
    def process_bind_param(self, value, dialect):
        return value.name if value is not None else None
    def process_result_value(self, value, dialect):
        return Country.get(value) if value is not None else None

class Good(Postgres.Base):

    __tablename__ = 'good'

    id              = Column('row_id', BigInteger, primary_key=True, autoincrement=True)
    state           = Column(Integer)
    e_code          = Column(String)
    uid             = Column(Binary)

    code            = Column(String)
    name            = Column(String)
    description     = Column(JSON)
    modify_time     = Column(DateTime)
    info            = Column(JSON)
    
    local_group     = Column(String, info = {'name':'Категория'}) #',    'name' : 'Категория',       'type':"group"},
    f2818049        = Column('f2818049', String, info = {'name':'Торговая марка'}) #",    "name" : 'Торговая марка',  'type':"classif"},
    f28835913       = Column('f28835913', String, info = {"name":'Ценовая ниша'}) #',    "name" : 'Ценовая ниша',    'type':"classif"},
    f15073289       = Column('f15073289', String, info = {"name" : 'Уценка'}) #',    "name" : 'Уценка',          'type':"codif", 'codif': {'07D2000307D20001': 'Нет', '07D2000307D20002': 'Да'} },
    f42401855       = Column('f42401855', String, info = {"name" : 'Основной цвет'}) #',    "name" : 'Основной цвет',   'type':"classif"},
    f15073282       = Column('f15073282', String, info = {"name" : 'Основной материал изготовления'}) #',    "name" : 'Основной материал изготовления',   'type':"classif"},
    f42401857       = Column('f42401857', String, info = {"name" : 'Размер'}) #',    "name" : 'Размер',   'type':"classif"},
    f62455820       = Column('f62455820', String, info = {"name" : 'Гендер'}) #',    "name" : 'Гендер',   'type':"classif"},
    f62455821       = Column('f62455821', String, info = {"name" : 'Целевая аудитория'})#',    "name" : 'Целевая аудитория',   'type':"classif"},
    f62455822       = Column('f62455822', String, info = {"name" : 'Назначение'}) #',    "name" : 'Назначение',   'type':"classif"},
    f61931523       = Column('f61931523', String, info = {"name" : 'Категория для интернет магазина'}) #',    "name" : 'Категория для интернет магазина',   'type':"classif"},
    f61669377       = Column('f61669377', String, info = { "name" : 'Старый постащик'}) #',    "name" : 'Старый постащик',   'type':"classif"}
    unit            = Column('unit_id'  , String, info={'name':'ЕИ'})
    country         = Column('country_id', String, info={'name':'Страна'})

    Index('', code)
    Index('', uid)

    @staticmethod
    def filter(_query):
        if len(_query) == 0:
            return None
        q = []
        for column_id, values in _query.items():
            if not values: continue
            if column_id == 'unit_id':
                column = Good.unit
                #values = Unit.get(values)
            elif column_id == 'country_id':
                column = Good.country
                #values = Country.get(values)
            else:
                column = getattr(Good, column_id, None)
                if column is None: continue

            if column_id in ['code', 'name'] : continue

            if isinstance(values, (list, tuple)):
                if len(values) == 1:
                    q.append(column == values[0])
                elif len(values) > 1:
                    q.append(column.in_(values))
            else:
                q.append(column == values)
        return and_(*q)

GoodTable = Good.__table__
Postgres.Table(GoodTable)
