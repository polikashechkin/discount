import json, datetime, arrow, re
from domino.core import log, HexToRaw, RawToHex
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime, Numeric, and_, or_, Date
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.oracle import RAW, NUMBER
from domino.databases.oracle import Oracle
from enum import Enum


class ПомарочныйУчет(Enum):
    Обязателен      = HexToRaw('0403002504030001') # 67305509[67305473]  "Обязателен"
    Не_обязателен   = HexToRaw('0403002504030004') # 67305509[67305476]  "Не обязателен"
    Нет_учета       = HexToRaw('0403002504030002') # 67305509[67305474]  "Нет учета"
    Ошибка          = HexToRaw('0403002504030003') # 67305509[67305475]  "Ошибка"
    Нет             = HexToRaw('07D2000307D20001') # "Нет : 0"    def __str__(self):
    Да              = HexToRaw('07D2000307D20002') # "Да : 1"

    def __str__(self):
        return self.name

    @staticmethod
    def get(value): 
        try:
            return ПомарочныйУчет(value)
        except:
            return None

class ПОМАРОЧНЫЙ_УЧЕТ(TypeDecorator):
    impl = RAW(8)
    def process_bind_param(self, value, dialect):
        return value.value if value is not None else None
    def process_result_value(self, value, dialect):
        return ПомарочныйУчет(value) if value is not None else None
'''
360[66387985
360[43122728
360[66387992
360[67305481
360[8847379
360[66387973
360[55509024
360[66387975
360[66387987
360[66387993
360[66388037
360[66387969
360[66387986
360[54919374
360[66387977
360[66387974
360[66387988
360[66387979
360[66387970
360[67305475
360[43122727
360[40304642
360[66387984
360[66387982
360[8847376
360[66387976
360[67305478
'''
class EgaisLine(Oracle.Base):
    
    ПомарочныйУчет = ПомарочныйУчет

    __tablename__ = 'db1_line'
    __table_args__ = {'extend_existing': True}
    
    #Приход_от_поставщика = 66388037
    Приход_от_поставщика                = 66387969
    Приход_по_внутреннему_перемещению   = 66387984
    VPP_EGAIS_LINE_TYPE                 = 66387984  # 360[66387984] 0000016803F50010 "Строка прихода по внутреннему перемещению ЕГАИС : СТРОКА"
    Расход_стороннему_покупателю        = 66387970
    Возврат_поставщику                  = 66387977 
    Списание_со_склада                  = 66387978
    # 67305478

    ПОМАРОЧНЫЙ_УЧЕТ_ОБЯЗАТЕЛЕН              = HexToRaw('0403002504030001') # 67305509[67305473]  "Обязателен"
    ПОМАРОЧНЫЙ_УЧЕТ_НЕ_ОБЯЗАТЕЛЕН           = HexToRaw('0403002504030004') # 67305509[67305476]  "Не обязателен"
    ПОМАРОЧНЫЙ_УЧЕТ_НЕТ_УЧЕТА               = HexToRaw('0403002504030002') # 67305509[67305474]  "Нет учета"
    ПОМАРОЧНЫЙ_УЧЕТ_ОШИБКА                  = HexToRaw('0403002504030003') # 67305509[67305475]  "Ошибка"

    #_0403002504030001 = HexToRaw('0403002504030001')

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

    egais_code          = Column('f15925250', String)
    mark_qty            = Column('f2818051', NUMBER(15,3))  # Количество акц.марок
    qty                 = Column('f14286852', NUMBER(15,3)) # Кол-во (факт.)
    
    #bill_B              = Column('f61669378', String) # номер справки Б
    bill_B              = Column('f42401810', String) # номер справки Б
    #mark_accounting     = Column('f56033310', RAW(8)) # помарочный учет
    помарочный_учет     = Column('f56033310', ПОМАРОЧНЫЙ_УЧЕТ)
    @property
    def помарочный_учет_обязателен(self):
        return self.помарочный_учет and self.помарочный_учет == ПомарочныйУчет.Обязателен
    line_number         = Column('f59375715', Numeric)

            #F15925250 state
    def __repr__(self):
        return f'<EgaisLine(id={self.ID}, type={self.TYPE}, egais_code={self.egais_code}, product_id={self.product_ID})>'

egais_line_types = [
    EgaisLine.Приход_от_поставщика,
    EgaisLine.Приход_по_внутреннему_перемещению,
    EgaisLine.Расход_стороннему_покупателю,
    EgaisLine.Возврат_поставщику,
    EgaisLine.Списание_со_склада,
    EgaisLine.Приход_по_внутреннему_перемещению
]

#EgaisLine.Class = (EgaisLine.CLASS == 1572865)
EgaisLine.VPP_EGAIS_LINE = and_(EgaisLine.CLASS == 1572865, EgaisLine.TYPE == EgaisLine.VPP_EGAIS_LINE_TYPE)
EgaisLine.Class = (EgaisLine.CLASS == 1572865)
EgaisLine.ClassType = and_(EgaisLine.CLASS == 1572865, EgaisLine.TYPE.in_(egais_line_types))
EgaisLineTable = EgaisLine.__table__

