import json, sqlite3, datetime, arrow, re, os
from domino.core import log
from discount.core import SCHEMES_FOLDER
from domino.databases.sqlite import Sqlite, JSON
from sqlalchemy import Column, Index, Integer, String
from settings import MODULE_ID

class Schema(Sqlite.Base):
    class НаборАкций:
        def __init__(self, дисконтная_схема, имя_набора):
            self.имя_набора = имя_набора
            self.список_акций = дисконтная_схема.info.get(self.имя_набора, [])
        
        def сохранить(self, дисконтная_схема):
            дисконтная_схема.info[self.имя_набора] = self.список_акций
        
        @property
        def размер(self):
            return len(self.список_акций)

        def акция_ID(self, i):
            return self.список_акций[i]

        def есть_акция_ID(self, акция_ID):
            for ID in self.список_акций:
                if str(ID) == str(акция_ID):
                    return True
            return False

        def добавить(self, акция):
            self.список_акций.append(акция.id)

        def присутствует(self, action):
            for ID in self.список_акций:
                if str(ID) == str(action.id):
                    return True
            return False
        
        def удалить(self, номер):
            del self.список_акций[номер]

        def вставить(self, номер, акция):
            self.список_акций.insert(номер, акция.id)

        def поставить_на_место(self, i, j):
            ID = self.список_акций[i]
            del self.список_акций[i]
            self.список_акций.insert(j, ID)

    __tablename__ = 'schema'

    id      = Column('id', Integer, nullable=False, primary_key=True)
    INFO    = Column('info', String)
    bigsize = Column(Integer)

    @property
    def ID(self):
        return self.id
    @property
    def info(self):
        return json.loads(self.INFO)

    @staticmethod
    def дата_утверждения(account_id, схема_ID):
        folder = SCHEMES_FOLDER(account_id)
        path = os.path.join(folder, str(схема_ID))
        if os.path.isfile(path):
            t = datetime.datetime.fromtimestamp(os.path.getmtime(path))
            return t.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return None

    def __init__(self, ID = None, TYPE=0):
        self.ID = ID
        self.TYPE = TYPE
        self.info = {}
        self._расчетные_акции = None
        self._послепродажные_акции = None

    def __str__(self):
        return f'ДисконтнаяСхема({self.ID})'

    @property
    def это_основная_схема(self):
        return self.ID is not None and str(self.ID) == '0'

    @property
    def набор_подразделений_ID(self):
        return self.info.get('набор_подразделений')
    @набор_подразделений_ID.setter
    def набор_подразделений_ID(self, value):
        self.info['набор_подразделений'] = value
    
    @property
    def расчетные_акции(self):
        if self._расчетные_акции is None:
            self._расчетные_акции = ДисконтнаяСхема.НаборАкций(self, 'расчетные_акции')
        return self._расчетные_акции
 
    @property
    def послепродажные_акции(self):
        if self._послепродажные_акции is None:
            self._послепродажные_акции = ДисконтнаяСхема.НаборАкций(self, 'послепродажные_акции')
        return self._послепродажные_акции

    def get_used_actions(self):
        used_actions = set()
        for action_id in self.расчетные_акции.список_акций:
            used_actions.add(int(action_id))
        for action_id in self.послепродажные_акции.список_акций:
            used_actions.add(int(action_id))
        return used_actions

    def get_dept_codes(self, SQLITE):
        if self.ID == 0:
            return []
        sql = f'select info from dept_set_item where dept_set = {self.набор_подразделений_ID}'
        codes = []
        for INFO, in SQLITE.execute(sql):
            info = json.loads(INFO)
            codes.append(info['code'])
        return codes

    @property
    def наименование(self):
        return self.info.get('description','')
    @наименование.setter
    def наименование(self,value):
        self.info['description'] = value
    @property
    def полное_наименование(self):
        return f'''Дисконтная схема "{self.info.get('description','')}"'''
    
    @property
    def info_dump(self):
        return json.dumps(self.info, ensure_ascii=False)
    @info_dump.setter
    def info_dump(self, value):
        try:
            self.info = json.loads(value)
        except:
            pass

ДисконтнаяСхема = Schema

def on_activate(account_id, LOG):
    SQLITE = Sqlite.Pool().session(account_id, module_id=MODULE_ID)
    SQLITE.execute('''
        create table if not exists schema (
            id integer not null primary key, TYPE integer not null default(0),
            info blob default('{}'),
            bigsize integer
        )
        ''')
    count = SQLITE.execute('select count(*) from schema where ID = 0').fetchone()[0]
    if not count:
        sql = '''insert into schema (ID, info) values (0, '{"description":"ОСНОВНАЯ СХЕМА"}')'''
        LOG(sql)
        SQLITE.execute(sql)

    columns = {}
    for column in SQLITE.execute(f'pragma table_info(schema)').fetchall():
        columns[column[1]] = column

    if 'bigsize' not in columns:
        sql = f'alter table schema add column bigsize integer'
        LOG(sql)
        SQLITE.execute(sql)

    SQLITE.commit()
    SQLITE.close()
