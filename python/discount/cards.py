import json, datetime, cx_Oracle, random, arrow, re
from domino.core import log
from domino.databases.postgres import Postgres
from discount.core import CARDS, CARDS_LOG, Engine
#from domino.databases import Databases, drop_table, table_exists
from discount.series import ТипКарты
import barcodenumber
import barcode
from sqlalchemy.orm.session import Session

#from settings import PostgresTable
from sqlalchemy import Column, String, Integer, BigInteger, SmallInteger, DateTime, Date, JSON, DECIMAL, Float, Boolean
from sqlalchemy.orm.session import Session

def execute_sql(cur, sql, log = None):
    if log is not None: 
        log(sql)
    cur.execute(sql) 

TRY_CREATE_COUNT = 10
OPERATION_NAME = [
    'Информация', 
    'Создание',
    'Активация', 
    'Блокировка', 
    'Разблокировка', 
    'Изменение параметра', 
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

class CardLog(Postgres.Base):

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

    @staticmethod
    def on_activate(account_id, msg_log):
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
        table.migrate(account_id, msg_log)

    ID              = Column('id', BigInteger, primary_key=True, autoincrement=True)
    STATE           = Column('state', SmallInteger)
    TYPE            = Column('type', SmallInteger)
    creation_date   = Column(DateTime)
    card_id         = Column(String)
    check_id        = Column(String)
    dept_code       = Column(String)
    user_name       = Column(String)
    cash            = Column(DECIMAL)
    points          = Column(DECIMAL)
    discount        = Column(DECIMAL)
    info            = Column(JSON)

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
    def comment(self):
        return self.info.get(CardLog.COMMENT)
    @comment.setter
    def comment(self, value):
        self.info[CardLog.COMMENT] = value
    @property
    def check_no(self):
        return self.info.get(CardLog.CHECK_NO)
    @check_no.setter
    def check_no(self, value):
        self.info[CardLog.CHECK_NO] = value
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
    
    __FIELDS__ = 'ID, TYPE, STATE, creation_date, card_id, check_id, dept_code, user_name, cash, points, discount, INFO'
    @staticmethod
    def __FROM_FIELDS__(fields):
        if fields:
            c = CardLog()
            c.ID, c.TYPE, c.STATE, c.creation_date, c.card_id, c.check_id, c.dept_code, c.user_name, c.cash, c.points, c.discount, INFO = fields
            if INFO:
                try:
                    c.info = json.loads(INFO)
                except:
                    c.info = {}
            else:
                c.info = {}
            return c

    @staticmethod
    def find(engine, where_clause, params = {}):
        cur = engine.pg_cursor
        cur.execute(f'''
        select {CardLog.__FIELDS__} from DISCOUNT_CARDLOG where {where_clause}
        ''', params)
        return CardLog.__FROM_FIELDS__(cur.fetchone())

    @staticmethod
    def findall(engine, where_clause, params = {}):
        cur = engine.pg_cursor
        log = []
        cur.execute(f'''
        select {CardLog.__FIELDS__} from DISCOUNT_CARDLOG where {where_clause}
        ''', params)
        for r in cur:
            log.append(CardLog.__FROM_FIELDS__(r))
        return log

    def create(self, engine):
        cur = engine.pg_cursor
        if self.creation_date is None:
            self.creation_date = datetime.datetime.now()
        #log.debug(f'cretae ({self.info})')
        if len(self.info) == 0:
            INFO = None
        else:
            INFO = json.dumps(self.info, ensure_ascii = False, check_circular = False)
        cur.execute(f'''
        insert into DISCOUNT_CARDLOG (
            TYPE, STATE, creation_date, 
            card_id, check_id, dept_code, user_name,
            cash, points, discount,
            info)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ''', [self.TYPE, self.STATE, self.creation_date, 
        self.card_id, self.check_id, self.dept_code, self.user_name,
        self.cash, self.points, self.discount,
        INFO])
   
CARD_STATE_NAME = ['Только содан(а)', 'В работе', 'Погашен(а)']

class Card(Postgres.Base):

    __tablename__ = 'discount_card'
    __table_args__ = {'extend_existing': True}
    
    CREATED = 0 # Только создана, но еще не в работе
    ТОЛЬКО_СОЗДАННАЯ_КАРТА = 0 # Только создана, но еще не в работе
    ACTIVE = 1 # Активная, действующая карта
    АКТИВНАЯ_КАРТА = 1 # Активная, действующая карта
    DISABLED = 2 # Карта заблокирована (Купон погашен)
    ЗАБЛОКИРОВАННАЯ_КАРТА = 2 # Карта заблокирована (Купон погашен)
    
    LOST = 3 # Карта утеряна или бракована, использование блокируется, требуется замена
    REPLACED = 4 # По утеряной карте выдали замену. Данная карта на ходится в архиве

    CHECK_ID = 'check_id'
    CHECK_DATE = 'check_date'
    ACTION_ID = 'action_id'

    ACTIVATION_DATE = 'a_date'
    DEACTIVATION_DATE = 'd_date'
    CREATE_DATE = 'c_date' # Дата создания карты
    PRICE = 'price' # Цена карточки при продаже (номинал для подарочных карт)
    REUSABLE = 'reusable' # 0 - Одноразовый сенртификат 1 - Многоразовый сертификат
    EXP_DAYS = 'exp_days' # Количество дней с момента активации до истечения строка действия
    
    ВХОДЯЩАЯ_СУММА_ПОКУПОК = 'I_TT'
    ВХОДЯЩЕЕ_КОЛИЧЕСТВО_ПОКУПОК = 'I_CHK'
    ВХОДЯЩИЙ_ОСТАТОК_ДЕНЕЖНЫХ_СРЕДСТВ = 'I_CH'

    @staticmethod
    def on_activate(account_id, msg_log):
        table = Postgres.Table('DISCOUNT_CARD')
        table.column('ID','VARCHAR NOT NULL PRIMARY KEY')
        table.column('PID','VARCHAR')
        table.column('CLASS','SMALLINT DEFAULT 0 NOT NULL')
        table.column('TYPE','SMALLINT DEFAULT 0 NOT NULL')
        table.column('STATE','SMALLINT DEFAULT 0 NOT NULL')
        table.column('MODIFY_DATE','TIMESTAMP')
        table.column('EXP_DATE','DATE')
        table.column('ACTIVATE_DATE','DATE')
        table.column('DEACTIVATE_DATE','DATE')
        table.column('MARKNUM','VARCHAR')
        table.column('DEPT_CODE','VARCHAR')
        table.column('CASH','FLOAT')
        table.column('POINTS','FLOAT')
        table.column('DISCOUNT','FLOAT') 
        table.column('PHONE','VARCHAR')
        table.column('PHONE_VERIFIED','BOOL')
        table.column('EMAIL','VARCHAR')
        table.column('EMAIL_VARIFIED','BOOL')
        table.column('DAY','DATE')
        table.column('NAME','VARCHAR')
        table.column('NAME1','VARCHAR')
        table.column('NAME2','VARCHAR')
        table.column('IS_TEST','BOOL')
        table.column('REUSABLE','BOOL')
        table.column('TOTAL','FLOAT')
        table.column('CHECKS','INTEGER')
        table.column('INFO','JSONB')
        table.column('ctime','timestamp default current_timestamp')

        table.index('TYPE', name='DISCOUNT_CARD_BY_TYPE')
        table.index('PHONE', name = 'DISCOUNT_CARD_BY_PHONE')
        table.index('IS_TEST', name = 'DISCOUNT_CARD_BY_TEST')
        table.index('MODIFY_DATE', name ='DISCOUNT_CARD_BY_MODIFY_DATE')

        table.migrate(account_id, msg_log)

        table = Postgres.Table('DISCOUNT_CARD_NUMERATOR')
        table.column('CLASS','SMALLINT DEFAULT 0 NOT NULL')
        table.column('TYPE','SMALLINT DEFAULT 0 NOT NULL')
        table.column('NUMBER','BIGINT DEFAULT 0 NOT NULL')
        table.migrate(account_id, msg_log)

    ID              = Column('id', String, primary_key=True)
    PID             = Column('pid', String)
    CLASS           = Column('class', SmallInteger)
    TYPE            = Column('type', SmallInteger, nullable=False)
    STATE           = Column('state', SmallInteger, nullable=False)
    modify_date     = Column(DateTime)
    exp_date        = Column(Date)
    activation_date = Column('activate_date', Date)
    deactivation_date = Column('deactivate_date', Date)
    marknum         = Column(String)
    dept_code       = Column(String)
    cash            = Column(Float)
    points          = Column(Float)
    discount        = Column(Float)
    phone           = Column(String)
    phone_verified  = Column(Boolean)
    email           = Column(String)
    email_verified  = Column('email_varified', Boolean)
    день_рождения   = Column('day', String)
    фамилия         = Column('name', String)
    имя             = Column('name1', String)
    отчество        = Column('name2', String)
    is_test         = Column(Boolean)
    reusable        = Column(Boolean)
    total           = Column(Float)
    checks          = Column(Integer)
    info            = Column(JSON)
    ctime           = Column(DateTime)
    
    @property
    def id(self):
        return self.ID

    @property
    def pid(self):
        return self.PID

    def __init__(self, ID = None, STATE = 0, CLASS = 0, TYPE = 0):
        self.ID = ID
        self.PID = None
        #self.client_UID = None
        #self.card_UID = None
        self.STATE = STATE
        self.CLASS = CLASS
        self.TYPE = TYPE
        self.modify_date = None
        self.exp_date = None
        self.activation_date = None
        self.deactivation_date = None
        self.marknum = None
        self.dept_code = None
        self.cash = None
        self.discount = None
        self.points = None
        self.phone = None
        self.phone_verified = None
        self.email = None
        self.email_verified = None
        self.день_рождения = None
        self.фамилия = None
        self.имя = None
        self.отчество = None
        self.is_test = None
        self.reusable = None
        self.total = None
        self.checks = None
        self.info = {}

    def __repr__(self):
        return f'DiscountCard(ID={self.ID}, CLASS={self.CLASS}, TYPE={self.TYPE}, marknum={self.marknum}'

    def зафиксировать_покупку(self, check):
        if self.total is None:
            self.total = 0
        if self.checks is None:
            self.checks = 0
        self.checks += 1
        self.total += check.total
        дата = str(check.date.date())
        if self.дата_последней_покупки and self.дата_последней_покупки == дата:
            self.количество_покупок_за_последнюю_дату += 1 
        else:
            self.дата_последней_покупки = дата
            self.количество_покупок_за_последнюю_дату = 1 

    def аннулировать_покупку(self, check):
        if self.total is None:
            self.total = 0
        if self.checks is None:
            self.checks = 0
        if self.checks > 0:
            self.checks -= 1
        self.total += check.total
        if self.total < 0:
            self.total = 0
        #дата = str(check.date.date())
        #if self.дата_последней_покупки and self.дата_последней_покупки == дата:
        #    self.количество_покупок_за_последнюю_дату += 1 
        #else:
        #    self.дата_последней_покупки = дата
        #    self.количество_покупок_за_последнюю_дату = 1 

    @property
    def дата_последней_покупки(self):
        return self.info.get('PD')
    
    @дата_последней_покупки.setter
    def дата_последней_покупки(self, value):
        self.info['PD'] = str(value)

    @property
    def количество_покупок_за_последнюю_дату(self):
        return self.info.get('PQ')
    @количество_покупок_за_последнюю_дату.setter
    def количество_покупок_за_последнюю_дату(self, value):
        self.info['PQ'] = value
    
    @property
    def входящее_количество_покупок(self):
        return self.info.get(Card.ВХОДЯЩЕЕ_КОЛИЧЕСТВО_ПОКУПОК)
    @property
    def входящая_сумма_покупок(self):
        return self.info.get(Card.ВХОДЯЩАЯ_СУММА_ПОКУПОК)
    
    def обновление_входящих_параметров(self, total = None, checks=None, cash=None):
        #log.debug(f'обновление_входящих_параметров({self.ID}, {total}, {checks}, {cash}')
        #log.debug(f'self.total = {self.total} self.checks = {self.checks} self.info={self.info}')
        updated = False
        if total:
            if self.total is None:
                self.total = 0
            i_total = self.info.get(Card.ВХОДЯЩАЯ_СУММА_ПОКУПОК, 0)
            if i_total != total:
                self.info[Card.ВХОДЯЩАЯ_СУММА_ПОКУПОК] = total
                self.total += (total - i_total)
                updated = True

        if checks:
            if self.checks is None:
                self.checks = 0
            i_checks = self.info.get(Card.ВХОДЯЩЕЕ_КОЛИЧЕСТВО_ПОКУПОК, 0)
            if i_checks != checks:
                self.info[Card.ВХОДЯЩЕЕ_КОЛИЧЕСТВО_ПОКУПОК] = checks
                self.checks += (checks - i_checks)
                updated = True
        
        if cash:
            if self.cash is None:
                self.cash = 0
            i_cash = self.info.get(Card.ВХОДЯЩИЙ_ОСТАТОК_ДЕНЕЖНЫХ_СРЕДСТВ, 0)
            if i_cash != cash:
                self.info[Card.ВХОДЯЩИЙ_ОСТАТОК_ДЕНЕЖНЫХ_СРЕДСТВ] = cash
                self.cash += (cash - i_cash)
                updated = True

        #log.debug(f'self.total = {self.total} self.checks = {self.checks} self.info={self.info}')
        return updated

    def set_deactivation_date(self):
        self.deactivation_date = datetime.date.today()

    def set_activation_date(self):
        self.activation_date = datetime.date.today()

    @property
    def creation_date(self):
        return self.info.get(Card.CREATE_DATE)

    @property
    def телефон_для_печати(self):
        return Card.преобразовать_к_печатному_виду(self.phone)
    @property
    def телефон_для_ввода(self):
        if self.phone is None:
            return ''
        else:
            a = str(self.phone)
            return f'{a[1:4]} {a[4:7]} {a[7:]}'
    @staticmethod
    def преобразовать_к_печатному_виду(телефон):
        if телефон is None:
            return ''
        телефон = str(телефон)
        return f'+{телефон[0]} ({телефон[1:4]}) {телефон[4:7]}-{телефон[7:]}'
    @staticmethod
    def преобразовать_к_нормальному_виду(телефон):
        if телефон is None:
            return None
        else:
            try:
                телефон = str(телефон)
                телефон =  re.sub(r'[^0-9]','', телефон)
                if телефон == '':
                    return None
                if телефон[0] == '7':
                    pass
                elif телефон[0] == '8':
                    телефон = '7' + телефон[1:]
                else:
                    телефон = '7' + телефон
                if len(телефон) != 11:
                    return None
                return int(телефон)
            except:
                return None
    def установить_телефон(self, телефон):
        self.phone = Card.преобразовать_к_нормальному_виду(телефон)
    def изменить_телефон(self, телефон):
        if телефон: 
            телефон = Card.преобразовать_к_нормальному_виду(телефон)
            if not self.phone or телефон != self.phone:
                self.phone = телефон
                return True
        return False
    @property
    def пол(self):
        return self.info.get('SEX')
    @пол.setter
    def пол(self, value):
        self.info['SEX'] = value
    @property
    def рассылка_по_почте(self):
        return self.info.get('EM0', 0)
    @рассылка_по_почте.setter
    def рассылка_по_почте(self, value):
        self.info['EM0'] = value
    @property
    def рассылка_по_смс(self):
        return self.info.get('SMS', 0)
    @рассылка_по_смс.setter
    def рассылка_по_смс(self, value):
        self.info['SMS'] = value
    @property
    def ФИО(self):
        фио = []
        if self.фамилия:
            фио.append(self.фамилия)
        if self.имя:
            фио.append(self.имя)
        if self.отчество:
            фио.append(self.отчество)
        return ' '.join(фио).strip()
    @property
    def это_только_созданная_карта(self):
        return self.STATE == Card.CREATED
    @property
    def это_активная_карта(self):
        return self.STATE == Card.ACTIVE
    @property
    def это_заблокированная_карта(self):
        return self.STATE == Card.DISABLED
    
    @property
    def state_name(self):
        try:
            return CARD_STATE_NAME[self.STATE]
        except:
            return f'Состояние "{self.STATE}"'

    @staticmethod 
    def create_card(engine, card_type, number = None, user_name = None, check = None, is_test = False):
        postgres = engine if isinstance(engine, Session) else None
        prefix = card_type.prefix
        suffix = card_type.suffix
        digits = card_type.digits
        ean13 = card_type.code_format_ean13
        card = Card(TYPE = card_type.ID, STATE = Card.CREATED)
        card.modify_date = datetime.datetime.now()

        card.reusable = card_type.reusable
        if check:
            card.dept_code = check.dept_code
        if is_test or (check and check.is_test):
            card.is_test = 1

        if number:
            # создание с заданным номером
            if digits:
                s_number = str(number).zfill(digits)
            else:
                s_number = ''
            card.ID = f'{prefix}{s_number}{suffix}'
            if ean13:
                card.ID = str(barcode.get_barcode('ean13', card.ID))
            card.marknum = s_number
            if postgres:
                postgres.add(card)
            else:
                card.create(engine)
        else:
            # создание с применением случайой генерации номера
            try_number = 0
            last_error_message = ''
            while try_number < TRY_CREATE_COUNT:
                try_number += 1
                number = random.randrange( 10**(digits-1), 10**(digits)-1) 
                try:
                    card.ID = f'{prefix}{number}{suffix}'
                    if ean13:
                        card.ID = str(barcode.get_barcode('ean13', card.ID))
                    card.marknum = f'{number}'
                    if postgres:
                        postgres.add(card)
                        postgres.commit()
                    else:
                        card.create(engine)    
                    break
                except BaseException as ex:
                    if postgres:
                        postgres.rollback()
                    log.exception(f'{try_number} : {ex}')
                    last_error_message = f'{ex}'
                    #raise Exception(ex)
            # Проверка а получилось ли?
            if try_number >= TRY_CREATE_COUNT:
                log.error(f'Невозмоно создать карту : Сделано {try_number} попыток : {last_error_message}')
                raise Exception(f'Невозмоно создать карту. Сделано {try_number} попыток.')

        cardlog = CardLog(card.ID, CardLog.CREATE)
        cardlog.user_name = user_name
        cardlog.check(check)
        if postgres:
            postgres.add(cardlog)
        else:
            cardlog.create(engine)

        return card

    @staticmethod 
    def создать_карту(engine, card_type, number = None, user_name = None, check = None, is_test = False):
        return Card.create_card(engine, card_type, number = number, user_name = user_name, check = check, is_test = is_test)
    @staticmethod 
    def __создать_карту(engine, card_type, number = None, user_name = None, check = None, is_test = False):
        #log.debug(f'создать_карту(engine, {card_type}, number={number}, user_name={user_name}, check={check}, is_test={is_test})')
        card = Card(TYPE = card_type.ID)
        #card.CLASS = card_type.CLASS_ID
        card.STATE = Card.CREATED
        digits = card_type.digits
        prefix = card_type.prefix
        suffix = card_type.suffix
        ean13 = card_type.code_format_ean13
        random_mode = card_type.gen_mode_random
        #log.debug(f'digits={digits}, prefix={prefix}, suffix={suffix}, ramdom={random}')
        if card_type.reusable:
            card.reusable = True
        if check:
            card.dept_code = check.dept_code

        if is_test or (check and check.is_test):
            card.is_test = 1

        if random_mode:
            # создание с применением случайой генерации номера
            try_number = 0
            last_error_message = ''
            while try_number < TRY_CREATE_COUNT:
                try_number += 1
                number = random.randrange( 10**(digits-1), 10**(digits)-1) 
                try:
                    card.ID = f'{prefix}{number}{suffix}'
                    if ean13:
                        card.ID = barcode.get_barcode('ean13', card.ID)
                    card.marknum = f'{number}'
                    card.create(engine)
                    break
                except BaseException as ex:
                    log.exception(f'{try_number} : {ex}')
                    last_error_message = f'{ex}'
            # Проверка а получилось ли?
            if try_number >= TRY_CREATE_COUNT:
                raise Exception(f'Невозмоно создать карту : Сделано {try_number} попыток : {last_error_message}')
        else:
            # создание с последовательной нумеарций, следующий номер : number
            if digits:
                s_number = str(number).zfill(digits)
            else:
                s_number = ''
            card.ID = f'{prefix}{s_number}{suffix}'
            if ean13:
                card.ID = barcode.get_barcode('ean13', card.ID)
            card.marknum = s_number
            card.create(engine)

        cardlog = CardLog(card.ID, CardLog.CREATE)
        #log.debug(f'CREATE {cardlog.info}')
        if user_name:
            cardlog.user_name = user_name
        cardlog.check(check)
        cardlog.create(engine)
        #log.debug(f'CREATE {cardlog.info}')
        return card

    @staticmethod 
    def создать_подарочный_купон(engine, card_type, check, is_test = False):
        return Card.create_card(engine, card_type, number = None, user_name = None, check = check, is_test = is_test)

    @staticmethod 
    def __создать_подарочный_купон(engine, card_type, check, is_test = False):
        #log.debug(f'создать_подарочный_купон(engine, {card_type}, check={check}, is_test={is_test})')
        card = Card(TYPE = card_type.ID)
        #card.CLASS = card_type.CLASS_ID
        card.STATE = Card.CREATED
        digits = card_type.digits
        prefix = card_type.prefix
        suffix = card_type.suffix
        ean13 = card_type.code_format_ean13
        #random_mode = True
        #log.debug(f'digits={digits}, prefix={prefix}, suffix={suffix}, ramdom={random}')
        card.reusable = False
        card.dept_code = check.dept_code

        if is_test or (check and check.is_test):
            card.is_test = 1

        # создание с применением случайой генерации номера
        try_number = 0
        last_error_message = ''
        while try_number < TRY_CREATE_COUNT:
            try_number += 1
            number = random.randrange( 10**(digits-1), 10**(digits)-1) 
            try:
                card.ID = f'{prefix}{number}{suffix}'
                card.marknum = f'{number}'
                if ean13:
                    card.ID = barcode.get_barcode('ean13', card.ID)
                card.create(engine)
                break
            except BaseException as ex:
                log.exception(f'{try_number} : {ex}')
                last_error_message = f'{ex}'
        # Проверка а получилось ли?
        if try_number >= TRY_CREATE_COUNT:
            raise Exception(f'Невозмоно создать карту : Сделано {try_number} попыток : {last_error_message}')

        cardlog = CardLog(card.ID, CardLog.CREATE)
        #log.debug(f'CREATE {cardlog.info}')
        #if user_name:
        #    cardlog.user_name = user_name
        cardlog.check(check)
        cardlog.create(engine)
        #log.debug(f'CREATE {cardlog.info}')
        return card

    def activate(self, postgres, exp_days, discount, points, cash, user_name = None, check = None, operation=CardLog.ACTIVATE):
        self.STATE = Card.ACTIVE
        cardlog = CardLog(self.ID, operation)
        cardlog.STATE = Card.ACTIVE
        cardlog.check(check)
        if user_name:
            cardlog.user_name = user_name
        self.discount = discount
        cardlog.discount = self.discount
        self.points = points
        cardlog.points = self.points
        self.cash = cash
        cardlog.cash = self.cash
        #self.reusable = card_type.reusable

        if check:
            self.activation_date = check.date
            self.dept_code = check.dept_code
        else:
            self.activation_date = datetime.datetime.now()

        # срок действия
        #exp_days = card_type.exp_days
        if exp_days is not None:
            current_date = arrow.get()
            self.exp_date = current_date.shift(days = exp_days).date()
            #log.debug(f'exp_date={self.exp_date}, exp_days={card_type.exp_days}, current_date = {current_date}' )
        # -------------
        postgres.add(cardlog)
        #log.debug(f'ACTIVATE {cardlog.info}')
        #self.update(engine)

    def активировать(self, engine, card_type, user_name = None, check = None, operation=CardLog.ACTIVATE):
        self.STATE = Card.ACTIVE
        cardlog = CardLog(self.ID, operation)
        cardlog.STATE = Card.ACTIVE
        cardlog.check(check)
        if user_name:
            cardlog.user_name = user_name
        self.discount = card_type.discount
        cardlog.discount = self.discount
        self.points = card_type.points
        cardlog.points = self.points
        self.cash = card_type.cash
        cardlog.cash = self.cash

        self.reusable = card_type.reusable

        if check:
            self.activation_date = check.date
            self.dept_code = check.dept_code
        else:
            self.activation_date = datetime.datetime.now()

        # срок действия
        exp_days = card_type.exp_days
        if exp_days is not None:
            current_date = arrow.get()
            self.exp_date = current_date.shift(days = exp_days).date()
            #log.debug(f'exp_date={self.exp_date}, exp_days={card_type.exp_days}, current_date = {current_date}' )
        # -------------
        cardlog.create(engine)
        #log.debug(f'ACTIVATE {cardlog.info}')
        self.update(engine)

    def оплатить(self, engine, total, check):
        # списание денежных средств
        if not self.cash or self.cash < 0 or self.STATE != Card.ACTIVE:
            return
        if self.cash < total:
            total = self.cash

        if self.reusable:
            self.cash -= total
            cardlog = CardLog(self.ID, CardLog.ОПЛАТА)
            cardlog.check(check)
            cardlog.cash = -1 * total
            if self.cash <= 0: # все использовано
                self.cash = 0
                self.STATE = Card.DISABLED
                cardlog.STATE = Card.DISABLED
                self.set_deactivation_date()
            cardlog.create(engine)
        else:
            self.cash -= total
            if self.cash > 0: # что то еще осталось
                cardlog = CardLog(self.ID, CardLog.ОПЛАТА)
                cardlog.check(check)
                cardlog.cash = -1 * total
                cardlog.create(engine)
                # списываем с подразделения продавшего карту
                cardlog = CardLog(self.ID, CardLog.СПИСАНИЕ)
                cardlog.check(check)
                cardlog.dept_code = self.dept_code
                cardlog.cash = -1 * self.cash
                self.cash = 0
                self.STATE = Card.DISABLED
                self.set_deactivation_date()
                cardlog.STATE = Card.DISABLED
                cardlog.create(engine)
            else:
                cardlog = CardLog(self.ID, CardLog.ОПЛАТА)
                cardlog.check(check)
                cardlog.cash = -1 * total
                cardlog.STATE = Card.DISABLED
                self.cash = 0
                self.STATE = Card.DISABLED
                self.set_deactivation_date()
                cardlog.create(engine)
        self.update(engine)

    def разблокировать(self, engine, user_name = None):
        self.STATE = Card.ACTIVE
        cardlog = CardLog(self.ID, CardLog.ENABLE)
        self.activation_date = datetime.datetime.now()
        cardlog.STATE = Card.ACTIVE
        if user_name is not None:
            cardlog.usert_name = user_name
        cardlog.create(engine)
        self.update(engine)

    def заблокировать(self, engine, user_name = None):
        self.STATE = Card.DISABLED
        self.set_deactivation_date()
        cardlog = CardLog(self.ID, CardLog.DISABLE)
        cardlog.STATE = Card.DISABLED
        cardlog.user_name = user_name
        cardlog.create(engine)
        self.update(engine)

    def погасить_купон(self, engine, check = None, points = None):
        self.STATE = Card.DISABLED
        self.set_deactivation_date()
        cardlog = CardLog(self.ID, CardLog.ПОГАШЕНИЕ)
        cardlog.STATE = Card.DISABLED
        cardlog.check(check)
        if points:
            cardlog.points = -1 * points
            self.points -= points
        cardlog.create(engine)
        self.update(engine)

    def установить_параметры(self, engine, points, discount, user_name):
        if points:
            self.points = points
        if discount:
            self.discount = discount
        cardlog = CardLog(self.ID, CardLog.CHANGE_PARAM)
        if points:
            cardlog.points = points
        if discount:
            cardlog.discount = discount

        cardlog.user_name = user_name 
        cardlog.create(engine)
        self.update(engine)

    def начислить_баллы(self, engine, points, check = None, user_name = None):
        if self.points is None:
            self.points = 0
        if self.points:
            self.points = self.points + points
        else:
            self.points = points
        cardlog = CardLog(self.ID, CardLog.НАЧИСЛЕНИЕ_БАЛЛОВ)
        cardlog.check(check)
        cardlog.points = points
        if user_name:
            cardlog.user_name = user_name 
        cardlog.create(engine)
        self.update(engine)

    def списать_баллы(self, engine, points, check = None, оператор = None):
        # если нет никаких накопленных баллов и списывать нечего
        if not self.points or self.points <= 0:
            return
        # если недостаточно баллов - уменбшаем до возможного
        if self.points < points:
            points = self.points
        # ---------------------------
        cardlog = CardLog(self.ID, CardLog.СПИСАНИЕ_БАЛЛОВ)
        self.points -= points
        cardlog.points = -1 * points
        cardlog.check(check)
        if оператор is not None:
            cardlog.user_name = оператор 
        cardlog.create(engine)
        self.update(engine)

    def изменить_скидку(self, engine, discount, check = None, оператор = None):
        #log.debug(f'изменить_скидку(self, engine, {discount}, {check}):')
        # если процент не задан, то ничего не делаем
        if not discount: return False
        # если новй процент меньше старого, ничего не делаем
        if self.discount and self.discount > discount: return False
        # ---------------------------
        cardlog = CardLog(self.ID, CardLog.ИЗМЕНЕНИЕ_СКИДКИ)
        self.discount = discount
        cardlog.discount = discount
        cardlog.check(check)
        if оператор is not None:
            cardlog.user_name = оператор 
        cardlog.create(engine)
        self.update(engine)
        return True

    @staticmethod
    def count(engine, where_clause, params = []):
        #return Card.ora_count(engine, where_clause, params)
        return Card.pg_count(engine, where_clause, params)

    @staticmethod
    def ora_count(engine, where_clause, params = []):
        курсор = engine.cursor
        курсор.execute(f'select count(*) from {CARDS} where {where_clause}', params)
        return курсор.fetchone()[0]
    
    @staticmethod
    def pg_count(engine, where_clause, params = []):
        курсор = engine.pg_cursor
        курсор.execute(f'select count(*) from DISCOUNT_CARD where {where_clause}', params)
        return курсор.fetchone()[0]

    def create(self, engine, modify_date = datetime.datetime.now()):
        #self.ora_create(engine, modify_date)
        self.pg_create(engine, modify_date)

    def ora_create(self, engine, modify_date = datetime.datetime.now()):
        cur = engine.cursor

        self.modify_date = modify_date
        self.info[Card.CREATE_DATE] = f'{datetime.datetime.now()}'
        sql = f'''
        insert into {CARDS} 
        (ID, PID, CLASS, TYPE, STATE, 
        PHONE, MARKNUM, 
        DEPT_CODE, ACTIVATE_DATE, CASH, 
        MODIFY_DATE, EXP_DATE, DAY, 
        NAME1, NAME, NAME2, 
        INFO, 
        DISCOUNT, IS_TEST,
        EMAIL, PHONE_VERIFIED, EMAIL_VERIFIED,
        POINTS, REUSABLE)
        values (:0, :1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, 
            :14, :15, :16, :17, :18, :19, :20, :21, :22, :23)
        '''
        INFO = json.dumps(self.info)
        params = [
        self.ID, self.PID, self.CLASS, self.TYPE, self.STATE, 
        self.phone, self.marknum,
        self.dept_code, self.activation_date, self.cash,
        self.modify_date, self.exp_date, self.день_рождения,
        self.фамилия, self.имя, self.отчество,
        INFO, 
        self.discount, self.is_test,
        self.email, self.phone_verified, self.email_verified,
        self.points, self.reusable
        ]
        cur.execute(sql, params)

    def pg_create(self, engine, modify_date = datetime.datetime.now()):
        cur = engine.pg_cursor
        self.modify_date = modify_date
        #self.info[Card.CREATE_DATE] = f'{datetime.datetime.now()}'
        sql = f'''
        insert into DISCOUNT_CARD (
            ID, PID, CLASS, TYPE, STATE,
            MODIFY_DATE, EXP_DATE, ACTIVATE_DATE, DEACTIVATE_DATE,
            MARKNUM,
            DEPT_CODE,
            CASH, POINTS, DISCOUNT, 
            PHONE, PHONE_VERIFIED, EMAIL, EMAIL_VARIFIED,
            DAY, NAME, NAME1, NAME2, 
            IS_TEST, REUSABLE,
            TOTAL, CHECKS,
            INFO
        )
        values ( %s , %s, %s , %s, %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        '''
        INFO = json.dumps(self.info)
        params = [
        self.ID, self.PID, self.CLASS, self.TYPE, self.STATE, 
        self.modify_date, self.exp_date, self.activation_date, self.deactivation_date,
        self.marknum,
        self.dept_code,
        self.cash, self.points, self.discount,
        self.phone, bool(self.phone_verified) if self.phone_verified else None , self.email, bool(self.email_verified) if self.email_verified else None,
        self.день_рождения, self.фамилия, self.имя, self.отчество,
        bool(self.is_test) if self.is_test else None, bool(self.reusable) if self.reusable else None, 
        self.total, self.checks,
        INFO
        ]
        #log.debug(self.ID)
        #log.debug(f'pg_create sql : {sql}, params={params}')
        cur.execute(sql, params)
    
    def update(self, engine, modify_date = datetime.datetime.now()):
        #self.ora_update(engine, modify_date)
        self.pg_update(engine, modify_date)
    
    def ora_update(self, engine, modify_date = datetime.datetime.now()):
        cur = engine.cursor
        self.modify_date = modify_date

        INFO = json.dumps(self.info)
        params = [self.PID, self.CLASS, self.TYPE, self.STATE, 
        self.phone, self.marknum,
        self.dept_code, self.activation_date, self.cash,
        self.modify_date, self.exp_date, 
        self.день_рождения, 
        self.фамилия, self.имя, self.отчество,
        INFO, 
        self.discount,
        self.email, self.phone_verified, self.email_verified,
        self.points, self.reusable,
        self.ID]

        sql = f''' update {CARDS} 
        set PID=:0, CLASS=:1, TYPE=:2, STATE=:3, 
        PHONE=:4, MARKNUM = :5, 
        DEPT_CODE = :6, ACTIVATE_DATE = :7 , CASH = :8, 
        MODIFY_DATE =:9, EXP_DATE = :10, 
        DAY = :11,
        NAME1 = :12, NAME=:13, NAME2=:14,
        INFO=:15,
        DISCOUNT =:16, 
        EMAIL = :17, PHONE_VERIFIED = :18, EMAIL_VERIFIED = :19,
        POINTS = :20, REUSABLE = :21
        where ID = :22
        '''
        #log.debug(f'{sql}, {params}')
        cur.execute(sql, params)

    def pg_update(self, engine, modify_date = datetime.datetime.now()):
        cur = engine.pg_cursor
        self.modify_date = modify_date
        INFO = json.dumps(self.info)
        params = [
        self.PID, self.CLASS, self.TYPE, self.STATE, 
        self.modify_date, self.exp_date, self.activation_date, self.deactivation_date,
        self.marknum,
        self.dept_code,
        self.cash, self.points, self.discount,
        self.phone, bool(self.phone_verified) if self.phone_verified else None , self.email, bool(self.email_verified) if self.email_verified else None,
        self.день_рождения, self.фамилия, self.имя, self.отчество,
        bool(self.is_test) if self.is_test else None, bool(self.reusable) if self.reusable else None,
        self.total, self.checks,
        INFO,
        self.ID
        ]
        sql = f''' update DISCOUNT_CARD set 
            PID=%s, CLASS=%s, TYPE=%s, STATE=%s,
            MODIFY_DATE=%s, EXP_DATE=%s, ACTIVATE_DATE=%s, DEACTIVATE_DATE=%s,
            MARKNUM=%s,
            DEPT_CODE=%s,
            CASH=%s, POINTS=%s, DISCOUNT=%s, 
            PHONE=%s, PHONE_VERIFIED=%s, EMAIL=%s, EMAIL_VARIFIED=%s,
            DAY=%s, NAME=%s, NAME1=%s, NAME2=%s, 
            IS_TEST=%s, REUSABLE=%s,
            TOTAL = %s, CHECKS = %s,
            INFO = %s
            where ID = %s
        '''
        #log.debug(f'{sql}, {params}')
        cur.execute(sql, params)
    
    __FIELDS__= \
        'ID,PID,CLASS,TYPE,STATE,MODIFY_DATE,EXP_DATE,ACTIVATE_DATE,DEACTIVATE_DATE,MARKNUM,DEPT_CODE, CASH, POINTS, DISCOUNT,'\
        'PHONE, PHONE_VERIFIED, EMAIL, EMAIL_VARIFIED, DAY, NAME, NAME1, NAME2,'\
        'IS_TEST, REUSABLE, TOTAL, CHECKS, INFO'
    @staticmethod
    def __LOAD__(r):
        if r is None:
            return None
        c = Card()
        c.ID,c.PID,c.CLASS, c.TYPE, c.STATE, \
        c.modify_date, c.exp_date, c.activation_date, c.deactivation_date, \
        c.marknum, c.dept_code, \
        c.cash, c.points, c.discount,\
        c.phone, c.phone_verified, c.email, c.email_verified, \
        c.день_рождения, c.фамилия, c.имя, c.отчество,\
        c.is_test, c.reusable, c.total, c.checks, INFO = r
        c.info = INFO
        #c.info = json.loads(INFO) if INFO else {}
        return c
            
    def _from_record(self, r):
        self.ID = r[0]
        self.PID = r[1]
        self.CLASS = r[2]
        self.TYPE = r[3]
        self.STATE = r[4]
        self.phone = r[5]
        self.marknum = r[6]
        #self.клиент_UID = r[7]
        self.dept_code = r[7]
        self.activation_date = r[8]
        self.cash = r[9]
        self.modify_date = r[10]
        self.exp_date = r[11]
        self.день_рождения = r[12]
        self.фамилия = r[13]
        self.имя = r[14]
        self.отчество = r[15]
        INFO = r[16]
        self.discount = r[17]
        self.is_test = r[18]
        self.email = r[19]
        self.phone_verified = r[20]
        self.email_verified = r[21]
        self.points = r[22]
        #self.reusable = r[24]
        try:
            self.info = json.loads(INFO)
        except:
            self.info = {}
    ПОЛЯ_БД = 'ID, PID, CLASS, TYPE, STATE, PHONE, MARKNUM, DEPT_CODE, ACTIVATE_DATE, CASH, MODIFY_DATE, EXP_DATE, DAY, NAME1, NAME, NAME2, INFO, DISCOUNT, IS_TEST, EMAIL, PHONE_VERIFIED, EMAIL_VERIFIED, POINTS'

    @staticmethod
    def get(engine, card_id):
        if isinstance(engine, Session):
            card = engine.query(Card).get(card_id)
            log.debug(f'{card} = QUERY {card_id}')
            if not card and len(card_id) == 13 and barcodenumber.check_code_ean13(card_id):
                log.debug(f'{card} = QUERY {card_id[:12]}')
                card = engine.query(Card).get(card_id[:12])
            return card
        else:
            cur = engine.pg_cursor
            sql = f'select {Card.__FIELDS__} from {Card.__tablename__} where id=%s'
            cur.execute(sql, [card_id])
            r = cur.fetchone()
            if r is None:
                log.debug(f'НЕТ КАРТЫ {card_id}')
                if len(card_id) == 13 and barcodenumber.check_code_ean13(card_id):
                    cur.execute(sql, [card_id[:12]])
                    r = cur.fetchone()
                    if r is None:
                        log.debug(f'НЕТ КАРТЫ {card_id[:12]}')
                        return None
                else:
                    return None
            return Card.__LOAD__(r)
        #return Card.ora_get(engine, ID)
        #return Card.pg_get(engine, ID)

    #@staticmethod
    #def ora_get(engine, ID):
    #    cur = engine.cursor
    #    cur.execute(f'''select {Card.ПОЛЯ_БД} from {CARDS} where ID=:0''', [ID])
    #    r = cur.fetchone()
    #    if r is None:
    #        return None
    #    c = Card()
    #    c._from_record(r)
    #    return c

    @staticmethod
    def pg_get(engine, ID):
        return Card.pg_findfirst(engine, 'ID=%s', [ID]) 

    @staticmethod
    def findfirst(engine, where_clause, params=[]):
        #return Card.ora_findfirst(engine, where_clause, params)
        return Card.pg_findfirst(engine, where_clause, params)

    #@staticmethod
    #def ora_findfirst(engine, where_clause, params=[]):
    #    cur = engine.cursor
    #    cur.execute(f'''select {Card.ПОЛЯ_БД} from {CARDS} where {where_clause}''', params)
    #    r = cur.fetchone()
    #    if r is None:
    #        return None
    #    c = Card()
    #    c._from_record(r)
    #    return c

    @staticmethod
    def pg_findfirst(engine, where_clause, params=[]):
        cur = engine.pg_cursor
        cur.execute(f'''select {Card.__FIELDS__} from DISCOUNT_CARD where {where_clause}''', params)
        return Card.__LOAD__(cur.fetchone())

    @staticmethod
    def findall(engine, where_clause = None, params=[], filter = None, max_records=None, limit = None):
        if limit:
            max_records = limit
        #return Card.ora_findall(engine, where_clause, params, filter, max_records)
        return Card.pg_findall(engine, where_clause, params, filter, max_records)

    @staticmethod
    def ora_findall(engine, where_clause = None, params=[], filter = None, max_records=None):
        cur = engine.cursor
        cards = []
        if where_clause is not None:
            sql = f'select {Card.ПОЛЯ_БД} from {CARDS} where {where_clause}'
        else:
            sql = f'select {Card.ПОЛЯ_БД} from {CARDS}'
        cur.execute(sql, params)
        for r in cur:
            card = Card()
            card._from_record(r)
            if filter is not None and not filter(card):
                continue
            cards.append(card)
            if max_records is not None and len(cards) >= max_records:
                break
        return cards

    @staticmethod
    def pg_findall(engine, where_clause = None, params=[], filter=None, max_records=None):
        cur = engine.pg_cursor
        cards = []
        if where_clause is not None:
            sql = f'select {Card.__FIELDS__} from DISCOUNT_CARD where {where_clause}'
        else:
            sql = f'select {Card.__FIELDS__} from DISCOUNT_CARD'
        if max_records:
            sql += f' limit {max_records}'
        #log.debug(f'SQL={sql} PARAMS={params}')
        cur.execute(sql, params)
        for r in cur:
            #log.debug(f'{r}')
            card = Card.__LOAD__(r)
            #if filter is not None and not filter(card):
            #    continue
            cards.append(card)
            #if max_records is not None and len(cards) >= max_records:
            #    break
        return cards

    @staticmethod
    def delete(engine, where_clause, params = []):
        #Card.ora_delete(engine, where_clause, params)
        Card.pg_delete(engine, where_clause, params)

    @staticmethod
    def ora_delete(engine, where_clause, params = []):
        cur = engine.cursor
        cur.execute(f'delete from {CARDS} where {where_clause}', params)
    
    @staticmethod
    def pg_delete(engine, where_clause, params = []):
        cur = engine.pg_cursor
        cur.execute(f'delete from DISCOUNT_CARD where {where_clause}', params)
    
    @staticmethod
    def deleteall(engine, where_clause, params = []):
        Card.pg_deleteall(engine, where_clause, params)

    @staticmethod
    def ora_deleteall(engine, where_clause, params = []):
        cur = engine.cursor
        cur.execute(f'delete from {CARDS} where {where_clause}', params)

    @staticmethod
    def pg_deleteall(engine, where_clause, params = []):
        cur = engine.pg_cursor
        cur.execute(f'delete from DISCOUNT_CARD where {where_clause}', params)
    

