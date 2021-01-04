import json, datetime, arrow, re
from sqlalchemy import Column, Integer, String, JSON, DateTime, Binary, Numeric
from sqlalchemy import or_, and_
from sqlalchemy.dialects.oracle import RAW, NUMBER, VARCHAR2, DATE
from sqlalchemy.orm import synonym

from domino.core import log
from domino.tables.oracle.DB1_LINE import DB1_LINE
from domino.databases.oracle import RawToHex, HexToRaw
from domino.dicts.vat import Vat
from domino.dicts.yes_no import YesNo

class InvoiceLine(DB1_LINE):

    __tablename__ = 'db1_line'
    __table_args__ = {'extend_existing': True}

    qty         = Column('f14286852', NUMBER(15,3)) # Количество
    qty_doc     = Column('f14286860', NUMBER(15,3)) # 
    qty_fact    = Column('f40042516', NUMBER(15,3)) # Подтвержденное количество, cчитанное количество

    line_number = Column('f6684696', NUMBER(10,0))
    price       = Column('f15007745', NUMBER(19,6))
    @property
    def PRICE(self):
        return f'{int(self.price)}.{int(self.price * 100) % 100:02}'

    egais_code  = Column('f15925250', String)

    vat_id      = Column('f14286858', RAW(8)) 
    @property
    def vat_name(self):
        return Vat.get(self.vat_id).name
    @property
    def vat_value(self):
        return Vat.get(self.vat_id).value
    @property
    def vat(self):
        return Vat.get(self.vat_id)

    warning_sign  = Column('f2818057', RAW(8))
    warning_desc = Column('f8847382', String) 
    @property
    def warning(self):
        return YesNo(self.warning_sign, False)

    sum_doc     = Column('f15073284', NUMBER(19,2)) #Сумма документальная по Домино,  Сумма по цене по накладной поставщика (док)
    sum_doc_sup = Column('f33619978', NUMBER(19,2))
    qty_doc_sup = Column('f40042517', NUMBER(15,3))
        
    exp_date    = Column('f14286868', DATE) 
    @property
    def срок_годности(self):
        return self.exp_date

    vetsert     = Column('f59375717' , VARCHAR2(40))

    def __repr__(self):
        return f'<InvoiceLine(id={self.ID}, type={self.TYPE}, documnet_id={self.document_ID}, product_id={self.product_ID}, egais_code={self.egais_code}, qty={self.qty}, qty_fact={self.qty_fact}, qty_doc={self.qty_doc})>'


InvoiceLine.ClassType = and_(InvoiceLine.CLASS == 14286849, InvoiceLine.TYPE == 14286855)

InvoiceLineTable = InvoiceLine.__table__ 


