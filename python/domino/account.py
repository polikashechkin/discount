import os
import json
import requests
import sqlite3
from domino.core import log, Server, create_guid, Version, DOMINO_ROOT

ACCOUNTS = os.path.join(DOMINO_ROOT, 'accounts')
DEPTS_DB = os.path.join(DOMINO_ROOT,'data','account.db')
ACCOUNTS_DB = DEPTS_DB
MASTER_DEPT_CODE = '.'
 
def create_structure():
    os.makedirs('/DOMINO/data', exist_ok=True)
    with sqlite3.connect(DEPTS_DB) as conn:
        conn.executescript('''
        create table if not exists depts 
        (
            guid not null primary key,
            account_id  not null, 
            type        not null,
            code        not null,
            status      integer default(0), 
            parent, 
            uid, 
            name        default(''), 
            description default(''), 
            address     default(''), 
            access_time,
            info        blob, 
            CONSTRAINT code_unique UNIQUE (account_id, type, code)
        );
        '''
        )

def get_accounts_info():
    accounts = []
    for account_id in os.listdir(ACCOUNTS):
        a = AccountInfo.read(os.path.join(ACCOUNTS, account_id))
        if a is not None:
            accounts.append(a)
    return accounts 

class AccountConfigProduct:
    def __init__(self, id, version):
        self.id = id
        self.version = Version.parse(version) if version is not None else None

class AccountConfig:
    def __init__(self):
        self._products = {}
    def add(self, product_id, version = None):
        product = AccountConfigProduct(product_id, version)
        self._products[product.id] = product
    def remove(self, product_id):
        del self._products[product_id]
    def get(self, product_id):
        return self._products.get(product_id)
    @property
    def products(self):
        return self._products.values()

    @staticmethod
    def load(account):
        config = AccountConfig()
        products = account.info.js.get('products')
        if products is not None:
            for product in products:
                product_id = product.get('id')
                if product_id is not None:
                    config._products[product_id] = AccountConfigProduct(product_id, product.get('version'))
        return config

    @staticmethod
    def save(config, account):
        products_js = []
        for product in config.products:
            if product.version is not None:
                product_js = {'id': product.id, 'version':str(product.version) }
            else:
                product_js = {'id':product.id, 'version' : 'active'}
            products_js.append(product_js)
        account.info.js['products'] = products_js
        account.info.write(account.folder)
        
class AccountInfo:
    def __init__(self, js = {}):
        self.js = js
    
    def get(self, name, default = None):
        return self.js.get(name, default)
    
    @property
    def id(self):
        return self.js.get('company')

    @property
    def account_id(self):
        return self.js.get('company')

    @property
    def alias(self):
        return self.js.get('owner')

    @property
    def password(self):
        credentials = self.js.get("credentials")
        if credentials is not None:
            return credentials.get('ac')
        else:
            return None

    @property
    def name(self):
        return self.js.get('description', self.id)

    @property
    def description(self):
        return self.js.get('description')
    
    @property
    def config_id(self):
        return self.js.get('config')
    
    def write(self, folder):
        file = os.path.join(folder, 'info.json')
        with open(file, 'w') as f:
           json.dump(self.js, f, ensure_ascii=False, indent=3)
 
    @staticmethod
    def read(folder):
        try:
            file = os.path.join(folder, 'info.json')
            with open(file, 'r') as f:
                return AccountInfo(json.load(f))
        except:
            return AccountInfo()

    @staticmethod
    def create(account_id, description = None):
        folder = os.path.join(ACCOUNTS, account_id)
        info = AccountInfo.read(folder)
        if info is not None:
            return info
        info = AccountInfo()
        info.js['company'] = account_id
        info.js['config'] = account_id
        if description is not None:
            info.js['description'] = description
        info.write(folder)
        return info

    @staticmethod
    def load(account_id, ac_domino_ru):
        try:
            query = f'https://{ac_domino_ru}/domino/active/python/accounts.get_info'
            r = requests.get(query, {'account_id':account_id})
            #print(r.url)
            if r.status_code == 200:
                return AccountInfo(r.json())
            else:
                return None
        except:
            log.exception(f'AccoutInfo.load({account_id}, {ac_domino_ru})')
            return None

    @staticmethod
    def exists(account_id):
        return os.path.isfile(os.path.join(ACCOUNTS, account_id, 'info.json'))

