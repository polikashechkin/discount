import json, datetime, cx_Oracle, random, arrow, re
from domino.core import log
from discount.core import CARDS, CARDS_LOG

CLIENT = 'DB1_AGENT'

class Клиент:
    
    def __init__(self, ID = None):
        self.ID = ID
        self.CLASS = 0
        self.TYPE = 1
        self.фамилия = None
        self.имя = None
        self.отчество = None
        self.день_рождения = None
        self.рассылка_по_СМС = None
        self.рассылка_по_почте = None
        self.пол = None
        self.телефон = None
        self.почта = None
    
    @staticmethod
    def преобразовать_к_печатному_виду(телефон):
        if телефон is None:
            return ''
        телефон = str(телефон)
        return f'+{телефон[0]} ({телефон[1:4]}) {телефон[4:7]}-{телефон[7:]}'

    @property
    def телефон_для_печати(self):
        return Клиент.преобразовать_к_печатному_виду(self.телефон)

    @property
    def телефон_для_ввода(self):
        if self.телефон is None:
            return ''
        else:
            a = str(self.телефон)
            return f'{a[1:4]} {a[4:7]} {a[7:]}'

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
        self.телефон = Клиент.преобразовать_к_нормальному_виду(телефон)

    def изменить_телефон(self, телефон):
        телефон = Клиент.преобразовать_к_нормальному_виду(телефон)
        if телефон != self.телефон:
            self.телефон = телефон
            return True
        else:
            return False

    @property
    def ФИО(self):
        фио = []
        if self.фамилия is not None:
            фио.append(self.фамилия)
        if self.имя is not None:
            фио.append(self.имя)
        if self.отчество is not None:
            фио.append(self.отчество)
        return ' '.join(фио).strip()

    @staticmethod
    def count(курсор, where_clause, params = []):
        курсор.execute(f'select count(*) from {CLIENT} where {where_clause}', params)
        return курсор.fetchone()[0]

    def create(self, cur):
        sql = f'''
        insert into {CLIENT} 
        (ID, PID, CLASS, TYPE, STATE, 
        PHONE, MARKNUM, PARTNER, 
        DEPT_CODE, ACTIVATE_DATE, CASH, 
        MODIFY_DATE, EXP_DATE, DAY, 
        NAME1, NAME, NAME2, 
        INFO, DISCOUNT, IS_TEST)
        values (:0, :1, :2, :3, :4, :6, :6, :7, :8, :9, :10, :11, :12, :13, 
            :14, :15, :16, :17, :18, :19)
        '''
        params = [
        self.ID, self.CLASS, self.TYPE, 
        self.фамилия, self.имя, self.отчество, self.пол, self.день_рождения,
        self.телефон, self.почта,
        self.рассылка_по_СМС, self.рассылка_по_почте,
        ]
        cur.execute(sql, params)

    def update(self, cur, дата_последнего_изменения = datetime.datetime.now()):
        self.дата_последнего_изменения = дата_последнего_изменения
        #if self._card_stat is not None:
        #    self._card_stat.save(self)
        if self.телефон is not None:
            if not isinstance(self.телефон, int):
                try:
                    self.телефон = int(self.телефон)
                except:
                    self.телефон = None

        params = [self.PID, self.CLASS, self.TYPE, self.STATE, 
        self.телефон, self.маркировочный_номер, self.клиент_UID,
        self.код_подразделения, self.дата_активации, self.остаток_денежных_средств,
        self.дата_последнего_изменения, self.дата_окончания_действия, 
        self.день_рождения, 
        self.фамилия, self.имя, self.отчество,
        self.info_dump, 
        self.процент_скидки,
        self.ID]

        sql = f''' update {CARDS} 
        set PID=:0, CLASS=:1, TYPE=:2, STATE=:3, 
        PHONE=:4, MARKNUM = :5, PARTNER=:6, 
        DEPT_CODE = :7, ACTIVATE_DATE = :8 , CASH = :9, 
        MODIFY_DATE =:10, EXP_DATE = :11, 
        DAY = :12,
        NAME1 = :13, NAME=:14, NAME2=:15,
        INFO=:16,
        DISCOUNT =:17
        where ID = :18
        '''
        #log.debug(f'{params}')
        #log.debug(f'{sql}')
        cur.execute(sql, params)

    def get_attrib(self, name, default=None):
        return self.info.get(name, default)

    def _from_record(self, r):
        self.ID = r[0]
        self.PID = r[1]
        self.CLASS = r[2]
        self.TYPE = r[3]
        self.STATE = r[4]
        self.телефон = r[5]
        self.маркировочный_номер = r[6]
        self.клиент_UID = r[7]
        self.код_подразделения = r[8]
        self.дата_активации = r[9]
        self.остаток_денежных_средств = r[10]
        self.дата_последнего_изменения = r[11]
        self.дата_окончания_действия = r[12]
        self.день_рождения = r[13]
        self.фамилия = r[14]
        self.имя = r[15]
        self.отчество = r[16]
        self.info_dump = r[17]
        self.процент_скидки = r[18]
        self.is_test = r[19]
    
    ПОЛЯ_БД = 'ID, PID, CLASS, TYPE, STATE, PHONE, MARKNUM, PARTNER, DEPT_CODE, ACTIVATE_DATE, CASH, MODIFY_DATE, EXP_DATE, DAY, NAME1, NAME, NAME2, INFO, NVL(DISCOUNT, 0), IS_TEST'

    @staticmethod
    def get(cur, ID):
        cur.execute(f'''select {Card.ПОЛЯ_БД} from {CARDS} where ID=:0''', [ID])
        r = cur.fetchone()
        #log.debug(f'get({ID}) = {r}')
        if r is None:
            return None
        c = Card()
        c._from_record(r)
        return c

    @staticmethod
    def find_by_num(cur, TYPE, маркировачный_номер):
        маркировачный_номер = маркировачный_номер.strip()
        TYPE = int(TYPE)
        for card in Card.findall(cur, 'TYPE=:0', [TYPE]):
            if card.маркировочный_номер == маркировачный_номер:
                return card

    @staticmethod
    def findall(cur, where_clause = None, params=[], filter = None, max_records=None):
        #log.debug(f'findall({cur}, {where_clause}, {params}')
        cards = []
        if where_clause is not None:
            sql = f'select {Card.ПОЛЯ_БД} from {CARDS} where {where_clause}'
        else:
            sql = f'select {Card.ПОЛЯ_БД} from {CARDS}'
        #log.debug(f'{sql} {params}')
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

    

