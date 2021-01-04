from flask import make_response
import os, json, redis, sys, importlib, time, platform
from domino.core import Version, log as LOG 
from domino.account import find_account, Dept
from domino.databases.oracle import Databases, domino_login
from domino.page import Page
from domino.databases.postgres import Postgres
from domino.tables.postgres.request_log import RequestLog
#import xml.etree.cElementTree as ET
from lxml import etree as ET
             
def DEBUG(msg):
    #LOG.debug(msg)
    pass
          
def make_download_file_responce(file, file_name=None):
    #log.debug(f'{self}.download("{file}", file_name="{file_name}")')
    if not os.path.isfile(file):
        return f'File "{file}" not found','404 File "{file}" not found'
    if file_name is None:
        file_name = os.path.basename(file)
    with open(file, 'rb') as f:
        response  = make_response(f.read())
    response.headers['Content-Type'] = 'application/octet-stream'
    #response.headers['Content-Description'] = 'File Transfer'
    response.headers['Content-Disposition'] = 'attachment; filename={0}'.format(file_name)
    response.headers['Content-Length'] = os.path.getsize(file)
    return response
     
def make_show_file_responce(file):
    #log.debug(f'{self}.download("{file}", file_name="{file_name}")')
    if not os.path.isfile(file):
        return f'File "{file}" not found','404 File "{file}" not found'
    with open(file, 'rb') as f:
        response  = make_response(f.read())
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    #response.headers['Content-Description'] = 'File Transfer'
    response.headers['Content-Disposition'] = 'inline'
    response.headers['Content-Length'] = os.path.getsize(file)
    return response

class Response:
    def __init__(self, application, request):
        self.application = application
        self.request = request
        self.SESSION_KEY = self.request.args.get('sk')

    def make_response(self, name):
        f = getattr(self, name, None)
        return f() if f is not None else None
    
    def __getattr__(self, name):
        if name == 'SESSION_INFO':
            r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
            if self.SESSION_KEY is not None:
                self.SESSION_INFO = r.hgetall(self.SESSION_KEY)
            else:
                self.SESSION_INFO = None
            return self.SESSION_INFO
        elif name == 'account_id':
            account_id = self.request.args.get('account_id')
            if account_id is None:
                if self.SESSION_INFO is not None:
                    account_id = self.SESSION_INFO.get('account')
            self.account_id = account_id
            return account_id
        raise AttributeError(name)
    
    def make_show_string_response(self, string, content_type='text/plain; charset=utf-8'):
        response  = make_response(string)
        response.headers['Content-Type'] = content_type
        #response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = 'inline'
        response.headers['Content-Length'] = len(string)
        return response

    def make_show_file_response(self, file, content_type='text/plain; charset=utf-8'):
        if not os.path.isfile(file):
            return f'File "{file}" not found','404 File "{file}" not found'
        with open(file, 'rb') as f:
            response  = make_response(f.read())
        response.headers['Content-Type'] = content_type
        #response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = 'inline'
        response.headers['Content-Length'] = os.path.getsize(file)
        return response

    def make_download_file_response(self, file, file_name = None):
        return make_download_file_responce(file, file_name)

class Status:
    def __init__(self, js = {}, params = {}):
        self.js = js
        for key, value in params.items():
            self.js[str(key)] = str(value)
    def json(self):
        return json.dumps(self.js, ensure_ascii=False)

    def xml(self):
        STATUS = ET.fromstring('<STATUS/>')
        for key, value in self.js.items():
            ET.SubElement(STATUS, key).text = str(value)
        return ET.tostring(STATUS, encoding="utf-8").decode('utf-8')

    @staticmethod
    def success(params = {}):
        return Status({"status":"success"}, params)

    @staticmethod
    def error(msg, params = {}):
        return Status({"status":"error", "message":msg}, params)
 
    @staticmethod
    def exception(msg, params = {}):
        return Status({"status":"exception", "message":msg}, params)
 
class Request:
    def __init__(self, flask_request, application):
        self.request = flask_request
        self.flask_request = flask_request
        self.application = application
        self._sk_info = None

    @property
    def sk_info(self):
        if self._sk_info is None:
            SK = self.request.args['sk']
            r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
            self._sk_info = r.hgetall(SK)
        return self._sk_info
    
    @property
    def user_name(self):
        return self.sk_info.get('domino_user_name', '')
    
    @property
    def user_id(self):
        return self.sk_info.get('domino_user_id')
         
    @property 
    def url(self):
        return self.request.url
    @property
    def args(self):
        return self.request.args
    @property
    def form(self):
        return self.request.form
    @property
    def files(self):
        return self.request.files
 
    def get(self, *names):
        for name in names:
            value = self.flask_request.args.get(name)
            if value is None and self.flask_request.method == 'POST':
                value = self.flask_request.form.get(name)
            if value is not None:
                return value
        return None
 
    def arg(self, name):
        value = self.request.args.get(name)
        if value is None and self.request.method == 'POST':
            value = self.request.form.get(name)
        return value

    def account(self):
        account = find_account(self.account_id())
        if account is None:
            raise Exception('Соединение аннулировано. Требуется перезагрузка.')
        return account 

    def account_id(self):
        account_id = self.request.args.get('account_id')
        if account_id is not None:
            return account_id
        #SK = self.request.args['sk']
        #r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
        #sk_info = r.hgetall(SK)
        return self.sk_info.get('account')

    def download(self, file, file_name = None):
        return make_download_file_responce(file, file_name)

    def __str__(self):
        return f'Request()'
    
