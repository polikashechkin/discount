# -*- coding: utf-8 -*-
import os, sys, datetime, time, sqlite3, pickle, arrow, shutil, subprocess, psutil, re, glob
from domino.jobs import Proc
from domino.page import Page
from domino.core import log, start_log, DOMINO_ROOT
#from domino.databases import Databases
from discount.core import DISCOUNT_DB, PRODUCT_COLUMNS_FILE
#from discount.users import Пользователь
from discount.page import DiscountPage
from domino.page_controls import Кнопка, КраснаяКнопка
#from domino.crontab import CronJob, JOBS_DB
from domino.reports import Report
from domino.postgres import Postgres
from domino.page_controls import FormControl

TIMEOUT = 100
DESCRIPTION = 'Удаление чеков'
MODULE = 'discount'
PROC = 'remove_checks.py'
MIN_DAYS = 0

class КоличествоДней(FormControl.Param):
    def __init__(self):
        super().__init__('days', 'Количество дней хнанения чеков', type='number', min=10)
    def get_value(self, page):
        return page.proc.info.get('days', MIN_DAYS)
    def set_default(self, page):
        page.proc.info['days'] = MIN_DAYS
        page.proc.save()
    def save(self, page):
        days = int(page.get(self.ID))
        if days < 3:
            raise Exception('Количество дне не может быть менее 3-х')
        page.proc.info['days'] = days
        page.proc.save()

ПараметрыПроцедуры = FormControl('proc_params')
ПараметрыПроцедуры.append(КоличествоДней())

class ThePage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request, controls = [ПараметрыПроцедуры])
        self.proc = Proc.get(self.account_id, MODULE, PROC)

    def run(self):
        Proc,start(self.account_id, MODULE, PROC, description=DESCRIPTION)
        self.message(f'Запущена задача')

    def open(self):
        self.title(f'{self.proc.ID}, {DESCRIPTION}')
        p = self.toolbar('about').style('align-items:center')
        t = p.item().text_block()
        t.text('''
        Данная процедура удаляет чеки для освобождения дисковой памяти.
        ''') 
        КраснаяКнопка(p.item(ml='auto'), 'Запустить').onclick('.run')
        p = self.text_block().mt(1)
        p.header('Алгоритм')
        p.text('''
        Определяется список дней для удаления. Он определяется на 
        основании заданного количества дней от текущей даты.
        Поле этого, процедура перибирает дни и удаляет их по одному от конца списка.
        Удаляются дампы чеков и записи в таблице индексов чеков.
        ''')
        p = self.text_block().mt(1)
        p.text('''
        Реально дисковое простанство не возвращается в систему в случае с
        индексной таблицей чеков. Пространство высвобождается только для
        вторичного использования записями чеков. Это позволяет паралельно 
        с этим работать. Для реального высвобождения дискового простанства (если
        потребуется) можно сделать это с помощью средств управления БД.
        ''')
        p = self.text_block().mt(1)
        p.header('Параметры')
        ПараметрыПроцедуры(self)

class TheJob(Proc.Job):
    def __init__(self, ID):
        log.info(f'Запуск задачи {ID} : load')
        super().__init__(ID)
        self.report = {}
        self.tables = {}
        self.report['tables'] = self.tables
        self.table = {}
        self.tables['table'] = self.table
        self.columns = {}
        self.table['columns'] = [{}, {'type':'integer'}, {'type':'integer'}]

    def __call__(self):
        if self.account_id is None:
            self.error(f'Не задано учетной записи')
        
        self.DAYS = self.info.get('days', MIN_DAYS)
        if not self.DAYS:
            self.log('НЕ ЗАДАНО КОЛИЧЕСТВО ДНЕЙ')
            return
        else:
            self.log(f'КОЛИЧЕСТВО ДНЕЙ {self.DAYS}')
        
        self.pg_connection = Postgres.connect(self.account_id)
        self.pg_cursor = self.pg_connection.cursor()
        self.check_for_break()
        self.удаление_чеков()
        Proc.start(self.account_id, MODULE, 'cleaning.py', description=DESCRIPTION)
        self.log(f'Запущена задача "cleaning"')

    def список_дней_для_обработки(self, years_folder):
        LAST_DATE = datetime.date.today() - datetime.timedelta(days = self.DAYS)
        days = []
        for year in os.listdir(years_folder):
            year_folder = os.path.join(years_folder, year)
            for month in os.listdir(year_folder):
                month_folder = os.path.join(year_folder, month)
                for day in os.listdir(month_folder):
                    day_folder = os.path.join(month_folder, day)
                    try:
                        date = arrow.get(f'{year}-{month}-{day}').date()
                        if date < LAST_DATE:
                            days.append([date, day_folder])
                        else:
                            self.log(f'{date} : пропущено')
                    except BaseException as ex:
                        self.log(f'{day_folder} : {ex}')
        return days

    def удаление_чеков(self):
        self.log(f'УДАЛЕНИЕ ЧЕКОВ')
        folder = os.path.join(DOMINO_ROOT, 'accounts', self.account_id, 'data', 'discount', 'checks')
        days = self.список_дней_для_обработки(folder)

        for date, folder in days:
            self.check_for_break()
            try:
                with self.pg_connection:
                    self.pg_cursor.execute('delete from discount_check where check_date < %s', [date])
                    self.pg_connection.commit()
                #self.pg_cursor.execute('vacuum')
                shutil.rmtree(folder)
                self.log(f'{date}')
            except BaseException as ex:
                log.exception('remove_check')
                self.log(f'Удаление {date} {folder} : {ex}')

if __name__ == "__main__":
    ID = sys.argv[1]
    try:
        with TheJob(ID) as job:
            job()
    except:
        log.exception(__file__)

