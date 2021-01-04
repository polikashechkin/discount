# -*- coding: utf-8 -*-
import os, sys, datetime, time, sqlite3, pickle, arrow, shutil, subprocess, psutil, re, glob
from domino.jobs import Proc
from domino.page import Page
from domino.core import log, start_log, DOMINO_ROOT
#from domino.databases import Databases
from discount.core import DISCOUNT_DB, PRODUCT_COLUMNS_FILE, Engine
#from discount.users import Пользователь
from discount.page import DiscountPage
from domino.page_controls import Кнопка, КраснаяКнопка, ПлоскаяТаблица
from domino.reports import Report
from domino.postgres import Postgres
from domino.page_controls import FormControl
from discount.series import CardType
from discount.cards import Card, CardLog
import xml.etree.cElementTree as ET

from sqlalchemy import text as T, func as F, and_, or_

from domino.tables.postgres.report import Report
from domino.tables.postgres.report_line import ReportLine

from domino.postgres import Postgres
POSTGRES = Postgres.Pool()

TIMEOUT = 100
DESCRIPTION = 'Получение справок по дисконтным картам'
PROC = 'export_cards.py'
MODULE = 'discount'
MIN_DAYS = 2

def on_activate(account_id, on_actvate_log):
    Proc.create(account_id, MODULE, PROC, description=DESCRIPTION, url='export_cards')

class ReportType:
    АКТИВНЫЕ_КАРТЫ = ''
    АКТИВИРОВАННЫЕ_ЗА_ПЕРИОД = 'a'
    ПОГАШЕННЫЕ_ЗА_ПЕРИОД = 'd'
    def __init__(self, id, name, period=False):
        self.id = id
        self.name = name
        self.period = period

    @staticmethod
    def get(type_id):
        return report_types.get(type_id)

    @staticmethod
    def all():
        return report_types.values()

report_types = {
    ReportType.АКТИВНЫЕ_КАРТЫ : ReportType(ReportType.АКТИВНЫЕ_КАРТЫ, 'Активные карты'),
    ReportType.АКТИВИРОВАННЫЕ_ЗА_ПЕРИОД : ReportType(ReportType.АКТИВИРОВАННЫЕ_ЗА_ПЕРИОД, 'Активированные за период', period=True),
    ReportType.ПОГАШЕННЫЕ_ЗА_ПЕРИОД : ReportType(ReportType.ПОГАШЕННЫЕ_ЗА_ПЕРИОД, 'Использованные за период', period=True),
}

