import sqlite3, json, datetime, re, json
from sqlalchemy import text as T, and_, func as F
from domino.core import log
from discount.core import DISCOUNT_DB
from . import Button, TextWithComments, Toolbar, Table, Row, Input, Select, IconButton, Title
from . import DeleteIconButton, AddIconButton, RemoveIconButton
from domino.page_controls import TabControl, ПлоскаяТаблица
from discount.dept_sets import DeptSet
#, DeptSetItem
from discount.schemas import ДисконтнаяСхема
from discount.page import DiscountPage as BasePage
from grants import Grants

from tables.sqlite.dept_set_item import DeptSetItem

from domino.tables.postgres.dept_param import DeptParam
from domino.tables.postgres.dept import Dept
from tables.postgres.schema_dept_order import SchemaDeptOrder
from tables.postgres.schema_dept_order_line import SchemaDeptOrderLine
from tables.postgres.protocol import Protocol

MAX_ROWS = 30000

dept_set_tabs = TabControl('dept_set_tab_control', visible='tab_visible', mt=-3)
dept_set_tabs.append('show_depts', 'Подразделения', 'подразделения')
dept_set_tabs.append('find_depts', 'Добавление подразделений', 'поиск_подразделений')
#dept_set_tabs.append('changes_tab', 'Планируемые изменения', 'changes_tab')

# wddwdwwdwd = Form.Item(Integer(122,12), onchange = page,value'.wddwdwd' 'acount_field', label='wdwddwdwd', options = (wddwdwddwd, ('','') []]onchange=labwwd(page, value):  )

