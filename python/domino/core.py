import os, sys
import json
import shutil
import requests
import datetime
import subprocess
import pickle
import logging
import uuid
import arrow
import re
import platform

if platform.system() == 'Windows':
    DOMINO_ROOT = 'C:\\DOMINO'
    IS_WINDOWS = True
    IS_LINUX = False
else:   
    DOMINO_ROOT = '/DOMINO'
    IS_WINDOWS = False
    IS_LINUX = True

DOMINO_LOG = os.path.join(DOMINO_ROOT, 'log')
os.makedirs(DOMINO_LOG, exist_ok=True)

SERVER_CONFIG_FILE = '/DOMINO/domino.config.info.json'
INSTALLED_PRODUCTS = '/DOMINO/products'
STORE_PRODUCTS = '/DOMINO/public/products'
PUBLIC_PRODUCTS = '/DOMINO/public/products'
JOBS = '/DOMINO/jobs'
JOB_REPORTS = '/DOMINO/jobs.reports'

log = logging.getLogger('domino')
hdlr = logging.FileHandler(os.path.join(DOMINO_LOG, 'domino.log'))
formatter = logging.Formatter('%(asctime)s %(levelname)s %(module)s %(message)s')
#formatter = logging.Formatter('%(asctime)s %(levelname)s %(module)s.%(funcName)s %(message)s')
hdlr.setFormatter(formatter)
log.addHandler(hdlr) 
#log.setLevel(logging.INFO)
log.setLevel(logging.DEBUG)

start_log = logging.getLogger('start')
start_hdlr = logging.FileHandler(os.path.join(DOMINO_LOG, 'start.log'))
start_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
#formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
start_hdlr.setFormatter(start_formatter)
start_log.addHandler(start_hdlr) 
#log.setLevel(logging.INFO)
start_log.setLevel(logging.DEBUG)

def RawToHex(r):
    if isinstance(r, str):
        return r
    else:
        return r.hex().upper() if r else None

def HexToRaw(h):
    return bytes.fromhex(h) if h else None


def create_uuid():
    return str(uuid.uuid4())
def create_guid():
    return str(uuid.uuid4())

def str_to_time(time_string):
    try:
        hour, minute, second = time_string.split(':')
        return datetime.time(hour = int(hour), minute=int(minute), second=int(second))
    except:
        return None
    
class Version:
    def __init__(self, major, minor, draft, build = 10000):
        self.NONE_RELEASE = 10000
        self.n = [int(major), int(minor), int(draft), int(build)]
        self._make_id()

    def _make_id(self):
        if self.n[3] == 10000:
            self.id = '{0}.{1}.{2}'.format(self.n[0], self.n[1], self.n[2])
        else:
            self.id = '{0}.{1}.{2}.{3}'.format(self.n[0], self.n[1], self.n[2], self.n[3])
        
    @property
    def is_draft(self):
        return self.n[3] == self.NONE_RELEASE
    def is_draft_of(self, other):
        return (self.compare(other, 3) == 0) and (self.n[3] == self.NONE_RELEASE)
    def draft(self):
        return Version(self.n[0], self.n[1], self.n[2])

    def next(self):
        if self.n[3] == self.NONE_RELEASE:
            return Version(self.n[0], self.n[1], self.n[2], 0)
        else:
            return Version(self.n[0], self.n[1], self.n[2], self.n[3] + 1)
    @staticmethod
    def parse(s):
        try:
            parts = str(s).split('.')
            l = len(parts)
            if l == 3:
                return Version(parts[0], parts[1], parts[2])
            elif l == 4:
                return Version(parts[0], parts[1], parts[2], parts[3])
            else:
                return None
        except:
            return None

    @staticmethod
    def versions_dump(versions):
        versions_id = []
        for version in versions:
            versions_id.append(version.id)
        return json.dumps(versions_id)

    def compare(self, other, len = 4):
        for i in range(len):
            if self.n[i] < other.n[i]:
                return -1
            elif self.n[i] > other.n[i]:
                return 1
        return 0
        
    def __eq__(self, other): # x == y вызывает x.__eq__(y).
        return self.compare(other) == 0
    def __ne__(self, other): # x != y вызывает x.__ne__(y)
        return self.compare(other) != 0
    def __lt__(self, other): # x < y вызывает x.__lt__(y).
        return self.compare(other) < 0 
    def __le__(self, other): # x ≤ y вызывает x.__le__(y).
        return self.compare(other) <= 0 
    def __gt__(self, other): #  x > y вызывает x.__gt__(y).
        return self.compare(other) > 0
    def __ge__(self, other): # x ≥ y вызывает x.__ge__(y)
        return self.compare(other) >= 0 
    def __hash__(self):
        return self.id.__hash__()

    def __str__(self):
        return self.id