class ThePage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.proc = Proc.get(self.account_id, MODULE, PROC)

    def run(self):
        report_type_id = self.proc.info.get('report_type_id', '')
        report_type = report_types[report_type_id]
        card_type_id = self.proc.info.get('card_type_id')
        card_type = CardType.get(self.cursor, card_type_id)
        start_date = self.get('start_date')
        end_date = self.get('end_date')
        self.proc.info['start_date'] = start_date
        self.proc.info['end_date'] = end_date
        self.proc.save()
        Proc.start(self.account_id, MODULE, PROC, description=DESCRIPTION, info={'report_type_id':report_type_id})
        self.message(f'Заказана справка "{report_type.name}", "{card_type.полное_наименование}", с {start_date} по {end_date} (включительно)')
    
    def change_params(self):
        export_format = self.get('export_format')
        #card_type = self.get('card_type')
        start_date = self.get('start_date')
        self.proc.info['start_date'] = start_date
        end_date = self.get('end_date')
        self.proc.info['end_date'] = end_date
        self.proc.info['export_format'] = export_format
        card_type_id = self.get('card_type_id')
        self.proc.info['card_type_id'] = card_type_id
        #self.message(f'{report_type.name}, {card_type.полное_наименование}')
        self.proc.save()
        #self.proc.info['card_type'] = card_type
        self.message(f'{export_format}, {start_date}')
    
    def change_report_type(self):
        report_type_id = self.get('report_type_id')
        self.proc.info['report_type_id'] = report_type_id
        report_type = report_types.get(report_type_id)
        self.message(f'{report_type.name}')
        self.proc.save()
        self.print_params()

    def print_report_type(self):
        toolbar = self.toolbar('report_type')
        select = toolbar.item().select(name='report_type_id', value=self.proc.info.get('report_type_id'))\
            .onchange('.change_report_type', forms=[toolbar])
        #for report_type in report_types.values():
        for report_type in ReportType.all():
            select.option(report_type.id, report_type.name.upper())

    def change_export_card_field(self):
        field_id = self.get('field_id')
        fields = self.proc.info.get('fields')
        if fields is None:
            fields = {}
            self.proc.info['fields'] = fields
        if field_id in fields:
            del fields[field_id]
            #self.message(f'{field_id} : False')
        else:
            fields[field_id] = True
            #self.message(f'{field_id} : True')
        self.proc.save()
        
        self.print_params()

    def print_export_card_field(self, row, field_id, description):
        cell = row.cell(width=2)
        fields = self.proc.info.get('fields')
        if fields and fields.get(field_id):
            button = cell.icon_button('check', style='color:green')
        else:
            button = cell.icon_button('check', style='color:lightgray')
        button.onclick('.change_export_card_field', {'field_id':field_id})
        cell = row.cell(width=10)
        cell.text(f'{field_id}')
        cell = row.cell()
        cell.text(description)
        #row.cell().text(f'{fields}')

    def print_params(self):
        report_type = report_types.get(self.proc.info.get('report_type_id', ''))
        params = self.toolbar('params').mt(1)
        #--------------------------------------------
        select = params.item(mr=0.5).select(label='Тип карты', name='card_type_id', value=self.proc.info.get('card_type_id'))\
            .onchange('.change_params', forms=[params])
        for card_type in CardType.findall(self.cursor):
            name = card_type.полное_наименование
            #self.log(f'{card_type.ID} : {name}')
            select.option(card_type.ID, f'{name}')
        #--------------------------------------------
        if report_type.period:
            params.item(mr=0.5).input(name='start_date', label='Дата начальная', value=self.proc.info.get('start_date'), type='date')\
                .onkeypress(13, '.change_params', forms=[params])\
                .onchange('.change_params', forms=[params])
            params.item().input(name='end_date', label='Дата конечная', value=self.proc.info.get('end_date'), type='date')\
                .onkeypress(13, '.change_params', forms=[params])\
                .onchange('.change_params', forms=[params])
        #--------------------------------------------
        p = self.text_block().mt(1)
        p.text('Список выгружаемых параметров карты')
        table = ПлоскаяТаблица(self, 'table')
        self.print_export_card_field(table.row('id'), 'id', 'Индентификатор карты (включая префиксы и суффиксы)')
        self.print_export_card_field(table.row('marknum'), 'marknum', 'Номер карты (без префиксов и суффиксов)')
        #self.print_export_card_field(table.row('activation_date'), 'activation_date', 'Дата активации')
        #self.print_export_card_field(table.row('deactivation_date'), 'deactivation_date', 'Дата погашения (днактивации)')
        self.print_export_card_field(table.row('date'), 'date', 'Дата активации/погашения')
        #self.print_export_card_field(table.row('deactivation_date'), 'deactivation_date', 'Дата погашения (днактивации)')
        self.print_export_card_field(table.row('dept_code'), 'dept_code', 'Код подразделения (активация/погашение)')
        #self.print_export_card_field(table.row('price'), 'price', 'Цена продажи карты или номинал для подарочной карты')
        #--------------------------------------------
        actions = self.toolbar('actions').mt(2)
        КраснаяКнопка(actions, 'Заказать справку').onclick('.run', forms=[params])

    def open(self):
        self.title(f'{self.proc.ID}, {DESCRIPTION}')
        p = self.toolbar('about').style('align-items:center')
        t = p.item().text_block()
        #t.text('''
        #Выгружаются данные по картам. Либо по всем, либо только по заданному типу.
        #Формат выгрузки может быть либо XML либо CSV.
        #Файлы можно посмотерь или выгрузить в разделе ФАЙЛЫ соотвествующей задачи.
        #Файлы имеют имя <номер типа карты>.[xml|csv]. Кодировка UTF-8
        #''') 
        self.print_report_type()
        self.print_params()

        #КраснаяКнопка(p, 'Запустить').onclick('run')

