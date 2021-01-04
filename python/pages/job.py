import flask, sqlite3, json, sys, os
from domino.page import Page
from domino.core import log
from domino.jobs import JobReport
from domino.page import Page
from domino.jobs_pages import JobTabControl, JobPage

domino_job_tabs = JobTabControl()
domino_job_tabs.append('started_jobs', 'Запущенные задачи', 'print_started_jobs', 'started_jobs_visible')

class ThePage(JobPage):
    def __init__(self, application, request):
        super().__init__(application, request, domino_job_tabs)

    def print_started_jobs(self):
        file = os.path.join(self.job.folder, 'started_jobs_file.txt')
        table = self.table('table', hole_update=True)
        if os.path.exists(file):
            table.column().text('Время запуска')
            table.column().text('Номер')
            table.column().text('Время (ms)')
            table.column().text('Процедура')
            table.column().text('Модуль')
            table.column().text('Учетная запись')
            try:
                with open(file) as f:
                    start, job_id, time_ms, module_id, procedure, account_id = f.read().split('\t', 5)
                    row = table.row()
                    row.text(start)
                    row.text(job_id)
                    row.text(round(float(time_ms), 6))
                    row.text(procedure)
                    row.text(module_id)
                    row.text(account_id)
            except BaseException as ex:
                table.row().text(f'{ex}')
    
    def started_jobs_visible(self):
        log.debug(f'started_jobs_visible(')
        return self.job.product_id == 'domino' and self.job.program == 'cron'


