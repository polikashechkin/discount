import os, datetime, sqlite3, arrow, flask, json, time
from domino.core import log, DOMINO_ROOT
from domino.page import Page as BasePage
from domino.page_controls import TabControl, print_check_button, print_std_buttons, Кнопка, ПлоскаяТаблица
from domino.jobs import JobReport, Задача, remove_job, JOBS_DB, Proc

JobTabs = TabControl('job_tabs')
JobTabs.item('log', 'Журнал', 'print_log')
JobTabs.item('files', 'Файлы', 'print_files')

class Page(BasePage):

    def __init__(self, application, request):
        super().__init__(application, request, controls=[JobTabs])
        self.ID = self.attribute('job_id')
        with Proc.connect() as conn:
            cur = conn.cursor()
            sql = '''
            select 
                JOB.STATE, 
                JOB.START_DATE, 
                JOB.END_DATE, 
                JOB.DESCRIPTION, 
                JOB.NAME, 
                JOB.UUID, 
                JOB.PID,
                PROC.ACCOUNT_ID, 
                PROC.MODULE, 
                PROC.PROC, 
                PROC.INFO,
                JOB.INFO
            from 
                proc_jobs JOB join procs PROC on JOB.PROC_ID = PROC.ID
            where JOB.ID=?
            '''
            cur.execute(sql, [self.ID])
            self.JOB_STATE, self.JOB_START_DATE, self.JOB_END_DATE, self.JOB_DESCRIPTION, self.JOB_NAME, self.JOB_GUID, self.JOB_PID, \
            self.PROC_ACCOUNT_ID, self.PROC_MODULE, self.PROC_PROC, self.PROC_INFO, self.JOB_INFO \
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
                    Кнопка(row.cell(width=10).css('text-right'), 'Выгрузить').onclick('domino/job.download_file', {"file_name":name, "job_id":self.ID}, target='download')
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
        p.append(f'Параметры запуска "{self.JOB_INFO}"')
        
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

    def __call__(self):
        self.title(f'{self.ID} {self.DESCRIPTION} ')
        self.print_params()
        JobTabs(self)
