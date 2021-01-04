from domino.databases.sqlite import Sqlite, JSON
from sqlalchemy import Column, Index, BigInteger, Integer, String, SmallInteger, DateTime, text as T
from settings import MODULE_ID

def on_activate(account_id, on_activate_log):
    SQLITE = Sqlite.Pool().session(account_id, module_id=MODULE_ID)
    #sql = '''
    #    drop table complex_good_set_item;
    #'''
    #on_activate_log(sql)
    #SQLITE.execute(T(sql))
    sql = '''
        create table if not exists complex_good_set_item
        (
            set_id integer not null,
            child_id integer not null,
            primary key (set_id, child_id)
        )
    '''
    #on_activate_log(sql)
    SQLITE.execute(T(sql))
    #sql = '''
    #    create unique index if not exists complex_good_set_item_on_set_id_child_id on complex_good_set_item (set_id, child_id);
    #'''
    #on_activate_log(sql)
    #SQLITE.execute(T(sql))
    sql = '''
        create index if not exists complex_good_set_item_on_child_id on complex_good_set_item (child_id);
    '''
    #on_activate_log(sql)
    SQLITE.execute(T(sql))
    SQLITE.commit()
    SQLITE.close()

    #names = []
    #for info in SQLITE.execute(T('pragma table_info("PRODUCT_SET_ITEM")')):
    #    names.append(info[1])

class ComplexGoodSetItem(Sqlite.Base):

    __tablename__ = 'complex_good_set_item'

    set_id          = Column(Integer, nullable=False, primary_key=True)
    child_id        = Column(Integer, nullable=False, primary_key=True)

    Index('', child_id)

    @staticmethod
    def childs(SQLITE, set_id):
        childs = []
        for child_id, in SQLITE.query(ComplexGoodSetItem.child_id).filter(ComplexGoodSetItem.set_id == set_id):
            childs.append(child_id)
        return childs

    @staticmethod
    def add(SQLITE, set_id, child_id):
        sql = f'insert or ignore into complex_good_set_item values({set_id}, {child_id})'
        SQLITE.execute(T(sql))

    @staticmethod
    def remove(SQLITE, set_id, child_id):
        SQLITE.query(ComplexGoodSetItem)\
            .filter(ComplexGoodSetItem.set_id == set_id, ComplexGoodSetItem.child_id == child_id)\
            .delete()
        #sql = f'delete from complex_good_set_item where set_id={set_id} and child_id={child_id})'
        #SQLITE.execute(T(sql))
