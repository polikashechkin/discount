import os, datetime, sqlite3, json, shutil, arrow
from domino.core import DOMINO_ROOT, log
from domino.page import Page
from domino.page_controls import СтандартныеКнопки
from domino.postgres import Postgres

class Report:
    @staticmethod
    def migrate(account_id, log):
        conn = Postgres.connect(account_id)
        with conn:
            cur = conn.cursor()
            cur.execute('''
            create table if not exists reports(
                report_id varchar primary key,
                module varchar not null,
                year integer,
                month integer,
                name varchar,
                version integer,
                info bjson
            )
            ''')

    DEFAULT_TABLE = 'table'
    TOTAL = 'TOTAL'
    ALL = 'ALL'
    INTEGER = 'integer'
    class Tab:
        def __init__(self, js, **kwargs):
            self.js = js
            for key, value in kwargs.items():
                self.js[key] = value
    
    class Table:
        DIMS = 'dims'
        INDICATORS = 'indicators'
        RECORDS = 'records'
        VALUES = 'values'
        
        class Total:
            def __init__(self):
                self.dims = {}
                self.total = None

            def subdim(self, dim_id):
                total = self.dims.get(dim_id)
                if total is None:
                    total = Report.Table.Total()
                    self.dims[dim_id] = total

            def add(self, dims, values):
                if len(dims) > 0:
                    subdims = dims[1:]
                    self.subdim(dims[0]).add(subdims, values)
                    self.subdim('TOTAL').add(subdims, values)
                if self.total is None:
                    self.total = values
                else:
                    for i in range(len(values)):
                        self.total[i] += values[i]

        class Row:
            def __init__(self, table, js, values = None, **kwargs):
                self.table = table
                self.js = js
                for key, value in kwargs.items():
                    self.js[key] = value
                if values is not None: 
                    self.js['cells'] = values
                elif 'cells' not in js:
                    self.js['cells'] = self.table.cells.copy()
            @property
            def cells(self):
                return self.js['cells']
            @cells.setter
            def cells(self, values):
                self.js['cells'] = values

            def columns(self, *args):
                i = 0
                for arg in args:
                    self.cells[i] = arg
                    i += 1

            def __getitem__(self, i):
                return self.cells[i]
            def __setitem__(self, i, value):
               self.cells[i] = value
        
        def __init__(self, js, name = None, **kwargs):
            self.js = js
            if name:
                self.js['name'] = name

            if 'columns' not in js:
                self.js['columns'] = []
            if 'rows' not in js:
                self.js['rows'] = {}

            if Report.Table.DIMS not in self.js:
                self.js[Report.Table.DIMS] = {}
            if Report.Table.INDICATORS not in self.js:
                self.js[Report.Table.INDICATORS] = {}

            if Report.Table.RECORDS not in self.js:
                self.js[Report.Table.RECORDS] = {}

            #self.columns = self.js['columns']
            self.rows = self.js['rows']
            self.last_ID = 0
            self.cells = []

            for key, value in kwargs.items():
                self.js[key] = value

        @property
        def dims(self):
            return self.js[Report.Table.DIMS]
        @dims.setter
        def dims(self, value):
            dims = self.js[Report.Table.DIMS]
            for ID, INFO in value.items():
                dims[ID] = INFO
        
        @property
        def indicators(self):
            return self.js[Report.Table.INDICATORS]

        @indicators.setter
        def indicators(self, value):
            indicators = self.indicators
            for ID, INFO in value.items():
                indicators[ID] = INFO
        
        def add(self, dims, values):
            primary_key = '/'.join(dims)
            record = self.js[Report.Table.RECORDS].get(primary_key)
            if record is None:
                self.js[Report.Table.RECORDS][primary_key] = [dims, values]
            else:
                for i in range(len(values)):
                    record[1][i] += values[i]
        
        def make_totals(self):
            dims_values = []
            curr_dims = []
            DIMS = self.js[Report.Table.DIMS]
            for dim_info in DIMS.values():
                dim_values = dim_info.get(Report.Table.VALUES)
                if dim_values is None:
                    dim_values = {}
                    dim_info[Report.Table.VALUES] = dim_values
                dims_values.append(dim_values)
                curr_dims.append(None)

            for record in self.js[Report.Table.RECORDS]:
                # Добавляем значение ID в словари DIMS
                for i in range(len(record[0])):
                    dim_id = record[0][i]
                    dim_values = dims_values[i]
                    if dim_id not in dim_values:
                        dim_values[dim_id] = {}
                # 
        
        def create_dim_names(self, dim_id, get_name):
            DIMS = self.js[Report.Table.DIMS]
            dim_info = DIMS.get(dim_id)
            if dim_info is not None:
                dim_values = dim_info.get(Report.Table.VALUES)
                if dim_values is not None:
                    for ID, INFO in dim_values.items():
                        INFO['name'] = get_name(ID)
                    log.debug(f'NO VALUES {dim_info}')


        @property
        def columns(self):
            return self.js['columns']
        @columns.setter
        def columns(self, js):
            self.js['columns'] = js
            self.cells = []
            for column in js.values():
                self.cells.append(column.get('default'))

        #def column(self, default=None, **kwargs):
        #    column_js = {}
        #    self.columns.append(column_js)
        #    self.cells.append(default)
        #    return Report.Table.Column(self, column_js, **kwargs)
        
        @property
        def has_named_columns(self):
            for column in self.columns.items():
                if 'name' in column:
                    return True
            return False

        def row(self, ID = None, values=None, **kwargs):
            if ID is None:
                self.last_ID +=1
                ID = f'_{self.last_ID}_'
                JS = {}
                self.rows[ID] = JS
                return Report.Table.Row(self, JS, values, **kwargs)
            else:
                JS = self.rows.get(str(ID))
                if JS is None:
                    JS = {}
                    self.rows[str(ID)] = JS
                    return Report.Table.Row(self, JS, values, **kwargs)
                else:
                    return Report.Table.Row(self, JS, values, **kwargs)

    def __init__(self, account_id, module, name, year = 0, month = 0):
        self.js = {}
        self.account_id = account_id
        self.module = module
        self.name = name
        self.year = year
        self.month = month
        self.js['account_id'] = account_id
        self.js['module'] = module
        self.js['name'] = name
        self.js['year'] = year
        self.js['month'] = month
        self.js['enums'] = {}
        self.js['tabs'] = {}
        self.js['tables'] = {}
        self.info = {}

    def __str__(self):
        return f'<Report {self.account_id} {self.name}>'
    
    def tab(self, ID, **kwargs):
        tab_js = self.tabs.get(ID) 
        if tab_js is None:
            tab_js = {}
            self.tabs[ID] = tab_js
        return Report.Tab(tab_js, **kwargs)

    @property
    def enums(self):
        return self.js['enums']
    @property
    def tables(self):
        return self.js['tables']

    @property
    def tabs(self):
        return self.js['tabs']

    def create_enum(self, enum_name, options = None):
        enum_dictionary = {}
        if options is not None:
            if isinstance(options, dict):
                for key, name in options.items():
                    enum_dictionary[key] = name
            elif isinstance(options, list):
                for key, name in options:
                    enum_dictionary[key] = name
        self.enums[enum_name] = enum_dictionary
        return enum_dictionary

    def get_enum(self, enum_name):
        return self.enums.get(enum_name)

    def table(self, ID, **kwargs):
        table_js = self.tables.get(ID) 
        if table_js is None:
            table_js = {}
            self.tables[ID] = table_js
        return Report.Table(table_js, **kwargs)

    def create(self, update=True):
        log.debug(f'{self}.create({update})')
        conn = Report.reports_connection(self.account_id, self.module)
        INFO = json.dumps(self.info, ensure_ascii = False)
        folder = Report.make_folder(self.account_id, self.module)
        with conn:
            cur = conn.cursor()
            cur.execute('select version from reports where name=? and year=? and month=?',
                [self.name, self.year, self.month])
            last_version = -1
            for version, in cur:
                if version > last_version:
                    last_version = version
            version = last_version + 1
            creation_date = f'{datetime.datetime.now()}'
            cur.execute('insert into reports (account_id, module, name, year, month, info, creation_date, version) values (?,?,?,?,?,?,?,?)',
            [self.account_id, self.module, self.name, self.year, self.month, INFO, creation_date, version])
            ID = cur.lastrowid
            self.js['ID'] = ID
            self.js['creation_date'] = creation_date
            self.js['version'] = version
            with open(os.path.join(folder, f'{ID}.json'), 'w') as f:
                json.dump(self.js, f, ensure_ascii=False)
            if update:
                cur.execute('select ID from reports where name=? and year=? and month=? and ID != ?',
                    [self.name, self.year, self.month, ID])
                OLDS = cur.fetchall()
                for OLD_ID, in OLDS:
                    Report._delete_file(cur, folder, OLD_ID)
        return ID

    @staticmethod
    def make_folder(account_id, module):
        folder = os.path.join(DOMINO_ROOT, 'accounts', account_id, 'data', module, 'reports')
        os.makedirs(folder, exist_ok=True)
        return folder

    @staticmethod
    def reports_connection(account_id, module):
        #log.debug(f'reports_connection({account_id}, {module})')
        folder = Report.make_folder(account_id, module)
        reports_db = os.path.join(folder, 'reports.db')
        #log.debug(f'{reports_db}')
        if os.path.isfile(reports_db):
            return sqlite3.connect(reports_db)
        else:
            conn = sqlite3.connect(reports_db)
            conn.executescript('''
            create table if not exists reports
            (
                ID integer not null primary key,
                creation_date text not null,
                account_id text not null,
                module text not null,
                name text not null,
                year integer default 0 not null,
                month integer default 0 not null,
                version integer default 0 not null,
                info blob default '{}'
            );
            create index if not exists report_by_name on reports(name, year, month);
            '''
            )
            return conn

    @staticmethod
    def _delete_file(cur, folder, ID):
        cur.execute('delete from reports where ID=?', [ID])
        report_file = os.path.join(folder, f'{ID}.json')
        if os.path.isfile(report_file):
            os.remove(report_file)

    @staticmethod
    def delete_report(account_id, module, ID):
        folder = Report.make_folder(account_id, module)
        conn = Report.reports_connection(account_id, module)
        with conn:
            cur = conn.cursor()
            Report._delete_file(cur, folder, ID)

    @staticmethod
    def create_report(account_id, module, name, year = 0, month = 0, info = None, update=True, report = None ):
        conn = Report.reports_connection(account_id, module)
        INFO = json.dumps(info, ensure_ascii=False) if info is not None else '{}' 
        folder = Report.make_folder(account_id, module)
        with conn:
            cur = conn.cursor()
            cur.execute('select version from reports where name=? and year=? and month=?',
                [name, year, month])
            last_version = -1
            for version, in cur:
                #log.debug(f'VERSION {version}, {last_version}')
                if version > last_version:
                    last_version = version
            #log.debug(f'{last_version}')
            version = last_version + 1
            creation_date = f'{datetime.datetime.now()}'
            cur.execute('insert into reports (account_id, module, name, year, month, info, creation_date, version) values (?,?,?,?,?,?,?,?)',
            [account_id, module, name, year, month, INFO, creation_date, version])
            ID = cur.lastrowid
            report['name'] = name
            report['year'] = year
            report['month'] = month
            report['ID'] = ID
            report['creation_date'] = creation_date
            report['version'] = version
            report_file = os.path.join(folder, f'{ID}.json')
            log.debug(f'CREATE REPORT {ID}, {report_file}')
            with open(report_file, 'w') as f:
                json.dump(report, f, ensure_ascii=False)
            if update:
                cur.execute('select ID from reports where name=? and year=? and month=? and ID != ?',
                    [name, year, month, ID])
                OLDS = cur.fetchall()
                for OLD_ID, in OLDS:
                    #log.debug(f'DELETE {OLD_ID}')
                    Report._delete_file(cur, folder, OLD_ID)
        return ID

    @staticmethod
    def load_report(account_id, module, ID):
        report = Report(account_id, module, ID)
        folder = Report.make_folder(account_id, module)
        with open(os.path.join(folder, f'{ID}.json'), 'r') as f:
            report.js = json.load(f)
        return report