class Dept:
    SERVER_GUID = 'server_guid'
    DATABASE_URI = 'database_uri'
    def  __init__(self, account_id, guid = None, code='', name='', status = 0, uid = None, address = '', info = {}):
        self.account_id = account_id
        self.guid = guid if guid is not None else create_guid()
        self.code = code 
        self.name = name
        self.status = status
        self.uid = uid
        self.address = address
        if type(info) == dict:
            self.info = info
        else:
            try:
                self.info = json.loads(info)
            except:
                self.info = {}
    def __str__(self):
        return f'Dept({self.account_id},{self.guid})'
    @property
    def is_account_dept(self):
        return self.code is not None and self.code == MASTER_DEPT_CODE

    @property
    def enabled(self):
        return self.status >= 0 
    @property
    def is_maindept(self):
        return self.code == MASTER_DEPT_CODE

    def get_param(self, name):
        return self.info.get(str(name))

    def set_param(self, name, value):
        self.info[str(name)] = value

    @staticmethod
    def create(conn, dept):
        with conn:
            conn.execute('''
            insert into depts 
            (account_id, guid, code, name, status, uid, address, info, type)
            values (?,?,?,?,?,?,?,?, 'LOCATION')'''
            , [dept.account_id, dept.guid, dept.code, dept.name, 
            dept.status, dept.uid, dept.address, json.dumps(dept.info, ensure_ascii=False)])
    
    @staticmethod
    def update(conn, dept): 
        conn.execute('''
            update depts 
            set code=?, name=?, status=?, uid=?, address=?, info=?
            where account_id=? and guid=?
            ''', 
            [dept.code, dept.name, dept.status, dept.uid, dept.address, json.dumps(dept.info, ensure_ascii=False), dept.account_id, dept.guid]
        )

    @staticmethod
    def insert_or_replace(conn, dept):
        conn.execute('''
            insert or replace into depts 
            (account_id, guid, code, name, status, uid, address, info, type)
            values (?,?,?,?,?,?,?,?, 'LOCATION')
            ''', 
            [dept.account_id, dept.guid, dept.code, dept.name, dept.status, dept.uid, dept.address, json.dumps(dept.info,ensure_ascii=False)]
        )

    @staticmethod
    def findall(conn, where_clause = None, params = []):
        depts = []
        cur = conn.cursor()
        if where_clause is None:
            cur.execute(''' 
                select account_id, guid, code, name, status, uid, address, info
                from depts
                ''')
        else:
            cur.execute(f''' 
                select account_id, guid, code, name, status, uid, address, info
                from depts
                where {where_clause}
                ''', params)
        for account_id, guid, code, name, status, uid, address, info in cur:
            dept = Dept(account_id, guid, code, name, status, uid, address, info)
            depts.append(dept)
        cur.close()
        return depts

    @staticmethod
    def count(conn, where_clause = None, params = []):
        depts = []
        cur = conn.cursor()
        if where_clause is None:
            cur.execute(''' 
                select count(*)
                from depts
                ''')
        else:
            cur.execute(f''' 
                select count(*) 
                from depts
                where {where_clause}
                ''', params)
        return cur.fetchone()[0]

    @staticmethod
    def find(account_id, code):
        with sqlite3.connect(DEPTS_DB) as conn:
            cur = conn.cursor()
            cur.execute('''
                select guid, code, name, status, uid, address, info
                from depts
                where account_id=? and (guid = ? or code=?)
            '''
            , [account_id, code, code])
            r = cur.fetchone()
        if r is None:
            return None
        else:
            return Dept(account_id, r[0], r[1], r[2], r[3], r[4], r[5], r[6])
    
    @staticmethod
    def get(conn, account_id, code):
        cur = conn.cursor()
        if len(code) > 30: 
            cur.execute('''
                select guid, code, name, status, uid, address, info
                from depts
                where account_id=? and guid = ?
            ''' , [account_id, code])
        else:
            cur.execute('''
                select guid, code, name, status, uid, address, info
                from depts
                where account_id=? and code = ?
            ''' , [account_id, code])
        r = cur.fetchone()
        if r is None:
            return None
        else:
            return Dept(account_id, r[0], r[1], r[2], r[3], r[4], r[5], r[6])

    @staticmethod
    def delete(conn, account_id, guid):
        conn.execute('''
                delete from depts
                where account_id=? and guid = ?
            ''' , [account_id, guid])

