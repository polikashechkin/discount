 #import json, datetime, arrow
from sqlalchemy import Column, Integer, String, JSON, DateTime, or_, and_, Date
from sqlalchemy.dialects.oracle import RAW, NUMBER
from domino.databases.oracle import Oracle, RawToHex, HexToRaw
from domino.core import log
#from domino.tables.oracle.invoice_line import InvoiceLine
from domino.tables.oracle.DB1_DOCUMENT import DB1_DOCUMENT
from enum import Enum, IntEnum

from domino.tables.oracle.egais_line import EgaisLine, ПОМАРОЧНЫЙ_УЧЕТ, ПомарочныйУчет

class EgaisDocumentType(IntEnum):

    Приход_от_поставщика                = 66387971
    Расход_стороннему_покупателю        = 66387972
    Списание_со_склада                  = 66387979
    Приход_по_внутреннему_перемещению   = 66387984
    Расход_по_внутреннему_перемещению   = 66387977
    Возврат_поставщику                  = 66387978
    Возврат_товаров_поставщику          = 14286853
    Возврат_поставщику_по_претензиям    = 12058695
    Возврат_реализация_неликвидного_товара_поставщику = 28835963
    
    @staticmethod
    def get(value):
        return EgaisDocumentType(int(value))
    
    def __str__(self):
        return self.name

class EgaisDocument(DB1_DOCUMENT):
    ПомарочныйУчет = ПомарочныйУчет

    Type = EgaisDocumentType

    __tablename__ = 'db1_document'
    __table_args__ = {'extend_existing': True}

    exchange_status_ПОДТВЕРЖДЕН         = HexToRaw('07D2000307D20002')
    F33620483_0403002504030001          = HexToRaw('0403002504030001') # помарочный учет
    
    F14286853_07D2000307D20002 = HexToRaw('07D2000307D20002')

    egais_doc           = Column('f14286860', String) #Идентификатор ТТН в ЕГАИС 331[14286860]
    #exchange_status     = Column('f61669377', RAW(8)) # статус подтветрждения из ЕГАИС
    exchange_status     = Column('f61669377', Oracle.YES_NO) # статус подтветрждения из ЕГАИС
    F14286853           = Column('f14286853', RAW(8))
    #F33620483           = Column('f33620483', RAW(8)) # какой то статус
    помарочный_учет     = Column('f33620483', ПОМАРОЧНЫЙ_УЧЕТ) 
    F60424223           = Column('f60424223', RAW(8))
    comment             = Column('f13', String)
    fsrar_id            = Column('f14286872', String)
    invoice_id          = Column('f15073282' , RAW(8))
    
    @property
    def type_(self):
        return EgaisDocumentType(self.TYPE)

    @property
    def document_type_(self):
        return EgaisDocumentType(self.TYPE)
    
    def __repr__(self):
        return f'<EgaisDocument(id={RawToHex(self.id)}, type={self.TYPE}), code={self.code}, comment={self.comment}>'
 
EgaisDocument.InWork = and_(
    EgaisDocument.state != 1, 
    #EgaisDocument.F33620483 == EgaisDocument.F33620483_0403002504030001,
    EgaisDocument.F14286853 == None
    )

EgaisDocument.Class = (EgaisDocument.CLASS == 65537)
EgaisDocument.ClassType = and_(
    EgaisDocument.CLASS == 65537, 
    EgaisDocument.TYPE.in_([
        EgaisDocument.Type.Приход_от_поставщика.value,
        EgaisDocument.Type.Приход_по_внутреннему_перемещению.value,
        EgaisDocument.Type.Возврат_поставщику.value,
        EgaisDocument.Type.Возврат_поставщику_по_претензиям.value,
        EgaisDocument.Type.Возврат_реализация_неликвидного_товара_поставщику.value,
        EgaisDocument.Type.Возврат_товаров_поставщику.value,
        EgaisDocument.Type.Расход_по_внутреннему_перемещению.value,
        EgaisDocument.Type.Расход_стороннему_покупателю.value,
        EgaisDocument.Type.Списание_со_склада.value
    ])
    )

#EgaisDocument.type_names = {
#    EgaisDocument.Приход_от_поставщика : 'Приход от поставщика',
#    EgaisDocument.Приход_по_внутреннему_перемещению : 'Приход по внутреннему перемещению',
#    EgaisDocument.Возврат_поставщику : 'Возврат поставщику',
#    EgaisDocument.Возврат_поставщику_по_претензиям : 'Возврат поставщику по претензиям',
#    EgaisDocument.Возврат_реализация_неликвидного_товара_поставщику : 'Возврат реализация неликвидного товара поставщику',
#    EgaisDocument.Возврат_товаров_поставщику : 'Возврат товаров поставщику',
#   EgaisDocument.Расход_стороннему_покупателю : 'Расход стороннему покупателю',
#    EgaisDocument.Расход_по_внутреннему_перемещению : 'Расход по внутреннему перемещению',
#    EgaisDocument.Списание_со_склада : 'Списание со склада'
#}

EgaisDocumentTable = EgaisDocument.__table__
