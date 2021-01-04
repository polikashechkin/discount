import os, logging, datetime, time, threading
from domino.core import DOMINO_ROOT, log as domino_log
from sqlalchemy.ext.declarative import declarative_base

PostgresTable = declarative_base()

MODULE_ID = 'discount'
GRANT_MODULE_ID = MODULE_ID
def DATABASE_DB(account_id):
    return os.path.join(DOMINO_ROOT, 'accounts', account_id, 'data', f'{MODULE_ID}.db')

LOG_FILE = os.path.join(DOMINO_ROOT, 'log', f'{MODULE_ID}.log')

LOG = logging.getLogger(MODULE_ID)
hdlr = logging.FileHandler(LOG_FILE)
formatter = logging.Formatter('%(message)s')
hdlr.setFormatter(formatter)
LOG.addHandler(hdlr) 
LOG.setLevel(logging.DEBUG)
PID = os.getpid()

class log:
    #count = 0
    @staticmethod
    def timing(start):
        if start:
            ms = round((time.perf_counter() - start) * 1000, 2)
            return f'{ms}'
        else:
            return '-'
    @staticmethod
    def info(msg, start = None):
        LOG.info(f'{datetime.datetime.now()}\tINFO\t{os.getpid()}:{threading.get_ident()}\t{msg}\t{log.timing(start)}')
        #log.count += 1
    @staticmethod
    def error(msg, start=None):
        LOG.error(f'{datetime.datetime.now()}\tERROR\t{os.getpid()}:{threading.get_ident()}\t{msg}\t{log.timing(start)}')
        #log.count += 1
    @staticmethod
    def worning(msg, start=None):
        LOG.error(f'{datetime.datetime.now()}\tWORNING\t{os.getpid()}:{threading.get_ident()}\t{msg}\t{log.timing(start)}')
        #log.count += 1
