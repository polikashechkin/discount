import os, json
from domino.core import log, DOMINO_ROOT, Version

class Module:
    def __init__(self, module_id):
        self.id = module_id
        info_file = Module.__get_info_file(module_id)
        with open(info_file) as f:
            self.info = json.load(f)
        self.version = Version.parse(self.info.get('version'))
        self.name = self.info.get('short_name')
        #grants_file = Module.__get_grants_file(module_id)
        #if os.path.isfile(grants_file):
        #    with open(grants_file) as f:
        #        self.grants = json.load(f)
        #else:
        #    self.grants = None
        settings_json = Module.__get_settings_file(module_id)
        if os.path.isfile(settings_json):
            with open(settings_json) as f:
                self.settings = json.load(f)
        else:
            self.settings = {}

    def __repr__(self):
        return f'<Module(id={self.id}, version={self.version})>'
    
    @property
    def grant_module_id(self):
        return self.settings.get('grant_module_id', self.id)
        #if self.grants:
        #    module_id = self.grants.get('module_id')
        #    return module_id if module_id else self.id
        #else:
        #    return self.id
    @property
    def is_public(self):
        #return self.grants is None
        return False
    @property
    def start_page(self):
        return self.settings.get('start_page', '/web')

    @property
    def is_login(self):
        run_type = self.info.get('run_type')
        return run_type and run_type == 'login'
    @property
    def external_grants(self):
        return self.grant_module_id != self.id
    
    @staticmethod
    def __get_info_file(module_id):
        return os.path.join(DOMINO_ROOT, 'products', module_id, 'active', 'info.json')
    #@staticmethod
    #def __get_grants_file(module_id):
    #    return os.path.join(DOMINO_ROOT, 'products', module_id, 'active', 'grants.json')
    @staticmethod
    def __get_settings_file(module_id):
        return os.path.join(DOMINO_ROOT, 'products', module_id, 'active', 'settings.json')

    @staticmethod
    def get(module_id):
        info_file = Module.__get_info_file(module_id)
        if not os.path.isfile(info_file):
            return None
        else:
            return Module(module_id)

