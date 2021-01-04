import json, datetime, cx_Oracle, random, arrow, re
import barcodenumber, barcode

from domino.core import log
from enum import IntEnum
#from discount.core import CARDS, CARDS_LOG, Engine

from domino.databases.postgres import Postgres
from domino.tables.postgres.discount_cardlog import DiscountCardLog
#from discount.series import ТипКарты

#from settings import PostgresTable
from sqlalchemy import Column, String, Integer, BigInteger, SmallInteger, DateTime, Date, JSON, DECIMAL, Float, Boolean
from sqlalchemy import func as F, text as T
from sqlalchemy.types import TypeDecorator
from sqlalchemy.ext.mutable import MutableDict

TRY_CREATE_COUNT = 10
CARD_STATE_NAME = ['Только содан(а)', 'В работе', 'Погашен(а)']

def on_activate(account_id, on_activate_log):
    on_activate_log(f'Устаревший вызов DiscountCard.on_activate()')
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

    table.migrate(account_id, on_activate_log)

    table = Postgres.Table('DISCOUNT_CARD_NUMERATOR')
    table.column('CLASS','SMALLINT DEFAULT 0 NOT NULL')
    table.column('TYPE','SMALLINT DEFAULT 0 NOT NULL')
    table.column('NUMBER','BIGINT DEFAULT 0 NOT NULL')
    table.migrate(account_id, on_activate_log)

class DiscountCardState(IntEnum):
    CREATED = 0 # Только создана, но еще не в работе
    #ТОЛЬКО_СОЗДАННАЯ_КАРТА = 0 # Только создана, но еще не в работе
    ACTIVE = 1 # Активная, действующая карта
    #АКТИВНАЯ_КАРТА = 1 # Активная, действующая карта
    DISABLED = 2 # Карта заблокирована (Купон погашен)
    #ЗАБЛОКИРОВАННАЯ_КАРТА = 2 # Карта заблокирована (Купон погашен)
    CARD_REF = 3 # Карта является ссылкой на другую карту (используется как альтернативная / дополнительная карта )

    __state_names__ = ['ТОЛЬКО_СОЗДАННАЯ_КАРТА', 'АКТИВНАЯ_КАРТА', 'ЗАБЛОКИРОВАННАЯ_КАРТА', 'КАРТА ССЫЛКА']
    
    @property
    def description(self):
        return DiscountCard.State.__state_names__[self.value] if self.value is not None else None

    def __str__(self):
        return DiscountCard.State.__state_names__[self.value] if self.value else None

class DISCOUNT_CARD_STATE(TypeDecorator):
    impl = SmallInteger
    def process_bind_param(self, value, dialect):
        return value.value if value is not None else None
    def process_result_value(self, value, dialect):
        return DiscountCardState(value) if value is not None else DiscountCardState.CREATED