class Account:
    def __init__(self, account_id):
      self.id = account_id
      self.folder = os.path.join(ACCOUNTS, self.id)
      self._info = None

    @staticmethod
    def all():
        accounts = []
        for account_id in os.listdir(ACCOUNTS):
            if os.path.isfile(os.path.join(ACCOUNTS, account_id, 'info.json')):
                accounts.append(Account(account_id))
        return accounts

    def path(self, *paths):
      path = self.folder
      for p in paths:
         path = os.path.join(path, p)
      return path
    
    def find_depts(self):
        with sqlite3.connect(DEPTS_DB) as conn:
            depts = sorted(Dept.findall(conn, "account_id=? and name != ''", [self.id]), key = lambda dept : dept.code)
        return depts
    
    def find_dept(self, code = MASTER_DEPT_CODE):
        if code is None or code.strip() == '':
            code = MASTER_DEPT_CODE
        return Dept.find(self.id, code)
    
    @staticmethod
    def create_or_update(account_info):
        account_id = account_info.account_id
        account_folder = os.path.join(f'/DOMINO/accounts/{account_id}')
        if not os.path.exists(account_folder):
            os.makedirs(account_folder, exist_ok=True)
        account_info.write(account_folder)
        return Account(account_id)

    @property
    def info(self):
      if self._info is None: 
         self._info = AccountInfo.read(self.folder)
      return self._info
    @info.setter
    def info(self, value):
        self._info = value 
        self.info.write(self.folder)
         
    def save(self):
        self.info.write(self.folder)

    def set_param(self, name, value):
        params = self.info.js.get('params')
        if params is None:
            params = {}
            self.info.js['params'] = params
        params[str(name)] = str(value)
        self.info.write(self.folder)
    def get_param(self, name):
        try:
            params = self.info.js.get('params')
            return params.get(str(name))
        except:
            return None

    def params(self):
        if self.info.js.get('params') is None:
            return []
        else:
            return self.info.js.get('params').items()

    def remove_product_param(self, product_id, key):
        try:
            params = self.info.js.get('product_params')
            product_params = params.get(str(product_id))
            del product_params[str(key)]
            self.info.write(self.folder)
        except:
            pass

    def set_product_param(self, product_id, key, value):
        params = self.info.js.get('product_params')
        if params is None:
            params = {}
            self.info.js['product_params'] = params
        product_params = params.get(str(product_id))
        if product_params is None:
            product_params = {}
            params[str(product_id)] = product_params
        product_params[str(key)] = value
        self.info.write(self.folder)

    def get_product_param(self, product_id, key):
        try:
            return self.info.js['product_params'][str(product_id)][str(key)]
        except:
            return None

    def product_params(self):
        result = []
        try:
            for product_id, p_params in self.info.js.get('product_params').items():
                for key, value in p_params.items():
                    result.append([product_id, key, value])
            return result
        except BaseException as ex:
            #log.exception(f'account.params')
            return result

    @staticmethod
    def create(account_id, description=None):
        account = find_account(account_id)
        if account is not None:
            return account
        if not account_id.isdigit():
            raise Exception(f'Недопустимый идентификатор учетной записи "{account_id}"')
        folder = os.path.join(ACCOUNTS, account_id)
        os.mkdir(folder)
        AccountInfo.create(account_id)
        return Account(account_id)

    @staticmethod
    def findall(query = None):
        accounts = []
        for account_id in os.listdir(ACCOUNTS):
            if account_id.isdigit():
                accounts.append(Account(account_id))
        return accounts

    @property
    def alias(self):
        return self.info.js.get('owner')
    @alias.setter
    def alias(self,value):
        self.info.js['owner'] = value
        self.info.write(self.folder)

    @property
    def password(self):
        return self.info.password
    @password.setter
    def password(self, value):
        credentials = self.info.js.get("credentials")
        if credentials is not None:
            credentials['ac'] = value
        else:
            self.info.js["credentials"] = {'ac':value}
        self.info.write(self.folder)
            
    @property
    def description(self):
        try:
            return self.info.description
        except:
            return ''
    @description.setter
    def description(self, value):
        self.info.js['description'] = value

    @property
    def config_id(self):
        try:
            return self.info.js['config']['name']
        except:
            return None

    @config_id.setter
    def config_id(self, value):
        self.info.js['config'] = {'name': value}
        self.info.write(self.folder)

    def get_database_uri(self):
        file = os.path.join(self.folder, 'resources', 'database.json')
        if not os.path.isfile(file):
            return None
        with open(file,'r') as f: js = json.load(f)
        return js['uri']

    def set_database_uri(self, uri):
        file = os.path.join(self.folder, 'resources', 'database.json')
        with open(file,'r') as f: js = json.load(f)
        js['uri'] = uri
        with open(file,'w') as f: json.dump(js, f)

    def __str__(self):
        return self.id

