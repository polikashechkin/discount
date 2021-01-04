import sys, os, datetime, json, uuid, time, sqlite3
#import xml.etree.cElementTree as ET
from domino.core import log, DOMINO_ROOT
from settings import MODULE_ID

class PosCheckLog:
    CREATE_DATABASE_STRIPT = '''
    create table if not exists log(
        CHECK_ID text not null,
        CREATION_DATE text, 
        TYPE text,
        MESSAGE text,
        INFO blob
    );
    '''
    INSERT = 'insert into LOG (CHECK_ID, CREATION_DATE, TYPE, MESSAGE) values(?,?,?,?)'
    HEADER = 'header'
    ERROR = 'error'
    COMMENT = 'comment'

    def __init__(self, account_id, check_id):
        self.account_id = account_id
        self.check_id = check_id
        self.connection = PosCheckLog.connect(self.account_id, self.check_id)
        self.cursor = self.connection.cursor()
        self.cursor.executescript(PosCheckLog.CREATE_DATABASE_STRIPT)

    @staticmethod
    def connect(account_id, check_id):
        db_file = os.path.join(DOMINO_ROOT, 'accounts', account_id, 'data', MODULE_ID, 'test', 'log.db')
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        return sqlite3.connect(db_file)

    def clear(self):
        with self.connection:
            self.cursor.execute('delete from LOG where CHECK_ID=?', [self.check_id])
        return self

    def select(self):
        self.cursor.execute('select TYPE, MESSAGE from log where check_id=? order by CREATION_DATE', [self.check_id])
        return self.cursor.fetchall()

    def comment(self, message = ''):
        with self.connection:
            self.cursor.execute(PosCheckLog.INSERT, [self.check_id, datetime.datetime.now(), PosCheckLog.COMMENT, message])
    def header(self, message = ''):
        with self.connection:
            self.cursor.execute(PosCheckLog.INSERT, [self.check_id, datetime.datetime.now(), PosCheckLog.HEADER, message])
    def error(self, message = ''):
        with self.connection:
            self.cursor.execute(PosCheckLog.INSERT, [self.check_id, datetime.datetime.now(), PosCheckLog.ERROR, message])