class TableFilter:
    def __init__(self, page, table):
        self.patterns = []
        for column_ID, column in table.columns.items():
            TYPE = column.get('type')
            pattern = None
            if TYPE and TYPE != 'integer':
                pattern = page.get(column_ID)
                if pattern is None: 
                    pattern = Report.TOTAL

            self.patterns.append(pattern)
        log.debug(f'TableFilter : {self.patterns}')
        
    def match(self, values):
        match = True
        for i in range(len(values)):
            value = f'{values[i]}'
            pattern = self.patterns[i]
            if pattern:
                if pattern == Report.ALL:
                    if value == Report.TOTAL:
                        match = False
                        break
                elif pattern != value:
                    match = False
                    break
        log.debug(f'MATCH : {match} : {values} : {self.patterns}')
        return match


class ReportsPage(Page):
    def __init__(self, application, request, module = None):
        self.module = module if module else application.product_id
        super().__init__(application, request)

    def delete_report(self):
        ID = self.get('ID')
        Report.delete_report(self.account_id, self.module, ID)
        self.Row('table', ID)
        self.message(f'Удален отчет {ID}')

    def open(self):
        self.title(f'Отчеты')

        table = self.Table('table')
        table.column().text('#')
        table.column().text('Наименование')
        table.column().text('Период')
        table.column().text('Дата создания')
        conn = Report.reports_connection(self.account_id, self.module)
        cur = conn.cursor()
        cur.execute('select ID, name, year, month, creation_date, version from reports order by creation_date desc')
        for ID, NAME, YEAR, MONTH, CREATION_DATE, VERSION in cur:
            row = table.row(ID)
            row.cell().text(ID)
            row.cell().href(f'{NAME} ({VERSION})', 'report', {'ID' : f'{ID}'})
            cell = row.cell()
            if YEAR and MONTH:
                cell.text(f'{YEAR:04}-{MONTH:02}')
            creation_date = arrow.get(CREATION_DATE)
            row.cell(width=10, style='white-space:nowrap').text(creation_date.format('YYYY-MM-DD HH:MM:SS'))
            кнопки = СтандартныеКнопки(row)
            кнопки.кнопка('удалить', 'delete_report', {'ID':F'{ID}'})
        conn.close()