class ProductInfo:

    osComputer = 'server'
    osServer = 'computer'
    osUser = 'user'
    osMobile = 'mobile'
    osProject = 'project'

    def __init__(self, js = {}):
        self.js = js

    @property
    def id(self):
        return self.js.get('id')

    def __str__(self):
        return self.id

    def dumps(self):
        return json.dumps(self.js)

    def dump(self, f):
        json.dump(self.js, f)

    @staticmethod
    def loads(s):
        return ProductInfo(json.loads(s))

    @staticmethod
    def load(f):
        return ProductInfo(json.load(f))

class VersionInfo:
    def __init__(self, js = {}):
        self.js = js

    @staticmethod
    def loads(s):
        return VersionInfo(json.loads(s))

    @staticmethod
    def load(f):
        return VersionInfo(json.load(f))

    def dumps(self):
        return json.dumps(self.js)

    def dump(self, f):
        return json.dump(self.js, f)
    
    def write(self, folder):
        file = os.path.join(folder, 'info.json')
        with open(file, 'w') as f:
            json.dump(self.js, f, ensure_ascii=False)

    @staticmethod
    def read(self, folder):
        file = os.path.join(folder, 'info.json')
        with open(file, 'r') as f:
            return VersionInfo(json.load(f))

    @property
    def version(self):
        return Version.parse(self.js.get('version'))
    @version.setter
    def version(self, value):
        self.js['version'] = str(value)

    @property
    def product(self):
        return self.js.get('product')
    @product.setter
    def product(self, value):
        self.js['product'] = str(value)

    @property
    def id(self):
        return self.js.get('version')

    @property
    def description(self):
        return self.js.get('description', '')

    @property
    def creation_time(self):
        return self.js.get('creation_date', '')

    @property
    def creation_date(self):
        return self.js.get('creation_date', '')
    
    def __getitem__(self, name):
        return self.js.get(str(name))

    def __setitem__(self, name, value):
        self.js[str(name)] = value

    def __str__(self):
        return '{0} от {1}'.format(self.version, self.creation_time)

class Config:
    def __init__(self, id):
        self.id = str(id)
        self.js = {'id' : id, 'products' : {} }

    @property
    def products(self):
        return self.js['products']

    def _next_pos(self):
        max = 0
        for pos in self.js['products'].keys():
            i = int(pos)
            if max < i:
                max = i
        return str(max + 1)

    def get_product(self, product_id, create=False):
        for product in self.js['products'].values():
            if product['id'] == str(product_id):
                return product
        if create:
            product = {'product' : product_id}
            self.js['products'][self._next_pos()] = product
            return product
        else:
            return None
        
    def get_version(self, product_id):
        product = self.get_product(product_id)
        if product is not None:
            return Version.parse(product.get('version'))
        else:
            return None

    def set_version(self, product_id, version):
        product = self.get_product(product_id, create=True)
        if product is not None:
            product['version'] = str(version)
        else:
            return None

    def save(self):
        os.makedirs('/DOMINO/configs', exist_ok=True)
        file = os.path.join('/DOMINO/configs', self.id + ".json")
        with open(file, 'w') as f:
            json.dump(self.js, f)

    @staticmethod
    def get(id):
        config = None
        file = os.path.join('/DOMINO/configs', id + ".json")
        if os.path.isfile(file):
            with open(file, 'r') as f:
                js = json.load(f)
            config = Config(id)
            config.js = js
        return config

    def __str__(self):
        return self.id

