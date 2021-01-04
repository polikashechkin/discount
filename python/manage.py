
import sys, os, json, sqlite3, cx_Oracle

from domino.account import find_account
from domino.databases import Databases
from domino.postgres import Postgres
from discount.core import DISCOUNT_DB


class Console:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    COMMENT = '\033[90m'
    def __init__(self, MODULE):
        DIR = f'/DOMINO/data/test/{MODULE}/'
        os.makedirs(DIR, exist_ok=True)
        self.VALUES_FILE = os.path.join(DIR, 'questions')
        self.VALUES = {}
        os.makedirs(os.path.dirname(self.VALUES_FILE), exist_ok=True)
        try:
            with open(os.path.join(self.VALUES_FILE)) as f:
                self.VALUES = json.load(f)
        except:
            pass

    def input(self, q):
        old_value = self.VALUES.get(q, '')
        new_value = input(f'{q} [{old_value}] ? ')
        if new_value != '':
            self.VALUES[q] = new_value
            with open(self.VALUES_FILE, 'w') as f:
                json.dump(self.VALUES, f)
            return new_value
        else:
            return old_value

    def arg(self, n):
        try:
            return sys.argv[n]
        except:
            return None
    @staticmethod
    def print_comment(text):
        if text is not None:
            print('\033[90m' + str(text) + '\033[0m')
    @staticmethod
    def print_error(text):
        if text is not None:
            print('\033[91m' + str(text) + '\033[0m')
    @staticmethod
    def print_header(text):
        if text is not None:
            print('\033[1m' + str(text) + '\033[0m')
    @staticmethod
    def print_warning(text):
        if text is not None:
            print('\033[93m' + str(text) + '\033[0m')
    @staticmethod
    def print_help(text):
        if text is not None:
            print('\033[92m' + str(text) + '\033[0m')

    def error(self, msg):
        Console.print_error(msg)
        sys.exit()

    def warning(self, msg):
        Console.print_warning(msg)
        
    def comment(self, msg):
        Console.print_comment(msg)

    def help(self, msg):
        self.print_help(msg)
    '''
    def set_default(self, prompt, value):
        self.defaults[str(prompt)] = value
        with open(self.defaults_file, 'w') as f:
            json.dump(self.defaults, f)
    
    def input(self, prompt, default = None):
        if default is None:
            default = self.defaults.get(str(prompt))
        if default is None:
            default = ''
        value = input(f'{prompt} [{default}] ? ')
        if value.strip() == '':
            return default
        else:
            self.set_default(prompt, value)
            return value
    '''
    #def run(self, product, version, proc, params):
    #    program = f'/DOMINO/products/{product}/{version}/python/{proc}.py'
    #    if os.path.exists(program):
    #        args = " ".join(params)
    #        command = f'python3.6 {program} {args}'
    #        self.print_comment(command)
    #        os.system(command)
    
    def system(self, cmd):
        self.comment(cmd)
        os.system(cmd)

class Engines:
    def __init__(self, account):
        self.account = account
        self.account_id = account.id
        self._connection = None
        self._db_connection = None
        self._pg_connection = None
    
    @property
    def connection(self):
        if self._connection is None:
            self._connection = sqlite3.connect(DISCOUNT_DB(self.account_id))
        return self._connection
    @property
    def cursor(self):
        return self.connection.cursor()
    @property
    def db_connection(self):
        if self._db_connection is None:
            database = Databases().get_database(self.account_id)
            self._db_connection = database.connect()
        return self._db_connection
    @property
    def db_cursor(self):
        return self.db_connection.cursor()
    @property
    def pg_connection(self):
        if self._pg_connection is None:
            self._pg_connection = Postgres.connect(self.account_id)
        return self._pg_connection

from manage_utils.database_patch import корректировка_даты_активации
from manage_utils.actions_patch import общий_список_всех_акций

ACTIONS = [
    ['общий список свех акций', общий_список_всех_акций],
    ['корректировка_даты_активации', корректировка_даты_активации]
]

if __name__ == "__main__":
    c = Console('discount')
    account_alias = c.input('Учетная запись')
    account = find_account(account_alias)
    if account is None:
        c.error(f'Учетная запись "{account_alias}" не найдена')
    engines = Engines(account)
    count = 0
    print()
    for NAME, PROC in ACTIONS:
        count += 1
        print(f'{count:3} {NAME}')
    print()
    i = c.input('Операция')
    try:
        ACTION = ACTIONS[int(i)-1]
        print(ACTION[0])
    except:
        c.error('Неправильный выбор')
    ACTION[1](c, engines)



