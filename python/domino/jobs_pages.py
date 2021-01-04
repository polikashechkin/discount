import os, datetime, sqlite3, arrow, flask, json, time
from domino.core import log, DOMINO_ROOT
from domino.page import Page, Filter
from domino.page_controls import TabControl, print_check_button, print_std_buttons, Кнопка, ПлоскаяТаблица
from domino.jobs import JobReport, Задача, remove_job, JOBS_DB, Proc
from domino.application import make_download_file_responce
from domino.application import make_show_file_responce

def download_job_file(request):
    job_id = request.args.get('job_id')
    file_name = request.args.get('file_name')
    file = os.path.join(DOMINO_ROOT, 'jobs', job_id, file_name)
    log.debug(f'download_job_file : {file} : {os.path.getsize(file)} : {file_name}')
    with open(file, 'rb') as f:
        response  = flask.make_response(f.read())
    response.headers['Content-Type'] = 'application/octet-stream'
    response.headers['Content-Description'] = 'File Transfer'
    response.headers['Content-Disposition'] = f'attachment; filename={file_name}'
    response.headers['Content-Length'] = os.path.getsize(file)
    return response

JobTabs = TabControl('job_tabs')
JobTabs.item('log', 'Журнал', 'print_log')
JobTabs.item('files', 'Файлы', 'print_files')