class ServerConfig:
    ''' 
    Конфигурация сервера
    Хранится в файле /DOMINO/domino.config.info.ison : 
        {
            server_version : <версия сервера>
            password : <пароль доступа к серверу>
            products : [
                {"name":<идентификатор продукта>, "version":<рабочая версия>, "history":<список предыдущих версий>}
            ]
        }
    Для каждого продукта существует одна запись. В стуктуре этого не отражено по историческим причинам
    '''
    def __init__(self):
        if not os.path.isfile(SERVER_CONFIG_FILE):
            self.js = {}
        else:
            with open(SERVER_CONFIG_FILE) as f:
                self.js = json.load(f)

        self.products = self.js.get('products')
        if self.products is None:
            self.products = []
            self.js['products'] = self.products

    def save(self):
        with open(SERVER_CONFIG_FILE, 'w') as f:
            json.dump(self.js, f)

    @property
    def ac_domino_ru(self):
        return self.js.get('ac_domino_ru', 'ac.domino.ru')
    @ac_domino_ru.setter
    def ac_domino_ru(self, value):
        self.js['ac_domino_ru'] = value
        self.save()

    @property
    def account_id(self):
        return self.js.get('account_id')
    @account_id.setter
    def account_id(self, value):
        self.js['account_id'] = value
        self.save()
        
    def get_products(self):
        products = []
        for product in self.products:
            products.append(product['name'])
        return products

    def get_product(self, product, create=False):
        for j_product in self.products:
            if j_product['name'] == str(product):
                return j_product
        if create:
            j_product = {'name':str(product)}
            self.products.append(j_product)
            return j_product
        else:
            return None

    def get_version(self, product):
        j_product = self.get_product(product)
        if j_product is not None:
            return Version.parse(j_product.get('version'))
        else:
            return None

    def get_history_version(self, product):
        j_product = self.get_product(str(product))
        if j_product is not None:
            return Version.parse(j_product.get('history'))
        else:
            return None

    def set_version(self, product, version):
        j_product = self.get_product(product, create=True)
        j_product['history'] = j_product.get('version')
        j_product['version'] = str(version)
        self.save()
        log.info("%s %s активирована", str(product), str(version))

class Server:
    @staticmethod
    def product_folder(product):
        return os.path.join(INSTALLED_PRODUCTS, str(product))

    @staticmethod
    def version_folder(product, version):
        return os.path.join(INSTALLED_PRODUCTS, str(product), str(version))

    @staticmethod
    def get_products():
        products = []
        for product_id in os.listdir(INSTALLED_PRODUCTS):
            if os.path.isdir(os.path.join(INSTALLED_PRODUCTS, product_id)):
                products.append(product_id)
        return products

    @staticmethod
    def version_exists(product, version):
        return os.path.exists(Server.version_folder(product, version))

    @staticmethod
    def get_versions(product):
        versions = []
        dir = Server.product_folder(product)
        if os.path.isdir(dir):
            for version_id in os.listdir(dir):
                version = Version.parse(version_id)
                if version is not None:
                    versions.append(version)
        return versions

    @staticmethod
    def get_drafts(product):
        drafts = []
        for version in Server.get_versions(product):
            if version.is_draft:
                drafts.append(version)
        return drafts

    @staticmethod
    def get_versions_of_draft(product, draft):
        versions = []
        if draft is not None and draft.is_draft:
            for version in Server.get_versions(product):
                if version.is_draft: continue
                if not draft.is_draft_of(version): continue
                versions.append(version)
        return versions

    @staticmethod
    def get_latest_version_of_draft(product, draft):
        return max(Server.get_versions_of_draft(product, draft), default = None)

    @staticmethod
    def get_latest_version(product):
        return max(Server.get_versions(product), default = None)

    @staticmethod
    def get_version_info(product, version):
        info_file = os.path.join(Server.version_folder(product, version), 'info.json')
        if os.path.isfile(info_file):
            with open(info_file, "r") as f:
                return VersionInfo(json.load(f))
        return None

    @staticmethod
    def reload_server():
        resp = requests.get('http://localhost/domino/nginx/refresh.lua?sk=dev',  verify=False)
        if resp.status_code != 200:
            raise BaseException('Ошибка перезагрузки сервера')
        log.info("Сервер перезагружен")

    @staticmethod
    def install(product, version, distro_file):
        if not Server.version_exists(product, version):
            version_folder = Server.version_folder(product, version)
            os.makedirs(version_folder, exist_ok=True)
            shutil.unpack_archive(distro_file, extract_dir=version_folder)
    @staticmethod
    def get_config():
        return ServerConfig()

class Time:
    def __init__(self, value = None):
        self.__value = None
        if value is not None:
            self.fromstring(value)

    def time(self):
        return self.__value.time() if self.__value is not None else datetime.time(0,0)

    @property
    def undefined(self):
        return self.__value is None
    @property
    def defined(self):
        return self.__value is not None
    def tostring(self):
        return self.__value.format('HH:mm') if self.__value is not None else ''
    def __str__(self):
        return self.tostring()
    def fromstring(self, value):
        try:
            self.__value = arrow.get(value, 'HH:mm')
        except:
            self.__value = None
            
class Bool:
    def __init__(self, value=None):
        self.__value = False
        self.assing(value)
    def assing(self, value):
        try:
            if isinstance(value, bool):
                self.__value = value
            elif isinstance(value, str):
                self.fromstring(value)
            else:
                self.__value = False
        except:
            self.__value = False
    def __bool__(self):
        return self.__value
    def tostring(self):
        return "1" if self.__value else "0"
    def __str__(self):
        return self.tostring()
    def fromstring(self, value):
        try:
            self.__value = value == '1'
        except:
            self.__value = False


