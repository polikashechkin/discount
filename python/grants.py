from domino.core import log
from domino.postgres import Postgres
from domino.tables.postgres.grant import Grant
from settings import GRANT_MODULE_ID

POSTGRES = Postgres.Pool()

class Grants:

    module_id = GRANT_MODULE_ID

    SYSADMIN            = 1
    MANAGER             = 2
    ASSISTANT           = 20
    OPERATOR            = 4

    USER                = 0
    BOSS                = 2
    CARD_MANAGER        = 5
    DS_MANAGER          = 100 
    DS_ASSISTANT        = 101
    DS_WATCHING         = 102

    @staticmethod
    def all_grants():
        return [
            Grant.SYSADMIN,
            Grant.BOSS,
            Grant.ASSISTANT,
            Grant.OPERATOR,
            Grant.CARD_MANAGER,
            Grant.DS_MANAGER,
            Grant.DS_ASSISTANT,
            Grant.DS_WATCHING
        ]
    
    @staticmethod
    def name(grant_id):
        name = f'{grant_id}'
        if grant_id == Grants.USER:
            name = 'ПОЛЬЗОВАТЕЛЬ'
        elif grant_id == Grants.SYSADMIN:
            name = 'СИСТЕМНЫЙ АДМИНИСТРАТОР'
        elif grant_id == Grants.BOSS:
            name = 'РУКОВОДИТЕЛЬ'
        elif grant_id == Grants.ASSISTANT:
            name = 'ПОМОШНИК РУКОВОДИТЕЛЯ'
        elif grant_id == Grants.OPERATOR:
            name = 'ОПЕРАТОР'
        elif grant_id == Grants.CARD_MANAGER:
            name = 'ОТВЕТСТВЕННЫЙ ЗА ВЫПУСК КАРТ'
        elif grant_id == Grants.DS_MANAGER:
            name = 'МЕНЕДЖЕР ДИСКОНТНОЙ СХЕМЫ'
        elif grant_id == Grants.DS_ASSISTANT:
            name = 'ПОМОШНИК МЕНЕДЖЕРА ДИСКОНТНОЙ СХЕМЫ'
        elif grant_id == Grants.DS_WATCHING:
            name = 'СМОТРЯЩИЙ ДИСКОНТНОЙ СХЕМЫ'
        return name

    @staticmethod
    def full_name(grant_id, object_id='', get_object_name = None):
        name = Grants.name(grant_id)
        if object_id:
            if get_object_name is not None:
                return f'{name} "{get_object_name(object_id)}"'
            else:
                return f'{name} "{object_id}"'
        else:
            return name

    def __init__(self, account_id, user_id):
        postgres = POSTGRES.session(account_id)
        self.user_id = user_id
        self.__load(postgres)
        #log.debug(f'{self.grants}')
    
    def __load(self, postgres):
        self.grants = {}
        for grant_id, object_id in postgres.query(Grant.grant_id, Grant.object_id)\
            .filter(Grant.user_id == self.user_id)\
            .filter(Grant.module_id == Grants.module_id):
            grant = self.grants.get(grant_id)
            if grant is None:
                grant = set()
                self.grants[grant_id] = grant
            if object_id:
                grant.add(object_id)

    def __contains__(self, item):  
        if isinstance(item, (tuple, list)):
            for i in item:
                if i in self.grants:
                    return True
            return False
        else:
            return item in self.grants

    def match(self, grant_id, object_id = ''):
        if not object_id:
            object_id = ''
        else:
            object_id = str(object_id)
        match = False
        grant = self.grants.get(grant_id)
        if grant is not None:
            if not object_id:
                match = True
            else:
                match = object_id in grant
        #log.debug(f'match({TYPE}, {OBJECT}) = {match}')
        return match
    
    def get_description(self, get_object_name = None):
        description = []
        for grant_id, objects in self.grants.items():
            if len(objects) == 0:
                description.append(Grants.name(grant_id))
            else:
                for object_id in objects:
                    description.append(Grants.full_name(grant_id, object_id, get_object_name))
        return ', '.join(description)

    @staticmethod
    def empty(postgres):
        grant = postgres.query(Grant).filter(Grant.module_id == GRANT_MODULE_ID).limit(1).first()
        return grant is None

    @staticmethod
    def drop_grants(postgres):
        postgres.query(Grant).filter(Grant.module_id == GRANT_MODULE_ID).delete()

    @staticmethod
    def _granted(postgres, module_id, user_id, grant_id, object_id = ''):
        grant = postgres.query(Grant).filter(Grant.module_id == GRANT_MODULE_ID, Grant.grant_id==grant_id, Grant.object_id == object_id)\
            .first()
        return grant is not None

    def remove_grant(self, postgres, user_id, grant_id, object_id = ''):
        query = postgres.query(Grant).filter(Grant.module_id == GRANT_MODULE_ID, Grant.user_id == user_id, Grant.grant_id == grant_id)
        if object_id:
            query = query.filter(Grant.object_id == object_id)
        query.delete()
        self.__load(postgres)

    def add_grant(self, postgres, user_id, grant_id, object_id = ''):
        grant = Grant(module_id = GRANT_MODULE_ID, user_id = user_id, grant_id = grant_id, object_id = object_id)
        postgres.add(grant)
        self.__load(postgres)

    @staticmethod
    def add_grants(postgres, user_id, grants = None, object_id=''):
        if grants is None:
            grant = Grant(module_id = GRANT_MODULE_ID, user_id = user_id, grant_id = Grant.USER, object_id = object_id)
            postgres.add(grant)
        else:
            for grant_id in grants:
                grant = Grant(module_id = GRANT_MODULE_ID, user_id = user_id, grant_id = grant_id, object_id=object_id)
                postgres.add(grant)

    @staticmethod
    def remove_grants(postgres, user_id, grants = None, object_id=''):
        if grants is None:
            postgres.query(Grant).filter(Grant.module_id == GRANT_MODULE_ID, Grant.user_id == user_id)\
                .delete()
        else:
            for grant_id in grants:
                postgres.query(Grant).filter(Grant.module_id == GRANT_MODULE_ID, Grant.user_id == user_id)\
                    .filter(Grant.grant_id == grant_id, Grant.object_id == object_id)\
                    .delete()

    @staticmethod
    def remove_object(postgres, object_id):
        postgres.query(Grant).filter(Grant.module_id == GRANT_MODULE_ID, Grant.object_id == object_id)\
            .delete()
