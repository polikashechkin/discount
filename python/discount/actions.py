import json, sqlite3, datetime, arrow, re
from domino.core import log, Time, Bool
from discount.core import DISCOUNT_DB

def get(account_id, action_id):
    with sqlite3.connect(DISCOUNT_DB(account_id)) as conn:
        cur = conn.cursor()
        return Action.get(cur, action_id)

def find(account_id, where_clause = None, params=[]):
    return findall(account_id, where_clause, params)

def findall(account_id, where_clause = None, params=[]):
    actions = []
    try:
        with sqlite3.connect(DISCOUNT_DB(account_id)) as conn:
            cur = conn.cursor()
            actions = Action.findall(cur, where_clause, params)
        #log.debug(f'{account_id} : {len(actions)})')
        return actions
    except BaseException as ex:
        log.exception(f'discount.actions:findall({account_id}, {where_clause}, {params}) : {ex}')
        return actions

def update(account_id, action):
    with sqlite3.connect(DISCOUNT_DB(account_id)) as conn:
        cur = conn.cursor()
        action.update(cur)

def create(account_id, action):
    with sqlite3.connect(DISCOUNT_DB(account_id)) as conn:
        cur = conn.cursor()
        action.create(cur)

class ActionSetItem:
    ОСНОВНЫЕ_ТОВАРЫ = 0
    ИСКЛЮЧЕННЫЕ_ТОВАРЫ = 1
    СОПУТСТВУЮЩИЕ_ТОВАРЫ = 2
    def __init__(self, set_id = None, info = {}, ID = None, CLASS = 0, TYPE = 0, STATE = 0, action_id = None, INFO = None):
        self.ID = ID
        self.TYPE = TYPE
        self.CLASS = CLASS
        self.STATE = STATE

        self.action_id = action_id
        self.set_id = int(set_id)
        self.info = info

        if INFO is not None:
            try:
                info = json.loads(INFO)
            except:
                info = {}
    def create(self, cursor):
        if self.info is None:
            self.info = {}
        INFO = json.dumps(self.info)
        cursor.execute(f'insert into action_set_item (CLASS, TYPE, STATE, set_id, action_id, INFO) values(?, ?, ?, ?, ?, ?)',
        [self.CLASS, self.TYPE, self.STATE, self.set_id, self.action_id, INFO])
        self.ID = cursor.lastrowid
    def update(self, cursor):
        if self.info is None:
            self.info = {}
        INFO = json.dumps(self.info)
        cursor.execute(f'update action_set_item set CLASS=?, TYPE=?, STATE=?, set_id=?, action_id=?, INFO=? where ID=?',
        [self.CLASS, self.TYPE, self.STATE, self.set_id, self.action_id, INFO, self.ID])
    @staticmethod
    def findall(cursor, where_clause, params=[]):
        sets = []
        cursor.execute(f'select ID, CLASS, TYPE, STATE, set_id, action_id, INFO from action_set_item where {where_clause}', params)
        for ID, CLASS, TYPE, STATE, set_id, action_id, INFO in cursor:
            ps = ActionSetItem(ID=ID, CLASS=CLASS, TYPE=TYPE, STATE=STATE, set_id=set_id, action_id=action_id, INFO=INFO)
            sets.append(ps)
        return sets
    @staticmethod
    def get(cursor, ID):
        return ActionSetItem.findfirst('ID=?', [ID])
    @staticmethod
    def findfirst(cursor, where_clause, params=[]):
        cursor.execute(f'select ID, CLASS, TYPE, STATE, set_id, action_id, INFO from action_set_item where {where_clause}', params)
        r = cursor.fetchone()
        if r is None:
            return None
        else: 
            ID, CLASS, TYPE, STATE, set_id, action_id, INFO = r
            return ActionSetItem(ID=ID, CLASS=CLASS, TYPE=TYPE, STATE=STATE, set_id=set_id, action_id=action_id, INFO=INFO)
    @staticmethod
    def deleteall(cursor, where_clause, params=[]):
        cursor.execute(f'delete from action_set_item where {where_clause}', params)
    @staticmethod
    def count(cursor, where_clause, params=[]):
        cursor.execute(f'select count(*) from action_set_item where {where_clause}', params)
        return cursor.fetchone()[0]


