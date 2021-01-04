import os, datetime, sqlite3, arrow, flask, json, time
from domino.core import log, DOMINO_ROOT

from . import Page as BasePage
from . import Button, Toolbar, Title, Text

from domino.page_controls import TabControl, print_check_button, print_std_buttons, Кнопка, ПлоскаяТаблица
from domino.jobs import JobReport, Задача, remove_job, JOBS_DB, Proc

jobs_pages_jobs_tabs = TabControl('jobs_pages_jobs_tabs')
jobs_pages_jobs_tabs.item('current', 'Текущие', 'print_current_jobs')
jobs_pages_jobs_tabs.item('latest', 'Недавние', 'print_latest_jobs')
jobs_pages_jobs_tabs.item('archive', 'Архив', 'print_archive_jobs')

class Page(BasePage):
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
        row.href(ID, 'domino/pages/job', {"job_id":ID})
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

    def __call__(self):
        Title(self, 'Задачи / процессы')
        jobs_pages_jobs_tabs(self)