class ExportCards:
    def __init__(self, job, TYPE, name):
        self.TYPE = TYPE
        self.count = 0
        job.log(f'ВЫГРУЗКА {TYPE} : {name}')
        self.job = job
        if self.job.export_format and self.job.export_format == 'csv':
            self.CSV = True
        else:
            self.CSV = False
        self.XML = not self.CSV

        if self.XML:
            self.xcards = ET.fromstring('<cards/>')   
            self.xcards.attrib['type'] = f'{TYPE}'
            self.xcards.attrib['type_name'] = f'{name}'
            self.xcards.attrib['create'] = f'{datetime.datetime.now()}'
            self.out_file_path = os.path.join(self.job.folder, f'{self.TYPE}.xml')
        else:
            self.out_file_path = os.path.join(self.job.folder, f'{self.TYPE}.csv')
        self.out_file = open(self.out_file_path, 'w')
    
    def add(self, ID, MARKNUM, ACTIVATE_DATE, DEPT_CODE):
        self.count += 1
        if self.XML:
            xcard = ET.SubElement(self.xcards, 'card')
            xcard.attrib['id'] = f'{ID}'
            xcard.attrib['num'] = f'{MARKNUM}'
            if ACTIVATE_DATE:
                xcard.attrib['activation_date'] = f'{ACTIVATE_DATE}'
            if DEPT_CODE:
                xcard.attrib['dept_code'] = f'{DEPT_CODE}'
        else:
            self.out_file.write(f'{ID}\n')

    def save(self):
        if self.XML:
            out  = ET.tostring(self.xcards, encoding='utf-8').decode('utf-8')
            self.out_file.write(out)

        self.job.log(f'Выгружено {self.count} => {self.out_file_path}')
        self.out_file.close()

