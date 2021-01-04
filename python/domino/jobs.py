import os, sqlite3, uuid, sys, time
import pickle
import subprocess
import shutil
import psutil
import json
from datetime import datetime
from datetime import timedelta
import arrow
import redis
from threading import Thread
from queue import Queue

#from multiprocessing import Process, Value, Queue, Pipe
#import multiprocessing.sharedctypes
from importlib import import_module
from time import sleep

from domino.core import log, start_log, DOMINO_ROOT

JOBS_DB = '/DOMINO/data/jobs.db'
JOBS = '/DOMINO/jobs'
JOBS_TEMP= '/DOMINO/jobs.temp'

def job_folder(id):
    return os.path.join(JOBS, str(id))

def job_break_file(id):
    return os.path.join(JOBS, str(id), 'break')

def job_temp_folder(id):
    return os.path.join(JOBS_TEMP, str(id))

def connect():
    return sqlite3.connect(JOBS_DB)

def drop_structure():
    conn = connect()
    cur = conn.cursor()
    cur.execute('drop table jobs;')
    conn.close()
    
def create_structure():
    os.makedirs('/DOMINO/data', exist_ok=True)
    conn = connect()
    cur = conn.cursor()
    #cur.execute('''
    #    create table if not exists jobs (
    #        id integer not null primary key,
    #        status int not null default (0),
    #        pid int,
    #        account_id,
    #        product_id not null,  
    #        programm text,
    #
    #        name not null,
    #
    #        user_id,
    #        user_name text,
    #        type,
    #        uuid text,  
    #        description text default (''),
    #        start not null default(date()),
    #        end,
    #        comment text default (''),
    #        info blob
    #    );
    #    '''
    #)
    cur.execute('''
        create table if not exists PROC_JOBS (
            ID integer not null primary key,
            STATE integer not null default (-1),
            PROC_ID integer not null,
            PID int,
            NAME text not null, 
            UUID text,  
            DESCRIPTION text default (''),
            START_DATE,
            ENS_DATE,
            INFO blob default('{}')
        );
        '''
    )
    conn.close()

def select_jobs(query, args = []):
        conn = connect()
        cur = conn.cursor()
        cur.execute(query, args)
        r = cur.fetchall() 
        cur.close()
        conn.close()
        return r

def start(product_id, programm, args=[]):
    file_py  = f'/DOMINO/products/{product_id}/active/python/{programm}.py'
    params = []
    params.append('python3.6')
    params.append(file_py)
    uuid = create_uuid()
    params.append(uuid)
    for arg in args:
        params.append(str(arg)) 
    subprocess.Popen(params)
    return uuid

def query_job2(cur, account_id, product_id, program, argv = [], info = {}, имя = None):
    ID = Задача.создать(account_id, product_id, program , name = имя)
    folder = os.path.join(JOBS, str(ID))
    temp = os.path.join(JOBS_TEMP, str(ID))
    os.makedirs(temp, exist_ok=True)
    os.makedirs(folder, exist_ok=True)
    params = {'argv':argv, 'program':program, 'product_id':product_id}
    params['account_id'] = account_id
    with open(os.path.join(folder, 'params'), 'wb') as f:
        pickle.dump(params, f)
    return ID

def query_job(product_id, program, argv = []):
    uuid = create_uuid()
    conn = connect()
    start = datetime.now()
    id = None
    with conn:
        cur = conn.cursor()
        cur.execute( 
            '''
               insert into jobs (status, product_id, programm, start, uuid, name) 
               values (-1, ?, ?, ?, ?, ?);
            ''', 
            [product_id, program, start , uuid, '']
        )
        cur.execute('select last_insert_rowid();')
        id = cur.fetchone()[0]
        cur.close()
    folder = os.path.join(JOBS, str(id))
    temp = os.path.join(JOBS_TEMP, str(id))
    os.makedirs(temp, exist_ok=True)
    os.makedirs(folder, exist_ok=True)
    params = {'argv':argv, 'program':program, 'product_id':product_id}
    with open(os.path.join(folder, 'params'), 'wb') as f:
        pickle.dump(params, f)
    return id

def _job_subprocess(job_id, product_id, proc):
    file_py  = f'/DOMINO/products/{product_id}/active/python/{proc}.py'

def start_job2(cur, ID):
    #log.debug(f'start_job2')
    ID = int(ID)
    cur.execute('select product_id, programm from jobs where id=? and status = -1',[ID])
    product_id, program = cur.fetchone()
    file_py  = f'/DOMINO/products/{product_id}/active/python/{program}.py'
    subprocess.Popen(['python3.6', file_py, str(ID)])

def start_job(ID):
    #log.debug(f'start_job')
    ID = int(ID)
    conn = connect()
    with conn:
        start_job2(conn.cursor(), ID)

