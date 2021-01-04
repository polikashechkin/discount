import json, sqlite3, arrow, re
from enum import Enum
from discount.core import DISCOUNT_DB
from domino.core import log

class CardType:
    expiration_NONE = 'NO'
    expiration_YEAR = 'YEAR'
    expiration_DAYS = 'DAYS'
    expiration_DATE = 'DATE'

    activation_mode_SALE = 'sale'
    activation_mode_CREATE = 'create'

    namedPHONE = '2'

    gen_mode_RANDOM = 'random'
    gen_mode_SEQUENCE = 'sequence'
    
    EXPIRATION = 'expiration'
    EXPIRATION_DATE = 'expiration_date'
    EXPIRATION_DAYS = 'expiration_days' # Количество дней строка действия
    EXP_DAYS = 'expiration_days' # Количество дней строка действия
    CODE_FORMAT = 'code_format' 
    code_format_DEFAULT = '' 
    code_format_EAN13 = 'ean13' 
    SUFFIX = 'suffix' 
    PREFIX = 'prefix'
    DESCRIPTION = 'description'
    DIGITS = 'digits'
    NAMED = 'named'
    ACCUMULATIVE = 'accumulative'
    ACTIVATION_MODE = 'activation_mode'
    CASH = 'cash'
    POINTS = 'points' # начальное количество баллоы
    PRICE = 'price'
    REUSABLE = 'reusable'
    FALSE= '0'
    TRUE = '1'
    GEN_MODE = 'gen_mode'
    PERCENT = 'percent' # Процент скидка (ставка) утановленная для карты
    TODAY_COUNT = 'today_count' # Максимальное количество обращений допустимых в один день
    NEXT_NUMBER = 'next_number'
 
    def __init__(self, ID = None):
        self.id = int(ID) if ID is not None else None
        self.prefix = None
        self.type = None
        self.status = None
        self._start = None
        self._end = None
        self.info = {}
    
    
    @property
    def code_format(self):
        return self.info.get(CardType.CODE_FORMAT, CardType.code_format_DEFAULT)
    @property
    def code_format_ean13(self):
        return self.code_format == CardType.code_format_EAN13
    @code_format.setter
    def code_format(self, value):
        self.info[CardType.CODE_FORMAT] = value
        if value == CardType.code_format_EAN13:
            self.suffix = ''
            self.prefix = re.sub('[^0-9]', '', self.prefix)[:9] if self.prefix else f'{self.id:04}'
            self.digits = 12 - len(self.prefix)

    @property
    def reusable(self):
        reusable = self.info.get('reusable')
        return 1 if reusable else None
    @reusable.setter
    def reusable(self, value):
        if value and value == '1':
            self.info['reusable'] = 1
        else:
            try:
                del self.info['reusable']
            except:
                pass
    @property
    def ID(self):
        return self.id

    @property
    def next_number(self):
        return self.__get_int(Series.NEXT_NUMBER, 1)
    @next_number.setter
    def next_number(self, value):
        self.__set_int(Series.NEXT_NUMBER, value)

    @property
    def следующий_номер(self):
        return self.info.get(Series.NEXT_NUMBER, 1)
    @следующий_номер.setter
    def следующий_номер(self, value):
        self.info[Series.NEXT_NUMBER] = value

    @property
    def начальная_процентная_скидка(self):
        return self.discount

    def __get_float(self, name):
        value = self.info.get(name)
        return float(value) if value else None
    def __set_float(self, name, value):
        if value and value.strip():
            self.info[name] = float(value)
        else:
            try:
                del self.info[name]
            except:
                pass
    def __get_int(self, name, default = None):
        value = self.info.get(name)
        return int(value) if value else default
    def __set_int(self, name, value):
        if isinstance(value, (int, float)):
            self.info[name] = int(value)
        elif value and value.strip():
            self.info[name] = int(value)
        else:
            try:
                del self.info[name]
            except:
                pass

    @property
    def discount(self):
        return self.__get_float(Series.PERCENT)
    @discount.setter
    def discount(self, value):
        self.__set_float(Series.PERCENT, value)

    @property
    def начальнаое_количество_баллов(self):
        return self.points
    
    @property
    def points(self):
        return self.__get_float('points')
    @points.setter
    def points(self, value):
        self.__set_float('points', value)

    @property
    def номинал(self):
        return self.cash

    @property
    def cash(self):
        return self.__get_float(Series.CASH)
    @cash.setter
    def cash(self, value):
        self.__set_float(Series.CASH, value)
    @property
    def price(self):
        return self.__get_float(Series.PRICE)
    @price.setter
    def price(self, value):
        self.__set_float(Series.PRICE, value)

    def __str__(self):
        return f'Series({self.ID})'

    @property
    def percent(self):
        return self.discount

    @property
    def today_count(self):
        return self.__get_int(Series.TODAY_COUNT)
    @today_count.setter
    def today_count(self, value):
        self.__set_int(Series.TODAY_COUNT, value)

    @property
    def suffix(self):
        return self.info.get(Series.SUFFIX, '')
    @suffix.setter
    def suffix(self, value):
        self.info[Series.SUFFIX] = value.strip()


    @property
    def gen_mode_random(self):
        #if not self.это_купон:
        #    return False
        return self.info.get(Series.GEN_MODE, '') == Series.gen_mode_RANDOM

    @property
    def activation_mode(self):
        return self.info.get(Series.ACTIVATION_MODE, Series.activation_mode_CREATE)

    @property
    def named(self):
        return self.info.get(Series.NAMED, Series.FALSE) == Series.TRUE

    @property
    def accumulative(self):
        return self.info.get(Series.ACCUMULATIVE, Series.FALSE) == Series.TRUE

    @property
    def exp_days(self):
        return self.__get_int(Series.EXP_DAYS)
    @exp_days.setter
    def exp_days(self, value):
        self.__set_int(Series.EXP_DAYS, value)

    @property
    def digits(self):
        return self.__get_int(Series.DIGITS, 0)
    @digits.setter
    def digits(self, value):
        self.__set_int(Series.DIGITS, value)
    
    def CLASS_ID(self, application):
        if self.type == 'C01':
            return 1
        elif self.type == 'C02':
            return 2
        elif self.type == 'C03':
            return 3
        elif self.type == 'C04':
            return 4
        else:
            return 0

    def CLASS(self, application):
        return application['card_types'][self.type]

    def full_name(self, CLASSES):
        CLASS = CLASSES[self.type]
        return f'{CLASS.description()} {self.description}'

    @property
    def это_купон(self):
        return self.type == 'C01'
    @property
    def это_персональная_карта(self):
        return self.type == 'C04'
    @property
    def это_подарочная_карта(self):
        return self.type == 'C03'
    @property
    def это_дисконтная_карта(self):
        return self.type == 'C02'
    @property
    def наименование(self):
        return self.description if self.description is not None else ''
    @property
    def полное_наименование(self):
        if self.description and self.description.strip():
            return self.description
        else:
            return self.type_name
    @property
    def type_name(self):
        if self.type == 'C01':
            return 'Купон'
        elif self.type == 'C02':
            return 'Дисконтная карта'
        elif self.type == 'C03':
            return 'Подарочная карта'
        elif self.type == 'C04':
            return 'Персональная карта'
        else:
            return f'<{self.type}>'
    @property
    def start(self):
        return self._start
    @start.setter
    def start(self, value):
        try:
            self._start = arrow.get(value).date()
        except:
            self._start = None
    @property
    def end(self):
        return self._end
    @end.setter
    def end(self, value):
        try:
            self._end = arrow.get(value).date()
        except:
            self._end = None
    @property
    def description(self):
        return self.info.get(Series.DESCRIPTION, '')
    @description.setter
    def description(self, value):
        self.info[Series.DESCRIPTION] = value

    @property
    def info_dump(self):
        return json.dumps(self.info)
    @info_dump.setter
    def info_dump(self, value):
        try:
            self.info = json.loads(value)
        except:
            pass

    def __getitem__(self, key):
        return self.info.get(str(key))
    def __setitem__(self, key, value):
        self.info[str(key)] = value

    @staticmethod
    def get(cur, ID):
        return Series.find(cur, 'id=?', [int(ID)])

    @staticmethod
    def find(cur, where_clause, params):
        S = Series()
        q = f'select id, status, prefix, type, info, start, end from emission where {where_clause}'
        cur.execute(q,params)
        r = cur.fetchone()
        if r is None:
            return None
        else:
            S.id, S.status, S.prefix, S.type, S.info_dump, S.start, S.end = r
            return S

    def create(self, cur):
        cur.execute('insert into emission (type, prefix, info, start, end) values(?,?,?,?,?)',
            [self.type, self.prefix, self.info_dump, self.start, self.end])
        self.id = cur.lastrowid

    @staticmethod
    def findall(cur, where_claue = None, params = []):
        series = []
        if where_claue is not None:
            cur.execute(f'select ID, status, prefix, type, info, start, end from emission where {where_claue}', params)
        else:
            cur.execute(f'select ID, status, prefix, type, info , start, end from emission')
        for ID, status, prefix, type, info_dump, start, end in cur:
            s = Series(ID)
            s.status = status
            s.prefix = prefix
            s.type = type
            s.info_dump = info_dump
            s.start = start
            s.end = end

            series.append(s)
        return series

    def update(self, cur):
        cur.execute('''
        update emission set status=?, info=?, prefix=?, start=?, end=? where rowid=?
        ''', [self.status, self.info_dump, self.prefix, self.start, self.end, self.id])

ТипКарты = CardType    
Series = CardType