class ДеньНедели:
    def __init__(self, день, начало = '', окончание=''):
        self.день = int(день)
        self.начало = Time(начало)
        self.окончание = Time(окончание)
    
    @staticmethod
    def наименование(день):
        return arrow.locales.get_locale('ru_RU').day_name(день + 1)
            
    def __str__(self):
        return f'ДеньНедели({self.день})'

class ОграничениеПоДнямНедели:
    def __init__(self, action):
        js = action.info.get('дни_недели')
        if js is None:
            self.дни_недели = None
        else:
            self.дни_недели = []
            for day in js:
                if day is not None:
                    try:
                        self.дни_недели.append(ДеньНедели(day[0], day[1], day[2]))
                    except:
                        self.дни_недели.append(None)
                else:
                    self.дни_недели.append(None)
    @property
    def есть(self):
        return self.дни_недели is not None
    
    @есть.setter
    def есть(self, true):
        if true:
            if self.дни_недели is None:
                self.дни_недели = [None] * 7
        else:
            self.дни_недели = None

    def __getitem__(self, день):
        try:
            return self.дни_недели[день]
        except:
            return None

    def __setitem__(self, день, день_недели):
        try:
            self.дни_недели[день] = день_недели
        except:
            pass

    def save(self, action):
        #log.debug(f'{self.weekdays}')
        if self.дни_недели is not None:
            js = []
            for день_недели in self.дни_недели:
                if день_недели is None:
                    js.append(None)
                else:
                    js.append([день_недели.день, str(день_недели.начало), str(день_недели.окончание)])
            action.info['дни_недели'] = js
        else:
            try:
                del action.info['дни_недели']
            except:
                pass
class ActionUsedCards:
    def __init__(self, info):
        try:
            self.card_types = set(info.get('used_cards', []))
        except:
            self.card_types = set()
    def save(self, info):
        info['used_cards'] = list(self.card_types)

class ActionUsedActions:
    def __init__(self, info):
        try:
            self.actions = set(info.get('used_actions', []))
        except:
            self.actions = set()
    def __contains__(self, action_id):
        return action_id in self.actions
    def add(self, action_id):
        self.actions.add(action_id)
    def remove(self, action_id):
        self.actions.discard(action_id)
    def save(self, info):
        info['used_actions'] = list(self.actions)

class Persents_of_sum:
    def __init__(self, info):
        self.percents = []
        try:
            for s, p in info.get('percents_of_sum'):
                self.percents.append([int(s), float(p)])
        except:
            pass
        self.dim = len(self.percents)

    def save(self, info):
        percents = []
        info['percents_of_sum'] = percents
        for s, p in self.percents:
            percents.append([str(s), str(p)])
        #log.debug(f'{info}')
   
    def get_scale(self):
        scale=[]
        for p in self.percents:
            scale.append(str(p[0]))
        return ' '.join(scale)

    def sum_name(self, i):
        try:
            if i == self.dim - 1:
                return f'от {self.get_sum(i)}'
            else:
                return f'от {self.get_sum(i)} до {self.get_sum(i+1)}'

        except:
            return '?'

    def set_scale(self, scale):
        percents = []
        try:
            ss = re.findall(r'\d+', scale)
            #log.debug(f'{ss}')
            ss = [ int(s) for s in ss]
            #log.debug(f'{ss}')
            ss = sorted(ss)
            #log.debug(f'{ss}')
            i = 0
            for s in ss:
                percents.append([int(s), self.get_percent(i)])
                i +- 1
        except:
            pass
        self.percents = percents
        self.dim = len(self.percents)
    
    def get_percent(self, i):
        try:
            return self.percents[i][1]
        except:
            return 0.0

    def set_percent(self, i, percent):
        try:
            self.percents[i][1] = float(percent)
        except:
            log.exception(f'set_percent({i}, {percent})')

    def get_sum(self, i):
        try:
            return int(self.percents[i][0])
        except:
            return 0

    def find_percent(self, sum):
        percent = 0.0
        for s, p in self.percents:
            if s > sum:
                break
            else:
                percent = p
        return percent