class Задача:
    @staticmethod
    def запустить(account_id, product_id, proc_name, argv = [], name = '', description = None):
        #log.debug(f'Задача.запустить("{account_id}", "{product_id}", "{proc_name}", {argv}, "{name}", "{description}")')
        ID = Задача.создать(account_id, product_id, proc_name , name = name , description = description)
        folder = os.path.join(JOBS, str(ID))
        temp = os.path.join(JOBS_TEMP, str(ID))
        os.makedirs(temp, exist_ok=True)
        os.makedirs(folder, exist_ok=True)
        params = {'argv':argv, 'account_id' : account_id, 'program':proc_name, 'product_id':product_id}
        params['account_id'] = account_id
        with open(os.path.join(folder, 'params'), 'wb') as f:
            pickle.dump(params, f)

        file_py  = f'/DOMINO/products/{product_id}/active/python/{proc_name}.py'
        subprocess.Popen(['python3.6', file_py, str(ID)])

        #log.debug(f'{ID} = Задача.запустить(...)')
        return ID

    @staticmethod
    def создать(account_id, product_id, proc_name, UUID = None, name = '', description = None, INFO="{}"):
        #log.debug(f'Задача.создать()')
        if UUID is None:
            UUID = create_uuid()
        with sqlite3.connect(JOBS_DB) as conn:
            cur = conn.cursor()
            cur.execute( 
            '''
            insert into jobs (
                status, start, account_id, product_id, programm, uuid, name, description, info
                )
            values (-1, ?, ?, ?, ?, ?, ?, ?, ?);
            ''', 
            [datetime.now(), account_id, product_id, proc_name, UUID, name,  description, INFO]
            )
            ID =  cur.lastrowid
            conn.commit()
        return ID

    @staticmethod
    def изменить_статус(ID, статус, name = None, description = None, end=None, comment=None, pid=None):
        #log.debug(f'Задача.изменить_статус({ID}, {статус}, {name}, {description}, {end}, {comment}, {pid}):')
        статус = int(статус)
        with sqlite3.connect(JOBS_DB) as conn:
            курсор = conn.cursor()
            курсор.execute('update jobs set status = ? where id=?', [статус, ID])
            if name is not None:
                курсор.execute('update jobs set name = ? where id=?', [name, ID])
            if description is not None:
                курсор.execute('update jobs set description = ? where id=?', [description, ID])
            if end is not None:
                курсор.execute('update jobs set end = ? where id=?', [end, ID])
            if comment is not None:
                курсор.execute('update jobs set comment = ? where id=?', [comment, ID])
            if pid is not None:
                курсор.execute('update jobs set pid = ? where id=?', [pid, ID])
            conn.commit()

    @staticmethod
    def есть_активные_задачи_с_данным_именем(имя):
        conn = sqlite3.connect(JOBS_DB)
        cursor = conn.cursor()
        cursor.excecute('select count(*) from jobs where status = 0 and name=?',[имя])
        есть = cursor.fetchone()[0] > 0
        conn.close()
        return есть

    @staticmethod
    def последняя_задача_ID(account_id, product_id, proc_name):
        conn = sqlite3.connect(JOBS_DB)
        cursor = conn.cursor()
        cursor.execute('select max(id) from jobs where account_id=? and product_id=? and programm=?', [account_id, product_id, proc_name])
        r = cursor.fetchone()
        return r[0] if r is not None else None

    @staticmethod
    def последняя_задача(account_id, product_id, proc_name):
        job = None
        conn = sqlite3.connect(JOBS_DB)
        cursor = conn.cursor()
        cursor.execute('select max(id) from jobs where account_id=? and product_id=? and programm=?', [account_id, product_id, proc_name])
        r = cursor.fetchone()
        if r is None:
            return None
        ID = r[0]
        if ID is not None:
            job = JobReport(ID)
        conn.close()
        return job

    @staticmethod
    def findall(курсор, where_clause = None, params=[]):
        jobs = []
        if where_clause is None:
            курсор.execute(f'select id from jobs')
        else:
            курсор.execute(f'select id from jobs where {where_clause}', params)
        for ID, in курсор:
            jobs.append(JobReport(ID, курсор))
        return jobs

    @staticmethod
    def findfirst(курсор, where_clause = None, params=[]):
        if where_clause is None:
            курсор.execute(f'select id from jobs')
        else:
            курсор.execute(f'select id from jobs where {where_clause}', params)
        r = курсор.fetchone()
        if r is None:
            return None
        else:
            return JobReport(r[0], курсор)

def stop_job(ID, msg=''):
    with open(job_break_file(ID), 'w') as f:
        f.write(msg)

def _delete_job_folders(id):
        folder = job_temp_folder(id)
        if os.path.isdir(folder):
            shutil.rmtree(folder)
        folder = job_folder(id)
        if os.path.isdir(folder):
            shutil.rmtree(folder)

def clean_jobs():
    conn = connect()
    with conn:
        cur = conn.cursor()
        cur.execute('select id, pid from jobs where status <= 0')
        lines = cur.fetchall()
        for id, pid  in lines:
            if pid is None or not psutil.pid_exists(pid):
                cur.execute('delete from jobs where id=?', [id])
                conn.commit()
                _delete_job_folders(id)

