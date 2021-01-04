import json
from domino.core import log
from domino.databases.sqlite import Sqlite
from sqlalchemy import Column, Index, BigInteger, Integer, String, SmallInteger, DateTime

def on_activate(account_id, on_activate_log):
    pass

class DeptSetItem(Sqlite.Base):

    __tablename__ = 'dept_set_item'

    id              = Column(BigInteger, primary_key=True)
    #type_           = Column('type', SmallInteger)
    dept_set_id     = Column('dept_set', Integer)
    code            = Column('code', String)
    INFO            = Column(String)

    @property
    def info(self):
        return json.loads(self.INFO)

    @property
    def dept_code(self):
        return self.info.get('code')

    @staticmethod
    def get_all_codes(SQLITE):
        #log.debug(f'get_all_codes')
        codes = []
        for INFO, in SQLITE.execute('select info from dept_set_item'):
            #log.debug(f'{INFO}')
            info = json.loads(INFO)
            code = info.get('code')
            codes.append(code)
        return codes

    @staticmethod
    def get_set_codes(SQLITE, dept_set_id):
        codes = []
        sql = f'select info from dept_set_item where dept_set = {dept_set_id}'
        for INFO, in SQLITE.execute(sql):
            info = json.loads(INFO)
            code = info.get('code')
            codes.append(code)
        return codes

    def __repr__(self):
        return f'<DeptSetItem(id={self.id}, type={self.type_}, dept_set_id={self.dept_set_id}, info={self.info})>'

