import json, datetime, arrow, re
from domino.core import log, RawToHex, HexToRaw
from sqlalchemy import Column, Integer, String, JSON, DateTime, Binary
from sqlalchemy.dialects.oracle import RAW, NUMBER, DATE
from domino.databases.oracle import Oracle
from sqlalchemy.orm import synonym, aliased
from sqlalchemy.types import TypeDecorator
from domino.enums.unit import Unit
from domino.enums.country import Country

#from domino.dicts.unit import Unit
#from domino.dicts.yes_no import YesNo

from domino.tables.oracle.DB1_PRODUCT import DB1_PRODUCT

class UNIT(TypeDecorator):
    impl = RAW(8)
    def process_bind_param(self, value, dialect):
        return value.uid if value else None
    def process_result_value(self, value, dialect):
        return Unit.get(value)

class COUNTRY(TypeDecorator):
    impl = RAW(8)
    def process_bind_param(self, value, dialect):
        return value.uid if value else None
    def process_result_value(self, value, dialect):
        return Country.get(value)

#296[3342343] 0000012800330007 "Акцизный товар : Признак (Да/Нет)"

class Product(DB1_PRODUCT):
    
    __tablename__ = 'db1_product'
    __table_args__ = {'extend_existing': True}

    group_id        = Column('local_group', RAW(8))
    @property
    def group_ID(self):
        return RawToHex(self.group_id)
    article         = Column(String)
    alco_type_id    = Column('f42401861', RAW(8))
    крепость        = Column('f28835907', String)

    expiration_sign = Column('f28835855', Oracle.YES_NO)
    контролировать_срок_годности = synonym(expiration_sign)

    #expiration_sign = Column('f28835855', RAW(8)) 
    #@property
    #def контролировать_срок_годности(self):
    #    return YesNo(self.expiration_sign, False)

    vsd_sign = Column('f42401800', Oracle.YES_NO) 
    требует_сертификации = synonym(vsd_sign)
    #@property
    #def требует_сертификации(self):
    #    return YesNo(self.vsd_sign, False)

    #unit_id  = Column('f14745607', RAW(8))
    unit  = Column('f14745607', UNIT)
    country = Column('f14745604', COUNTRY) # Страна производства : Государство"
    #@property
    #def unit_ID(self):
    #    return RawToHex(self.unit_id)
    #@property
    #def unit_name(self):
    #    unit = Unit.get(uid = self.unit_id)
        #log.debug(f'{unit}')
    #    return unit.name if unit else ''

    def __repr__(self):
        #unit = Unit.get(uid = self.unit_id)
         return f'<Product(id={self.ID}, name={self.name})>'