def remove_job(id):
    conn = connect()
    with conn:
        cur = conn.cursor()
        cur.execute('delete from jobs where id=?;', [id])
        _delete_job_folders(id)

def remove_jobs(product_id, name = None):
        conn = connect()
        count = 0
        with conn:
            cur = conn.cursor()
            if name is None:
                cur.execute('select id from jobs where status != 0 and product_id=?;', [product_id])
            else:
                cur.execute('select id from jobs where status != 0 and product_id=? and name=?;', [product_id, name])
            r = cur.fetchall()
            for id, in r:
                count += 1
                cur.execute('delete from jobs where id=?;', [id])
                _delete_job_folders(id)
        return count
def job_is_active(product_id, name):
    conn = connect()
    with conn:
        cur = conn.cursor()
        cur.execute('select pid from jobs where status == 0 and product_id=? and name=?;', [product_id, name])
        r = cur.fetchall()
    for PID, in r:
        if PID is not None and psutil.pid_exists(PID):
            return True
    return False

class JobAlreadyWorking(Exception):
    pass

class JobSuccessException(Exception):
    def __init__(self, msg = ''):
        super().__init__(msg)

class JobErrorException(Exception):
    def __init__(self, msg = ''):
        super().__init__(msg)

class JobLogRecord:
    def __init__(self, start, message):
        self.start = start
        self.end = None
        self.message = message
    @property
    def s_start(self):
        return self.start.strftime("%Y-%m-%d  %H:%M:%S")
    @property
    def time(self):
        if self.end is not None:
            return self.end - self.start
        else:
            return None
    @property
    def s_time(self):
        time = self.time
        if time is None:
            return ''
        else:
            return time.strftime("%H:%M:%S")

class JobReport:
    def __init__(self, id, курсор = None):
        self.id = int(id)
        if курсор is None:
            conn = connect()
            cur = conn.cursor()
        else:
            cur = курсор.connection.cursor()
        cur.execute('select product_id, name, start, end, status, description, pid, uuid, info, comment, account_id, programm from jobs where id=?', [id])
        r = cur.fetchone()
        self.product_id, self.name, start_string, end_string, self.status, self.description, self.pid, self.uuid, info_dump, self.comment, self.account_id, self.program = r
        try:
            self.info = json.loads(info_dump)
        except:
            self.info = {}
        self.folder = os.path.join(JOBS, str(self.id))
        self.start = arrow.get(start_string).datetime
        if end_string is not None:
            self.end = arrow.get(end_string).datetime
        else:
            self.end = None
        self._params = None
    @property
    def ID(self):
        return self.id
    
    @property
    def wait_for_break(self):
        return os.path.isfile(job_break_file(self.id))

    @property
    def procname(self):
        return '/'.join([
            self.account_id if self.account_id is not None else '',
            self.product_id,
            self.program if self.program is not None else ''
            ])

    @property
    def params(self):
        if self._params is None:
            try:
                with open(os.path.join(self.folder, 'params'), 'rb') as f:
                    self._params = pickle.load(f)
            except:
                self._params = {}
        return self._params
    def get_param(self, name):
        return self.params.get(name)

    @staticmethod
    def by_uuid(uuid, count):
        conn = connect()
        with conn:
            cur = conn.cursor()
            while count > 0:
                cur.execute('select id from jobs where uuid=?', [uuid])
                r = cur.fetchone()
                if r is not None:
                    break
                else:
                    count -= 1
                    sleep(0.1)
        if r is None:
            return None
        else:
            id, = r
            return JobReport(id)
            
    @property
    def error(self):
        return self.status == 400
    @property
    def active(self):
        return self.status == 0
    @property
    def success(self):
        return self.status == 200
        
    @property
    def s_start(self):
        return self.start.strftime("%Y-%m-%d  %H:%M:%S")

    @property
    def s_end(self):
        if self.end is not None:
            return self.end.strftime("%Y-%m-%d  %H:%M:%S")
        else:
            return ''

    @property
    def time(self):
        if self.end is not None:
            return self.end - self.start
        else:
            return None

    @property
    def s_time(self):
        return f'{self.time}'

    def log(self):
        log = []
        index = -1
        log_file = os.path.join(self.folder, 'log') 
        if not os.path.isfile(log_file):
            return []
        with open(os.path.join(self.folder, 'log')) as f:
            for line in f:
                try:
                    start_string, message = (line.strip('\n\r')).split('\t')
                    start = arrow.get(start_string).datetime
                    r = JobLogRecord(start, message)
                    if len(log) > 0:
                        log[len(log)-1].end = start
                    log.append(r)
                except:
                    pass
        return log

    @staticmethod
    def select(query, args):
        conn = connect()
        cur = conn.cursor()
        cur.execute(query, args)
        r = cur.fetchall() 
        cur.close()
        conn.close()
        return r

    @staticmethod
    def findall(product_id = None, active = None):
        conditions = []
        if product_id is not None:
            conditions.append(f"product_id='{product_id}'")
        if active is not None:
            if active:
                conditions.append(f"status <= 0")
            else:
                conditions.append(f"status > 0")
        if len(conditions) > 0:
            where_clause = ' and '.join(conditions) 
            query = f'select id from jobs where {where_clause} order by id desc;'
        else:
            query = f'select id from jobs order by id desc;'
            
        #print (query)
        jobs = []
        for id, in JobReport.select(query,[]):
            jobs.append(JobReport(id))
        return jobs