def find_account(query):
   account_id = find_account_id(query)
   if account_id is not None:
      return Account(account_id)
   else:
      return None

def path(account_id, *paths):
   path = os.path.join(ACCOUNTS, account_id)
   for p in paths:
      path = os.path.join(path, p)
   return path

def find_account_id(query):
   if query is None: return None
   if os.path.isdir(os.path.join(ACCOUNTS, query)):
      return query
   for account_id in os.listdir(ACCOUNTS):
      file = os.path.join(ACCOUNTS, account_id, 'info.json')
      if os.path.isfile(file):
         with open(file, 'r') as f:
            info = json.load(f)
         owner = info.get('owner')
         if (owner is not None) and (owner == query):
            return account_id
   return None

class Device:
    def __init__(self, account_id=None, type=None, key=None):
        self.rowid = None
        self.account_id = account_id
        self.type = type
        self.key = key
        self.name = None
        self._status = 0
        self.description = None
        self.info = None
    @property 
    def status(self):
        return self._status
    @status.setter
    def status(self, value):
        try:
            self._status= int(value)
        except:
            self.status = 0
    @property 
    def info_dump(self):
        return json.dumps(self.info)
    @info_dump.setter
    def info_dump(self, value):
        try:
            self.info = json.loads(value)
        except:
            self.info = {}

    @staticmethod 
    def _get(cur, where, params):
        cur.execute(f'''
        select rowid, account_id, type, key, status, name, description, info from devices 
        where {where}
        ''', params)
        r = cur.fetchone()
        if r is None:
            return None
        else:
            d = Device()
            d.rowid, d.account_id, d.type, d.key, d.status, d.name, d.description, d.info_dump = r
            return d

    @staticmethod 
    def get_by_key(cur, account_id, type, key):
        return Device._get(cur, 'account_id=? and type=? and key=?', [account_id, type, key])

    @staticmethod 
    def get(cur, rowid):
        return Device._get(cur, 'rowid=?', [int(rowid)])

    @staticmethod
    def create(cur, account_id, type, key):
        cur.execute('''
        insert into devices (account_id, type, key) 
        values (?, ?, ?)
        ''', [account_id, type, key])
        d = Device(account_id, type, key)
        d.rowid = cur.lastrowid
        return d

    def update(self, cur):
        cur.execute('''
        update devices set status=?, name=?, description=?, info=? 
        where rowid=?
        ''', [self.status, self.name, self.description, self.info_dump, self.rowid])