class ReportPage(Page):
    def __init__(self, application, request, module = None):
        super().__init__(application, request)
        self.module = module if module else application.product_id
        self.ID = self.attribute('ID')
        self.report = Report.load_report(self.account_id, self.module, self.ID)
        self.TABS = self.report.js.get('tabs') 
        self.TABLES = self.report.js.get('tables')
        #group = self.report.get_enum('group')
        actions = self.report.get_enum('action')
        log.debug(f'{actions}')

    def on_change_tab(self):
        ID = self.get('tab_id')
        self.print_tabs(ID)
        self.print_toolbar(ID)            
        self.print_table(ID)

    def on_change_query(self):
        table_ID = self.get('table_id')
        self.print_table(table_ID)
        #self.message(f'on_change_query {table_ID}')

    def test_conditions(self, ROW, COLUMNS):
        if isinstance(ROW, dict):
            CELLS = ROW['cells']
        else:
            CELLS = ROW
        # проверка хапроса
        ok = True
        for i in range(len(CELLS)):
            query = COLUMNS[i].get('qiety')
            value = f'{CELLS[i]}'
            if query and value != query:
                ok = False
                break
        log.debug(f'{ok} : {CELLS}  : {COLUMNS}')
        return ok
        
    def print_row(self, row, CELLS, COLUMNS):
        #TYPE = 'text'
        for i in range(len(CELLS)):
            #INTEGER = False
            #ENUM = None
            #TYPE = None
            cell = row.cell()
            value = CELLS[i]
            COLUMN = COLUMNS[i] if i < len(COLUMNS) else None

            if COLUMN is not None:
                TYPE = COLUMN.get('type')
                ENUM = COLUMN.get('enum')
            else:
                TYPE = None
                ENUM = None
            #if TYPE == Report.INTEGER:
            #     INTEGER = True

            if TYPE and TYPE == Report.INTEGER:
                cell.css('text-right')
                if value:
                    cell.text(f'{value:,}')
            elif ENUM is not None:
                value = f'{value}'
                log.debug(f'{value} : {ENUM}')
                if value == Report.TOTAL:
                    cell.text(f'TOTAL')
                else:
                    name = ENUM.get(value)
                    cell.text(f'{name}')
                #log.debug(f'{TYPE} {value} {name} {ENUM}')
            else:
                cell.text(value)

    def print_toolbar(self, table_ID):
        TABLE = self.report.table(table_ID)
        log.debug(f'{TABLE.columns}')
        toolbar = self.Toolbar('toolbar')
        enum_columns = []
        for column_ID, column in TABLE.columns.items():
            TYPE = column.get('type')
            if TYPE:
                enum = self.report.get_enum(TYPE)
                if enum is not None:
                    # перечислимая колонка
                    enum_columns.append([column_ID, column, enum])
        if len(enum_columns) > 0:
            for column_ID, column, enum in enum_columns:
                select = toolbar.item(mr=1).select(label=f'{column.get("name")}', name=column_ID)
                select.option(Report.TOTAL, 'ИТОГ')
                select.option('ALL', 'ВСЕ')
                for ID, name in enum.items():
                    select.option(ID, name)
                select.onchange('.on_change_query', {'table_id':table_ID}, forms=[toolbar])
    
    def print_table(self, ID):
        TABLE = self.report.table(ID)
        table = self.Table('table').mt(1)

        COLUMNS = []
        has_named_columns = False
        log.debug(f'{TABLE.columns}')
        for column_ID, COLUMN in TABLE.columns.items():
            TYPE = COLUMN.get('type') 
            if TYPE and TYPE != Report.INTEGER:
                # это dimention
                #ENUM = self.report.get_enum(TYPE)
                COLUMN['enum'] = self.report.get_enum(TYPE)
                #if ENUM is not None:
                QUERY = self.get(column_ID)
                if QUERY is not None:
                    COLUMN['query'] = self.get(column_ID)
                else:
                    COLUMN['query'] = Report.TOTAL
            else:
                    
                COLUMN['query'] = None
            if 'name' in COLUMN:
                has_named_columns = True
            COLUMNS.append(COLUMN)

        if has_named_columns:
            for COLUMN in COLUMNS:
                name = COLUMN.get('name')
                TYPE = COLUMN.get('type') 
                column = table.column()
                if name:
                    column.text(name)
                if TYPE and TYPE=='integer':
                    column.css('text-right')
        

        log.debug(f'COLUMNS({ID}) {has_named_columns} : {COLUMNS} : {TABLE.columns}')
        # sql = 'select {fields} from {ID} where  eeee='2233232' and  

        FILTER = TableFilter(self, TABLE)
        ROWS = TABLE.js.get('rows')
        if isinstance(ROWS, dict):
            for ID, ROW in ROWS.items():
                if isinstance(ROW, dict):
                    record = ROW['cells']
                else:
                    record = ROW
                if FILTER.match(record):
                    row = table.row(ID)
                    self.print_row(row, record, COLUMNS)
        else:
            for ROW in ROWS:
                if isinstance(ROW, dict):
                    record = ROW['cells']
                else:
                    record = ROW
                if FILTER.match(record):
                    row = table.row()
                    self.print_row(row, record, COLUMNS)

    def print_tabs(self, ID):
        tabs = self.Tabs('tabs')
        for tab_id, INFO in self.report.tabs.items():
            tabs.item().text(INFO.get('name', '')).active(tab_id == ID).onclick('.on_change_tab', {'tab_id':tab_id})

    def open(self):
        name = self.report.js['name']
        self.title(f'{self.ID}, {name}')
        if len(self.report.tabs) > 0:
            self.print_tabs(Report.DEFAULT_TABLE)
        self.print_toolbar(Report.DEFAULT_TABLE)
        self.print_table(Report.DEFAULT_TABLE)
