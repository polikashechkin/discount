import flask, sqlite3, json, datetime, pickle, os, arrow
from domino.core import log
from . import Page, Select, Toolbar, Input, IconButton, Row
from . import BookmarkIconButton
from domino.tables.postgres.dept import Dept

from discount.checks import Check
from discount.page import DiscountPage
from domino.page_controls import Кнопка
from domino.page_controls import Кнопка as Button
from sqlalchemy import text as T

class ThePage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request)
        #self.account_id = self.request.account_id()

    def delete_bookmarks(self):
        self.postgres.query(Check).filter(Check.bookmark==True).delete()
        self.postgres.commit()
        self.print_table()

    def change_bookmark(self):
        check_id = self.get('check_id')
        check = self.postgres.query(Check).get(check_id)
        dept = self.postgres.query(Dept).get(check.dept_code)
        check.bookmark = not check.bookmark
        self.postgres.commit()
        row = Row(self, 'table', check_id)
        self.print_row(row, check, dept)

    def print_row(self, row, check, dept):
        #---------------------------------
        cell = row.cell()
        button = BookmarkIconButton(cell, check.bookmark)
        button.onclick('.change_bookmark', {'check_id':check.ID})
        #---------------------------------
        cell = row.cell()
        cell.style('width:1rem;')
        if check.is_test:
            cell.glif('circle', css='-text-danger', style='font-size:small; color:orange')

        if check.TYPE == 0:
            row.cell().text('продажа')
        elif check.TYPE == 1:
            row.cell().style('color:red').text('ВОЗВРАТ')
        else:
            row.cell().style('color:red').text(check.TYPE)

        row.cell().text(check.session_date)
        cell = row.cell()
        if dept:
            cell.text(f'{dept.name}')

        row.cell().text(check.check_date)
        row.text(check.pos_id)
        row.text(check.session_id)
        row.text(check.check_no)
        row.text(check.total)
        #row.cell(style='text-align:right').text(f'{TIME_MS} ms')
        row.href(f'Чек', 'pages/fs_check', {'check_id':check.ID})

    def print_table(self):
        self.print_toolbar()
        table = self.Table('table').mt(1)
        table.column('')
        table.column('')
        #if self.права.ЭТО_ТЕХНИЧЕСКАЯ_ПОДДЕРЖКА:
        #    table.column('GUID')

        table.column('Тип')
        table.column('Торговый день')
        table.column('Подразделение')
        table.column('Дата чека')
        table.column('ФР')
        table.column('Смена')
        table.column('Номер')
        #table.column('Кассир')
        table.column('Сумма')
        table.column('')
        table.column('')

        limit = int(self.get('limit', -100))

        query = self.postgres.query(Check, Dept).outerjoin(Dept, Dept.id == Check.dept_code)

        check_date = self.get('check_date')
        if check_date:
            check_date = arrow.get(check_date).date()
            query = query.filter(T(f"check_date::date = '{check_date}'"))

        dept_code = self.get('dept_code')
        if dept_code:
            query = query.filter(Check.dept_code == dept_code)

        check_no = self.get('номер_чека')
        if check_no:
            query = query.filter(Check.check_no == check_no)

        session_id = self.get('смена')
        if session_id:
            query = query.filter(Check.session_id == session_id)

        pos_id = self.get('фр')
        if pos_id:
            query = query.filter(Check.pos_id == pos_id)

        if limit >0:
            query = query.order_by(Check.creation_date).limit(limit)
        else:
            query = query.order_by(Check.creation_date.desc()).limit(-limit)

        for check, dept in query:
            row = table.row(check.ID)
            self.print_row(row, check, dept)

        #self.message(f'{len(checks)}')
    #def показать_по_дате_создания(self):
        #self.панель()
    #    self.print_table()

    def print_toolbar(self):
        query = self.toolbar('query')
        query.item().input(label='Дата', name = 'check_date', type='date', value=self.get('check_date'))
        select = query.item().select(label='Подразделение', name = 'dept_code', value=self.get('dept_code'))
        select.option('', '')
        for dept in self.postgres.query(Dept).order_by(Dept.name):
            select.option(dept.id, dept.name)

        query.item().input(label='Фискальный регистатор', name = 'фр', value=self.get('фр')).width(10)
        query.item().input(label='Смена', name = 'смена', value=self.get('смена')).width(6)
        query.item().input(label='Номер чека', name = 'номер_чека', value=self.get('номер_чека')).width(6)
        
        #IconButton(query.item(), 'refresh').tooltip('Сбросить фильтр')
        Button(query.item(ml='auto'), 'сбросить').tooltip('Сбросить фильтр')\
            .onclick('.print_table', 
                {'фр':'', 'смена':'', 'номер_чека': '', 'dept_code':'', 'check_date':'', 'limit':'-100' }
                )
        toolbar = self.toolbar('toolbar').mt(1)
        #3select = toolbar.item().select(name='limit', label='Показать')
        #select.option('', '')
        #select.option(200, 'Показать первые 200 записей')
        #select.option(500, 'Показать первые 500 записей')
        #select.option(1000, 'Показать первые 1000 записей')

        button = Кнопка(toolbar.item(mr=0.5), 'показать').onclick('.print_table', forms=[query, toolbar])
        select = Select(toolbar.item(mr=0.5), name = 'limit' , value=self.get('limit', -100))#.onchange('.показать_по_дате_создания', forms=[query, toolbar])
        select.option(-100, 'Последние 100 записей')
        select.option(-500, 'Последние 500 записей')
        select.option(-1000, 'Последние 1000 записей')
        select.option(100, 'Первые 100 записей')
        select.option(500, 'Первые 500 записей')
        select.option(1000, 'Первые 1000 записей')
        Button(toolbar.item(ml='auto'), 'Удалить закладки').onclick('.delete_bookmarks', forms=[query, toolbar])
        #button.item('Показать первые 200 записей').onclick('.показать_по_дате_создания', {'limit' : 200 }, forms=[query])
        #button.item('Показать первые 500 записей').onclick('.показать_по_дате_создания', {'limit' : 500 }, forms=[query])
        #button.item('Показать первые 1000 записей').onclick('.показать_по_дате_создания', {'limit' : 1000 }, forms=[query])
        #button.item('Показать последние 200 записей').onclick('.показать_по_дате_создания', {'limit' : -200 }, forms=[query])
        #button.item('Показать последние 500 записей').onclick('.показать_по_дате_создания', {'limit' : -500 }, forms=[query])
        #button.item('Показать последние 1000 записей').onclick('.показать_по_дате_создания', {'limit' : -1000 }, forms=[query])

        #Кнопка(toolbar, 'сбросить фильтр')\
        #    .onclick('.показать_по_дате_создания', 
        #        {'фр':'', 'смена':'', 'номер_чека': '', 'dept_code':'', 'check_date':'', 'limit':'200' }
        #        )

    def __call__(self):
        self.title(f'Чеки')
        #self.print_toolbar()
        #self.Table('table')
        self.print_table()
        

