import json, datetime, arrow, re
from domino.core import log
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime, Binary
from sqlalchemy.dialects.oracle import RAW, NUMBER
from sqlalchemy import or_
from domino.databases.oracle import Oracle

class BasketLine(Oracle.Base):

    __tablename__ = 'ANY_ASSORTMENT_LIST'.lower()

    basket_id = Column('TYPE_OF_ASSORTMENT_LIST'.lower(), RAW(8), primary_key = True)
    product_id = Column('product', RAW(8), primary_key=True)
    qty = Column('QUANTITY'.lower(), NUMBER(15,3))

BasketLineTable = BasketLine.__table__ 