class Action:
    print_mode_FOOTER = 'FOOTER'
    print_mode_HEADER = 'HEADER'
    print_mode_COUPON = 'COUPON'
    PRINT_MODE  = 'print_mode'
    print_lines_count_DEFAULT = 0
    print_lines_count_MAX = 41
    PRINT_LINES_COUNT = 'print_lines_count'
    START_DATE = 'start_date'
    END_DATE = 'end_date'

    DISCOUNT = 'discount' # Процентная скидка
    ПРОЦЕНТНАЯ_СКИДКА = 'discount'
    СУММОВАЯ_СКИДКА = 's_discount'
    FIXED_PRICE = 'fixed_price' # Окончательная цена
    SUPPLEMENT = 'supplement' # Дополнительная скидка (добавляется к остальным)
    TRUE = '1'
    FALSE = '0'
    
    СКИДКИ_НА_ТОВАРЫ = 'discount'
    ИСКЛЮЧЕННЫЕ_ТОВАРЫ = 'excluded_products'
    ОСНОВНЫЕ_ТОВАРЫ = 'основные_товары'
    РЕЕСТР_ЦЕН = 'реестр_цен'
    МНОЖИТЕЛЬ = 'множитель'
    АКЦИЯ = 'акция'
    
    ДИСКОНТНАЯ_КАРТА = 'дисконтная_карта'
    ПОДАРОЧНЫЙ_КУПОН = 'подарочный_купон'
    МИНИМАЛЬНАЯ_СУММА_ТОВАРОВ = 'минимальная_сумма_товаров'
    МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ = 'count'
    МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ = 'минимальное_количество_товаров'
    МИНИМАЛЬНАЯ_СУММА_ЧЕКА = 'summa'
    МИНИМАЛЬНАЯ_СУММА_ЧЕКА_БЕЗ_ИСКЛЮЧЕННЫХ = 'summa_wo_ex'
    МИНИМАЛЬНАЯ_СУММА_ЧЕКА_СО_СКИДКОЙ = 'summa_fact'
    МИНИМАЛЬНАЯ_СУММА_ЧЕКА_СО_СКИДКОЙ_БЕЗ_ИСКЛЮЧЕННЫХ = 'summa_fact_wo_ex'
    СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА = 'summa_mode'
    СХЕМА_ID = 'схема_ID'
    ПРОЦЕНТ_НАЧИСЛЕНИЯ_БАЛЛОВ = 'процент_начисления_баллов'
    НАЛИЧИЕ_КАРТЫ_КУПОНА = 'series_id'
    ПРОЦЕНТ_ОТ_ПОЗИЦИИ = 'процент_от_позиции'
    КЛЮЧЕВОЕ_СЛОВО = 'keyword'
    ШАБЛОН_QR_КОДА = 'pattern'
    КОЛИЧЕСТВО_СОПУТСТВУЮЩИХ_ТОВАРОВ = 'number_of_related_products'
    КОЛИЧЕСТВО_ДНЕЙ_ДО_ДНЯ_РОЖДЕНИЯ = 'days_before'
    КОЛИЧЕСТВО_ДНЕЙ_ПОСЛЕ_ДНЯ_РОЖДЕНИЯ = 'days_after'
    СТОИМОСТЬ_ОДНОЙ_ПОДАРОЧНОЙ_МАРКИ = 'mark_price'
    КОЛИЧЕСТВО_ТОВАРОВ_ДЛЯ_ПОЛУЧЕНИЯ_ПОДАРОЧНОЙ_МАРКИ = 'mark_q'
    ПОДРАЗДЕЛЕНИЕ = 'dept'
    ЦИФРА_НА_КОТОРУЮ_ОКАНЧИВАЕТСЯ_ЦЕНА = 'last_digit'
    ОКРУГЛЕНИЕ_БОНУСА = 'point_rounding'
    МАКСИМАЛЬНО_ОПЛАЧИВАЕМАЯ_СТОИМОСТЬ_ЧЕКА = 'max_percent'

    def __init__(self, id = None, type=None):
        self.id = id
        self.type = type
        self.status = 0
        self.info = {}
        self._used_cards = None
        self._percents_of_sum = None
        self._used_actions = None
        self._sets = None
        self._ограничание_по_дням_недели = None
    def __str__(self):
        return f'Action({self.type}, {self.id})'
    
    @property
    def type_(self):
        return self.type
        
    @property
    def ID(self):
        return self.id
    @property
    def TYPE(self):
        return self.type
    @property
    def схема_ID(self):
        return self.info.get(Action.СХЕМА_ID)
    @схема_ID.setter
    def схема_ID(self, value):
        self.info[Action.СХЕМА_ID] = value
    @property
    def округление(self):
        return int(self.info.get('округление', 100))
    @округление.setter
    def округление(self, value):
        self.info['округление'] = int(value)
    @property
    def формула_вычисления_подарка(self):
        return int(self.info.get('формула_вычисления_подарка', 2))
    @формула_вычисления_подарка.setter
    def формула_вычисления_подарка(self, value):
        self.info['формула_вычисления_подарка'] = int(value)
    @property
    def подарочный_купон(self):
        try:
            return int(self.info.get(Action.ПОДАРОЧНЫЙ_КУПОН))
        except:
            return None
    @property
    def акция(self):
        try:
            return int(self.info.get(Action.АКЦИЯ))
        except:
            return None
    @property
    def множитель(self):
        try:
            return float(self.info.get(Action.МНОЖИТЕЛЬ))
        except:
            return 0.0
    @property
    def ограничение_по_дням_недели(self):
        if self._ограничание_по_дням_недели is None:
            self._ограничание_по_дням_недели = ОграничениеПоДнямНедели(self)
        return self._ограничание_по_дням_недели
    
    @property
    def fixed_price(self):
        return self.info.get(Action.FIXED_PRICE, Action.FALSE) == Action.TRUE
    @fixed_price.setter
    def fixed_price(self, value):
        if value:
            self.info[Action.FIXED_PRICE] = Action.TRUE
        else:
            self.info[Action.FIXED_PRICE] = Action.FALSE
    @property
    def supplement(self):
        return self.info.get(Action.SUPPLEMENT, Action.FALSE) == Action.TRUE
    @supplement.setter
    def supplement(self, value):
        if value:
            self.info[Action.SUPPLEMENT] = Action.TRUE
        else:
            self.info[Action.SUPPLEMENT] = Action.FALSE
    def полное_наименование(self, action_types):
        if self.description and self.description.strip():
            return self.description
        else:
            action_type = action_types[self.type]
            return f'{action_type.description()}'
    def full_name(self, action_types):
        action_type = action_types[self.type]
        return f'{action_type.description()} {self.description}'

    @property
    def discount(self):
        try:
            return int(self.info.get(Action.DISCOUNT, 0))
        except:
            return 0
    @property
    def percents_of_sum(self):
        if self._percents_of_sum is None:
            self._percents_of_sum = Persents_of_sum(self.info)
        return self._percents_of_sum
    @property
    def used_actions(self):
        if self._used_actions is None:
            self._used_actions = ActionUsedActions(self.info)
        return self._used_actions
    @property
    def used_cards(self):
        if self._used_cards is None:
            self._used_cards = ActionUsedCards(self.info)
        return self._used_cards
    @property
    def print_lines_count(self):
        return int(self.info.get(Action.PRINT_LINES_COUNT, Action.print_lines_count_DEFAULT))
    @property
    def print_mode(self):
        return self.info.get(Action.PRINT_MODE, Action.print_mode_FOOTER)
    @property
    def after_sales_pos(self):
        try:
            return int(self.info.get('after_sales_pos'))
        except:
            return 0
    @after_sales_pos.setter
    def after_sales_pos(self, value):
        try:
            self.info['after_sales_pos'] = str(int(value))
        except:
            self.info['after_sales_pos'] = '0'
    @property
    def pos(self):
        try:
            return int(self.info.get('pos'))
        except:
            return 0
    @pos.setter
    def pos(self, value):
        try:
            self.info['pos'] = str(int(value))
        except:
            self.info['pos'] = '0'
    def get_date_param(self, name):
        try:
            return datetime.datetime.strptime(self.info.get(name), '%Y-%m-%d').date()
        except:
            return None
    def set_date_param(self, name, value):
        if value is None:
            self.info[name] = ''
            return
        value = value.strip()
        if value == '':
            self.info[name] = ''
            return
        date_param = datetime.datetime.strptime(value, '%Y-%m-%d')
        self.info[name] = date_param.strftime('%Y-%m-%d')
    @property
    def start_date(self):
        try:
            return arrow.get(self.info.get(Action.START_DATE, 'None'))
        except:
            return None
    @property
    def end_date(self):
        try:
            return arrow.get(self.info.get(Action.END_DATE,'None'))
        except:
            return None
    #def get_items(self, cur, type_id = 0):
    #    return ActionSetItem.findall(cur, 'action_id=? and type=?', [f'{self.id}', type_id])
    #def get_products_set(self, cur, set_id = 0):
    #    products = set()
    #    for item in self.get_items(cur, set_id):
    #        products.add(item.code)
    #    return products
    #def items(self, account_id, type_id = 0):
    #    with sqlite3.connect(DISCOUNT_DB(account_id)) as conn:
    #        cur = conn.cursor()
    #        return ActionSetItem.findall(cur, 'action_id=? and type=?', [f'{self.id}', type_id])
    #def get_props(self, cur, type_id = 0):
    #    return ActionSetItem.findall(cur, 'action_id=? and type=?', [f'{self.id}', type_id])
    @property
    def name(self):
        return self.info.get('description')
    @property
    def description(self):
        return self.info.get('description')
    @description.setter
    def description(self, value):
        self.info['description'] = value
    @property
    def info_dump(self):
        return json.dumps(self.info, ensure_ascii=False)
    @info_dump.setter
    def info_dump(self, value):
        try:
            self.info = json.loads(value)
        except:
            pass
    def get_int(self, key):
        try:
            return int(self.info.get(str(key)))
        except:
            return 0
    def get_float(self, key):
        try:
            return float(self.info.get(str(key)))
        except:
            return 0.0
    def __getitem__(self, key):
        return self.info.get(str(key))
    def __setitem__(self, key, value):
        self.info[str(key)] = value
    def create(self, cur):
        cur.execute('insert into actions (type, status, info) values(?,?,?)'
            ,[self.type, self.status, self.info_dump])
        self.id = cur.lastrowid
    @staticmethod
    def get(cur, id):
        a = Action(id)
        try:
            cur.execute('select type, status, info from actions where id=?',[id])
            a.type, a.status, a.info_dump = cur.fetchone()
            return a
        except:
            #log.exception(f'Action.get("{id}")')
            return None
    @staticmethod
    def findall(cur, where_clause = None, params = []):
        actions = []
        if where_clause is not None:
            q = f'select id, type, status, info from actions where {where_clause}'
            cur.execute(q, params)
        else:
            q = f'select id, type, status, info from actions'
            cur.execute(q)
        for action_id, action_type, status, info_dump in cur:
            a = Action(action_id)
            a.type = action_type
            a.status = status
            a.info_dump = info_dump
            actions.append(a)
        return actions
    @staticmethod
    def calc_actions(cursor, action_types):
        actions = []
        for action in Action.findall(cursor):
            action_type = action_types[action.type]
            if action_type is None:
                log.error(f'Недоступен тип акции "{action.type}"')
            elif action_type.hasCalculator:
                actions.append(action)
        return sorted(actions, key = lambda action : action.pos)
    @staticmethod
    def accept_actions(cursor, action_types):
        actions = []
        for action in Action.findall(cursor):
            action_type = action_types[action.type]
            if action_type is None:
                log.error(f'Недоступен тип акции "{action.type}"')
            elif action_type.hasAcceptor:
                actions.append(action)
        return sorted(actions, key = lambda action : action.after_sales_pos)
    def update(self, cur):
        if self._used_cards is not None:
            self._used_cards.save(self.info)
        if self._used_actions is not None:
            self._used_actions.save(self.info)
        if self._percents_of_sum is not None:
            self._percents_of_sum.save(self.info)
        if self._sets is not None:
            self._sets.save(self)
        
        if self._ограничание_по_дням_недели is not None:
            self._ограничание_по_дням_недели.save(self)

        cur.execute('update actions set status=?, info=? where id=?', [self.status, self.info_dump, self.id])

def create_structure(account_id, log):
    DB = DISCOUNT_DB(account_id)
    with sqlite3.connect(DB) as conn:
        #ActionSetItem.create_structure(conn, log)
        conn.executescript('''
        create table if not exists actions
        (
            ID          integer not null primary key, 
            TYPE        not null, 
            status      integer not null default(0),
            info        blob 
        );
        '''
        )
    print (f'Таблица "actions" создана.')
