import sys, os, datetime, sqlite3
from domino.core import log
from discount.schemas import ДисконтнаяСхема
from settings import MODULE_ID
from domino.databases.sqlite import Sqlite
from tables.sqlite.product_set import ProductSet as PS
from tables.sqlite.action_set_item import ActionSetItem as ITEM
from tables.sqlite.complex_good_set_item import ComplexGoodSetItem as CHILD
from discount.core import DISCOUNT_DB, SCHEMES_FOLDER

class DiscountSchema:
    def __init__(self, account_id):
        self.account_id = account_id
    
    def analize(self, schema_id):
        conn = sqlite3.connect(DISCOUNT_DB(self.account_id))
        cur = conn.cursor()
        SQLITE = Sqlite.Pool().session(self.account_id, module_id = MODULE_ID)
        #--------------------------------
        schema = ДисконтнаяСхема.get(cur, schema_id)
        self.used_actions = schema.get_used_actions()
        #--------------------------------
        self.used_sets = set()
        self.used_sets.add(PS.ПОСТОЯННО_ИСКЛЮЧЕННЫЕ_ТОВАРЫ_ID)
        self.complex_sets = set()
        for set_id, ps in SQLITE.query(ITEM.set_id, PS)\
            .join(PS, PS.id == ITEM.set_id)\
            .filter(ITEM.action_id.in_(self.used_actions)):
            if not ps:
                log.error(f'НЕСУЩЕСТВУЮЩИЙ НАБОР {set_id}')
            else:
                self.used_sets.add(set_id)
                if ps.type_ == PS.КОМПЛЕКСНЫЙ_НАБОР:
                    self.complex_sets.add(set_id)
        #--------------------------------
        for child_id, in SQLITE.query(CHILD.child_id)\
            .filter(CHILD.set_id.in_(self.complex_sets)):
                self.used_sets.add(child_id)
        #--------------------------------

        self.USED_ACTIONS = f'({",".join(str(id) for id in self.used_actions)})'
        self.USED_SETS = f'({",".join(str(id) for id in self.used_sets)})'

        log.info(f'Используемых акций : {len(self.used_actions)} : {self.USED_ACTIONS}')
        log.info(f'Используемых наборов : {len(self.used_sets)} : {self.USED_SETS}')
        
        SQLITE.close()
        conn.close()

    def accept(self, schema_id):

        log.info(f'УТВЕРЖДЕНИЕ СХЕМЫ {schema_id}')
        if str(schema_id) != "0":
            дата_утверждения = ДисконтнаяСхема.дата_утверждения(self.account_id, 0)
            if дата_утверждения is None:
                raise Exception('Прежде, чем утверждать какую либо дополнительную схему, следует утвердить ОСНОВНУЮ СХЕМУ')

        self.analize(schema_id)

        now = datetime.datetime.now()
        VERSION = now.strftime('%Y-%m-%d %H:%M:%S')
        папка = SCHEMES_FOLDER(self.account_id)
        os.makedirs(папка, exist_ok=True)
        БД = os.path.join(папка, f'{schema_id}')
        БД_временная = os.path.join(папка, f'{schema_id}.tmp')
        if os.path.exists(БД_временная):
            os.remove(БД_временная)

        src = DISCOUNT_DB(self.account_id)

        with sqlite3.connect(БД_временная) as conn:
            cur = conn.cursor()
            conn.executescript(f'''
            attach database "{src}" as src;
            create table emission as select * from src.emission;
            create table actions as select * from src.actions where id in {self.USED_ACTIONS};
            create table action_set_item as select * from src.action_set_item where action_set_item.action_id in {self.USED_ACTIONS};
            create table dept_set as select * from src.dept_set;
            create table dept_set_item as select * from src.dept_set_item;
            create table product_set as select * from src.product_set where id in {self.USED_SETS};
            create table good_set_item as select * from src.good_set_item where set_id in {self.USED_SETS};
            create table complex_good_set_item as select * from src.complex_good_set_item;
            create table schema as select * from src.schema where src.schema.ID = {schema_id};
            create index if not exists good_set_item_on_set_id_code on good_set_item(set_id, code); 
            detach src;
            ''')
            #create table product_set_item as select * from src.product_set_item where product_set in {self.USED_SETS};
            # ПЕРЕНОС ТОВАРНЫХ ЗАПРОСОВ
            #codes = []
            #cur.execute('select info from src.product_set_item')
            # -------------------------
            
            cur.execute('select count(*) from good_set_item')
            goods, = cur.fetchone()

        os.rename(БД_временная, БД)
        with open(os.path.join(папка, 'VERSION'), 'w') as f:
            f.write(VERSION)
        
        msg = f'Утверждение дисконтной схемы : акций {self.USED_ACTIONS} наборов {self.USED_SETS}, товаров {goods}'
        #Protocol.create(self.postgres, self.user_id, msg, schema_id=self.схема.ID)
        return msg