class JobPage(Page):
    def __init__(self, application, request):
        super().__init__(application, request, controls=[JobTabs])
        self.ID = self.attribute('job_id')
        with Proc.connect() as conn:
            cur = conn.cursor()
            sql = '''
            select 
            JOB.STATE, JOB.START_DATE, JOB.END_DATE, JOB.DESCRIPTION, JOB.NAME, JOB.UUID, JOB.PID,
            PROC.ACCOUNT_ID, PROC.MODULE, PROC.PROC, PROC.INFO
            from proc_jobs JOB join procs PROC on JOB.PROC_ID = PROC.ID
            where JOB.ID=?
            '''
            cur.execute(sql, [self.ID])
            self.JOB_STATE, self.JOB_START_DATE, self.JOB_END_DATE, self.JOB_DESCRIPTION, self.JOB_NAME, self.JOB_GUID, self.JOB_PID, \
            self.PROC_ACCOUNT_ID, self.PROC_MODULE, self.PROC_PROC, self.PROC_INFO \
                = cur.fetchone()
        self.proc_info = json.loads(self.PROC_INFO)
        self.error_message = Proc.Job.get_error_message(self.ID)
        if self.error_message:
            self.JOB_STATE = Proc.Job.STATE_ERROR

    @property
    def DESCRIPTION(self):
        if self.JOB_DESCRIPTION:
            return self.JOB_DESCRIPTION
        else:
            return self.proc_info.get('description', '')

    @property
    def JOB_TIME(self):
        return ''

    @property
    def JOB_ERROR(self):
        return self.error_message

    def print_files(self):
        table = ПлоскаяТаблица(self, 'table').mt(1)
        folder = os.path.join(DOMINO_ROOT, 'jobs', str(self.ID))
        for name in os.listdir(folder):
            if (name.endswith('.txt') or name.endswith('.zip') or name.endswith('.csv') or name.endswith('.xml') or name.endswith('.json')) and not name.startswith('_'):
                size = os.path.getsize(os.path.join(folder,name))
                if size > 0:
                    row = table.row()
                    row.text(name)
                    row.text(f'{size:,}')
                    Кнопка(row.cell(width=10).css('text-right'), 'Выгрузить').onclick('download_job_file', {"file_name":name, "job_id":self.ID}, target='download')
                    #Кнопка(row.cell(width=10), 'Посмотреть').onclick('show_job_file', {"file_name":name, "job_id":self.job.id}, target='new_window')

    def print_log(self):
        table = self.Table('table')
        log_file = os.path.join(DOMINO_ROOT, 'jobs', self.ID, 'log') 
        if os.path.isfile(log_file):
            previous = None
            продолжительность = None
            with open(log_file) as f:
                for line in f:
                    try:
                        row = table.row()
                        start_string, message = (line.strip('\n\r')).split('\t')
                        start = arrow.get(start_string)
                        #row.cell(width=10, style='white-space:nowrap').text(start.format('YYYY-MM-DD HH:mm:ss'))
                        row.cell(width=10, style='white-space:nowrap').text(start.format('HH:mm:ss'))
                        if previous is not None:
                            #row.cell().text(f'{продолжительность}')
                            продолжительность = start - previous
                            #row.cell().text(f'{start.datetime} - {previous.datetime}')
                            продолжительность = round(продолжительность.total_seconds(), 3)
                            cell = row.cell(style='white-space:nowrap')
                            if продолжительность:
                                cell.text(f'{продолжительность} c')
                        row.cell().text(message)
                        previous = start
                    except:
                        pass

    def print_params(self):
        
        params = ПлоскаяТаблица(self, 'params').cls('table-borderless').cls('shadow-sm', False)
        if self.JOB_STATE == Proc.Job.STATE_ONLINE:
            stat = f'В РАБОТЕ ({self.JOB_PID}), Начало {self.JOB_START_DATE}'
        elif self.JOB_STATE == Proc.Job.STATE_SUCCESS:
            stat = f'УСПЕШНО ЗАВЕРШЕНО, Начало {self.JOB_START_DATE}, Окончание {self.JOB_END_DATE}, Продолжительность {self.JOB_TIME}'
        elif self.JOB_STATE == Proc.Job.STATE_ERROR:
            stat = f'ЗАВЕРШЕНО С ОШИБКОЙ,  Начало {self.JOB_START_DATE}, Окончание {self.JOB_END_DATE}, Продолжительность {self.JOB_TIME}'
        else:
            stat = f'НЕИЗВЕСТНЫЙ СТАТУС "{self.JOB_STATE}", Начало {self.JOB_START_DATE}'

        state = params.row('state')
        state.text('Состояние')
        state.text(stat)

        if self.JOB_STATE == Proc.Job.STATE_ERROR:
            row = params.row() 
            row.text('Ошибка')
            row.text(self.JOB_ERROR, style='color:red; font-size: large')
 
        p = []
        p.append(f'GUID "{self.JOB_GUID}"')
        if self.PROC_ACCOUNT_ID is not None:
            p.append(f'Учетная запись "{self.PROC_ACCOUNT_ID}"')
        p.append(f'Модуль "{self.PROC_MODULE}"')
        p.append(f'Процедура "{self.PROC_PROC}"')
        if self.JOB_NAME:
            p.append(f'Имя "{self.JOB_NAME}"')
        
        #argv = self.job.params.get('argv')
        #args = []
        #if argv is not None:
        #    for arg in argv:
        #        if arg is None or arg.strip() == '':
        #            args.append('')    
        #        else:
        #            args.append(f'"{arg}"')
        #args = ' '.join(args)
        #p.append(f'Параметры запуска "{args}"')

        row = params.row() 
        row.text('Параметры')
        row.text(', '.join(p))

    def open(self):
        self.title(f'{self.ID} {self.DESCRIPTION} ')
        self.print_params()
        JobTabs(self)
# ---------------------------------------------------------------------------
# JOBS
# ---------------------------------------------------------------------------

jobs_pages_jobs_tabs = TabControl('jobs_pages_jobs_tabs')
jobs_pages_jobs_tabs.item('current', 'Текущие', 'print_current_jobs')
jobs_pages_jobs_tabs.item('latest', 'Недавние', 'print_latest_jobs')
jobs_pages_jobs_tabs.item('archive', 'Архив', 'print_archive_jobs')

