from domino.databases.sqlite import Sqlite
from sqlalchemy import Column, Index, BigInteger, Integer, String, SmallInteger, JSON, DateTime, text as T
from sqlalchemy.dialects.sqlite import BLOB 
from settings import MODULE_ID

def on_activate(account_id, on_activate_log):
    sqlite = Sqlite.Pool().session(account_id, module_id = MODULE_ID)
    sql = '''create table if not exists action_set_item
        (
            ID          integer not null primary key,
            CLASS       integer not null default(0),
            TYPE        integer not null default(0),
            STATE       integer not null default(0),
            action_id   integer not null,
            set_id      integer not null,
            info        blob  default('{}')
        );
        '''
    sqlite.execute(T(sql))

class ActionSetItem(Sqlite.Base):

    __tablename__ = 'action_set_item'

    ОСНОВНЫЕ_ТОВАРЫ = 0
    ИСКЛЮЧЕННЫЕ_ТОВАРЫ = 1
    СОПУТСТВУЮЩИЕ_ТОВАРЫ = 2

    id              = Column(Integer, primary_key=True, nullable=False)
    type_           = Column('type', Integer, nullable=False)
    action_id       = Column(Integer, nullable=False)
    set_id          = Column(Integer, nullable=False)
    #state          = Column()
    #class_         = Column()
    INFO            = Column('info', BLOB)

    @property
    def info(self):
        if self.INFO:
            try:
                return json.loads(self.INFO)
            except:
                return None
        else:
            return None

    def __repr__(self):
        return f'ActionSetItem(id={self.id}, type={self.type_}, action_id={self.action_id}, set_id={self.set_id}, info={self.info})'

    @staticmethod
    def sets(SQLITE, action_id, type_ = 0):
        sets = []
        for set_id, in SQLITE.query(ActionSetItem.set_id)\
            .filter(ActionSetItem.action_id == action_id, ActionSetItem.type_ == type_):
            sets.append(set_id)
        return sets
