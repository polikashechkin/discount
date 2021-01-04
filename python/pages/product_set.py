import sqlite3, json, datetime, re, time
from sqlalchemy import text as T, func as F, or_, and_, not_
from domino.core import log
from discount.actions import Action, ActionSetItem
from discount.core import DISCOUNT_DB
from domino.page import Page, Filter
from domino.page_controls import print_std_buttons, КраснаяКнопка, ПрозрачнаяКнопка, ПлоскаяТаблица, СтандартныеКнопки
from domino.page_controls import Кнопка, КнопкаВыбор
from discount.page import DiscountPage
from domino.page_controls import FormControl
from domino.page_controls import TabControl
from grants import Grants

from tables.Good import Good, QueryColumn
from domino.tables.postgres.report import Report
from domino.tables.postgres.report_line import ReportLine

#from tables.sqlite.product_set_item import ProductSetItem as ITEM
from tables.sqlite.good_set_item import GoodSetItem
from tables.sqlite.good_set_item import GoodSetItem as ITEM
from tables.sqlite.product_set import ProductSet as SET, ГотовыеНаборы
from tables.sqlite.product_set import ProductSet as PS
from tables.sqlite.complex_good_set_item import ComplexGoodSetItem as CHILD

from domino.pages import Title, Text, Toolbar, Button, FlatTable, Table, TextWithComments, Rows
from domino.pages import Input, InputText 
from domino.pages import IconButton, DeleteIconButton, EditIconButton, CheckIconButton, AddIconButton, RemoveIconButton, RefreshIconButton

MAX_ROWS = 200

product_set_tabs = TabControl('tab_control', visible='tab_visible')
product_set_tabs.append('products', 'Отобранные товары'.upper(), 'print_products')
product_set_tabs.append('поиск_товаров', 'Все товары'.upper(), 'поиск_товаров')
product_set_tabs.append('add_remove', 'Добавить из буфера обмена'.upper(), 'print_add_remove')
product_set_tabs.append('query_columns', 'Поисковые критерии'.upper(), 'print_query_columns_tab')
product_set_tabs.append('good_sets_tab', 'Наборы'.upper(), 'good_sets_tab')
product_set_tabs.append('good_sets_append_tab', 'Добавить'.upper(), 'good_sets_append_tab')
product_set_tabs.append('query_products_tab', 'Найденные товары'.upper(), 'query_products_tab')
product_set_tabs.append('virtual_set_tab', 'Условия вхождения товара в набор', 'virtual_set_tab')

def LOG(msg, start = None):
    if start:
        d = time.perf_counter() - start
    else:
        d = ''
    #log.debug(f'{msg} {d}')

