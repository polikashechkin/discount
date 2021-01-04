import logging, os, sys, datetime
from domino.core import DOMINO_ROOT, DOMINO_LOG

CARDS = 'DISCOUNT#CARDS2'
CARDS_LOG = 'DISCOUNT#CARDS_LOG'

MODULE_ID = 'discount'

def DISCOUNT_DB(account_id):
    return f'{DOMINO_ROOT}/accounts/{account_id}/data/discount.db'

def DISCOUNT_CALC_FOLDER(account_id):
    return f'{DOMINO_ROOT}/accounts/{account_id}/data/discount/calc'   
def SCHEMES_FOLDER(account_id):
    return f'{DOMINO_ROOT}/accounts/{account_id}/data/discount/schemas'

def PRODUCT_COLUMNS_FILE(account_id):
    return f'{DOMINO_ROOT}/accounts/{account_id}/data/discount/columns'

#LOG = logging.getLogger('discount')
#LOG_FILE = os.path.join(DOMINO_LOG, 'discount.log')
#hdlr = logging.FileHandler(LOG_FILE)
#formatter = logging.Formatter('%(levelname)s %(message)s')
#formatter = logging.Formatter('%(asctime)s %(levelname)s %(module)s.%(funcName)s %(message)s')
#hdlr.setFormatter(formatter)
#LOG.addHandler(hdlr) 
#log.setLevel(logging.INFO)
#LOG.setLevel(logging.DEBUG)

#class log:
#    @staticmethod
#    def info(msg):
#        LOG.info(f'{datetime.datetime.now()} {msg}')    
#    @staticmethod
#    def error(msg):
#        LOG.error(f'{datetime.datetime.now()} {msg}')
#    @staticmethod
#    def clear(self):
#        os.truncate(LOG_FILE)

class Engine:
    def __init__(self, ora_connection, pg_connection):
        self.cursor = ora_connection.cursor() if ora_connection is not None else None
        self.pg_connection = pg_connection
        self.pg_cursor = pg_connection.cursor()

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.pg_cursor:
            self.pg_cursor.close()

def discount_log(msg = None):
    if msg is None:
        LOG.info('')
    else:
        now = datetime.datetime.now()
        LOG.info(f'{now:%H:%M:%S} {msg}')


class Finder:
    def __init__(self, page, method='.find'):
        self.query = None
        self.method = method
        query = page.get('finder')
        if query is not None:
            query = query.strip().upper()
            if query != '':
                self.query = query

    def match(self, *names):
        if self.query is None:
            return True
        for name in names:
            if str(name).upper().find(self.query) != -1:
                return True
        return False

    #@staticmethod
    def append(self, toolbar):
        query = toolbar.page.get('finder')
        g = toolbar.input_group()
        g.input(value = query if query is not None else '', name='finder')
        #toolbar.input(value = query if query is not None else '', name='finder')
        g.button('').glif('search').on_click(self.method, forms=[toolbar])