class JobsPage(Page):
    def __init__(self, application, request):
        super().__init__(application, request, controls=[jobs_pages_jobs_tabs])
        self.job_id = self.attribute('job_id')
        self.конкретная_учетная_запись = True
        self._connection = None
        self._cursor = None
        self.is_domino = self.application.product_id == 'domino'
    @property
    def connection(self):
        if self._connection is None:
            self._connection = Proc.Job.connect()
        return self._connection
    @property
    def cursor(self):
        if self._cursor is None:
            self._cursor = self.connection.cursor()
        return self._cursor
    
    def delete(self):
        ID = self.get('job_id')
        Proc.Job.delete(ID)
        self.Row('table', ID)
        self.message(f'Удалена задача "{ID}"')

    def print_job_status(self, cell, STATE):
        if STATE == Proc.Job.STATE_ONLINE:
            # Работающие задачи
            cell.glif('spinner', css='fa-pulse')
        elif STATE == Proc.Job.STATE_STOPPING:
            cell.glif('ban', style='color:tomato', css=' fa-pulse')
        elif STATE == Proc.Job.STATE_ABORT:
            cell.glif('trash', style='color:gray')
        elif STATE == Proc.Job.STATE_SUCCESS:
            pass
        elif STATE == Proc.Job.STATE_ERROR:
            cell.glif('star', style='color:red')
        elif STATE == Proc.Job.STATE_STARTING:
            cell.glif('star', style='color:gray', css='fa-pulse')
        else:
            cell.text(STATE)

    def print_row(self, row, ID, PROC_ID, STATE, START_DATE, DESCRIPTION, INFO, ACCOUNT_ID):
        ID = str(ID)
        error_message = Proc.Job.get_error_message(ID)
        if error_message:
            STATE = Proc.Job.STATE_ERROR
        self.print_job_status(row.cell(), STATE)
        #row.cell().text(STATE)
        row.href(ID, 'job', {"job_id":ID})
        row.text(f'{START_DATE}')
        row.text(DESCRIPTION)
        cell = row.cell().css('text-right')
        if STATE != Proc.Job.STATE_ONLINE:
            cell.icon_button('close', style='color:red').onclick('.delete', {'job_id':ID})
        else:
            cell.icon_button('ban', style='color:tomato').onclick('.stop', {'job_id':ID})\
                .tooltip('послать сигнал на завершение задачи')

    def print_jobs(self, where_clause, params):
        #self.toolbar('toolbar').mt(1).cls('table-borderless')
        table = self.Table('table').mt(0.5).cls('table-borderless table-sm').cls('shadow-sm', False)
        if self.is_domino:
            account_query = ''
        else:
            account_query = f' and PROC.ACCOUNT_ID = ?'
            params.append(self.account_id)

        sql = f'''
            select 
            JOB.ID, JOB.STATE, JOB.PROC_ID, JOB.START_DATE, JOB.DESCRIPTION, JOB.INFO,
            PROC.INFO, PROC.ACCOUNT_ID
            from proc_jobs JOB join procs PROC on JOB.PROC_ID = PROC.ID  
            where ({where_clause}) {account_query} 
            order by JOB.START_DATE desc limit 200
            '''
        self.cursor.execute(sql, params)
        for ID, STATE, PROC_ID, START_DATE, DESCRIPTION, INFO, PROC_INFO, ACCOUNT_ID in self.cursor:
            row = table.row(ID)
            proc_info = json.loads(PROC_INFO)
            if not DESCRIPTION:
                DESCRIPTION = proc_info.get('description','')
            self.print_row(row, ID, PROC_ID, STATE, START_DATE, DESCRIPTION, INFO, ACCOUNT_ID)

    def print_current_jobs(self):
        Proc.Job.check()
        self.Toolbar('toolbar')
        self.print_jobs('JOB.STATE == 0 or JOB.START_DATE > ?', [datetime.datetime.now() - datetime.timedelta(days=2)])

    def print_latest_jobs(self):
        self.Toolbar('toolbar')
        self.print_jobs('JOB.START_DATE > ?', [datetime.datetime.now() - datetime.timedelta(days=30)])
    
    def delete_all_archive_jobs(self):
        where_clause = 'JOB.START_DATE < ? and JOB.STATE != 0'
        params = [datetime.datetime.now() - datetime.timedelta(days=30)]
        if self.is_domino:
            account_query = ''
        else:
            account_query = f' and PROC.ACCOUNT_ID = ?'
            params.append(self.account_id)

        sql = f'''
            select 
            JOB.ID
            from proc_jobs JOB join procs PROC on JOB.PROC_ID = PROC.ID  
            where ({where_clause}) {account_query} 
            order by JOB.START_DATE desc limit 200
            '''
        self.cursor.execute(sql, params)
        jobs = self.cursor.fetchall()
        for ID, in jobs:
            Proc.Job.delete(ID)
        self.message(f'Удалено {len(jobs)} задач.')
        self.print_archive_jobs()

    def print_archive_jobs(self):
        toolbar = self.Toolbar('toolbar').mt(0.5)
        button = Кнопка(toolbar, 'Удалить все задачи', ml='auto')
        button.onclick('.delete_all_archive_jobs')
        self.print_jobs('JOB.START_DATE < ?', [datetime.datetime.now() - datetime.timedelta(days=30)])

    def open(self):
        self.title('Задачи')
        jobs_pages_jobs_tabs(self)