def create_uuid():
    return str(uuid.uuid4())

class Job:
    STATUS_ONLINE = 0
    STATUS_STOPPING = 1
    STATUS_QUERY = -1
    STATUS_SUCCESS = 200
    STATUS_ERROR = 400

    Error = 400
    Success = 200
    Active = 0
    QUERY = -1

    @staticmethod
    def exists_active_jobs(product, job_name):
        conn = connect()
        cur = conn.cursor()
        cur.execute('select count(*) from jobs where product_id=? and name=?', [product, job_name])
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count > 0

    @staticmethod
    def get_status(id):
        conn = connect()
        cur = conn.cursor()
        cur.execute('select status from jobs where id=?', [id])
        r = cur.fetchone()
        cur.close()
        conn.close()
        if r is None:
            return None
        else:
            return r[0]

    @staticmethod
    def open(ID = None):
        if ID is None:
            ID = sys.argv[1]
        return Job(ID=ID)

    @staticmethod
    def reopen(ID):
        return Job(ID=ID)

    def __init__(self, product = None, name = None, description = None, uuid = None, is_unique = False, ID = None, account_id = None, proc_name = None):
        self.quite = False
        if ID is None:
            self.product = product
            self.account_id = account_id
            if uuid is None:
                self.uuid = create_uuid()
            else:
                self.uuid = uuid
            self.proc_name = proc_name
            self.pid = os.getpid()
            self.start = datetime.now()
            self.id = None
            self.status = -1
            self.info = {}
            self.params = {}
            self.name = name
            self.description = description if description is not None else ''

            self.id = Задача.создать(self.account_id, self.product, self.proc_name,
                UUID = self.uuid, name = self.name, description = self.description )
        else:
            self.id = int(ID)
            self.status = 0
            self.info = {}
            self.получить_параметры_запуска()

        self.pid = os.getpid()
        Задача.изменить_статус(self.id, self.status, pid = self.pid)

        # создаем папки для хранения файлов
        self.folder = os.path.join(JOBS, str(self.id))
        self.temp = os.path.join(JOBS_TEMP, str(self.id))
        os.makedirs(self.temp, exist_ok=True)
        os.makedirs(self.folder, exist_ok=True)
        self.break_file = job_break_file(self.id)

        # загружаем параметры
        try:
            with open(os.path.join(self.folder, 'params'), 'rb') as f:
                self.params = pickle.load(f)
        except:
            self.params = {}

        # создаем log и запмсываем начальную запись
        self.log_path = os.path.join(self.folder, 'log')
        self.log(f'')
            #log.debug(f'__init__() name={self.name}')

    def получить_параметры_запуска(self):
        conn = sqlite3.connect(JOBS_DB)
        cur = conn.cursor()
        cur.execute('''
            select account_id, product_id, programm, uuid, name, description 
            from jobs where id=?
            ''', [self.id])
        self.account_id, self.product, self.proc_name, self.uuid, self.name, self.description = cur.fetchone()
        self.start = datetime.now()
        cur.close()
        conn.close()

    def _wait_for_stop_some_jobs(self, cur):
        start_log.debug(f'{self.id} : START _wait_for_stop_some_jobs')
        while True:
            clean_jobs()
            cur.execute('''
            select count(*) from jobs where name=? and status == 0 and id !=?
            ''', [self.name, self.id])
            count = cur.fetchone()[0]
            if count == 0:
                break
            self.check_for_break()
            #print(f'{self.id} : Ожидание окончания прочих задач')
            sleep(5)
        start_log.debug(f'{self.id} : END _wait_for_stop_some_jobs')

    def _send_break_for_some_jobs(self, cur):
        #start_log.debug(f'{self.id} : _send_break_for_some_jobs')
        clean_jobs()
        cur.execute('''
            select id from jobs where name=? and status == 0 and id !=?
            ''', [self.name, self.id])
        for ID, in cur:
            #start_log.debug(f'{self.id} : _send_break_for_some_jobs : {ID}')
            stop_job(ID)

    def start_and_stop_previous(self, name = None, description = None):
        if name is not None:
            self.name = name
        self.description = description
        Задача.изменить_статус(self.id, 0, name = name, description = description)

        with sqlite3.connect(JOBS_DB) as conn:
            cur = conn.cursor()
            self._send_break_for_some_jobs(cur)
            self._wait_for_stop_some_jobs(cur)
            conn.close()

    def stop_if_next_exists(self):
        #cur = self.conn.cursor()
        #cur.execute(
        #    'select count(*) from jobs where name=? and status = 0 and id > ?',
        #    [self.name, self.id]
        #    )
        #count = cur.fetchone()[0]
        #if count > 0 :
        #    self.success('Остановлена, посскольку работет более позняя задача')
        pass

    def start_if_not_exists(self, name = None, description = None):
        self.start_unconditionly(name, description)
        #self.name = name
        #if description is not None:
        #    self.description = description
        #with self.conn:
        #    cur = self.conn.cursor()
        #    cur.execute(
        #        'select count(*) from jobs where name=? and status < 0 and id !=?',
        #        [self.name, self.id]
        #        )
        #    count = cur.fetchone()[0]
        #   cur.close()
        #   if count > 0:
        #        self.error(f'Задача аннулирована, т.к. выполняется аналогичная')
        #   self.conn.execute('''
        #        update jobs set name=?, description=? where id=?
        #        '''
        #        , [self.name, self.description, self.id]
        #        )
          
    def start_unconditionly(self, name = None, description = None):
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        Задача.изменить_статус(self.id, 0, name = name, description = description)
        #with self.conn:
        #    self.conn.execute(
        #       update jobs set name=?, description=? where id=?
        #                       , [self.name, self.description, self.id]
        #       )
    
    def check_for_break(self):
        #start_log.debug(f'{self.id} : check_for_break')
        if os.path.exists(self.break_file):
            with open(self.break_file) as f:
                text = f.readline()
            #start_log.debug(f'{self.id} : check_for_break BREAK')
            self.error(text)

    def set_name(self, name, description = None, unique = False):
        self.name = name
        if description is not None:
            self.description = description
        Задача.изменить_статус(self.id, self.status, name = name, description=description)
        #with self.conn:
        #    self.conn.execute('''
        #        update jobs set name=?, description=? where id=?
        #        '''
        #        , [self.name, self.description, self.id]
        #        )
    
    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type is None:
            self.close(Job.Success)
        elif exception_type == JobSuccessException:
            self.close(Job.Success, str(exception_value))
        else:
            self.close(Job.Error, str(exception_value))

    def save_info(self):
        #with self.conn:
        #    self.conn.execute('update jobs set info=? where id=?', [json.dumps(self.info), self.id])
        pass

    def arg(self, i):
        try:
            return self.params['argv'][i] 
        except:
            return None
    
    def set_params(self, **params):
        for name, value in params.items():
            self.params[name] = value
        with open(os.path.join(self.folder, 'params'), 'wb') as f:
            pickle.dump(self.params, f) 

    def get_param(self, name):
        return self.params.get(name)

    def log(self, msg):
        start = datetime.now()
        with open(self.log_path, "a") as f:
            f.write(f'{start}\t{msg}\n')

    def close(self, status = 200, comment = None):
        #log.debug(f'close job {self.id} {status} {comment}')
        if os.path.isdir(self.temp):
            shutil.rmtree(self.temp)
        Задача.изменить_статус(self.id, status, end = datetime.now(), comment = comment)            
        #with self.conn: 
        #    cur = self.conn.cursor()
        #    cur.execute('update jobs set comment=?, info=?, end=?, status=?  where id=?;', 
        #    [comment, json.dumps(self.info), datetime.now(), status, self.id])

        if status == 200:
            self.log(f"{comment}")
        else:
            self.log(f"Завешрено с ошибкой. {comment}")
        #self.conn.close()
            
    def error(self, error):
        raise Exception(error)
        #self.close(400, comment)

    def success(self, msg):
        raise JobSuccessException(msg)

    def clean(self, name = None):
        pass

