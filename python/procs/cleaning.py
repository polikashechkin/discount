# -*- coding: utf-8 -*-
import os, sys, datetime, time, sqlite3, pickle, arrow, shutil, subprocess, psutil, re, glob

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.append(path)

from domino.jobs import Proc
#from domino.page import Page
from domino.core import log, start_log, DOMINO_ROOT
#from domino.databases import Databases
from discount.core import DISCOUNT_DB, PRODUCT_COLUMNS_FILE
#from discount.users import Пользователь
from discount.page import DiscountPage
from pages import Button, Table, Text, Title, Input, Toolbar
from domino.reports import Report
from domino.postgres import Postgres
from domino.page_controls import FormControl
from discount.schemas import Schema
from discount.actions import Action
from domino.databases.sqlite import Sqlite
from tables.sqlite.action_set_item import ActionSetItem
from tables.sqlite.complex_good_set_item import ComplexGoodSetItem
from tables.sqlite.product_set import ProductSet
#from tables.sqlite.product_set_item import ProductSetItem

TIMEOUT = 100
DESCRIPTION = 'Реорганизация данных'
PROC_ID = 'procs/cleaning.py'
MODULE_ID = 'discount'
MIN_DAYS = 2

POSTGRES = Postgres.Pool()

def on_activate(account_id, on_activate_log):
    Proc.create(account_id, MODULE_ID, PROC_ID, description = DESCRIPTION, url='procs/cleaning')

