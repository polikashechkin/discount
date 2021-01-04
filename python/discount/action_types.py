import os, sys, json, importlib
from domino.core import log

class ActionType:
    def __init__(self, id, module):
        self.id = id
        self.module = module

    @property
    def IS_AVAILABLE(self):
        try:
            return self.module.IS_AVAILABLE
        except:
            return True

    @property
    def SUPPLEMENT(self):
        try:
            return self.module.SUPPLEMENT
        except:
            return False

    @property
    def FIXED_PRICE(self):
        try:
            return self.module.FIXED_PRICE
        except:
            return False

    @property
    def CLASS(self):
        try:
            return self.module.CLASS
        except:
            return 0
    
    @property
    def PERCENT(self):
        try:
            return self.module.PERCENT
        except:
            return False

    @property
    def CARD(self):
        try:
            return self.module.CARD
        except:
            return False

    @property
    def DESCRIPTION(self):
        return self.module.DESCRIPTION
    @property
    def ABOUT(self):
        return self.module.ABOUT

    def is_available(self):
        return self.IS_AVAILABLE
        
    @property
    def about(self):
        try:
            return self.module.ABOUT
        except:
            return ''
    
    @property
    def hasCalculator(self):
        try:
            return hasattr(self.module, 'Calculator')
        except:
            return False

    @property
    def hasAcceptor(self):
        try:
            return hasattr(self.module, 'Acceptor')
        except:
            return False

    def description(self):
        return self.module.DESCRIPTION

    def calc(self, check):
        return self.module.calc(check)

    def Calculator(self, application, cursor, action, LOG, SQLITE):
        return self.module.Calculator(application, cursor, action, LOG, SQLITE)

    def Acceptor(self, application, cursor, action, LOG, SQLITE):
        return self.module.Acceptor(application, cursor, action, LOG, SQLITE)

    def __str__(self):
        return f"ActionType({self.id})"

class ActionTypes:
    def __init__(self, application):
        self._types = {}
        try:
            for id in os.listdir(os.path.join(application.python_path, 'action_types')):
                if id.endswith('.py') and id.startswith('A'):
                    try:
                        id = id.replace('.py', '')
                        #log.debug(f'load {name}')
                        module = importlib.import_module(f'action_types.{id}')
                        action_type = ActionType(id, module)
                        self._types[action_type.id] = action_type
                    except:
                        log.exception(f'action_type("{id}")')
                    #log.debug(f'action_types {self.action_types}')
        except:
            log.exception(f'action_types()')

    def __getitem__(self, name):
        return self._types.get(name)

    def types(self):
        return self._types.values()