class ApplicationModule:
    def __init__(self, request_path, module, is_page=True):
        self.request_path = request_path
        self.module = module
        self.is_page = is_page
        self.ThePage = getattr(self.module, 'ThePage', None)
        self.TheResponse  = getattr(self.module, 'TheResponse', None)

class Application:  
    class AccountDatabase:
        def __init__(self, account_id, dept_id):
            self.account_id = account_id
            self.dept_id = dept_id
            self.database = None
          
    def __init__(self, file_path, framework = None):
        if framework:
            self.framework = framework
        else:
            self.framework = 'B4'

        self.python_path = os.path.dirname(file_path)
        self.version_folder = os.path.dirname(self.python_path)
        version_info_file = os.path.join(self.version_folder, 'info.json')
        if not os.path.isfile(version_info_file):
            raise Exception('Создание appication в неправильном контексте "{file_path}"')
        with open(os.path.join(self.version_folder, 'info.json')) as f: 
            self.version_info = json.load(f)
        self.version = Version.parse(self.version_info['version'])

        self.product_id = self.version_info.get('id')
        if self.product_id is None:
            self.product_id = self.version_info.get('product')

        self.module_id = self.product_id
        self.module_name = self.version_info.get('short_name')

        self.modules = {}
        self.databases = Databases()
        self.account_databases = {}

        if self.python_path not in sys.path:
            sys.path.append(self.python_path)

        self.params = {}
        self.reload_counter = 0

    def __getitem__(self, key):
        return self.params.get(key)

    def __setitem__(self, key, value):
        self.params[key] = value
 
    def pg_connect(self, account_id):
        return Postgres.connect(account_id)

    def account_database_connect(self, account_id, dept_id = None, for_write=False):
        account_database_key = f'{account_id}:{dept_id}'
        account_database = self.account_databases.get(account_database_key)
        if account_database is None:
            # Новое соединение
            account_database = Application.AccountDatabase(account_id, dept_id)
            #log.debug(f'Новое соединение {account_id} {dept_id}')
            database_id = None
            if dept_id is not None:
                dept = Dept.find(account_id, dept_id)
                #log.debug(f'"{dept}" = Dept.find("{account_id}", "{dept_id}")')
                if dept is not None:
                    database = Databases().get_database(account_id, dept.guid)
                    #log.debug(f'"{database}" = Databases.get_database("{account_id}", "{dept.guid}")')
                    if database is not None:
                        database_id = dept.guid
            # Вибираем нужную базу данных из пула баз данных по account_id и database_id
            account_database.database = self.databases.pool_database(account_id, database_id)
            #log.debug(f'"{account_database.database}" = self.databases.pool_database({account_id}, {database_id})')
            self.account_databases[account_database_key] = account_database
         
        # коннекция из пула соединений базы данных        
        #connection = account_database.database.acquire()
        connection = account_database.database.connect()
        if for_write:
            domino_login(connection)
        return connection

    def include(self, request_path, module, is_page):
        module = ApplicationModule(request_path, module, is_page)
        #module.request_path = request_path
        #module.module = module import('domino.jobs').as('pages/jobs' ThePage = Responce=)
        #module.is_page = is_page ThePage = 'pages/wdwdwddw.description', TheSerringsPage = 'pages/wdwdwddw.settings'__', 
        self.modules[module.request_path] = module

    def module(self, module_name):
        self.page_module(module_name)

    def page(self, module_name):
        self.page_module(module_name)
  
    def page_module(self, module_name):
        try:
            module = ApplicationModule(
                '/'+ module_name.replace('.', '/'), 
                importlib.import_module(module_name),
                True
                )
            #module.request_path = '/'+ module_name.replace('.', '/')
            #module.module = importlib.import_module(module_name)
            #module.is_page = True
            self.modules[module.request_path] = module
        except:
            LOG.exception(f'application.page_module("{module_name}")')
    
    def responce_module(self, module_name):
        try:
            module = ApplicationModule(
                '/'+ module_name.replace('.', '/'),
                importlib.import_module(module_name),
                False
            )
            #module.request_path = '/'+ module_name.replace('.', '/')
            #odule.module = importlib.import_module(module_name)
            #module.is_page = False
            self.modules[module.request_path] = module
        except:
            LOG.exception(f'application.response_module("{module_name}")')

    def responses(self, folder):
        try:
            for file_name in os.listdir(os.path.join(self.python_path, folder)):
                self.responce_module(f'{folder}.{file_name}')
        except:
            LOG.exception(f'application.responses("{folder}")')
        
    def responce(self, request):
        return self.make_responce(request)

    def request(self, flask_request):
        return Request(flask_request, self)
    
    def make_download_job_file_responce(self, request):
        job_id = request.args.get('job_id')
        file_name = request.args.get('file_name')
        file = os.path.join('/DOMINO/jobs',job_id, file_name)
        return make_download_file_responce(file)
                 
    def make_show_job_file_responce(self, request):
        job_id = request.args.get('job_id')
        file_name = request.args.get('file_name')
        file = os.path.join('/DOMINO/jobs',job_id, file_name)
        return make_show_file_responce(file)
   
    def make_responce(self, request):
        return self.make_response(request)
 
    def response_s(self, request, Response, fn = None, sessions = None):
        try:
            r = Response(self, request)
            for session in sessions:
                setattr(r, session.name, session)
            response = r.make_response(fn)
            for session in sessions:
                session.commit()
            return response 
        except BaseException as ex:
            LOG.exception(request.url)
            for session in sessions:
                session.rollback()
            return f'{ex}', 500
        finally:  
            for session in sessions:
                session.close()
       
    def response(self, request, Response, fn = None, engines = None, log = False):
        sessions = []
        postgres = None
        request_log = None
        try:
            if log:
                request_log = RequestLog(self.module_id, request.url)
            r = Response(self, request)
            r.request_log = request_log
            DEBUG(f'Response(self, request) => {r}')
            #№account_id = r.account_id
            #log.debug(f'{account_id}')
            account_id = r.account_id if hasattr(r, 'account_id') else None
            dept_code = r.dept_code if hasattr(r, 'dept_code') else None
            if request_log:
                request_log.dept_code = dept_code
            if engines is not None:
                for engine in engines:
                    #log.debug(f'{engine}.session({account_id}, {dept_code}, {self.module_id})')
                    session = engine.session(account_id, dept_id = dept_code, module_id = self.module_id)
                    if session is not None:
                        sessions.append(session) 
                        setattr(r, engine.engine_name, session)
                        if engine.engine_name == 'postgres':
                            postgres = session
            
            response = r.make_response(fn)
            if postgres and request_log:
                request_log.response_text = response
                postgres.add(request_log)
            for session in sessions:
                session.commit()
            return response 
        except BaseException as ex:
            LOG.exception(request.url)
            for session in sessions:
                session.rollback()
            if postgres and request_log:
                postgres.add(request_log)
                request_log.status_code = 500
                request_log.response_text = f'{ex}'
                session.commit()
            return f'{ex}', 500
        finally:  
            for session in sessions:
                session.close()
    
    def make_response(self, request):
        try:
            pos = request.path.find('.')
            if pos != -1:
                module_name = request.path[:pos]
                func_name = request.path[pos+1:]
            else:
                module_name = request.path
                func_name = None

            if module_name == '/download_job_file':
                return self.make_download_job_file_responce(request)
            elif module_name == '/show_job_file':
                return self.make_show_job_file_responce(request)
  
            module = self.modules.get(module_name)
            if module is None:
                return f'Не найден модуль "{module_name}"', '500'
            
            response = None

            reload = request.args.get('reload')
            if reload:
                self.reload_counter += 1
                DEBUG(f'RELOAD {self.reload_counter} {reload}: {module_name}')
            #if reload:
            #    return 'reload', 404

            if module.ThePage is not None:
                ThePage = module.ThePage(self, request)
                response = ThePage.make_response(func_name)

            if response is not None:
                return response

            if module.TheResponse is not None:
                TheRespose = module.TheResponse(self, request)
                response = TheRespose.make_response(func_name)
            
            if response is not None:
                return response
            
            # совместимость уже не помню с чем
            if module.is_page:
                if func_name is None:
                    func_name = 'open'
                func = getattr(module.module, func_name, None)
                if func is None:
                    return f'Не найдена функция "{func_name}" в модуле"{module_name}"', '404'

                page = Page(self, Request(request, self))
                try:
                    responce = func(page)
                    if responce is None:
                        if page.get('_pu'):
                            return page.update()
                        else:
                            return page.html()
                    else:
                        return responce
                except BaseException as ex:
                    LOG.exception(request.url)
                    page.message(f'{ex}')
                    if page.get('_pu'):
                        return page.update()
                    else:
                        return page.html()
            else:
                if func_name is None:
                    func_name = 'responce'
                func = getattr(module.module, func_name)
                if func is None:
                    return f'Не найдена функция "{func_name}" в модуле"{module_name}"', '404'
                try:
                    responce = func(Request(request, self))
                    if responce is None:
                        return ''
                    else:
                        return responce
                except BaseException as ex:
                    LOG.exception(request.url)
                    return f'{ex}', '500'

        except BaseException as ex:
            LOG.exception(f'application.make_responce({request})')
            return f'{ex}', '500'
 
    @property
    def hostname(self):
        try:
            return platform.uname().node
        except:
            return ''
 
def SUCCESS():
    return json.dumps({'status':'success'})

def ERROR(message):
    return json.dumps({'status':'error', 'message':message})