# ---------------------------------------------------------------------------
# PROCS PAGE
# ---------------------------------------------------------------------------

class ProcsPage(Page):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.product_id = application.product_id
        self.is_domino = self.application.product_id == 'domino'

    def __call__(self):
        self.title('Процедуры')
        if not self.sheduler_online():
            self.text_block().style('color:red')
            self.text('ПЛАНИРОВШИК НЕ ЗАПУЩЕН, ПРОЦЕДУРЫ АВТОМАТИЧЕСКИ ЗАПУСКАТСЯ НЕ МОГУТ')
        self.print_table()
    
    def sheduler_online(self):
        conn = Proc.connect()
        cur = conn.cursor()
        try:
            cur.execute('select ID from procs where account_id=? and module=? and proc=?', ['', 'domino', 'sheduler.py'])
            ID = cur.fetchone()[0]
            sql = f'select count(*) from proc_jobs where STATE = 0 and proc_id = {ID}'
            log.debug(sql)
            cur.execute(sql)
            count = cur.fetchone()[0]
            return count > 0
        except:
            log.exception(__name__)
            return False

    def print_table(self):
        conn = Proc.connect()
        cur = conn.cursor()
        if self.product_id == 'domino':
            cur.execute('select ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO from procs')
        else:
            cur.execute('select ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO from procs where ACCOUNT_ID=? and MODULE = ?', [self.account_id, self.product_id])
        procs = cur.fetchall()

        table = self.Table('table')
        table.column()
        table.column().text('#')
        if self.is_domino:
            table.column().text('Учетная запись')
            table.column().text('Модуль')
        table.column().text('Процедура')
        table.column().text('Автозапуск')
        table.column().text('Последняя задача')
        table.column().text('')
        for ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO in procs:
            row = table.row(ID)
            self.print_row(cur, row, ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO)
        conn.close()

    def print_edit(self, cur, row, ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO):
        info = json.loads(INFO)
        
        # Состояние
        cell = row.cell(width=2)
        if STATE == Proc.STATE_ENABLED:
            cell.icon_button('check', style='color:green')
        else:
            cell.icon_button('check', style='color:lightgray')
        #button.onclick('.change_state', {'proc_id':ID})

        # ID
        row.cell().text(ID)
        # ACCOUNT_ID
        if self.is_domino:
            row.cell().text(ACCOUNT_ID)
        # Процедура
        cell = row.cell()
        description = info.get('description', f'{ACCOUNT_ID}.{MODULE}.{PROC}')
        if STATE == Proc.STATE_DISABLED:
            cell.style('color:lightgray')
            cell.text(description)
        else:
            #url = info.get('url')
            #if url:
            #    cell.href(description, url, {})
            #else:
            cell.text(description)

        # Автозапуск
        cell = row.cell()
        #toolbar = cell.toolbar()
        TIME = info.get('TIME','')
        DAYS = info.get('DAYS', '')
        cell.input(label='Вермя', name='proc_time', value=TIME)
        cell.input(label='Дни', name='proc_days', value=DAYS)
        #if STATE == Proc.STATE_DISABLED:
        #    cell.style('color:lightgray')
        #if CLASS == 0:
        #    TIME = info.get('TIME','')
        #    DAYS = info.get('DAYS', '')
        #    if TIME:
        #        cell.text(f'{TIME} {DAYS}')
                #cell.icon_button('edit', style='color:lightgray')
        #    else:
        #        cell.text('НЕТ')
        #elif CLASS == 1:
        #    cell.text('ПОСТОЯННО')
        #elif CLASS == 2:
        #    cell.text('ПРИ СТАРТЕ')
        
        # Последняя задача
        text = row.cell().text_block()
        JOB_ID, JOB_STATE, START_DATE = Proc._last_job(cur, ID)
        if JOB_ID:
            if JOB_STATE == Proc.Job.STATE_ONLINE:
                text.glif('spinner', css=' fa-pulse')
            elif JOB_STATE == Proc.Job.STATE_STOPPING:
                text.glif('ban', css=' fa-pulse', style='color:tomato')
            elif JOB_STATE == Proc.Job.STATE_SUCCESS:
                pass
            elif JOB_STATE == Proc.Job.STATE_ABORT:
                text.glif('trash', style='color:gray')
            else:
                text.text(JOB_STATE)
            text.text(' ')
            #text.href(f'{JOB_ID} ({START_DATE})', 'job', {'job_id':JOB_ID})
        
        # Команды
        cell = row.cell(width=10).css('text-right')
        cell.icon_button('check', style='color:green').onclick('.save', {'proc_id':ID}, forms=[row])
        cell.icon_button('close', style='color:gray').onclick('.cancel', {'proc_id':ID})

    def print_row(self, cur, row, ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO):
        info = json.loads(INFO)
        
        # Состояние
        cell = row.cell(width=2)
        if STATE == Proc.STATE_ENABLED:
            button = cell.icon_button('check', style='color:green')
        else:
            button = cell.icon_button('check', style='color:lightgray')
        button.onclick('.change_state', {'proc_id':ID})

        # ID
        row.cell().text(ID)
        if self.is_domino:
            row.cell().text(ACCOUNT_ID)
            row.cell().text(MODULE)

        # Процедура
        cell = row.cell()
        description = info.get('description', f'{ACCOUNT_ID}.{MODULE}.{PROC}')
        if STATE == Proc.STATE_DISABLED:
            cell.style('color:lightgray')
            cell.text(description)
        else:
            url = info.get('url')
            if url and url != 'None' and not self.is_domino:
                cell.href(description, url, {})
            else:
                cell.text(description)

        # Автозапуск
        cell = row.cell()
        if STATE == Proc.STATE_DISABLED:
            cell.style('color:lightgray')
        if CLASS == 0:
            TIME = info.get('TIME','')
            DAYS = info.get('DAYS', '')
            if TIME:
                cell.text(f'{TIME} {DAYS}')
                #cell.icon_button('edit', style='color:lightgray')
            else:
                cell.text('-')
        elif CLASS == 1:
            cell.text('ПОСТОЯННО')
        elif CLASS == 2:
            cell.text('ПРИ СТАРТЕ')
        
        # Последняя задача
        cell = row.cell()
        text = cell.text_block()
        JOB_ID, JOB_STATE, START_DATE = Proc._last_job(cur, ID)
        error_message = Proc.Job.get_error_message(JOB_ID)
        if error_message:
            JOB_STATE = Proc.Job.STATE_ERROR
        if JOB_ID:
            if JOB_STATE == Proc.Job.STATE_ONLINE:
                text.glif('spinner', css=' fa-pulse')
            elif JOB_STATE == Proc.Job.STATE_STOPPING:
                text.glif('ban', css=' fa-pulse', style='color:tomato')
            elif JOB_STATE == Proc.Job.STATE_SUCCESS:
                pass
            elif JOB_STATE == Proc.Job.STATE_ABORT:
                text.glif('trash', style='color:gray')
            elif JOB_STATE == Proc.Job.STATE_ERROR:
                text.glif('star', style='color:red')
                cell.tooltip(error_message)
            else:
                text.text(JOB_STATE)
            text.text(' ')
            text.href(f'{JOB_ID} ({START_DATE})', 'job', {'job_id':JOB_ID})
        
        # Команды
        cell = row.cell(width=10).css('text-right')
        if STATE == Proc.STATE_ENABLED:
            if CLASS == 0:
                cell.icon_button('edit', style='color:lightgray').onclick('.edit', {'proc_id':ID, 'job_id':JOB_ID})
                if JOB_ID and JOB_STATE == Proc.Job.STATE_ONLINE:
                    cell.icon_button('stop', style='color:tomato').onclick('.stop', {'proc_id':ID, 'job_id':JOB_ID})
                cell.icon_button('play_arrow', style='color:green').onclick('.start', {'proc_id':ID})
            elif CLASS == 1:
                if JOB_ID and JOB_STATE == Proc.Job.STATE_ONLINE:
                    cell.icon_button('refresh', style='color:green').onclick('.restart', {'proc_id':ID, 'job_id':JOB_ID})
                else:
                    cell.icon_button('play_arrow', style='color:green').onclick('.start', {'proc_id':ID})

    def change_state(self):
        ID = self.get('proc_id')
        with Proc.connect() as conn:
            cur = conn.cursor()
            cur.execute('select ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO from procs where ID=?', [ID])
            ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO = cur.fetchone()
            JOB_ID, JOB_STATE, START_DATE = Proc._last_job(cur, ID)
        
        if STATE == Proc.STATE_ENABLED:
            STATE = Proc.STATE_DISABLED
            if CLASS == 1:
                if JOB_ID and JOB_STATE == Proc.Job.STATE_ONLINE:
                    Proc.Job.stop(JOB_ID)
        else:
            STATE = Proc.STATE_ENABLED

        with Proc.connect() as conn:
            cur = conn.cursor()
            cur.execute('update procs set STATE=? where ID=?', [STATE, ID])
            row = self.Row('table', ID)
            self.print_row(cur, row, ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO)

    def update_row(self, ID):
        #time.sleep(0.5)
        with Proc.connect() as conn:
            cur = conn.cursor()
            cur.execute('select ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO from procs where ID=?', [ID])
            ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO = cur.fetchone()
            row = self.Row('table', ID)
            self.print_row(cur, row, ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO)

    def cancel(self):
        ID = self.get('proc_id')
        self.update_row(ID)

    def save(self):
        ID = self.get('proc_id')
        TIME = self.get('proc_time')
        DAYS = self.get('proc_days')
        with Proc.connect() as conn:
            cur = conn.cursor()
            cur.execute('select ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO from procs where ID=?', [ID])
            ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO = cur.fetchone()
            info = json.loads(INFO)
            info['TIME'] = TIME
            info['DAYS'] = DAYS
            INFO = json.dumps(info)
            cur.execute('update procs set INFO=? where ID=?', [INFO, ID])
            row = self.Row('table', ID)
            self.print_row(cur, row, ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO)

    def edit(self):
        ID = self.get('proc_id')
        #time.sleep(0.5)
        with Proc.connect() as conn:
            cur = conn.cursor()
            cur.execute('select ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO from procs where ID=?', [ID])
            ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO = cur.fetchone()
            row = self.Row('table', ID)
            self.print_edit(cur, row, ID, CLASS, STATE, ACCOUNT_ID, MODULE, PROC, INFO)

    def start(self):
        ID = self.get('proc_id')
        Proc.start_by_id(ID)
        self.update_row(ID)
        self.message(f'Запушена новая задача для процедуры "{ID}"')

    def restart(self):
        PROC_ID = self.get('proc_id')
        JOB_ID = self.get('job_id')
        Proc.Job.stop(JOB_ID)
        self.update_row(PROC_ID)
        self.message(f'Начат останов задачи "{JOB_ID}" и перезапуск процедуры "{ID}"')

    def stop(self):
        PROC_ID = self.get('proc_id')
        JOB_ID = self.get('job_id')
        Proc.Job.stop(JOB_ID)
        self.update_row(PROC_ID)
        self.message(f'Начат останов задачи "{JOB_ID}"')

