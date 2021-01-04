import json, datetime, arrow, re
from domino.core import log
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime, Binary
from sqlalchemy.dialects.oracle import RAW, NUMBER
from sqlalchemy import or_, and_
from domino.databases.oracle import Oracle, HexToRaw, RawToHex

from sqlalchemy.types import TypeDecorator
from enum import Enum

from domino.tables.oracle.DB1_CLASSIF import DB1_CLASSIF

class BasketType(Enum):
    ЛИЧНАЯ_КОРЗИНА = [HexToRaw('03F1000103F10003'), HexToRaw('0017013803570127')]
    ОБЩАЯ_КОРЗИНА = [HexToRaw('03F1000103F10002'), HexToRaw('0017013803570128')]
    КОЛЛЕКТИВНАЯ_КОРЗИНА = [HexToRaw('03F1000103F10004'), HexToRaw('0017013803570129')]
    @staticmethod
    def get(value):
        if value in BasketType.ЛИЧНАЯ_КОРЗИНА.value:
            return BasketType.ЛИЧНАЯ_КОРЗИНА
        elif value in BasketType.ОБЩАЯ_КОРЗИНА.value:
            return BasketType.ОБЩАЯ_КОРЗИНА
        elif value in BasketType.КОЛЛЕКТИВНАЯ_КОРЗИНА.value:
            return BasketType.КОЛЛЕКТИВНАЯ_КОРЗИНА
    def __str__(self):
        return self.name

class Basket(DB1_CLASSIF):
    
    BasketType = BasketType

    __tablename__ = 'db1_classif'
    __table_args__ = {'extend_existing': True}

    basket_type_id = Column('f34996228', RAW(8))
    owner_id = Column('f34996225', RAW(8))
    dept_id = Column('f15073281', RAW(8))
    
    @property
    def owner_ID(self):
        return RawToHex(self.owner_id)
    @property
    def basket_type_ID(self):
        return RawToHex(self.basket_type_id)
    @property
    def basket_type(self):
        return BasketType.get(self.basket_type_id)
    @property
    def dept_ID(self):
        return RawToHex(self.dept_id)

Basket.ClassType = and_(Basket.CLASS == 28835869, Basket.TYPE == 43122699) 
Basket.ЛИЧНЫЕ_КОРЗИНЫ = and_(Basket.ClassType, Basket.basket_type_id.in_(BasketType.ЛИЧНАЯ_КОРЗИНА.value))
Basket.КОЛЛЕКТИВНЫЕ_КОРЗИНЫ = and_(Basket.ClassType, Basket.basket_type_id.in_(BasketType.КОЛЛЕКТИВНАЯ_КОРЗИНА.value))
Basket.ОБЩИЕ_КОРЗИНЫ = and_(Basket.ClassType, Basket.basket_type_id.in_(BasketType.ОБЩАЯ_КОРЗИНА.value))

BasketTable = Basket.__table__ 