class JobStopException(BaseException):
    pass

class Proc:
    '''
    CREATE TABLE procs (
            ID integer not null primary key,
            CLASS integer not null default 0,
            TYPE integer not null default 0,
            STATE integer not null default 0,
            ACCOUNT_ID text,
            MODULE text not null,
            PROC text not null,
            PARAMS blob default '{}',
            INFO blob default '{}',
            INST integer not null default 1,
            AUTORESTART integer not null default 0,
            UNIQUE(ACCOUNT_ID, MODULE, PROC)
    '''
    CLASS_SHEDULED = 0
    CLASS_SERVICE = 1
    CLASS_MANUAL = 3
    STATE_DISABLED = 1
    STATE_ENABLED = 0
    NO_ACCOUNT_ID = ''

    class Job:
        STATE_ONLINE = 0
        STATE_STOPPING = 1
        STATE_STARTING = -1
        STATE_ABORT = -2
        STATE_QUERY = -1
        STATE_SUCCESS = 200
        STATE_ERROR = 400

        @staticmethod
        def get_error_message(job_id):
            #log.debug(f'def get_error_message({job_id}):')
            error_message = None
            error_message_file = os.path.join(DOMINO_ROOT, 'jobs', str(job_id), 'error_message')
            if os.path.exists(error_message_file):
                #log.debug(f'open({error_message_file})')
                with open(error_message_file) as f:
                    error_message = f.read()
            return error_message
        @staticmethod
        def set_error_message(job_id, error_message):
            error_message_file = os.path.join(DOMINO_ROOT, 'jobs', job_id, 'error_message')
            with open(error_message_file, 'w') as f:
                f.write(error_message)

        @staticmethod
        def state_name(STATE):
            if STATE == None:
                return ''
            STATE = int(STATE)
            if STATE == Proc.Job.STATE_ONLINE:
                return 'A'
            elif STATE == Proc.Job.STATE_STOPPING:
                return 'D'
            elif STATE == Proc.Job.STATE_STARTING:
                return 'Q'
            elif STATE == Proc.Job.STATE_ABORT:
                return 'X'
            elif STATE == Proc.Job.STATE_SUCCESS:
                return 'S'
            elif STATE == Proc.Job.STATE_ERROR:
                return 'E'
            else:
                return f'{STATE}'

        def __init__(self, ID):
            self.ID = ID
            self.redis = redis.Redis(host='localhost', port=6379)
            self.queue = Queue()
            thread = Thread(target = Proc.Job.msg_listener, args=(self.ID, self.queue))
            thread.setDaemon(True)
            thread.start()
            # создаем папки для хранения файлов
            self.folder = os.path.join(DOMINO_ROOT, 'jobs', str(self.ID))
            self.temp = os.path.join(DOMINO_ROOT, 'jobs', str(self.ID), 'temp')
            os.makedirs(self.temp, exist_ok=True)
            os.makedirs(self.folder, exist_ok=True)
            # считываем основные параметры задачи
            with Proc.connect() as conn:
                cur = conn.cursor()
                sql = '''
                    select proc.ID, proc.ACCOUNT_ID, proc.INFO, job.INFO
                    from proc_jobs job join procs proc on job.PROC_ID = proc.ID
                    where job.ID = ? 
                '''
                cur.execute(sql, [ID])
                self.proc_id, self.account_id, INFO, JOB_INFO = cur.fetchone()
                self.info = json.loads(INFO)
                self.job_info = json.loads(JOB_INFO)
            # создаем log и запмсываем начальную запись
            self.log_path = os.path.join(self.folder, 'log')
            self.log(f'{ID}')

        def get(self, name, default = None):
            value = self.job_info.get(name)
            if value is not None:
                return value
            value = self.info.get(name)
            return value if value is not None else default

        def get_int(self, name, default = None):
            try:
                value = self.get(name)
                return int(value) if value is not None else default
            except:
                log.exception(__file__)
                return default

        def get_date(self, name, default = None):
            try:
                value = self.get(name)
                return arrow.get(value).date() if value is not None else default
            except:
                log.exception(__file__)
                return default

        def get_datetime(self, name, default = None):
            try:
                value = self.get(name)
                return arrow.get(value).datetime() if value is not None else default
            except:
                log.exception(__file__)
                return default

        def __str__(self):
            return f'<Job {self.ID}>'

        def __enter__(self):
            return self

        def __exit__(self, exception_type, exception_value, traceback):
            #log.debug(f'{self}.__exit__({exception_type}, {exception_value})')
            if exception_type is None:
                self.close(Proc.Job.STATE_SUCCESS)
            elif exception_type == JobSuccessException:
                self.close(Proc.Job.STATE_SUCCESS)
            elif exception_type == JobErrorException:
                self.close(Proc.Job.STATE_ERROR, str(exception_value))
            else:
                self.close(Proc.Job.STATE_ERROR, str(exception_value))

        def error(self, error):
            raise Exception(error)
            #self.close(400, comment)

        def success(self, msg):
            raise JobSuccessException(msg)

        def log(self, msg):
            start = datetime.now()
            with open(self.log_path, "a") as f:
                f.write(f'{start}\t{msg}\n')

        @staticmethod
        def msg_listener(job_ID, queue):
            r = redis.Redis(host='localhost', port=6379)
            p = r.pubsub()
            p.subscribe('job:stop')
            for m in p.listen():
                if m['type'] == 'message':
                    message = json.loads(m['data'])
                    if str(message['job_id']) == str(job_ID) :
                        msg = json.dumps({'job_id':job_ID})
                        #log.debug(f'msg_listener({job_ID}) : redis.publish(job:stopping, {msg})')
                        r.publish('job:stopping', msg)
                        queue.put('job:stop') 

        def check_for_break(self):
            #log.debug(f'{self}.check_for_break')    
            if self.queue.empty():
                #log.debug(f'{self}.check_for_break : is empty')    
                return
            msg = self.queue.get_nowait()
            #log.debug(f'{self}.check_for_break "{msg}"')
            if msg == 'job:stop':
                raise JobStopException()

        def close(self, status = 200, error_msg = None):
            #log.debug(f'{self}.close({status})')
            if status != Proc.Job.STATE_SUCCESS:
                self.log(f'{error_msg}')
                Proc.Job.set_error_message(self.ID, error_msg)

            msg = json.dumps({"job_id" : self.ID, 'status' : status, 'state':status})
            #log.debug(f'{self}.close : redis.publish(job:stopped,{msg})')
            self.redis.publish('job:stopped', msg)


        @staticmethod
        def connect():
            return sqlite3.connect(os.path.join(DOMINO_ROOT, 'data', 'jobs.db'))
    
        @staticmethod
        def stop(ID):
            r = redis.Redis(host='localhost', port=6379)
            msg = json.dumps({"job_id":ID})
            #log.debug(f'Job.stop({ID}) : redis.publish(job:stop,{msg})')
            r.publish('job:stop', msg)

        @staticmethod
        def check():
            r = redis.Redis(host='localhost', port=6379)
            msg = json.dumps({})
            #log.debug(f'Job.check() : redis.publish(job:check, {msg})')
            r.publish('job:check', msg)

        @staticmethod
        def delete(ID):
            with Proc.connect() as conn:
                cur = conn.cursor()
                cur.execute('delete from proc_jobs where id=?', [int(ID)])
            folder = os.path.join(DOMINO_ROOT, 'jobs', str(ID))
            if os.path.isdir(folder):
                shutil.rmtree(folder)

        @staticmethod
        def read_log(ID):
            log_file = os.path.join(DOMINO_ROOT, 'jobs', str(ID), 'log')
            log = ''
            if os.path.isfile(log_file):
                with open(log_file) as f:
                    log = f.read()
            return log 

        @staticmethod
        def get_info(ID):
            try:
                with Proc.connect() as conn:
                    cur = conn.cursor()
                    cur.execute('select INFO from proc_jobs where id=?', [int(ID)])
                    INFO = cur.fetchone()[0]
                return json.loads(INFO)
            except:
                log.exception(__name__)
                return {}

    @staticmethod
    def connect():
        return sqlite3.connect(os.path.join(DOMINO_ROOT, 'data', 'jobs.db'))

    #def __init__():
    #    pass

    @staticmethod
    def get_by_id(id):
        with Proc.connect() as conn:
            cur = conn.cursor()
            sql = 'select ID, ACCOUNT_ID, MODULE, PROC, INFO from procs where ID=? '
            params = [id]
            #log.debug(f'{sql} {params}')
            cur.execute(sql, params)
            ID, account_id, module, proc, INFO = cur.fetchone()
            proc = Proc()
            proc.account_id = account_id
            proc.module = module
            proc.proc = proc
            proc.ID = ID
            proc.info = json.loads(INFO)
        return proc

    @staticmethod
    def get(account_id, module, proc):
        if not account_id:
            account_id = ''
        with Proc.connect() as conn:
            cur = conn.cursor()
            sql = 'select ID, INFO from procs where ACCOUNT_ID=? and MODULE=? and PROC=?'
            params = [account_id, module, proc]
            #log.debug(f'{sql} {params}')
            cur.execute(sql, params)
            ID, INFO = cur.fetchone()

            proc = Proc()
            proc.account_id = account_id
            proc.module = module
            proc.proc = proc
            proc.ID = ID
            proc.info = json.loads(INFO)
        return proc

    def save(self):
        with Proc.connect() as conn:
            cur = conn.cursor()
            sql = 'update procs set INFO=? where ID=?'
            INFO = json.dumps(self.info, ensure_ascii=False)
            cur.execute(sql, [INFO, self.ID])

    @staticmethod
    def get_params(ID):
        with Proc.connect() as conn:
            cur = conn.cursor()
            cur.execute('select PARAMS from proc where ID=?', [ID])
            return json.loads(cur.fetchone()[0])

    @staticmethod
    def change_params(ID, **kwargs):
        with Proc.connect() as conn:
            cur = conn.cursor()
            cur.execute('select PARAMS from proc where ID=?', [ID])
            PARAMS = cur.fetchone()[0]
            params = json.loads(PARAMS)
            for key, value in kwargs.items():
                params[key] = value
            PARAMS = json.dumps(params, ensure_ascii=False)
            cur.excecute('update proc self PARAMS=? where ID=?', PARAMS, ID)

    @staticmethod
    def create(account_id, module, proc, CLASS=0, description=None, time=None, days=None, enable=None, url=None):
        if not account_id:
            account_id = ''
        with Proc.connect() as conn:
            cur = conn.cursor()
            cur.execute('select ID, INFO from procs where ACCOUNT_ID=? and MODULE=? and PROC=?', [account_id, module, proc])
            r = cur.fetchone()
            if r is not None:
                ID, INFO = r
                info = json.loads(INFO)
                if description:
                    info['description'] = description
                if url:
                    info['url'] = url
                INFO = json.dumps(info, ensure_ascii=False)
                sql = 'update procs set CLASS=?, INFO=? where ID=?'
                params = [CLASS, INFO, ID]
                cur.execute(sql, params)
                #log.debug(f'{sql} {params}')
            else:    
                info = {}
                if description:
                    info['description'] = description
                if time:
                    info['TIME'] = time
                if days:
                    info['DAYS'] = days
                if url:
                    info['url'] = url
                INFO = json.dumps(info, ensure_ascii=False)
                if enable is not None:
                    STATE = Proc.STATE_ENABLED if enable else Proc.STATE_DISABLED
                else:
                    STATE = Proc.STATE_ENABLED
                sql = 'insert or replace into procs (CLASS, STATE, account_id, module, proc, INFO) values(?,?,?,?,?,?)'
                params = [CLASS, STATE, account_id, module, proc, INFO]
                cur.execute(sql, params)
                #log.debug(f'{sql} {params}')
                ID = cur.lastrowid
        return ID

    @staticmethod
    def delete(ID, module_id=None, proc=None):
        with sqlite3.connect(os.path.join(DOMINO_ROOT, 'data', 'jobs.db')) as conn:
            cur = conn.cursor()
            if module_id is None:
                sql = 'delete from procs where ID=?'
                params = [ID]
            else:
                sql = 'delete from procs where account_id=? and module =? and proc=?'
                params = [ID, module_id, proc]

            cur.execute(sql, params)

    @staticmethod
    def change_state(ID, STATE):
        with sqlite3.connect(os.path.join(DOMINO_ROOT, 'data', 'jobs.db')) as conn:
            cur = conn.cursor()
            sql = 'update procs set STATE=? where ID=?'
            params = [STATE, ID]
            cur.execute(sql, params)

    @staticmethod
    def _last_job(cur, proc_ID):
        sql = 'select ID, STATE, START_DATE from proc_jobs where proc_id=? order by start_date desc limit 1'
        cur.execute(sql, [proc_ID])
        job = cur.fetchone()
        if job is None:
            return (None, None, None)
        else:
            ID, STATE, START_DATE = job
            try:
                if START_DATE:
                    START_DATE = arrow.get(START_DATE).date()
            except:
                START_DATE = None
            STATE = int(STATE)
            return ID, STATE, START_DATE

    @staticmethod
    def start_by_id(proc_ID, name=None, description=None, info=None):
        if proc_ID is None:
            return
        r = redis.StrictRedis(host='localhost', port=6379)
        msg = {"ID":proc_ID}
        if name:
            msg['NAME'] = name
        if description:
            msg['DESCRIPTION'] = description
        if info is not None:
            msg['INFO'] = info
        else:
            msg['INFO'] = {}
        msg = json.dumps(msg)
        #log.debug(f'Proc.start_by_id({proc_ID}) : redis.publish(job:start, {msg})')
        r.publish('job:start', msg)
        #with Proc.connect() as conn:
        #    cur = conn.cursor()
        #    job_ID = Proc._start(cur, proc_ID)
        #Job.START(job_ID)                
        #return job_ID

    @staticmethod
    def get_id(account_id, module, proc):
        proc_ID = None
        if not account_id:
            account_id = Proc.NO_ACCOUNT_ID
        with Proc.connect() as conn:
            cur = conn.cursor()
            sql = 'select ID from procs where account_id=? and module = ? and proc=?'
            params = [account_id, module, proc]
            cur.execute(sql, params)
            r = cur.fetchone()
            if r is not None:
                proc_ID, = r
        return proc_ID

    @staticmethod
    def start(account_id, module, proc, name=None, description=None, info=None):
        proc_ID = Proc.get_id(account_id, module, proc)
        if proc_ID:
            Proc.start_by_id(proc_ID, name=name, description=description, info=info)
        #    job_ID = Proc._start(cur, proc_ID)
        #Job.START(job_ID)                
        #return job_ID

    @staticmethod
    def clean(ID):
        with Proc.connect() as conn:
            cur = conn.cursor()
            qdate = datetime.now() - timedelta(minutes=10)
            cur.execute('select ID from proc_jobs where proc_id=? and (state > 100 or state = -2 or state=-1)', [ID])
            jobs = cur.fetchall()
        for job_ID, in jobs:
            Proc.Job.delete(job_ID)
        return len(jobs)

    @staticmethod
    def autostart(ID, TIME = None, DAYS = None):
        with Proc.connect() as conn:
            cur = conn.cursor()
            cur.execute('select INFO from procs where ID=?', [int(ID)])
            INFO = cur.fetchone()[0]
            info = json.loads(INFO)
            if TIME:
                info['TIME'] = TIME
            else:
                if 'TIME' in info:
                    del info['TIME']
            if DAYS:
                info['DAYS'] = DAYS
            else:
                if 'DAYS' in info:
                    del info['DAYS']
            INFO = json.dumps(info, ensure_ascii=False)
            cur.execute('update procs set info = ? where ID=?', [INFO, int(ID)])







        
