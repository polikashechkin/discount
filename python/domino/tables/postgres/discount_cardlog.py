import json, datetime, random, arrow, re
from domino.core import log
from domino.databases.postgres import Postgres
from sqlalchemy import Column, Index, String, Integer, BigInteger, SmallInteger, DateTime, Date, JSON, DECIMAL, Float, Boolean
from sqlalchemy.orm import synonym

OPERATION_NAME = [
    'Информация', 
    'Создание',
    'Активация', 
    'Блокировка', 
    'Разблокировка', 
    'Изменение данных', 
    'Замена',
    'Начисление', 
    'Списание',
    'Использование',
    'Списание',
    'Покупка',
    'Оплата',
    'Погашение',
    'Изменение скидки'
    ]

def on_activate(account_id, on_activate_log):
    on_activate_log(f'Устаревший вызов DISCOUNT_CARDLOG.on_activate')
    table = Postgres.Table('DISCOUNT_CARDLOG')
    table.column('ID','BIGSERIAL')
    table.column('TYPE','SMALLINT DEFAULT 0 NOT NULL')
    table.column('STATE','SMALLINT')
    table.column('CARD_ID','VARCHAR NOT NULL')
    table.column('CHECK_ID','VARCHAR')
    table.column('DEPT_CODE','VARCHAR')
    table.column('USER_NAME','VARCHAR')
    table.column('CREATION_DATE','TIMESTAMP NOT NULL')
    table.column('CASH','DECIMAL')
    table.column('POINTS','DECIMAL')
    table.column('DISCOUNT','DECIMAL')
    table.column('INFO','JSONB')
    table.index('CARD_ID', 'CREATION_DATE', name='DISCOUNT_CARDLOG_BY_CARD')
    table.migrate(account_id, on_activate_log)

class DiscountCardLog(Postgres.Base):

    __tablename__ = 'discount_cardlog'
    __table_args__ = {'extend_existing': True}


    INFO = 0 # Инофрмационное сообщение произвольной природы
    CREATE = 1 # Создание карты
    ACTIVATE = 2 # Активация карты, может быть вместо создания
    DISABLE = 3 # Блокировка карты, покашение купоня
    ENABLE = 4 # Разблокировка карты, повторная активация
    CHANGE_PARAM = 5 # Изменение параметров карты (персональных данных)
    REPLACE = 6 # Замена карты с копирование параметров
    НАЧИСЛЕНИЕ_БАЛЛОВ = 7 
    СПИСАНИЕ_БАЛЛОВ = 8
    ИСПОЛЬЗОВАНИЕ = 9 
    СПИСАНИЕ = 10 
    ПОКУПКА = 11
    ОПЛАТА = 12
    ПОГАШЕНИЕ = 13
    ИЗМЕНЕНИЕ_СКИДКИ = 14

    COMMENT = 'MSG'
    CHECK_NO = 'NO'

    ID              = Column('id', BigInteger, primary_key=True, autoincrement=True, nullable=False)
    STATE           = Column('state', SmallInteger)
    TYPE            = Column('type', SmallInteger)
    creation_date   = Column(DateTime)
    card_id         = Column(String, nullable=False)
    check_id        = Column(String)
    dept_code       = Column(String)
    user_name       = Column(String)
    cash            = Column(DECIMAL)
    points          = Column(DECIMAL)
    discount        = Column(DECIMAL)
    info            = Column(Postgres.JSON)

    def __init__(self, card_id = None, operation = 0, creation_date = None):
        self.ID = None
        self.STATE = 0
        self.TYPE = operation
        self.creation_date = creation_date
        if self.creation_date is None:
            self.creation_date = datetime.datetime.now()
        self.card_id = card_id
        self.check_id = None
        self.dept_code = None
        self.user_name = None
        self.cash = None
        self.points = None
        self.discount = None
        self.info = {}

    @property
    def ctime(self):
        return self.creation_date
    @property
    def comment(self):
        return self.info.get(DiscountCardLog.COMMENT) if self.info else None
    @comment.setter
    def comment(self, value):
        if not self.info:
            self.info = {}
        self.info[DiscountCardLog.COMMENT] = value
    @property
    def check_no(self):
        return self.info.get(DiscountCardLog.CHECK_NO)
    @check_no.setter
    def check_no(self, value):
        self.info[DiscountCardLog.CHECK_NO] = value
    def check(self, check):
        if check:
            self.dept_code = check.dept_code
            user_name = check.params.get('CASHER')
            if user_name:
                self.user_name = user_name
            if check.pos_id: 
                self.check_no = f'{check.pos_id} {check.session_id} {check.check_no}'
                self.check_id = check.ID
    @property
    def operation_name(self):
        try:
            return OPERATION_NAME[self.TYPE]
        except:
            return ''
   
table = Postgres.Table('DISCOUNT_CARDLOG')
table.column('type','smallint default 0 not null')
table.column('creation_date','timestamp default current_timestamp')
table.index('card_id', 'creation_date', name='discount_cardlog_by_card')

