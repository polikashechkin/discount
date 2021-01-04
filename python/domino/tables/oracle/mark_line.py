import json, datetime, arrow, re
from domino.core import log
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime, Numeric, and_ , or_, insert, Date
from sqlalchemy.dialects.oracle import RAW, NUMBER
from sqlalchemy.orm import synonym
from sqlalchemy.types import TypeDecorator
from domino.databases.oracle import Oracle, HexToRaw, RawToHex
from enum import Enum

class MarkLineStatus(Enum):
    Загружена       = HexToRaw('03F5002E03F50001') #66388014[66387969] 03F5002E03F50001 "Загружен"
    Считана         = HexToRaw('03F5002E04030001') #66388014[67305473] 03F5002E04030001 "Считан"
    Добавлена       = HexToRaw('03F5002E03F50002') #66388014[66387970] 03F5002E03F50002 "Добавлен"
    Не_подтверждена = HexToRaw('03F5002E03F50003') #66388014[66387971] 03F5002E03F50003 "Не подтвержден"
    Подтверждена    = HexToRaw('03F5002E03F50005') #66388014[66387973] 03F5002E03F50005 "Подтвержден"
    Списана         = HexToRaw('03F5002E03F50006') #66388014[66387974] 03F5002E03F50006 "Списан"
    Блокирована     = HexToRaw('03F5002E03F50007') #66388014[66387975] 03F5002E03F50007 "Блокирован"

    def __str__(self):
        return self.name

class MARK_LINE_STATUS(TypeDecorator):
    impl = RAW(8)
    def process_bind_param(self, value, dialect):
        return value.value if value is not None else None
    def process_result_value(self, value, dialect):
        return MarkLineStatus(value) if value is not None else None

class MarkLine(Oracle.Base):

    Status = MarkLineStatus

    __tablename__ = 'db1_line'
    __table_args__ = {'extend_existing': True}

    MARK_LINE_CLASS                     = 1572865

    #VPP_MARK_LINE_TYPE                 = 67305495
    OLD_MARK_LINE_TYPE                  = 66388008
    Приход_от_поставщика_старая_марка   = 66388008

    Приход_от_поставщика_короткая_марка = 66388037
    Приход_от_поставщика_длинная_марка  = 67305490

    VPP_MARK_LINE_TYPE                  = 66388038
    Приход_по_внутреннему_перемещению   = 66388038
    
    VPP_OLD_MARK_LINE_TYPE              = 66388018
    
    #ЗАГРУЖЕНА               = HexToRaw('03F5002E03F50001')
    #СЧИТАНА                 = HexToRaw('03F5002E04030001')
    #ЕЩЕ_СТАТУС_В_ПРИХОДЕ    = HexToRaw('03F5002E03F50005')

    # 03F5002E03F50005 03F5002E03F50005

    id          = Column('id', RAW(8), primary_key=True)
    pid         = Column('pid', RAW(8))
    CLASS       = Column('class', NUMBER(10,0))
    TYPE        = Column('type', NUMBER(10,0))
    product_id  = Column('product', RAW(8))
    party_id    = Column('f12', RAW(8))
    document_id = Column('document', RAW(8))
    date        = Column('line_date', Date)

    @property
    def ID(self):
        return RawToHex(self.id)
    @property
    def PID(self):
        return RawToHex(self.pid)
    @property
    def product_ID(self):
        return RawToHex(self.product_id)
    @property
    def document_ID(self):
        return RawToHex(self.document_id)

    #status_id   = Column('f15073300', RAW(8))
    status      = Column('f15073300', MARK_LINE_STATUS)
    barcode     = Column('f14745605', String)
    egais_code  = Column('f15925250', String)
    
    #egais_code  = Column('f15925250', String)
    
    @staticmethod
    def insert(values):
        values[MarkLine.CLASS] = MarkLine.MARK_LINE_CLASS
        values[MarkLine.date] = datetime.date.today()
        return insert(MarkLineTable, values = values)
    
    def __repr__(self):
        return f'<MarkLine( id={self.ID}, pid={self.PID}, type={self.TYPE}, document_id={self.document_ID}, barcode={self.barcode})>'

MarkLine.VPP_MARK_LINE = and_(MarkLine.CLASS == 1572865, MarkLine.TYPE == MarkLine.VPP_MARK_LINE_TYPE)
MarkLine.VPP_OLD_MARK_LINE = and_(MarkLine.CLASS == 1572865, MarkLine.TYPE == MarkLine.VPP_OLD_MARK_LINE_TYPE)
MarkLine.Приход_от_поставщика = and_(
    MarkLine.CLASS == 1572865, 
    or_(
        MarkLine.TYPE == MarkLine.Приход_от_поставщика_длинная_марка, 
        MarkLine.TYPE == MarkLine.Приход_от_поставщика_короткая_марка
        )
    )
MarkLine.Class = (MarkLine.CLASS == 1572865)
MarkLineTable = MarkLine.__table__
