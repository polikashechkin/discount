import os, datetime, sqlite3, arrow, json, time
from domino.core import log, DOMINO_ROOT
from . import Page as BasePage
from . import Button, Toolbar, Title, Text, FlatButton
from domino.page_controls import TabControl, print_check_button, print_std_buttons, Кнопка, ПлоскаяТаблица
from domino.jobs import JobReport, Задача, remove_job, JOBS_DB, Proc

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.product_id = application.product_id
        self.is_domino = self.application.product_id == 'domino'

    def __call__(self):
        Title(self, 'Процедуры')
        toolbar = Toolbar(self, 'toolbar').mb(0.5)
        if not self.sheduler_online():
            Button(toolbar, 'ПЛАНИРОВШИК НЕ ЗАПУЩЕН, ПРОЦЕДУРЫ АВТОМАТИЧЕСКИ ЗАПУСКАТСЯ НЕ МОГУТ')\
                .style('color:white; background-color:red').disabled(True)
        else:
            Button(toolbar, 'ПЛАНИРОВШИК ЗАПУЩЕН, ПРОЦЕДУРЫ БУДУТ ЗАПУСКАТСЯ ПО РАСПИСАНИЮ')\
                .style('color:green; -background-color:red').disabled(True)


        Button(toolbar.item(ml='auto'), 'Задачи/Процессы').onclick('domino/pages/jobs')

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
        table.column().text('Расписание')
        table.column().text('Последний запуск')
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

        # расписание
        cell = row.cell()
        if STATE != Proc.STATE_DISABLED:
            if CLASS == 0:
                TIME = info.get('TIME','')
                DAYS = info.get('DAYS', '')
                if TIME:
                    if DAYS:
                        cell.href(f'{DAYS} каждого месяца в {TIME}', 'domino/pages/proc_shedule', {'proc_id':ID})
                    else:
                        cell.href(f'Ежедневно в {TIME}', 'domino/pages/proc_shedule', {'proc_id':ID})
                else:
                    cell.style('color:ref')
                    #FlatButton(cell, 'Задать расписание').onclick('domino/pages/proc_shedule', {'proc_id':ID})
                    cell.href(f'не задано'.upper(), 'domino/pages/proc_shedule', {'proc_id':ID}, style='color:lightgray')
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
            text.href(f'{JOB_ID} ({START_DATE})', 'domino/pages/job', {'job_id':JOB_ID})
        
        # Команды
        cell = row.cell(width=10).css('text-right')
        if STATE == Proc.STATE_ENABLED:
            if CLASS == 0:
                #cell.icon_button('edit', style='color:lightgray').onclick('.edit', {'proc_id':ID, 'job_id':JOB_ID})
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