class TheJob(Proc.Job):
    def __init__(self, ID):
        #log.info(f'Запуск задачи {ID}, card_report')
        super().__init__(ID=ID)

    def create_report(self):
        self.report = Report(class_ = 'discount_card', type_ = self.info.get('report_type_id', ReportType.АКТИВНЫЕ_КАРТЫ), info={})
        self.report.info['card_type_id'] = self.info.get('card_type_id')
        self.start_date = self.report.info['start_date'] = self.info.get('start_date')
        self.end_date = self.report.info['end_date'] = self.info.get('end_date')
        self.report.info['fields'] = self.info['fields']

        self.card_type = CardType.get(self.cursor, self.report.info['card_type_id'])
        self.report_type = report_types[self.report.type_]
        self.report.name = f'{self.report_type.name}, {self.card_type.полное_наименование}'
        if self.report_type.period:
            self.report.name += f', c {self.start_date} по {self.end_date} (включительно)'

        self.postgres.add(self.report)
        self.postgres.commit()
        return self.report.id

    def create_deactivate_card_report(self, report):
        start_date = self.report.info.get('start_date')
        end_date = self.report.info.get('end_date')
        sql = f'''
            select log.card_id, card.marknum, log.creation_date, "check".dept_code
            from discount_cardlog as log, discount_card as card, discount_check as "check"
            where 
            card.id = log.card_id 
            and "check".id = log.check_id
            and card.type = {self.card_type.ID}
            and log.type = {CardLog.ОПЛАТА}
            and log.creation_date >= '{start_date}' and log.creation_date <= '{end_date}'
            order by log.creation_date
        '''
        self.log(sql.replace('\n', ' '))
        fields = self.report.info.get('fields')
        lines = 0 
        for ID, marknum, date, dept_code in self.postgres.execute(T(sql)):
            lines += 1
            if lines % 10000 == 0:
                self.check_for_break()
                self.log(lines)
                self.postgres.commit()
            report_line = ReportLine(report_id = self.report.id, info={})
            info = {}
            if 'id' in fields:
                info['id'] = ID
            if 'marknum' in fields:
                info['marknum'] = marknum
            if date and 'deactivation_date' in fields:
                #info['date'] = f'{date}'
                info['date'] = date.strftime("%Y-%m-%d %H:%M:%S")
            if dept_code and 'dept_code' in fields:
                info['dept_code'] = dept_code
            report_line.info = info
            self.postgres.add(report_line)
            #ReportLine.insert(self.postgres, self.report.id, info)
        
        self.log(f'{lines}')
        self.report.state = 1
        self.report.lines = lines

    def create_activate_card_report(self, report):
        start_date = report.info.get('start_date')
        end_date = report.info.get('end_date')
        #query = self.postgres.query(Card)
        sql = f'select id, marknum, activate_date, dept_code from discount_card where TYPE = {self.card_type.ID}'
        if report.type_ == ReportType.АКТИВНЫЕ_КАРТЫ:
            sql += ' order by activate_date '
        elif report.type_ == ReportType.АКТИВИРОВАННЫЕ_ЗА_ПЕРИОД:
            #query = query.filter(Card.activation_date >= start_date, Card.activation_date <= end_date)
            #query = query.order_by(Card.activation_date)
            sql += f" and activate_date >= '{start_date}' and activate_date <= '{end_date}' "
            sql += ' order by activate_date '
        else:
            self.log('НЕИЗВЕСТНЫЙ ТИП ОТЧЕТА')
            return 

        self.log(sql)
        fields = report.info.get('fields')
        lines = 0 
        for ID, marknum, activation_date, dept_code in self.postgres.execute(T(sql)):
        #self.log(query)
        #for card in query:
            #self.log(f'{ID}, {marknum}, {activation_date}, {dept_code}')
            lines += 1
            if lines % 10000 == 0:
                self.check_for_break()
                self.log(lines)
                self.postgres.commit()
            report_line = ReportLine(report_id = report.id, info={})
            info = {}
            if 'id' in fields:
                info['id'] = ID
            if 'marknum' in fields:
                info['marknum'] = marknum
            if activation_date and 'date' in fields:
                info['date'] = f'{activation_date}'
            if dept_code and 'dept_code' in fields:
                info['dept_code'] = dept_code
            report_line.info = info
            self.postgres.add(report_line)
            #ReportLine.insert(self.postgres, self.report.id, info)
        
        self.log(f'{lines}')
        report.state = 1
        report.lines = lines

    def dowork(self):
        report_id = self.create_report()
        report = self.postgres.query(Report).get(report_id)
        self.log(f'{report_id}=>{report}')
        if report.type_ == ReportType.ПОГАШЕННЫЕ_ЗА_ПЕРИОД:
            self.create_deactivate_card_report(report)
        else:
            self.create_activate_card_report(report)

    def __call__(self):
        self.postgres = POSTGRES.session(self.account_id)
        self.connection = sqlite3.connect(DISCOUNT_DB(self.account_id))
        self.cursor = self.connection.cursor()
        try:
            self.dowork()
            self.postgres.commit()
        except BaseException as ex:
            log.exception(__file__)
            self.postgres.rollback()
            self.error(f'{ex}')
        finally:
            self.postgres.close()
            self.connection.close()
        self.log(f'ОКОНЧАНИЕ')

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            with TheJob(sys.argv[1]) as job:
                job()
        except BaseException as ex:
            log.exception(__name__)
