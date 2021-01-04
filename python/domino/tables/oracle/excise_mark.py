import json, datetime, arrow, re
from domino.core import log, RawToHex, HexToRaw
from sqlalchemy import Column, Integer, String, JSON, DateTime, Date, Numeric, text as T
from sqlalchemy.dialects.oracle import RAW, NUMBER
from sqlalchemy.orm import synonym
from sqlalchemy.types import TypeDecorator
from domino.databases.oracle import Oracle
from enum import Enum

class MarkStatus(Enum):
    Загружена       = HexToRaw('03F5002E03F50001') #66388014[66387969] 03F5002E03F50001 "Загружен"
    Считана         = HexToRaw('03F5002E04030001') #66388014[67305473] 03F5002E04030001 "Считан"
    Добавлена       = HexToRaw('03F5002E03F50002') #66388014[66387970] 03F5002E03F50002 "Добавлен"
    Не_подтверждена = HexToRaw('03F5002E03F50003') #66388014[66387971] 03F5002E03F50003 "Не подтвержден"
    Подтверждена    = HexToRaw('03F5002E03F50005') #66388014[66387973] 03F5002E03F50005 "Подтвержден"
    Списана         = HexToRaw('03F5002E03F50006') #66388014[66387974] 03F5002E03F50006 "Списан"
    Блокирована     = HexToRaw('03F5002E03F50007') #66388014[66387975] 03F5002E03F50007 "Блокирован"

    def __str__(self):
        return self.name

class MARK_STATUS(TypeDecorator):
    impl = RAW(8)
    def process_bind_param(self, value, dialect):
        return value.value if value is not None else None
    def process_result_value(self, value, dialect):
        return MarkStatus(value) if value is not None else None

class ExciseMark(Oracle.Base):

    Status = MarkStatus

    __tablename__ = 'excise_mark'

    id                  = Column(RAW(8))
    pid                 = Column('box_id', RAW(8)) # Идентификатор упаковки, соотретствует EsciseMark.id групповой упаковке 
    TYPE                = Column('type', NUMBER(10,0)) # 1 - Одиночная марка; 2 - групповая упаковка
    fsrar_id            = Column(String)
    code                = Column(String, primary_key=True) # код марки
    egais_code          = Column('code_egais', String) 
    code_egais          = synonym(egais_code)
    product_id          = Column(RAW(8)) 
    status              = Column('status_id', MARK_STATUS)

    bill_B              = Column('party_f2', String) # Номер справки Б (наша)
    
    @property 
    def product_ID(self):
        return RawToHex(self.product_id)

    def __repr__(self):
        return f'<ExciseMark(code={self.code}, egais_code={self.egais_code}, bill_B={self.bill_B}, product_id={self.product_ID})>'

ExciseMarkTable = ExciseMark.__table__            