class DiscountCard(Postgres.Base):

    State = DiscountCardState 

    __tablename__ = 'discount_card'
    __table_args__ = {'extend_existing': True}

    CREATED = 0 # Только создана, но еще не в работе
    ТОЛЬКО_СОЗДАННАЯ_КАРТА = 0 # Только создана, но еще не в работе
    ACTIVE = 1 # Активная, действующая карта
    АКТИВНАЯ_КАРТА = 1 # Активная, действующая карта
    DISABLED = 2 # Карта заблокирована (Купон погашен)
    ЗАБЛОКИРОВАННАЯ_КАРТА = 2 # Карта заблокирована (Купон погашен)
    CARD_REF = 3 # Карта является ссылкой на другую карту (используется как альтернативная / дополнительная карта )

    #REPLACED = 4 # По утеряной карте выдали замену. Данная карта на ходится в архиве

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

    РАССЫЛКА_ПО_СМС = 'SMS'
    РАССЫЛКА_ПО_ПОЧТЕ = 'EM0'
    CLIENT_UID = 'c_UID'
    CARD_UID = 'UID'
    ПОЛ = 'SEX'

    ID              = Column('id', String, primary_key=True)
    pid             = Column(String)
    CLASS           = Column('class', SmallInteger)
    TYPE            = Column('type', SmallInteger, nullable=False)
    ctime           = Column(DateTime, default=F.current_timestamp())
    #type_           = Column('type', DiscountCardTYPE)
    #STATE           = Column('state', SmallInteger, nullable=False)
    state           = Column('state', DISCOUNT_CARD_STATE, nullable=False)
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
    info            = Column('info', Postgres.JSON)

    def __init__(self, ID = None, state = DiscountCardState.CREATED, CLASS = 0, TYPE = 0):
        self.changed = False
        self.ID = ID
        self.pid = None
        #self.client_UID = None
        #self.card_UID = None
        self.state = state
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

    @property
    def id(self):
        return self.ID

    @property
    def STATE(self):
        return self.state.value if self.state is not None else None
    
    @STATE.setter
    def STATE(self, value):
        self.state = DiscountCardState(value) if value is not None else None

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
        return self.info.get(DiscountCard.ВХОДЯЩЕЕ_КОЛИЧЕСТВО_ПОКУПОК)
    @property
    def входящая_сумма_покупок(self):
        return self.info.get(DiscountCard.ВХОДЯЩАЯ_СУММА_ПОКУПОК)
    
    def обновление_входящих_параметров(self, total = None, checks=None, cash=None):
        #log.debug(f'обновление_входящих_параметров({self.ID}, {total}, {checks}, {cash}')
        #log.debug(f'self.total = {self.total} self.checks = {self.checks} self.info={self.info}')
        updated = False
        if total:
            if self.total is None:
                self.total = 0
            i_total = self.info.get(DiscountCard.ВХОДЯЩАЯ_СУММА_ПОКУПОК, 0)
            if i_total != total:
                self.info[DiscountCard.ВХОДЯЩАЯ_СУММА_ПОКУПОК] = total
                self.total += (total - i_total)
                updated = True

        if checks:
            if self.checks is None:
                self.checks = 0
            i_checks = self.info.get(DiscountCard.ВХОДЯЩЕЕ_КОЛИЧЕСТВО_ПОКУПОК, 0)
            if i_checks != checks:
                self.info[DiscountCard.ВХОДЯЩЕЕ_КОЛИЧЕСТВО_ПОКУПОК] = checks
                self.checks += (checks - i_checks)
                updated = True
        
        if cash:
            if self.cash is None:
                self.cash = 0
            i_cash = self.info.get(DiscountCard.ВХОДЯЩИЙ_ОСТАТОК_ДЕНЕЖНЫХ_СРЕДСТВ, 0)
            if i_cash != cash:
                self.info[DiscountCard.ВХОДЯЩИЙ_ОСТАТОК_ДЕНЕЖНЫХ_СРЕДСТВ] = cash
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
        return self.info.get(DiscountCard.CREATE_DATE)

    @property
    def телефон_для_печати(self):
        return DiscountCard.преобразовать_к_печатному_виду(self.phone)
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
        self.phone = DiscountCard.преобразовать_к_нормальному_виду(телефон)
    def изменить_телефон(self, телефон):
        if телефон: 
            телефон = DiscountCard.преобразовать_к_нормальному_виду(телефон)
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
        self.info['SMS'] = int(value) if value else None
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
        return self.STATE == DiscountCard.CREATED
    @property
    def это_активная_карта(self):
        return self.STATE == DiscountCard.ACTIVE
    @property
    def это_заблокированная_карта(self):
        return self.STATE == DiscountCard.DISABLED
    
    @property
    def state_name(self):
        try:
            #return CARD_STATE_NAME[self.STATE]
            return self.state.description
        except:
            return f'Состояние "{self.STATE}"'

    def change_if_base_data(self, CLASS, STATE, marknum, dept_code, activation_date, exp_date, card_UID):
        if self.CLASS != CLASS:
            self.CLASS = CLASS
            #log.debug(f'CLASS {self.CLASS} : {CLASS}')
            self.changed = True
        if self.STATE != STATE:
            self.STATE = STATE
            #log.debug(f'STATE {self.STATE} : {STATE}')
            self.changed = True
        if self.marknum != marknum:
            self.marknum = marknum
            #log.debug(f'marknum {self.marknum} : {marknum}')
            self.changed = True
        if self.dept_code != dept_code:
            self.dept_code = dept_code
            #log.debug(f'dept_code {self.dept_code} : {dept_code}')
            self.changed = True
        if activation_date:
            activation_date = activation_date.date()
        if self.activation_date != activation_date:
            self.activation_date = activation_date
            #log.debug(f'activation_date {self.activation_date} : {activation_date}')
            self.changed = True
        if exp_date:
            exp_date = exp_date.date()
        if self.exp_date != exp_date:
            self.exp_date = exp_date
            #log.debug(f'exp_date {self.exp_date} : {exp_date}')
            self.changed = True
        if self.info.get(DiscountCard.CARD_UID) != card_UID:
            self.info[DiscountCard.CARD_UID] = card_UID
            #log.debug(f'{Card.CARD_UID} {self.info.get(Card.CARD_UID)} : {card_UID}')
            self.changed = True

    def change_of_personal_data(self, фамилия, имя, отчество, день_рождения, пол):
        if self.фамилия != фамилия:
            self.фамилия = фамилия
            self.changed = True
        if self.имя != имя:
            self.имя = имя
            self.changed = True
        if self.отчество != отчество:
            self.отчество = отчество
            self.changed = True
        if день_рождения:
            день_рождения = день_рождения.date()
        if self.день_рождения != день_рождения:
            self.день_рождения = день_рождения
            self.changed = True
        if self.info.get(DiscountCard.ПОЛ) != пол:
            self.info[DiscountCard.ПОЛ] = пол
            self.changed = True
    
    def change_client_UID(self, client_UID):
        if self.info.get(DiscountCard.CLIENT_UID) != client_UID:
            self.info[DiscountCard.CLIENT_UID] = client_UID
            self.chaged = True

    def change_phone(self, src_phone, рассылка_по_смс):
        phone = DiscountCard.преобразовать_к_нормальному_виду(src_phone)
        #log.debug(f'{phone} {src_phone}')
        if self.phone != phone:
            self.phone = phone
            self.changed = True
        if рассылка_по_смс != self.info.get(DiscountCard.РАССЫЛКА_ПО_СМС):
            self.info[DiscountCard.РАССЫЛКА_ПО_СМС] = рассылка_по_смс
    
    def change_email(self, email, рассылка_по_почте):
        if self.email != email:
            self.email = email
            self.chaged = True            
        if self.рассылка_по_почте != рассылка_по_почте:
            self.рассылка_по_почте = рассылка_по_почте
            self.changed = True

    @staticmethod 
    def create_card(postgres, card_type, number = None, user_name = None, check = None, is_test = False):
        prefix = card_type.prefix
        suffix = card_type.suffix
        digits = card_type.digits
        ean13 = card_type.code_format_ean13
        card = DiscountCard(TYPE = card_type.ID, state = DiscountCard.State.CREATED)
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
            postgres.add(card)
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
                    break
                except BaseException as ex:
                    postgres.rollback()
                    log.exception(f'{try_number} : {ex}')
                    last_error_message = f'{ex}'
                    #raise Exception(ex)
            # Проверка а получилось ли?
            if try_number >= TRY_CREATE_COUNT:
                log.error(f'Невозмоно создать карту : Сделано {try_number} попыток : {last_error_message}')
                raise Exception(f'Невозмоно создать карту. Сделано {try_number} попыток.')

        cardlog = DiscountCardLog(card.ID, DiscountCardLog.CREATE)
        cardlog.user_name = user_name
        cardlog.check(check)
        postgres.add(cardlog)
        return card

    def activate(self, postgres, exp_days, discount, points, cash, user_name = None, check = None, operation=DiscountCardLog.ACTIVATE):
        self.STATE = DiscountCard.ACTIVE
        cardlog = DiscountCardLog(self.ID, operation)
        cardlog.STATE = DiscountCard.ACTIVE
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
            log.debug(f'exp_date={self.exp_date}, exp_days={exp_days}, current_date = {current_date}' )
        # -------------
        postgres.add(cardlog)
        #log.debug(f'ACTIVATE {cardlog.info}')
        #self.update(engine)

    def оплатить(self, postgres, total, check):
        # списание денежных средств
        if not self.cash or self.cash < 0 or self.STATE != DiscountCard.ACTIVE:
            return
        if self.cash < total:
            total = self.cash

        if self.reusable:
            self.cash -= total
            cardlog = DiscountCardLog(self.ID, DiscountCardLog.ОПЛАТА)
            cardlog.check(check)
            cardlog.cash = -1 * total
            if self.cash <= 0: # все использовано
                self.cash = 0
                self.STATE = DiscountCard.DISABLED
                cardlog.STATE = DiscountCard.DISABLED
                self.set_deactivation_date()
            postgres.add(cardlog)
        else:
            self.cash -= total
            if self.cash > 0: # что то еще осталось
                cardlog = DiscountCardLog(self.ID, DiscountCardLog.ОПЛАТА)
                cardlog.check(check)
                cardlog.cash = -1 * total
                postgres.add(cardlog)
                # списываем с подразделения продавшего карту
                cardlog = DiscountCardLog(self.ID, DiscountCardLog.СПИСАНИЕ)
                cardlog.check(check)
                cardlog.dept_code = self.dept_code
                cardlog.cash = -1 * self.cash
                self.cash = 0
                self.STATE = DiscountCard.DISABLED
                self.set_deactivation_date()
                cardlog.STATE = DiscountCard.DISABLED
                postgres.add(cardlog)
            else:
                cardlog = DiscountCardLog(self.ID, DiscountCardLog.ОПЛАТА)
                cardlog.check(check)
                cardlog.cash = -1 * total
                cardlog.STATE = DiscountCard.DISABLED
                self.cash = 0
                self.STATE = DiscountCard.DISABLED
                self.set_deactivation_date()
                postgres.add(cardlog)

    def разблокировать(self, postgres, user_name = None):
        self.STATE = DiscountCard.ACTIVE
        cardlog = DiscountCardLog(self.ID, DiscountCardLog.ENABLE)
        self.activation_date = datetime.datetime.now()
        cardlog.STATE = DiscountCard.ACTIVE
        if user_name is not None:
            cardlog.usert_name = user_name
        postgres.add(cardlog)

    def заблокировать(self, postgres, user_name = None):
        self.STATE = DiscountCard.DISABLED
        self.set_deactivation_date()
        cardlog = DiscountCardLog(self.ID, DiscountCardLog.DISABLE)
        cardlog.STATE = DiscountCard.DISABLED
        cardlog.user_name = user_name
        postgres.add(cardlog)

    def погасить_купон(self, postgres, check = None, points = None):
        self.STATE = DiscountCard.DISABLED
        self.set_deactivation_date()
        cardlog = DiscountCardLog(self.ID, DiscountCardLog.ПОГАШЕНИЕ)
        cardlog.STATE = DiscountCard.DISABLED
        cardlog.check(check)
        if points:
            cardlog.points = -1 * points
            self.points -= points
        postgres.add(cardlog)

    def установить_параметры(self, postgres, points, discount, user_name):
        if points:
            self.points = points
        if discount:
            self.discount = discount
        cardlog = DiscountCardLog(self.ID, DiscountCardLog.CHANGE_PARAM)
        if points:
            cardlog.points = points
        if discount:
            cardlog.discount = discount

        cardlog.user_name = user_name 
        postgres.add(cardlog)

    def начислить_баллы(self, postgres, points, check = None, user_name = None):
        if self.points is None:
            self.points = 0
        if self.points:
            self.points = self.points + points
        else:
            self.points = points
        cardlog = DiscountCardLog(self.ID, DiscountCardLog.НАЧИСЛЕНИЕ_БАЛЛОВ)
        cardlog.check(check)
        cardlog.points = points
        if user_name:
            cardlog.user_name = user_name 
        postgres.add(cardlog)

    def списать_баллы(self, postgres, points, check = None, оператор = None):
        # если нет никаких накопленных баллов и списывать нечего
        if not self.points or self.points <= 0:
            return
        # если недостаточно баллов - уменбшаем до возможного
        if self.points < points:
            points = self.points
         # ---------------------------
        cardlog = DiscountCardLog(self.ID, DiscountCardLog.СПИСАНИЕ_БАЛЛОВ)
        self.points -= points
        cardlog.points = -1 * points
        cardlog.check(check)
        if оператор is not None:
            cardlog.user_name = оператор 
        postgres.add(cardlog)

    def изменить_скидку(self, postgres, discount, check = None, оператор = None):
        #log.debug(f'изменить_скидку(self, engine, {discount}, {check}):')
        # если процент не задан, то ничего не делаем
        if not discount: return False
        # если новй процент меньше старого, ничего не делаем
        if self.discount and self.discount > discount: return False
        # ---------------------------
        cardlog = DiscountCardLog(self.ID, DiscountCardLog.ИЗМЕНЕНИЕ_СКИДКИ)
        self.discount = discount
        cardlog.discount = discount
        cardlog.check(check)
        if оператор is not None:
            cardlog.user_name = оператор 
        postgres.add(cardlog)
        return True

    @staticmethod
    def find(postgres, card_id):
        card = postgres.query(DiscountCard).get(card_id)
        if not card and len(card_id) == 13 and barcodenumber.check_code_ean13(card_id):
            card = postgres.query(DiscountCard).get(card_id[:12])
        if card and card.TYPE == 0 and card.state == DiscountCard.State.CARD_REF:
            card = postgres.query(DiscountCard).get(card.pid)
        return card

DiscountCardTable = DiscountCard.__table__
table = Postgres.Table(DiscountCardTable)
table.column('class','smallint default 0 not null')
table.column('type','smallint default 0 not null')
table.column('state','smallint default 0 not null')
table.column('ctime','timestamp default current_timestamp')