class ThePage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request, controls=[product_set_tabs])
        self.set_id = int(self.attribute('set_id'))
        self._product_set = None
        self._MANAGER = None
        self.sqlite = None
        self.postgres = None
    
    @property
    def MANAGER(self):
        if self._MANAGER is None:
            self._MANAGER = self.grants.match(Grants.DS_MANAGER, self.product_set.schema_id) \
                     or  self.grants.match(Grants.DS_ASSISTANT, self.product_set.schema_id)
        return self._MANAGER
    
    @property
    def READONLY(self):
        return not self.MANAGER

    @property
    def product_set(self):
        if not self._product_set:
            #self._product_set = ProductSet.get(self.cursor, self.set_id)
            self._product_set = self.sqlite.query(SET).get(self.set_id)
        return self._product_set

    def save(self):
        self.sqlite.query(SET).filter(SET.id == self.set_id)\
            .update(
                {
                    SET.info : self.product_set.info,
                    SET.type_ : self.product_set.type_
                })
    @property
    def это_живой_набор(self):
        return self.product_set.type_ == SET.ТОВАРНЫЙ_ЗАПРОС
    @property
    def это_реестр_цен(self):
        return self.product_set.type_ == SET.ТОВАРНЫЙ_НАБОР_С_ЦЕНАМИ
    @property
    def это_карты(self):
        return self.set_id in [SET.ДИСКОНТНЫЕ_КАРТЫ_ID, SET.ПОДАРОЧНЫЕ_КАРТЫ_ID, SET.ПОСТОЯННО_ИСКЛЮЧЕННЫЕ_ТОВАРЫ_ID]
    # ----------------------------------------------
    def tab_visible(self, tab_id):
        if self.READONLY:
            return tab_id in ['products', 'groups']
        elif self.product_set.type_ == SET.ТОВАРНЫЙ_НАБОР:
            return tab_id in ['products', 'поиск_товаров', 'add_remove']
        if self.product_set.type_ == SET.ТОВАРНЫЙ_НАБОР_С_ЦЕНАМИ:
            return tab_id in ['products', 'поиск_товаров', 'add_remove']
        elif self.product_set.type_ == SET.ТОВАРНЫЙ_ЗАПРОС:
            return tab_id in ['query_columns', 'query_products_tab']
        elif self.product_set.type_ == SET.КОМПЛЕКСНЫЙ_НАБОР:
            return tab_id in ['good_sets_tab', 'good_sets_append_tab', 'query_products_tab']
        elif self.product_set.type_ == SET.ВИРТУАЛЬНЫЙ_НАБОР:
            return tab_id in ['virtual_set_tab']
        elif self.это_карты:
            return tab_id in ['products', 'поиск_товаров']
        return False

    # ------------------------------------------------------------------------------
    # ВИРТУАЛЬНЫЙ НАБОР 9.00^ 
    # ------------------------------------------------------------------------------
    def virtual_set_tab(self):
        self.text_block('about')
        self.toolbar('toolbar_top').mt(1)
        self.print_conditions()
        self.toolbar('toolbar_bottom').mt(1)

    def print_conditions(self):
        price_format = self.product_set.condition.get(PS.PRICE_FORMAT)
        no_price_format = self.product_set.condition.get(PS.NO_PRICE_FORMAT)
        table = FlatTable(self, 'table').mt(1)
        row = table.row(PS.PRICE_FORMAT)
        row.cell().text('Розничная цена товара в чеке оканчивается на цифру')
        select = row.cell().select(name=PS.PRICE_FORMAT, value=price_format)\
            .onchange('.change_condition', forms=[table])
        select.option('', 'НЕ ИМЕЕТ ЗНАЧАНИЯ')
        for i in [0,1,2,3,4,5,6,7,8,9]:
            select.option(i,i)
        #row = table.row(PS.NO_PRICE_FORMAT)
        #row.cell(width=20).text('Цена товара в чеке НЕ оканчивается на')
        #select = row.cell().select(name=PS.NO_PRICE_FORMAT, value=no_price_format)\
        #    .onkeypress(13, '.change_condition', forms=[table])
        #select.option('', 'НЕ ИМЕЕТ ЗНАЧАНИЯ')
        #for i in [0,1,2,3,4,5,6,7,8,9]:
        #    select.option(i,i)

    def change_condition(self):
        self.product_set.condition[PS.PRICE_FORMAT] = self.get(PS.PRICE_FORMAT)
        self.product_set.condition[PS.NO_PRICE_FORMAT] = self.get(PS.NO_PRICE_FORMAT)
        self.save()
        self.print_conditions()

    # ------------------------------------------------------------------------------
    # ОТОБРАННЫЕ НАБОРЫ
    # ------------------------------------------------------------------------------
    def good_sets_tab(self):
        self.text_block('about')
        self.toolbar('toolbar_top').mt(1)
        self.print_good_sets()
        self.toolbar('toolbar_bottom').mt(1)

    def print_good_sets(self):
        childs = CHILD.childs(self.sqlite, self.set_id)
        table = Table(self, 'table').mt(1)
        good_sets = self.sqlite.query(SET)\
            .filter(SET.id.in_(childs))\
            .all()
        for good_set in sorted(good_sets, key=lambda good: f'{good.name}' if good.id > 0 else ''):
            row = table.row(good_set.id)
            #row.cell(width=3).text(good_set.id)
            row.cell().text(good_set.name)
            cell = row.cell(align='right', style='color:gray')
            if good_set.id >= 0:
                cell.text(f'{good_set.type_name} ({good_set.schema_id})'.upper())
            DeleteIconButton(row.cell(width=2)).onclick('.remove_child', {'child_id':good_set.id})
        
    def remove_child(self):
        child_id = int(self.get('child_id'))
        CHILD.remove(self.sqlite, self.set_id, child_id)
        self.sqlite.commit()
        Rows(self, 'table').row(child_id)
        self.заголовок()

     # ------------------------------------------------------------------------------

    def good_sets_append_tab(self):
        #self.good_set = self.sqlite.query(SET).get(self.set_id)
        self.text_block('about')
        self.toolbar('toolbar_top').mt(1)
        self.print_good_sets_for_append()
        self.toolbar('toolbar_bottom').mt(1)

    def print_good_sets_for_append(self):
        self.good_set = self.sqlite.query(SET).get(self.set_id)
        childs = CHILD.childs(self.sqlite, self.set_id)
        table = Table(self, 'table').mt(1)
        good_sets = self.sqlite.query(SET)\
            .filter(SET.id != self.set_id)\
            .filter( 
                not_(
                    SET.id.in_(childs)
                    )
            )\
            .filter(
                or_(
                    SET.id.in_([SET.ПОДАРОЧНЫЕ_КАРТЫ_ID, SET.ДИСКОНТНЫЕ_КАРТЫ_ID]),
                    and_(
                        SET.id > 0,
                        or_(
                            SET.schema_id == self.product_set.schema_id,
                            SET.schema_id == 0
                            ),
                        SET.class_ == SET.ОБЩИЙ_НАБОР,
                        SET.type_.in_([SET.ТОВАРНЫЙ_ЗАПРОС, SET.ТОВАРНЫЙ_НАБОР, SET.ТОВАРНЫЙ_НАБОР_С_ЦЕНАМИ, SET.ВИРТУАЛЬНЫЙ_НАБОР])
                    ),
                )
            )\
            .all()
        for good_set in sorted(good_sets, key=lambda good: f'{good.name}' if good.id > 0 else ''):
            if not good_set.name : continue
            row = table.row(good_set.id)
            #row.cell(width=3).text(good_set.id)
            row.cell().text(good_set.name)
            cell = row.cell(align='right', style='color:gray')
            if good_set.id >= 0:
                cell.text(f'{good_set.type_name} ({good_set.schema_id})'.upper())
            AddIconButton(row.cell(width=2)).onclick('.add_child', {'child_id':good_set.id})

    def add_child(self):
        child_id = int(self.get('child_id'))
        CHILD.add(self.sqlite, self.set_id, child_id)
        self.sqlite.commit()
        Rows(self, 'table').row(child_id)
        self.заголовок()

    # ------------------------------------------------------------------------------
    # ПОИСКОВЫЕ КРИТЕРИИ
    # ------------------------------------------------------------------------------
    def print_query_columns_tab(self):
        self.text_block('about').mt(1)
        self.toolbar('toolbar_top').mt(1)
        self.print_query_columns()
        self.toolbar('toolbar_bottom').mt(1)
    def print_query_columns(self):
        table = ПлоскаяТаблица(self, 'table').mt(1)
        query = self.product_set.query
        for column in Good.QueryColumns(self.pg_cursor):
            if not column.is_dictionary:
                continue
            row = table.row(column.ID)
            values = query.get(column.ID)
            query_names = []
            if values is not None:
                names = column.get_names(self.pg_cursor) 
                if isinstance(values, list):
                    for value in values:
                        row = table.row(f'colimn_id__{value}')
                        name = names.get(value, value)
                        query_names.append(f'{name} ({value})')
                elif values:
                    value = values
                    name = names.get(value, value)
                    query_names.append(f'{name}:{value}')

            row.cell(style='white-space:nowrap').href(column.name.upper(), 'pages/product_set_query_column', {'product_set_id' : self.product_set.id, 'column_id' : column.ID})
            row.cell().text(', '.join(query_names))
            cell = row.cell(width=2)
            if len(query_names) > 0:
                DeleteIconButton(cell).onclick('.on_delete_query_value', {'column_id':column.ID})

    def on_delete_query_value(self):
        column_id = self.get('column_id')
        value = self.get('value')
        query = self.product_set.query
        if value:
            values = query.get(column_id)
            if values is not None:
                if isinstance(values, (list)):
                    values.remove(value)
                    if len(values) == 0:
                        del query[column_id]
                else:
                    del query[column_id]
        else:
            if column_id in query:
                del query[column_id]
        self.save()
        self.print_query_columns()

    # ------------------------------------------------------------------------------
    # НАЙДЕННЫЕ ТОВАРЫ 
    # ------------------------------------------------------------------------------
    def query_products_tab(self):
        self.text_block('about')
        toolbar = self.toolbar('toolbar_top').mt(0.5)
        toolbar.item(mr=0.5).input(label='Код (начальные символы)', name='good_code')\
            .onkeypress(13, '.query_products_table', forms=[toolbar])
        toolbar.item(mr=0.5).input(label='Наименование (вхождение)', name='good_name')\
            .onkeypress(13, '.query_products_table', forms=[toolbar])
        self.query_products_table()
        self.toolbar('toolbar_bottom').mt(1)
    def query_products_table(self):
        #finder = {'code' : self.get('good_code'), 'name' : self.get('good_name')}
        набор = ГотовыеНаборы(self.sqlite, LOG).готовый_набор(self.set_id)
        набор.prepeare(LOG)
        #набор = НАБОР.create(self.sqlite, self.set_id, LOG)
        query = набор.query(self.postgres)
        #query = Good.query(self.postgres, self.product_set.query)
        good_code = self.get('good_code')
        if good_code:
            query = query.filter(Good.code.ilike(f'{good_code.strip()}%'))
        good_name=self.get('good_name')
        if good_name:
            query = query.filter(Good.name.ilike(f'%{good_name.strip()}%'))
        query = query.order_by(Good.name).limit(MAX_ROWS)
        #log.debug(query)
        table = self.Table('table').mt(0.5)
        for good in query:
            row = table.row(good.code)
            self.print_good_code(row, good.code, good.e_code)
            self.print_good_name(row, good.name, good.description)
    # ------------------------------------------------------------------------------
    # ОТОБРАННЫЕ ТОВАРЫ
    # ------------------------------------------------------------------------------
    def print_products(self):
        # ------------------------
        self.text_block('about')
        self.товары_верхняя_панель()
        table = self.Table('table').mt(1)
        bottom = self.toolbar('toolbar_bottom').mt(1)
        #--------------------------
    def товары_верхняя_панель(self):
        #top = self.toolbar('toolbar_top').mt(1).style('align-items:center')
        top = ПлоскаяТаблица(self, 'toolbar_top').cls('table-hover', False).mt(1)
        #p = top.row().cell().toolbar().cls('flex-wrap')
        
        count = self.sqlite.query(F.count()).filter(ITEM.set_id == self.set_id).scalar()
        #count = ProductSetItem.count(self.cursor, 'product_set=? and TYPE=?', [self.set_id, 0])
        #pp = p.item().Text().mb(0.5).ml(0.5)
        #if count:
        #    pp.text(f'ТОВАРОВ {count}')
        #else:
        #    pp.style('color:gray')
        #    pp.text(f'ТОВАРОВ НЕТ')
        
        p = top.row().cell().toolbar().cls('flex-wrap')
        if count:
            p.item(mr=0.5).input(label='Код товара', name='code')
            p.item(mr=0.5).input(label='Наименование', name='name')
            #Кнопка(p, 'Показать').mr(0.5).onclick('.товары_показать', forms=[p])
            button = Кнопка(p, 'Показать').mr(0.5)
            button.item('Показать первые 200 товаров').onclick('.товары_показать', {'limit':200}, forms=[p])
            button.item('Показать первые 500 товаров').onclick('.товары_показать', {'limit':500}, forms=[p])
            button.item('Показать первые 1000 товаров').onclick('.товары_показать', {'limit':1000}, forms=[p])
            button.item('Показать все товары').onclick('.товары_показать', {'limit':0}, forms=[p])
            #Кнопка(p, 'Выгрузить').mr(0.5).onclick('responses/download_product_set', {'account_id':self.account_id, 'set_id':self.set_id}, target='DOWNLOAD')
            Кнопка(p.item(ml='auto'), 'Справка').onclick('.report_product_set', {'account_id':self.account_id, 'set_id':self.set_id})
        if not self.READONLY:
            if self.это_живой_набор:
                Кнопка(p,'Обновить').onclick('.товары_обновить')
            else:
                if count:
                    Кнопка(p.item(ml=0.5), 'Удалить все товары').onclick('.remove_all_products')
    
    def товары_показать(self):
        LIMIT = int(self.get('limit', 0))
        table = self.Table('table').mt(1)
        # --------------------
        items = {}
        for item in self.sqlite.query(ITEM).filter(ITEM.set_id == self.set_id):
            items[item.code] = item
        # --------------------
        if self.это_реестр_цен:
            table.column().text('Код')
            table.column().text('Описание')
            table.column().text('Цена')
            table.column().text('')
        # --------------------
        query = self.postgres.query(Good)
        query = query.filter(Good.code.in_(items))
        #count = 0
        CODE = self.get('code')
        if CODE:
            query = query.filter(Good.code.ilike(f'{CODE}%'))
        # --------------------
        NAME = self.get('name')
        if NAME:
            query = query.filter(Good.name.ilike(f'%{NAME}%'))
        # --------------------
        query = query.order_by(Good.name)
        if LIMIT:
            query = query.limit(LIMIT)
        # --------------------
        for good in query:
            item = items[good.code]
            row = table.row(item.id)
            self.товары_строка(row, good, items[good.code])

    def товары_строка(self, row, good, item):
        self.print_good_code(row, good.code, good.e_code)
        #self.print_good_name(row, good.name, good.description)
        self.print_good_name(row, good.name, None)

        if self.это_реестр_цен:
            cell = row.cell(width=10).cls('align-middle')
            if not item.price:
                cell.html('''<span style="color:red;"> НЕТ ЦЕНЫ</span>''')
            else:
                cell.text(item.PRICE)
            
            cell = row.cell(width=10, align='right')
            if not self.READONLY:
                DeleteIconButton(cell).onclick('.product_delete', {'item_id':str(item.id)})
                EditIconButton(cell).onclick('.товары_редактировать', {'item_id':str(item.id)})
                row.onclick('.товары_редактировать', {'item_id':str(item.id)})
        else:
            cell = row.cell(width=2)
            if not self.READONLY:
                DeleteIconButton(cell).onclick('.product_delete', {'item_id':str(item.id)})

    def товары_редактировать(self):
        item_id = self.get('item_id')
        item = self.sqlite.query(ITEM).get(item_id)
        good = self.postgres.query(Good).filter(Good.code == item.code).first()
        row = Rows(self, 'table').row(item_id)
        self.print_good_code(row, good.code, good.e_code)
        self.print_good_name(row, good.name, good.description)

        row.cell(width=10).input(name='цена', value = item.PRICE)\
            .onkeypress(13, '.товары_сохранить', {'item_id':item_id}, forms=[row])
        кнопки = СтандартныеКнопки(row, params={'item_id':item_id}, width=10)
        кнопки.кнопка('сохранить', 'товары_сохранить', forms=[row])
        кнопки.кнопка('отменить', 'товары_отменить')

    def товары_сохранить(self):
        item_id = int(self.get('item_id'))
        item = self.sqlite.query(ITEM).get(item_id)
        item.PRICE = float(self.get('цена'))
        row = Rows(self, 'table').row(item_id)
        good = self.postgres.query(Good).filter(Good.code == item.code).first()
        self.товары_строка(row, good, item)

    def товары_отменить(self):
        item_id = int(self.get('item_id'))
        item = self.sqlite.query(ITEM).get(item_id)
        good = self.postgres.query(Good).filter(Good.code == item.code).first()
        row = Rows(self, 'table').row(item_id)
        self.товары_строка(row, good, item)

    def product_delete(self):
        item_id = int(self.get('item_id'))
        self.sqlite.query(ITEM).filter(ITEM.id == item_id).delete()
        #with self.connection:
        #    ProductSetItem.deleteall(self.cursor, 'ID=?', [item_id])
        Rows(self, 'table').row(item_id)
        self.товары_верхняя_панель()
        self.заголовок()

    def remove_all_products(self):
        self.sqlite.query(ITEM).filter(ITEM.set_id == self.set_id).delete()
        self.print_products()
        self.заголовок()
    
    def report_product_set(self):
        # список всех наименований товаров
        good_names = {}
        for good_code, good_name in self.postgres.query(Good.code, Good.name):
            good_names[good_code] = good_name

        # список элементов набора с наименованиями
        items = []
        for item in self.sqlite.query(GoodSetItem).filter(GoodSetItem.set_id == self.set_id):
            items.append(item)
            item.name = good_names.get(item.code, '')
        log.debug(f'ITEMS {len(items)}')
        
        report = Report('', 'good_set_items', info = {'set_id':self.set_id})
        report.name = f'Товарный набор "{self.product_set.name}"'
        self.postgres.add(report)
        self.postgres.commit()

        #stream = io.StringIO()
        #for item in sorted(items, key = item.name):
        lines = 0
        for item in items:
            lines += 1
            info = {'code':item.code, 'name':item.name}
            if item.price:
                info['price'] = f'{round(item.price/100, 2)}'
            else:
                info['price'] = '0'
            report.line(self.postgres, info)
        
        report.state = 1
        report.lines = lines
        self.postgres.commit()
        self.message(f'Справка {report.id}, {report.name}, строк {lines}')

    # -------------------------------------------------------------------------------
    # ВСЕ ТОВАРЫ
    # -------------------------------------------------------------------------------
    def поиск_товаров(self):
        self.text_block('about')
        self.поиск_товаров_верхняя_панель()
        self.table('table', hole_update=True)
        #self.поиск_товаров_таблица()
        self.toolbar('toolbar_bottom').mt(1)
        # -----------------------
    def print_query_column(self, column, toolbar, value):
        item = toolbar.item(mr=0.5)
        if column.is_dictionary:
            select = item.select(label=column.name, value = value, name = column.ID)\
                .onchange('.save_product_query', forms=[toolbar])
            for code, name in column.get_names(self.pg_cursor).items():
                select.option(code, name)
        else:
            item.input(label=column.name, value=value, name=column.ID)\
                .onkeypress(13, '.save_product_query', forms=[toolbar])
    def поиск_товаров_верхняя_панель(self):
        toolbar_top = ПлоскаяТаблица(self, 'toolbar_top').cls('table-hover', False)
        # -----------------------------
        toolbar_query = toolbar_top.row().cell().toolbar().cls('flex-wrap') 
        unusable_columns = []
        usable_columns = []
        query = self.product_set.query
        for column in Good.QueryColumns(self.pg_cursor):
            value = query.get(column.ID)
            #log.debug(f'{value} = self.product_set.query.get({column.ID})')
            if value is None:
                unusable_columns.append(column)
            elif isinstance(value, (list, tuple)):
                value = value[0] if len(value) > 0 else ''
                self.print_query_column(column, toolbar_query, value)
                usable_columns.append(column)
            else:
                self.print_query_column(column, toolbar_query, value)
                usable_columns.append(column)
        # -----------------------------
        usable_columns_exists = len(usable_columns) > 0
        if not usable_columns_exists:
            p = toolbar_query.item().text_block().ml(1)
            p.style('color:gray')
            p.text('Не задано ни одного поискового критерия'.upper())
        # -----------------------------
        toolbar_actions = toolbar_top.row().cell().toolbar().mt(0.3)
        if self.это_живой_набор:
            if usable_columns_exists:
                Кнопка(toolbar_actions, 'Сохранить критерии поиска', mr=0.5).onclick('.поиск_товаров_сохранить_критерии_поиска', forms=[toolbar_query])
        else:
            if usable_columns_exists:
                button = Кнопка(toolbar_actions, 'Показать', mr=0.5)\
                    .onclick('.поиск_товаров_найти_товары', {'order_by':'order by name'}, forms=[toolbar_top])
                #button.item('ПОКАЗАТЬ ПО КОДУ ').onclick('.поиск_товаров_найти_товары', {'order_by':'order by code'}, forms=[панель])
                #button.item('ПОКАЗАТЬ ПО НАИМЕНОВАНИЮ ').onclick('.поиск_товаров_найти_товары', {'order_by':'order by name'}, forms=[панель])
            if usable_columns_exists:
                Кнопка(toolbar_actions, 'Добавить в набор', mr=0.5)\
                    .onclick('.add_goods_by_query', forms=[toolbar_top])
        # -----------------------------
        if len(unusable_columns) > 0:
            button = КнопкаВыбор(toolbar_actions, 'Добавить поисковый критерий', mr=0.5)
            for column in unusable_columns:
                button.item(column.name.upper()).onclick('.add_product_query_column', {'column_id' : column.ID})
        if len(usable_columns) > 0:
            button = КнопкаВыбор(toolbar_actions, 'Удалить поисковый критерий', mr=0.5)
            for column in usable_columns:
                button.item(column.name.upper()).onclick('.delete_product_query_column', {'column_id' : column.ID})
    def save_product_query_values(self):
        query = self.product_set.query
        for column_id in Good.Columns:
            value = self.get(column_id.lower())
            #log.debug(f'save_product_query_values "{column_id}" : "{value}" : {query}')
            if value is None:
                if column_id in query:
                    del query[column_id]
            else:
                query[column_id] = value
    def save_product_query(self):
        self.save_product_query_values()
        self.save()
        self.поиск_товаров_верхняя_панель()
    def delete_product_query_column(self):
        ID = self.get('column_id')
        if ID in self.product_set.query:
            del self.product_set.query[ID]
        self.save()
        self.поиск_товаров_верхняя_панель()
    def add_product_query_column(self):
        ID = self.get('column_id')
        self.product_set.query[ID] = ''
        self.save()
        #log.debug(f'add_product_query_column {ID} : {self.product_set.query}')
        self.поиск_товаров_верхняя_панель()
    
    def print_good_code(self, row, code, e_code):
        #TextWithComments(row.cell(), code, [e_code] if e_code else None)
        row.cell(width=10, style='white-space:nowrap').text(code)
        #row.cell().html(f'''<span style="white-space:nowrap">{code}</span><p style="font-size:small;color:gray; line-height: 0.7em">{e_code}</p>''')
    def print_good_name(self, row, name, description):
        comments = []
        if description is not None:
            for имя, значение in description.items():
                comments.append(f'{имя} "{значение}"')
        TextWithComments(row.cell(), name, comments)
        #row.cell().html(f'''{name}<p style="font-size:small;color:gray; line-height: 1em">{', '.join(параметры)}</p>''')
    
    def поиск_товаров_таблица(self):
        table = self.Table('table').mt(0.5)
        # --------------------
        codes = set()
        for code, in self.sqlite.query(ITEM.code).filter(ITEM.set_id == self.set_id):
            codes.add(code)
        # --------------------
        query = Good.query(self.postgres, self.product_set.query)
        code = self.get('code')
        name = self.get('name')
        if code:
            query = query.filter(Good.code.ilike(f'{code}%')) 
        if name:
            query = query.filter(Good.name.ilike(f'%{name}%')) 

        query = query.order_by(Good.name).limit(MAX_ROWS)
        for good in query:
        #    count += 1
            row = table.row(good.code)
            exists = good.code in codes
            self.print_good_code(row, good.code, good.e_code)
            self.print_good_name(row, good.name, good.description)
            cell = row.cell(width=2)
            if not exists:
                AddIconButton(cell).onclick('.add_good_by_code', {'code' : good.code }) 

    def add_goods_by_query(self):
        self.save_product_query()
        query = self.postgres.query(Good.code)
        query = query.filter(Good.filter(self.product_set.query))
        code = self.get('code')
        name = self.get('name')
        if code:
            query = query.filter(Good.code.ilike(f'{code}%')) 
        if name:
            query = query.filter(Good.name.ilike(f'%{name}%')) 
        added = 0
        for code, in query:
            added += ITEM.add(self.sqlite, self.set_id, code)
        self.sqlite.commit()
        self.заголовок()
        self.message(f'Добавлено {added} товаров"')
        
    def add_good_by_code(self):
        added = 0
        code = self.get('code')
        added += ITEM.add(self.sqlite, self.set_id, code) 
        self.заголовок()
        self.table('table').row(code)
        self.message(f'Добавлено {added} товаров {code}')
    
    #def поиск_товаров_добавить_товар(self):
    #    code = self.get('code')
    #    added = 0
    #    with self.connection:
    #        added += self.product_set.добавить_товар_по_коду(self.cursor, self.db_cursor, self.ТОВАРНЫЕ_ТЕГИ, code)
    #    self.table('table').row(code)
    #    self.message(f'Добавлено {added} товаров"')

    def поиск_товаров_сохранить_критерии_поиска(self):
        query = self.product_set.query
        for column_id in query:
            value = self.get(column_id)
            query[column_id] = value
        self.save()

    def поиск_товаров_найти_товары(self):
        self.save_product_query()
        self.поиск_товаров_таблица()
    # ---------------------------------------------------------------------------
    # ADD / REMOVE
    # ---------------------------------------------------------------------------
    def print_add_remove(self):
        # ------------------------
        self.add_remove_описание()
        top = Toolbar(self, 'toolbar_top').mt(1)
        textarea = self.textarea('table', name='products').mt(1).style('height:20rem')
        bottom = self.toolbar('toolbar_bottom').mt(1)
        # -----------------------
        #if self.это_реестр_цен:
        #    ПрозрачнаяКнопка(top, 'Добавить товары и цены').onclick('.add_products_and_prices', forms=[textarea])
        Button(top.item(), 'Добавить товары').onclick('.add_products', forms=[textarea])
        Button(top.item(ml=1), 'Удалить товары').onclick('.remove_products', forms=[textarea])
    def add_remove_описание(self):
        p = self.text_block('about').mt(1)
        p.text('''
        В данном режиме 
        добавляются и удаляются товары из буфера обмена, в который 
        вносятся данные о товарах с помощью copy-paste в виде текста. 
        Это может быть достаточно произвольный текст, включающий 
        в себя в том числе и коды товаров, которые "выуживаются" 
        из текста согласно шаблону, остальной текст игнорируется. 
        Коды товаров проверяются по справочнику товаров и 
        добавляются в набор или удаляются из него, согласно выбранной операции. 
        Таким образом можно загружать товары из файлов, почтовых сообщений, excel таблиц, 
        отчетов и вообще из всего, 
        что можно скопировать в буфер обмена.
        Шаблон товара предполагает, что код товара может состоять из букв, цифр, дефиса(-) и косой черты(/)
        ''')
        p.newline(style = "margin-top:0.3rem")
        p.text('''
            Шаблон товара предполагает, что код товара может состоять из букв, цифр, 
            дефиса(-) и косой черты(/)
        ''')
        if self.это_реестр_цен:
            p.newline(style = "margin-top:0.3rem")
            p.text('''
            В режиме ДОБАВЛЕНИЯ ТОВАРОВ И ЦЕН, из текста "выуживаются" пары
            код и цена. Цена обязательно должна иметь точку(.). 
            Это позволяет отличать
            цену от просто набора цифр, который часто встечается в кодах товаров.
            ''')
    def get_add_remove_codes(self):
        #PATTERN = r'\d[\w-]{5,30}'
        PATTERN = r'[\w\-/]{5,40}'
        products = self.get('products')
        return re.findall(PATTERN, products)

    #def добавить_товар(self, code, name, info={}):
    #    added = 0
    #    item = ProductSetItem()
    #    item.product_set = self.set_id
    #    item.info = info
    #    item.code = code
    #    item.description = name
    #    try:
    #        item.create(self.cursor)
    #        added += 1
    #    except:
    #        pass
    #    return added

    def add_products(self):
        added = 0
        codes = self.get_add_remove_codes()
        query = self.postgres.query(Good.code).filter(Good.code.in_(codes))
        _codes = []
        for code, in query:
            _codes.append(code)
            added += ITEM.add(self.sqlite, self.set_id, code)
        self.sqlite.commit()
        self.message(f'Добавлено {added} товаров')
        self.заголовок()
    def add_products_and_prices(self):
        PATTERN = r'[\w\-/]{5,40}|[0-9]+.[0-9]+'
        products = self.get('products')
        
        codes = []
        for code in re.findall(PATTERN, products):
            good_code = self.postgres.query(Good.code).filter(Good.code == code).first()
            if good_code:
                codes.append(code)
            elif code.find('.') != -1:
                try:
                    code = float(code)
                    codes.append(code)
                except:
                    pass

        codes_and_prices = []
        product_code = None
        product_price = None
        for code in codes:
            if isinstance(code, str):
                product_code = code
            elif isinstance(code, float):
                product_price = code
            if product_code is not None and product_price is not None:
                codes_and_prices.append([product_code, product_price])        
                product_code = None
                product_price = None

        added = 0

        #with self.connection:
        #    for code, price in codes_and_prices:
        #        added += self.add_good_by_code(code, price)
                #added += self.product_set.добавить_товар_по_коду(self.cursor, self.db_cursor, self.ТОВАРНЫЕ_ТЕГИ, code, цена = price)

        self.message(f'Добавлено/обнавлено {added} товаров. {codes_and_prices}')
    def remove_products(self):
        codes = set(self.get_add_remove_codes())
        remove_codes = []
        for code, in self.postgres.query(Good.code).filter(Good.code.in_(codes)):
            remove_codes.append(code)
        query = self.sqlite.query(ITEM).filter(ITEM.set_id == self.set_id, ITEM.code.in_(remove_codes))
        rowcount = query.delete(synchronize_session=False)
        self.sqlite.commit()
        self.message(f'Удалено {rowcount} товаров')
        self.заголовок()
    
    # ---------------------------
    # OPEN
    # ---------------------------
    def on_change_params(self):
        product_set_type = int(self.get('product_set_type'))
        if product_set_type == SET.КОМПЛЕКСНЫЙ_НАБОР:
            child = self.sqlite.query(CHILD).filter(CHILD.child_id == self.set_id).first()
            if child:
                self.error(f'Тип данного набора не может КОМПЛЕКСНЫЙ НАБОР, поскольку он уже входит в другой комплексный набор {child.set_id}')
                self.print_params()
                return
        goods_set = self.sqlite.query(SET).get(self.set_id)
        goods_set.clean(self.sqlite)
        self.sqlite.commit()

        #product_set_name = self.get('product_set_name')

        #self.product_set.info['description'] = product_set_name
        self.product_set.type_ = product_set_type
        self.save()

        self.заголовок()
        self.print_params()
        self.REFRESH=True
        #product_set_tabs.print(self)
        #self.message(f'{product_set_type} : {product_set_name}')

    def print_params(self):
        toolbar = self.toolbar('params')
        if self.product_set.class_ in [0,1] and not self.READONLY:
            if self.product_set.type_ in [SET.ТОВАРНЫЙ_НАБОР, SET.ТОВАРНЫЙ_ЗАПРОС, SET.КОМПЛЕКСНЫЙ_НАБОР, SET.ВИРТУАЛЬНЫЙ_НАБОР]:
                select = toolbar.item(mr=0.6).select(name='product_set_type', value=self.product_set.type_)\
                    .onchange('.on_change_params', forms=[toolbar])
                select.option(SET.ТОВАРНЫЙ_НАБОР, 'Товарный набор'.upper())
                select.option(SET.ТОВАРНЫЙ_ЗАПРОС, 'Товарный запрос'.upper())
                #select.option(ProductSet.TYPE_GROUPS, 'Набор категорий'.upper())
                select.option(SET.КОМПЛЕКСНЫЙ_НАБОР, 'Комплексный набор'.upper())
                select.option(PS.ВИРТУАЛЬНЫЙ_НАБОР, PS.TYPE_NAME(PS.ВИРТУАЛЬНЫЙ_НАБОР).upper())
        #if self.product_set.CLASS in [0] and not self.READONLY:
        #    toolbar.item(width=30).input(label='Наименование', name='product_set_name', value=self.product_set.description)\
        #        .onkeypress(13, '.on_change_params', forms=[toolbar])

    def заголовок(self):
        if self.это_карты:
            title = self.product_set.name
        else:
            title = f'{self.set_id}, {self.product_set.name}'
        if self.product_set.type_ in [SET.ТОВАРНЫЙ_НАБОР, SET.ТОВАРНЫЙ_НАБОР_С_ЦЕНАМИ]:
            count = self.sqlite.query(F.count()).filter(ITEM.set_id == self.set_id).scalar()    
            if count:
                title += f', товаров {count}'
            else:
                title += f', товаров нет'
        elif self.product_set.type_ in [SET.КОМПЛЕКСНЫЙ_НАБОР]:
            childs = CHILD.childs(self.sqlite, self.set_id)
            if len(childs) > 0:
                title += f', наборов {len(childs)}'
        Title(self, title)

    def __call__(self):
        self.заголовок()
        if not self.это_карты:
            self.print_params()
            #ОсновныеПараметры(self)
        product_set_tabs.print(self)