class Page(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.proc = Proc.get(self.account_id, MODULE_ID, PROC_ID)

    def change_params(self):
        days = int(self.get('days'))
        if days < 2:
            self.error('Количество дней не может быть менее 2-х')
            return
        self.proc.info['days'] = days
        self.proc.save()
        self.message(f'{days}')

    def __call__(self):
        Title(self, f'{self.proc.ID}, {DESCRIPTION}')
        Text(self).text('''
        Данная процедура очищает дисковое пространство, путем удалению потерявщих 
        актуальность данных. 
        ''') 
        #---------------------------------------
        p = Text(self).mt(1)
        p.header('Рабочие данные чека')
        p.text('''
        В процессе обработки чека создаются некоторые данные, которые нужны только 
        в период обработки чека, т.е. с момента его создания и до момента его 
        пробития. Также это касается данных дополнительного протоколирования,
        которые не имеют значения в историческом плане. 
        Все эти данные хранятся только заданное количество дней, затем уничтожаются. Минимально необходимо
        хранить рабочие данные в течение 2-х дней.
        ''')
        check_params = Toolbar(self, 'check_params').mt(0.5)
        Input(check_params.item(), name='days', label='Количество дней', value=self.proc.info.get('days', 2))\
            .onkeypress(13, '.change_params', forms=[check_params])
        #------------------------------------------
        p = Text(self).mt(1)
        p.header('Акции и товарные наборы')
        p.text('''
        Удаляются "висячие" акции, которые не связаны ни с одной дисконтоной схемой. 
        Также удаляются "висячие" индивидуальные наборы не свзанные ни с одной акцией.
        ''')

class TheJob(Proc.Job):
    def __init__(self, ID):
        #log.info(f'Запуск задачи {ID} : cleaning')
        super().__init__(ID)

    def __call__(self):
        self.pg_connection = Postgres.connect(self.account_id)
        self.pg_cursor = self.pg_connection.cursor()
        self.SQLITE = Sqlite.Pool().session(self.account_id, module_id=MODULE_ID)
        
        self.connection = sqlite3.connect(DISCOUNT_DB(self.account_id))
        self.cursor = self.connection.cursor()

        try:
            self.dowork()
            self.SQLITE.commit()
        except Exception as ex:
            log.exception(__file__)
            self.log(f'{ex}')
            self.SQLITE.rollback()
            raise Exception(ex)
        finally:
            self.SQLITE.close()

        self.connection.commit()
        self.connection.close()

        if self.pg_connection is not None:
            self.pg_connection.close()
        log.info(f'ЗАВЕРШЕНО УСПЕШНО')

    def dowork(self):
        #self.удаление_расчетов()
        self.calc_used_actions()
        #self.clean_actions()
        #self.clean_product_sets()
        #self.create_report()

    def create_report(self):
        #if self.account_id is None:
        #    self.error(f'Не задано учетной записи')
        
        self.total, self.used, self.free = shutil.disk_usage(os.path.join(DOMINO_ROOT, 'accounts', self.account_id))
        self.log(f'Использованное дисковое пространство : {self.used}')
        
        self.GIG = 1024 * 1024 * 1024

        mem = psutil.virtual_memory()
        total = mem[0]
        report = Report(self.account_id, MODULE_ID, 'Использование дискового пространства')
        table = report.table(Report.DEFAULT_TABLE)
        table.columns = {
            'name' :    { },
            'value':    { 'type':'integer'},
            'percent':  { }
            }

        #self.удаление_протоколов()

        self.log('РАСЧЕТ ИСПОЛЬЗУЕМОГО ПРОСТРАНСТВА')
        total, used, free = shutil.disk_usage(os.path.join(DOMINO_ROOT, 'accounts', self.account_id))
        table.row('total', values = ['Общее дисковое пространство', total, ''])
        table.row('used', values = ['Используемое дисковое пространство', used, ''])

        free_p = round(free / total * 100, 0)
        table.row('free', values = ['Свободное дисковое пространство', free, f'{free_p}%'])

        size = self.du(os.path.join(DOMINO_ROOT,'accounts', self.account_id))
        accouns_p = size * 100.0 / total
        accouns_p = round(accouns_p, 2)
        table.row('account_size', values = ['Дисковое простанство для учетной записи', size, f'{accouns_p}%'])

        size = self.du(os.path.join(DOMINO_ROOT,'accounts', self.account_id, 'data', 'discount', 'calc'))
        table.row('calc_size', values = ['Используемое пространство для рсчетов', size, ''])

        dump_size = self.du(os.path.join(DOMINO_ROOT,'accounts', self.account_id, 'data', 'discount', 'checks'))
        table.row('dump_size', values = ['Используемое пространство для дампов чеков', dump_size, ''])

        self.pg_cursor.execute("select pg_total_relation_size('discount_check')")
        table_size = self.pg_cursor.fetchone()[0]
        table.row('table_size', values = ['Размер индексной таблицы чеков', table_size, ''])

        self.pg_cursor.execute('select count(*) from discount_check') 
        checks = self.pg_cursor.fetchone()[0]
        table.row('checks', values = ['Общее количество чеклв', checks, ''])

        if checks:
            min_check_size = int((table_size + dump_size) / checks)
            table.row('min_check_size', values = ['Приблизительная оценка размера чека', min_check_size, ''])

            self.pg_cursor.execute('select count(*) from (select count(*) count, check_date::date date from discount_check group by check_date::date) days')
            days = self.pg_cursor.fetchone()[0]
            if days:
                table.row('days', values = ['Количество торговых дней', days, ''])
                checks_of_day = int(checks/days)
                table.row('checks_of_day', values = ['Среднее количество чеков в день', checks_of_day, ''])
                if checks_of_day and min_check_size:
                    free_days = int(free/(checks_of_day * min_check_size))
                    table.row('free_days', values = ['Приблизительное количество дней, для которых есть еще место', free_days, ''])
 
        self.log(f'Освобождено : {self.used - used}')

        report.create()
        self.log(f'СОХРАНЕНИЕ ОТЧЕТА')

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

    def удаление_расчетов(self):
        self.log(f'УДАЛЕНИЕ РАСЧЕТОВ')
        self.DAYS = int(self.info.get('days', MIN_DAYS))
        self.log(f'Количество дней {self.DAYS}')

        calc_folder = os.path.join(DOMINO_ROOT, 'accounts', self.account_id, 'data', 'discount', 'calc')
        days = self.список_дней_для_обработки(calc_folder)

        for date, folder in days:
            try:
                shutil.rmtree(folder)
                self.log(f'Удаление {date} {folder}')
            except BaseException as ex:
                log.exception('cleaning')
                self.log(f'Удаление {date} {folder} : {ex}')

    def удаление_протоколов(self):
        self.log(f'УДАЛЕНИЕ ПРОТОКОЛОВ')
        folder = os.path.join(DOMINO_ROOT, 'accounts', self.account_id, 'data', 'discount', 'checks')
        days = self.список_дней_для_обработки(folder)
        
        for date, folder in days:
            for dept_name in os.listdir(folder):
                dept_folder = os.path.join(folder, dept_name)
                xml_count = 0
                xml_error = 0
                for path in glob.glob(f'{dept_folder}/*.xml'):
                    xml_count += 1
                    try:
                        os.remove(path)
                    except:
                        xml_error += 1
                        log.exception('')

                log_count = 0
                log_error = 0
                for path in glob.glob(f'{dept_folder}/*.log'):
                    log_count += 1
                    try:
                        os.remove(path)
                    except:
                        log_error += 1
                        log.exception('')

                stop_count = 0
                stop_error = 0
                for path in glob.glob(f'{dept_folder}/*.log'):
                    stop_count += 1
                    try:
                        os.remove(path)
                    except:
                        stop_error += 1
                        log.exception('')
                count = xml_count + log_count + stop_count
                error = xml_error + log_error + stop_error
                if count:
                    self.log(f'{date} удалено {count} ощибок {error}')
        self.log(f'обработано {len(days)} дней')
    
    def clean_product_sets(self):
        self.log('ОЧИСТКА ТОВАРНЫХ НАБОРОВ')

    def calc_used_actions(self):
        self.log('РЕОГРАНИЗАЦИЯ ОПИСАНИЯ ДИСКОНТНЫХ СХЕМ')
        #--------------------------------
        self.used_actions = set()
        count = 0
        comments = []
        for schema in Schema.findall(self.cursor):
            count += 1
            comments.append(f'{schema.ID}:{schema.наименование}')
            self.used_actions.update(schema.get_used_actions())
        self.log(f'Всего схем {count} : {", ".join(comments)}')
        #--------------------------------
        #self.all_actions = set()
        #self.unused_actions = set()
        #for action_id, in self.SQLITE.execute('select id from actions'):
        #    self.all_actions.add(action_id)
        #    if action_id not in self.used_actions:
        #        self.unused_actions.add(action_id)
        #self.log(f'Всего акций : {len(self.all_actions)} : {self.all_actions}')
        self.log(f'Используемых акций : {len(self.used_actions)} : {self.used_actions}')
        #self.log(f'Неиспользуемых акций : {len(self.unused_actions)} : {self.unused_actions}')
        #--------------------------------
        a = f'({",".join(str(a) for a in self.used_actions)})'
        self.log(f'УДАЛЕНИЕ НЕИСПОЛЬЗУЕМЫХ АКЦИЙ')
        sql = f'delete from actions where id not in {a}'
        self.log(sql)
        self.SQLITE.execute(sql)
        sql = f'delete from action_set_item where action_id not in {a}'
        self.log(sql)
        self.SQLITE.execute(sql)
        self.SQLITE.commit()
        #--------------------------------
        self.used_sets = set()
        self.used_sets.add(ProductSet.ПОСТОЯННО_ИСКЛЮЧЕННЫЕ_ТОВАРЫ_ID)
        self.complex_sets = set()
        for set_id, ps in self.SQLITE.query(ActionSetItem.set_id, ProductSet)\
            .outerjoin(ProductSet, ProductSet.id == ActionSetItem.set_id)\
            .filter(ActionSetItem.action_id.in_(self.used_actions)):
            if not ps:
                self.log(f'НЕСУЩЕСТВУЮЩИЙ НАБОР {set_id}')
            self.used_sets.add(set_id)
            if ps.type_ == ProductSet.КОМПЛЕКСНЫЙ_НАБОР:
                self.complex_sets.add(set_id)
        for set_id, in self.SQLITE.query(ComplexGoodSetItem.set_id)\
            .filter(ActionSetItem.set_id.in_(self.complex_sets)):
            self.used_sets.add(set_id)
        for child_id, in self.SQLITE.query(ComplexGoodSetItem.child_id)\
            .filter(ComplexGoodSetItem.set_id.in_(self.complex_sets)):
                self.used_sets.add(child_id)
        self.log(f'Используемых наборов : {len(self.used_sets)} : {self.used_sets}')
        self.log(f'В т.ч. комплексных : {len(self.complex_sets)} : {self.complex_sets}')
        #--------------------------------
        self.log(f'УДАЛЕНИЕ НЕИСПОЛЬЗУЕМЫХ ИНДИВИДУАЛЬНЫХ НАБОРОВ')
        used = f'({",".join(str(id) for id in self.used_sets)})'
        sql = f'delete from product_set where "class" = {ProductSet.ИНДИВИДУАЛЬНЫЙ_НАБОР}  and "id" not in {used} and "id" >= 0'
        self.log(sql)
        r = self.SQLITE.execute(sql)
        self.log(f'Удалено {r.rowcount} записей')
        self.SQLITE.commit()
        #--------------------------------
        self.log(f'УДАЛЕНИЕ "ВИСЯЧИХ" СТРОК')
        #used = f'({",".join(str(id) for id in self.used_sets)})'
        sql = f'delete from good_set_item where set_id not in (select id from product_set)'
        self.log(sql)
        r = self.SQLITE.execute(sql)
        self.log(f'Удалено {r.rowcount} записей')
        self.SQLITE.commit()
        sql = f'delete from complex_good_set_item where set_id not in (select id from product_set)'
        self.log(sql)
        r = self.SQLITE.execute(sql)
        self.log(f'Удалено {r.rowcount} записей')
        self.SQLITE.commit()
        #--------------------------------
        self.log(f'РЕОРГАНИЗАЦИЯ НАБОРОВ')
        sql = f'delete from good_set_item where set_id not in (select id from product_set where "type" in ({ProductSet.ТОВАРНЫЙ_НАБОР}, {ProductSet.ТОВАРНЫЙ_НАБОР_С_ЦЕНАМИ}))'
        self.log(sql)
        r = self.SQLITE.execute(sql)
        self.log(f'Удалено {r.rowcount} записей')
        self.SQLITE.commit()
        sql = f'delete from complex_good_set_item where set_id not in (select id from product_set where "type" = {ProductSet.КОМПЛЕКСНЫЙ_НАБОР})'
        self.log(sql)
        r = self.SQLITE.execute(sql)
        self.log(f'Удалено {r.rowcount} записей')
        self.SQLITE.commit()
        #--------------------------------
        self.log(f'СЖАТИЕ БД')
        sql='VACUUM'
        self.log(sql)
        r = self.SQLITE.execute(sql)
        self.log('РЕОГРАНИЗАЦИЯ УСПЕШНО ВЫПОЛНЕНА')

    def clean_actions(self):
        self.log('УДАЛЕНИЕ НЕИСПОЛЬЗУЕМЫХ АКЦИЙ')
        used_actions = set()
        good_sets = set()
        count = 0
        comments = []
        for schema in Schema.findall(self.cursor):
            count += 1
            comments.append(f'{schema.ID}:{schema.наименование}')
            for action_id in schema.расчетные_акции.список_акций:
                used_actions.add(int(action_id))
            for action_id in schema.послепродажные_акции.список_акций:
                used_actions.add(int(action_id))
        self.log(f'Схем {count} : {", ".join(comments)}')
        self.log(f'Используемых акций : {len(used_actions)} : {used_actions}')
        self.used_actions = used_actions
        # ------------------------------------------
        self.log(f'Используемых наборов : {len(good_sets)} : {good_sets}')
        not_used_actions = set()
        for action in Action.findall(self.cursor):
            if int(action.ID) not in self.used_actions:
                not_used_actions.add(int(action.ID))
        self.log(f'Не используемых акций : {len(not_used_actions)} : {not_used_actions}')
        self.log(F'Удаление на используемых акций')
        count = 0
        for action_id in not_used_actions:
            delete_action = 'delete from actions where id=?'
            delete_action_items = 'delete from action_set_item where action_id=?'
            self.cursor.execute(delete_action, [action_id])
            self.cursor.execute(delete_action_items, [action_id])
            self.connection.commit()
            count += 1
        self.log(F'Удалено {count} акций')

    def du(self, folder):
        try:
            cmd = f'du -d 0 -a -b {folder}'
            p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
            output = p.stdout#self.log(f'> {p.stdout}')
            out = output.decode('utf-8').strip().split('\t')
            return int(out[0]) 
        except BaseException as ex:
            self.log(f'{cmd} : {ex}')
            return 0

if __name__ == "__main__":
    log.debug(f'{__file__}, {sys.argv}')
    ID = sys.argv[1]
    try:
        with TheJob(ID) as job:
            job()
    except:
        log.exception(__file__)