class Page(BasePage):
    # selftab = PageControl(dept_set_tabs, mt=1, mb=1)

    def __init__(self, application, request):
        super().__init__(application, request, controls=[dept_set_tabs])
        self.набор_ID = int(self.attribute('набор_ID'))
        self._набор = None
        self.МЕНЕДЖЕР =  (Grants.BOSS, Grants.ASSISTANT) in self.grants
        self._order = None

    @property
    def order(self):
        if self._order is None:
            order = self.postgres.query(SchemaDeptOrder).filter(SchemaDeptOrder.schema_id == self.schema_id).one_or_none()
            if not order:
                order = SchemaDeptOrder(schema_id = self.schema_id)
                self.postgres.add(order)
                self.postgres.commit()
            self._order = order
        return self._order

    #@property
    #def это_живой_набор(self):
    #    return self.набор.это_живой_набор
    @property
    def набор(self):
        if self._набор is None:
            self._набор = DeptSet.get(self.cursor, self.набор_ID)
        return self._набор
    
    def tab_visible(self, tab_id):
        #if tab_id == 'changes_tab':
        #    count = self.postgres.query(F.count()).filter(SchemaDeptOrderLine.order_id == self.order.id).scalar()
        #    return count > 0
        return True
    @property
    def schema_id(self):
        return int(self.набор.дисконтная_схема_ID)

    # ------------------------------------------------------------------------------
    # Подразделения 
    # ------------------------------------------------------------------------------

    def подразделения(self):
        # ------------------------
        top = ПлоскаяТаблица(self, 'toolbar_top')
        about = self.text_block('about').mt(1)
        bottom = self.toolbar('toolbar_bottom').mt(1)
        self.print_table()

    def change_order(self):
        dept_id = self.get('dept_id')
        dept = self.postgres.query(Dept).get(dept_id)
        row = Row(self, 'table', dept.id)

        order_line = self.postgres.query(SchemaDeptOrderLine)\
            .filter(SchemaDeptOrderLine.order_id == self.order.id, SchemaDeptOrderLine.dept_id == dept.id)\
            .one_or_none()

        if order_line:
            if order_line.sign == True:
                self.postgres.query(SchemaDeptOrderLine)\
                .filter(SchemaDeptOrderLine.order_id == self.order.id, SchemaDeptOrderLine.dept_id == dept.id)\
                .delete()
                self.postgres.commit()
            elif order_line.sign == False:
                self.postgres.query(SchemaDeptOrderLine)\
                .filter(SchemaDeptOrderLine.order_id == self.order.id, SchemaDeptOrderLine.dept_id == dept.id)\
                .delete()
                self.postgres.commit()
                self.print_row(row, dept.id, dept.name, None)
        else:
            order_line = SchemaDeptOrderLine(order_id = self.order.id, dept_id = dept.id, sign=False)
            self.postgres.add(order_line)
            self.postgres.commit()
            self.print_row(row, dept.id, dept.name, False)

        self.заголовок()
    
    def print_table(self):
        table = Table(self, 'table').mt(1)
        codes = {}
        #for_delete = set()
        #for dept_id, in self.postgres.query(SchemaDeptOrderLine.dept_id)\
        #    .filter(SchemaDeptOrderLine.order_id == self.order.id, SchemaDeptOrderLine.sign == False):
        #    for_delete.add(dept_id)

        for item in self.sqlite.query(DeptSetItem).filter(DeptSetItem.dept_set_id == self.набор_ID):
            codes[item.dept_code] = None

        for order_line in self.postgres.query(SchemaDeptOrderLine)\
            .filter(SchemaDeptOrderLine.order_id == self.order.id):
            codes[order_line.dept_id] = order_line.sign

        #depts = []
        #for item in self.sqlite.query(DeptSetItem).filter(DeptSetItem.dept_set_id == self.набор_ID):
        #    depts.append(item.dept_code)
        query = self.postgres.query(Dept)\
            .filter(Dept.id.in_(codes))
        for dept in query.order_by(Dept.name):
            row = table.row(dept.id)
            self.print_row(row, dept.id, dept.name, codes.get(dept.id))
        #self.message(codes)

    def print_row(self, row, dept_id, name, sign):
        style = ''
        if sign == True:
            style = 'color:green'
        elif sign == False:
            style = 'color:red'
        row.cell(width=10, style=style).text(dept_id)
        row.cell(style=style).text(name)
        cell = row.cell(width=2, align='right')
        if self.МЕНЕДЖЕР:
            if sign == False:
                RemoveIconButton(cell).onclick('.change_order', {'dept_id':dept_id})
            elif sign == True:
                AddIconButton(cell).onclick('.change_order', {'dept_id':dept_id})
            else:
                IconButton(cell, None, 'remove', style='color:lightgray').onclick('.change_order', {'dept_id':dept_id})

    # -------------------------------------------------------------------------------
    # Поиск подразделений
    # -------------------------------------------------------------------------------
    def поиск_подразделений(self):
        # ------------------------
        toolbar = Toolbar(self, 'toolbar_top').mt(0.5)
        Input(toolbar.item(mr=0.5), name='name', label='Наименование').width(10)\
            .onkeypress(13, '.поиск_подразделений_таблица', forms=[toolbar])

        for param in DeptParam.all(self.postgres):
            select = Select(toolbar.item(mr=0.5), name=param.id, label=param.name)\
                .onchange('.поиск_подразделений_таблица', forms=[toolbar])
            select.option('','')
            select.options(param.options(self.postgres))

        select = Select(toolbar.item(mr=0.5), name='order_by', label='Сортировка по')\
                .onchange('.поиск_подразделений_таблица', forms=[toolbar])
        select.options([('', 'Наименованию'), ('1', 'Коду')])

        #Button(toolbar.item(ml='auto'), 'Добавить')\
        #    .onclick('.поиск_подразделений_добавить_все', forms=[toolbar])
        # ------------------------
        self.text_block('about').mt(1)
        # ------------------------
        self.поиск_подразделений_таблица()

    def add_to_order(self):
        dept_id = self.get('dept_id')
        dept = self.postgres.query(Dept).get(dept_id)
        order_line = SchemaDeptOrderLine(order_id = self.order.id, dept_id = dept.id, sign=True)
        self.postgres.add(order_line)
        row = Row(self, 'table', dept_id)
        self.print_all_depts_row(row, dept, True, False)
        self.заголовок()

    def delete_from_order(self):
        dept_id = self.get('dept_id')
        dept = self.postgres.query(Dept).get(dept_id)
        self.postgres.query(SchemaDeptOrderLine).filter(SchemaDeptOrderLine.order_id == self.order.id, SchemaDeptOrderLine.dept_id==dept.id).delete()
        row = Row(self, 'table', dept_id)
        self.print_all_depts_row(row, dept, False, False)
        self.заголовок()

    def print_all_depts_row(self, row, dept, in_order, in_sets):
        if in_sets:
            row.cell(width=10).text(f'{dept.id}').style('color:lightgray')
            row.cell().text(f'{dept.name}').style('color:lightgray')
        else:
            row.cell(width=10, style='color:green; -font-weight:bold' if in_order else '').text(f'{dept.id}')
            row.cell(style='color:green; -font-weight:bold' if in_order else '').text(f'{dept.name}')

        cell = row.cell(width=2, align='right')
        if not in_sets:
            icon = 'add'
            if in_order:
                IconButton(cell, None, icon, style='color:green')\
                    .onclick('.delete_from_order', {'dept_id' : dept.id})
            else:
            #highlight_off 
                IconButton(cell, None, icon, style='color:lightgray')\
                    .onclick('.add_to_order', {'dept_id' : dept.id})

    def поиск_подразделений_таблица(self):
        table = Table(self, 'table').mt(0.5)
        #использованные_коды = DeptSetItem.набор_кодов(self.cursor)
        использованные_коды = []
        for item in self.sqlite.query(DeptSetItem):
            использованные_коды.append(item.dept_code)
        query = self.postgres.query(Dept, SchemaDeptOrderLine)\
            .outerjoin(SchemaDeptOrderLine, and_(SchemaDeptOrderLine.dept_id == Dept.id, SchemaDeptOrderLine.order_id == self.order.id))
        name = self.get('name')
        if name:
            query = query.filter(Dept.name.ilike(f'%{name}%'))
        for param in DeptParam.all(self.postgres):
            value = self.get(param.id)
            if value:
                query = query.filter(T(f"{param.id}='{value}'"))
        order_by = self.get('order_by')
        if order_by:
            query = query.order_by(Dept.id)
        else:
            query = query.order_by(Dept.name)
       
        for dept, order_line in query.limit(300):
            row = table.row(dept.id)
            self.print_all_depts_row(row, dept, bool(order_line), dept.id in использованные_коды)
    # -------------------------------------------------------------------------------
    # ПЛАНИРУЕМЫЕ ИЗМЕНЕНИЯ
    # -------------------------------------------------------------------------------
    #def changes_tab(self):
    #    toolbar = Toolbar(self, 'toolbar_top').mt(0.5)
    #    self.text_block('about').mt(1)
    #    self.print_changes_table()
    #    toolbar = Toolbar(self, 'toolbar_bottom').mt(0.5)

    def accept(self):
        query = self.postgres.query(SchemaDeptOrderLine).filter(SchemaDeptOrderLine.order_id == self.order.id)
        for_delete = set()
        for order_line in query:
            if order_line.sign:
                dept_id = order_line.dept_id
                info = {'code':dept_id}
                item = DeptSetItem(dept_set_id=self.набор_ID, code=dept_id, INFO = json.dumps(info))
                self.sqlite.add(item)
                #item.create(self.cursor)
            else:
                for_delete.add(order_line.dept_id)
        self.sqlite.commit()
        query.delete()
        # удаление 
        sql = f'select id, info from dept_set_item where dept_set={self.набор_ID}'
        items = self.sqlite.execute(sql).fetchall()
        for id, INFO in items:
            info = json.loads(INFO)
            dept_code = info['code']
            if dept_code in for_delete:
                sql = f'delete from dept_set_item where id={id}'
                self.sqlite.execute(sql)
        self.sqlite.commit()

        Protocol.create(self.postgres, user_id = self.user_id, description='Изменение списка подразделений', schema_id=self.schema_id)
        #self.print_changes_table()
        #self.message(f'{for_delete}')
        self.заголовок()
        dept_set_tabs(self)

    #def remove_changes(self):
    #    dept_id = self.get('dept_id')
    #    dept = self.postgres.query(Dept).get(dept_id)
    #    self.postgres.query(SchemaDeptOrderLine)\
    #        .filter(SchemaDeptOrderLine.order_id == self.order.id, SchemaDeptOrderLine.dept_id == dept.id)\
    #       .delete()
    #    row = Row(self, 'table', dept_id)
    #    count = self.postgres.query(F.count()).filter(SchemaDeptOrderLine.order_id == self.order.id).scalar()
    #    if not count:
    #       self.changes_tab()
    #    self.заголовок()

    #def print_changes_row(self, row, order_line, dept):
    #    if order_line.sign:
    #        style = 'color:green'
    #        icon = 'add'
    #    else:
    #        style = 'color:red'
    #        icon = 'remove'
    #    row.cell(width=10, style=style).text(f'{dept.id}')
    #    row.cell(style=style).text(f'{dept.name}')

    #    cell = row.cell(width=2, align='right')
    #    IconButton(cell, None, icon, style=style)\
    #                .onclick('.remove_changes', {'dept_id' : dept.id})

    #def print_changes_table(self):
    #    table = Table(self, 'table')
    #    query = self.postgres.query(SchemaDeptOrderLine, Dept).join(Dept, Dept.id == SchemaDeptOrderLine.dept_id)\
    #        .filter(SchemaDeptOrderLine.order_id == self.order.id)
    #    for order_line, dept in query.order_by(Dept.name):
    #        row = table.row(dept.id)
    #       self.print_changes_row(row, order_line, dept)

    # ---------------------------
    # OPEN
    # ---------------------------
    def заголовок(self):
        count = self.sqlite.query(DeptSetItem).filter(DeptSetItem.dept_set_id == self.набор_ID).count()
        #count = DeptSetItem.count(self.cursor, 'dept_set=? and TYPE=?', [self.набор_ID, 0])
        if self.набор.CLASS == 1:
            схема = ДисконтнаяСхема.get(self.cursor, self.набор.дисконтная_схема_ID)
            if count:
                depts = f' ,подразделений {count}'
            else:
                depts = ''
            Title(self, f'{схема.наименование}{depts}')
        else:
            self.title(self.набор.полное_наименование)

        if self.МЕНЕДЖЕР:
            count = self.postgres.query(F.count()).filter(SchemaDeptOrderLine.order_id == self.order.id).scalar()
            toolbar = Toolbar(self, 'base_toolbar').mt(0)
            
            button = Button(toolbar.item(ml='auto'), f'Утвердить изменения')
            if count:
                button.style('color:white;background-color:red')            
                button.onclick('.accept')
            else:
                button.disabled(True)

    def __call__(self):
        self.postgres.query(SchemaDeptOrderLine).filter(SchemaDeptOrderLine.order_id == self.order.id).delete()
        self.заголовок()
        if not self.МЕНЕДЖЕР:
            self.print_table()
        else:
            dept_set_tabs(self)

# self.STATE['user_name'] = wdwddwdwd
# self.STATE['user_id'] = wdwdwdwdwdwd