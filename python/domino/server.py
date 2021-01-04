import os, sys
import json
import shutil
import requests
import datetime
import pickle

from domino.core import log, Version, VersionInfo, create_guid

SERVER_CONFIG_FILE = '/DOMINO/domino.config.info.json'
INSTALLED_PRODUCTS = '/DOMINO/products'
SERVER_GUID_FILE_PATH = '/etc/domino/guid'

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

class ServerInfo:
    def __init__(self):
        self.name = Server.name()
        self.guid = GUID

class Server:
    def __init__(self, domain_name):
        self.domain_name = domain_name
        self.url = ''
        self.status_code = 0
        self.error = ''
    
    def get(self, proc, params = {}, product_id = 'domino'):
        self.error = ''
        url = f'https://{self.domain_name}/{product_id}/active/python/{proc}'
        r = requests.get(url, params, stream=True)
        self.url = r.url
        self.status_code = r.status_code
        if r.status_code != 200:
            self.error = r.text
            #print(f'{r.status_code} : {r.url}')
            return None
        return pickle.loads(r.raw.read())
    
    @staticmethod
    def info():
        return ServerInfo()

    @staticmethod
    def name():
        return os.uname()[1]

    @staticmethod
    def guid():
        if os.path.isfile(SERVER_GUID_FILE_PATH):
            with open(SERVER_GUID_FILE_PATH) as f:
                return f.read().strip()
        else:
            os.makedirs(os.path.dirname(SERVER_GUID_FILE_PATH), exist_ok=True)
            guid = create_guid()
            with open(SERVER_GUID_FILE_PATH, "w") as f:
                f.write(guid)
            return guid

    @staticmethod
    def reg_server():
        domain_name = Server.get_config().ac_domino_ru
        return Server(domain_name)

    @staticmethod
    def get_active_version(product_id):
        config = Server.get_config()
        return config.get_version(product_id)

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
    def get_config():
        return ServerConfig()
  
GUID = Server.guid()
