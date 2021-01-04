import flask, sqlite3, json, datetime, os, arrow
from . import Button
from domino.page import Page
from domino.page_controls  import print_std_buttons, СтандартныеКнопки
from domino.page_controls  import ПрозрачнаяКнопка, КраснаяКнопка, КраснаяКнопкаВыбор, Кнопка
from domino.core import log
from discount.action_types import ActionTypes
import discount.actions
from discount.core import DISCOUNT_DB, SCHEMES_FOLDER
from discount.actions import Action
from discount.schemas import ДисконтнаяСхема
from discount.dept_sets import DeptSetItem

from discount.page import DiscountPage as BasePage
from grants import Grants

from tables.sqlite.product_set import ProductSet as PS
#from tables.sqlite.product_set_item import ProductSetItem as ITEM
from tables.sqlite.complex_good_set_item import ComplexGoodSetItem as CHILD
from domino.tables.postgres.dept import Dept
from tables.sqlite.schema import Schema

from discount.pos import PosCheck

from tables.postgres.protocol import Protocol
from components.discount_schema import DiscountSchema as DS

CALC_TAB = 'calc'
ACCEPT_TAB = 'accept'
PRODUCT_SETS_TAB = 'product_sets_tab'
TEST_CHECKS_TAB = 'test_checks_tab'

class ThePage(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.action_id = self.attribute('action_id')
        self._action = None
        self.tab_id = self.attribute('actions_tab_id', CALC_TAB)
        self.схема_ID = self.attribute('схема_ID')
        self.schema_id = int(self.схема_ID)
        self._схема = None
        self.BOSS   = self.grants.match(Grants.DS_MANAGER, str(self.схема_ID))
        self.ASSISTANT   = self.grants.match(Grants.DS_ASSISTANT, str(self.схема_ID))
        #self.СМОТРЯЩИЙ  = self.grants.match(Grants.DS_WATCHING, self.схема_ID)
        if self.BOSS:
            self.ASSISTANT = True
        
        self.ОСНОВНАЯ_СХЕМА = self.схема_ID == "0"
    @property
    def схема(self):
        if self._схема is None:
            self._схема = ДисконтнаяСхема.get(self.cursor, self.схема_ID)
        return self._схема

    @property
    def action(self):
        if self._action is None:
            self._action = Action.get(self.cursor, self.action_id)
        return self._action

    # ----------------------------------
    #   TEST CHECKS TAB 
    # ----------------------------------
    def test_checks_tab(self):
        self.test_checks_toolbar()
        self.test_checks_table()
    
    def test_checks_toolbar(self):
        toolbar = self.toolbar('toolbar').mt(1)
        Кнопка(toolbar.item(ml='auto'), 'создать').onclick('.test_check_create')
        #Кнопка(toolbar.item(ml=1), 'Тестовые карты').onclick('pages/test_cards')

    def test_checks_table(self):
        table = self.Table('table').mt(1)
        table.column()
        table.column().text('Описание')
        table.column().text('Подразделение')
        table.column().text('Дата')
        table.column().text('Сервер')
        table.column().text('Timeout')
        table.column()
        self.cursor.execute('select ID from TEST_CHECKS order by ID desc')
        for ID, in self.cursor:
            try:
                check = PosCheck.load(self.account_id, ID)
            except:
                continue
            if check.schema_id != self.схема_ID:
                continue
            #log.debug(f'{check}')
            row = table.row(ID)
            self.check_row(row, check, ID)

    def get_dept_name(self, code):
        self.pg_cursor.execute('select name from dept where id=%s', [code])
        r = self.pg_cursor.fetchone()
        return r[0] if r is not None else code

    def on_test_check_edit(self):
        check_id = self.get('check_id')
        check = PosCheck.load(self.account_id, check_id)
        row = self.Row('table', check_id)
        self.check_row(row, check, check_id, True)
        self.message(f'edit mode')

    def on_test_check_cancel(self):
        ID = self.get('check_id')
        check = PosCheck.load(self.account_id, ID)
        row = self.Row('table', ID)
        self.check_row(row, check, ID, False)
        self.message(f'cancel')
 
    def on_test_check_save(self):
        ID = self.get('check_id')
        check = PosCheck.load(self.account_id, ID)
        row = self.Row('table', ID)
        check.name = self.get('check_name')
        check.dept_code = self.get('check_dept_code')
        try:
            check.date = arrow.get(self.get('check_date')).datetime
        except:
            check.date = None
        check.server = self.get('check_server')
        try:
            check.timeout = int(self.get('check_timeout'))
        except:
            log.exception(__file__)
        check.save()
        self.check_row(row, check, ID, False)
        self.message(f'save')

    def get_dept_options(self, check):
        options = []
        #log.debug(f'get_dept_options : {check.schema_id}')
        schema_id = int(check.schema_id)
        if schema_id == 0:
            #log.debug(f'get_dept_options 2 : {schema_id}')
            all_codes = set()
            for schema in self.sqlite.query(Schema):
                codes = schema.get_dept_codes(self.sqlite)
                for code in codes:
                    all_codes.add(code)
                #log.debug(f'{codes}, {all_codes}')
                for dept in self.postgres.query(Dept).filter(Dept.id.notin_(all_codes)).order_by(Dept.name):
                    options.append([dept.id, dept.name])
        else:
            schema = self.sqlite.query(Schema).get(schema_id)
            codes = schema.get_dept_codes(self.sqlite)
            for dept in self.postgres.query(Dept).filter(Dept.id.in_(codes)).order_by(Dept.name):
                options.append([dept.id, dept.name])
        return options

    def check_row(self, row, check, ID, edit_mode=False):
        ID = str(ID)
        try:
            if check.test_mode == 0:
                кнопка = row.cell(width=2).icon_button('fiber_manual_record', style='color:orange')
                кнопка.tooltip('Проверка акций, ДО уверждения дисконтной схемы')
            else:
                кнопка = row.cell(width=2).icon_button('fiber_manual_record', style=f'color:lightgray')
                кнопка.tooltip('Проверка акций, ПОСЛЕ уверждения дисконтной схемы.')
            if not edit_mode:
                кнопка.onclick('.change_check_test_mode', {'ID' : ID})
            # описание
            cell = row.cell(width=20)
            if edit_mode:
                cell.input(name='check_name', value=check.name)\
                    .onkeypress(13, '.on_test_check_save', {'check_id':str(ID)}, [row])
            else:
                cell.href(check.name, 'pages/test.open', {'ID' : ID})
            # подразделение
            cell = row.cell()
            if edit_mode:
                select = cell.select(name = 'check_dept_code', value=check.dept_code)\
                    .onkeypress(13, '.on_test_check_save', {'check_id':str(ID)}, [row])
                for [code, name] in self.get_dept_options(check):
                    select.option(code, name)
            else:
                cell.text(f'{check.dept_code} {self.get_dept_name(check.dept_code)}')
            # дата
            cell = row.cell(width=15)
            if edit_mode:
                try:
                    value = check.date.strftime('%Y-%m-%dT%H:%M')
                except:
                    value = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')
                cell.input(name='check_date', value=value, type='datetime-local')\
                    .onkeypress(13, '.on_test_check_save', {'check_id':str(ID)}, [row])
            else:
                try:
                    value = check.date.strftime('%Y-%m-%d %H:%M')
                except:
                    value = 'Текущая дата и время'
                cell.text(value)
            # сервер 
            cell = row.cell()
            if edit_mode:
                cell.input(name='check_server', value=check.server)\
                    .onkeypress(13, '.on_test_check_save', {'check_id':str(ID)}, [row])
            else:
                cell.text(f'{check.server}')
            # timeout 
            cell = row.cell(width=4)
            if edit_mode:
                cell.input(name='check_timeout', value=check.timeout)
            else:
                cell.text(f'{check.timeout}c')
        except BaseException as ex:
            log.exception(__file__)
            row.cell().text(f'{ex}')
        #------------------------------------
        cell = row.cell(width=4, style='white-space:nowrap')
        if edit_mode:
            cell.icon_button('check', style='color:green').onclick('.on_test_check_save', {'check_id':str(ID)}, [row])
            cell.icon_button('close', style='color:gray').onclick('.on_test_check_cancel', {'check_id':str(ID)})
        else:
            cell.icon_button('edit', style='color:lightgray').onclick('.on_test_check_edit', {'check_id':str(ID)})
            cell.icon_button('close', style='color:red').onclick('.test_check_delete', {'check_id':str(ID)})
    
    def test_check_create(self):
        #схема_ID = self.get('схема_ID')
        #схема_наименование= self.get('схема_наименование')
        with self.connection:
            self.cursor.execute('''insert into TEST_CHECKS (NAME) values ('')''')
        ID = self.cursor.lastrowid
        #try:
        #    previous = PosCheck.load(self.account_id, ID - 1)
        #except:
        #    previous = None

        check = PosCheck(self.account_id, ID, self.схема_ID)
        check.session_id = f'{ID}'
        check.pos_id = f'{self.схема_ID}'
        #check.dept_code = self.get_first_dept_code(self.схема_ID)
        options = self.get_dept_options(check)
        if len(options):
            check.dept_code = options[0][0]
        check.check_no = 1
        #if previous:
        #    check.server = previous.server
        check.save()
        self.test_checks_tab()

    def test_check_delete(self):
        ID = int(self.get('check_id'))
        with self.connection:
            self.cursor.execute('''delete from TEST_CHECKS where ID=?''', [ID])

        self.Row('table', ID)

    def change_check_test_mode(self):
        ID = self.get('ID')
        check = PosCheck.load(self.account_id, ID)
        if check.test_mode == 0:  
            check.test_mode = 1
        else:
            check.test_mode = 0
        check.save()
        row = self.Row('table', ID)
        self.check_row(row, check, ID)

    # ----------------------------------
    #   ТОВАРНЫЕ НАБОРЫ
    # ----------------------------------
    def product_sets_tab(self):
        self.product_sets_toolbar()
        self.product_sets_table()

    def product_sets_toolbar(self):
        p = self.toolbar('toolbar').mt(1)
        if self.ASSISTANT:
            Кнопка(p, 'Создать набор').onclick('.create_set')
            #Кнопка(p, 'Создать живой набор', ml=0.5).onclick('.создать_живой_набор')
            Кнопка(p, 'Создать товарный набор с ценами', ml=0.5).onclick('.create_price_set')
            #Кнопка(p, 'Очистить', ml='auto').onclick('.cleaning').tooltip('Удалить все наборы, которын не используются ни в одной акции')

    def ps_depends(self, set_id):
        depends = []
        actions = []
        sql = '''
            select distinct action_id from action_set_item where set_id = ?
        '''
        self.cursor.execute(sql, [set_id])    
        for action_id, in self.cursor:
            actions.append(str(action_id))
        if len(actions) > 0:
            depends.append(f'используется в акциях {",".join(actions)}')

        parents = []
        for child in self.sqlite.query(CHILD).filter(CHILD.child_id == set_id):
            parents.append(f'{child.set_id}')
        if len(parents) > 0:
            depends.append(f'используется в комплекстых наборах {",".join(parents)}')

        if len(depends) == 0:
            return None
        else:
            return ' '.join(depends)
        
    #def actions_of_set(self, set_ID):
    #    actions = []
    #    sql = ''' 
    #        select distinct action_id from action_set_item where set_id = ?
    #    '''
    #    self.cursor.execute(sql, [set_ID])    
    #    for action_ID, in self.cursor:
    #        actions.append(str(action_ID))
    #3    if len(actions) == 0:
    #        return None
    #    else:
    #        return actions

    def on_edit_set_row(self):
        set_id = int(self.get('product_set_id'))
        ps = self.sqlite.query(PS).get(set_id)
        row = self.Row('table', ps.id)
        self.print_set_row(row, ps, True)

    def on_cancel_set_row(self):
        set_id = int(self.get('product_set_id'))
        ps = self.sqlite.query(PS).get(set_id)
        row = self.Row('table', ps.id)
        self.print_set_row(row, ps)

    def on_save_set_row(self):
        set_id = int(self.get('product_set_id'))
        name = self.get('name')
        #self.message(f'{name}')
        ps = self.sqlite.query(PS).get(set_id)
        ps.name = name
        row = self.Row('table', ps.id)
        self.print_set_row(row, ps)

    def print_set_row(self, row, ps, edit_mode=False):
        #cell = row.cell(width=2)
        #if p.это_живой_набор:
        #    cell.icon_button('refresh').tooltip('Это живой товарный набор')
        #elif p.это_реестр_цен:
        #    cell.icon_button('fiber_manual_record', style='color:red').tooltip('Это товарный набор с ценами')
        #else:
        #    cell.icon_button('').tooltip('Это товарный набор')
        
        #-------------------------------------------
        if edit_mode:
            row.style('warning').css('table-warning shadow') 
            cell = row.cell(width=3)
            cell.text(ps.id)
            cell = row.cell()
            cell.input(name='name', value=ps.name)\
                .onkeypress(13, '.on_save_set_row', {'product_set_id': ps.id}, forms=[row])
        else:
            cell = row.cell(width=3)
            cell.href(ps.id, 'pages/product_set', {'set_id':ps.id})
            cell = row.cell()
            cell.href(ps.name, 'pages/product_set', {'set_id':ps.id})
        #--------------------------------------------
        cell = row.cell(align='right', style='color:gray')
        cell.text(ps.type_name.upper())

        #--------------------------------------------
        ps_depends = self.ps_depends(ps.id)
        #row.cell().text(f'{actions}')
        cell = row.cell(width=6, align='right')
        if edit_mode:
            cell.icon_button('check', style='color:green')\
                .onclick('.on_save_set_row', {'product_set_id' : ps.id}, forms=[row])
            cell.icon_button('close', style='color:gray')\
                .onclick('.on_cancel_set_row', {'product_set_id':ps.id})
        else:
            if self.ASSISTANT:
                cell.icon_button('edit', style='color:lightgray')\
                    .onclick('.on_edit_set_row', {'product_set_id' : ps.id})
                #row.onclick('.on_edit_set_row', {'product_set_id' : ps.id})

                if ps_depends:
                    cell.icon_button('close', style='color:lightgray')\
                        .tooltip(f'Удаление запрешено. Данный набор {ps_depends}')
                else:
                    cell.icon_button('close', style='color:red').onclick('.delete_set', {'set_id':ps.id})

    def product_sets_table(self):
        table = self.Table('table').mt(1)
        #product_sets = ProductSet.findall(self.cursor, 'schema_id=? and CLASS = 0', [int(self.схема_ID)])
        product_sets = self.sqlite.query(PS)\
            .filter(PS.schema_id == int(self.схема_ID), PS.class_ == 0)\
            .all()
        for p in sorted(product_sets, key=lambda p : p.id, reverse=True):
            row = table.row(p.id)
            self.print_set_row(row, p)

    def delete_set(self):
        set_id = int(self.get('set_id'))
        PS.delete(self.sqlite, set_id)
        #self.sqlite.query()
        #with self.connection:
        #    ProductSet.deleteall(self.cursor, 'ID=?', [set_id])
        #    ProductSetItem.deleteall(self.cursor, 'product_set=?', [set_id])
        self.table('table').row(set_id)

    def create_set(self):
        p = PS()
        p.class_ = PS.ОБЩИЙ_НАБОР
        p.type_ = PS.ТОВАРНЫЙ_НАБОР
        p.schema_id = self.схема.ID
        p.name = '<Товарный набор>'
        self.sqlite.add(p)
        self.sqlite.commit()
        #self.sqlite.query(ITEM)
        #self.sqlite()
        #with self.connection:
        #    p.create(self.cursor)
        #    ProductSetItem.deleteall(self.cursor, 'product_set=?', [p.ID])
        self.product_sets_table()

    def create_price_set(self):
        p = PS()
        p.class_ = PS.ОБЩИЙ_НАБОР
        p.type_ = PS.ТОВАРНЫЙ_НАБОР_С_ЦЕНАМИ
        p.name = '<Товарный набор с ценами>'
        p.schema_id = self.схема.ID
        self.sqlite.add(p)
        self.sqlite.commit()
        #with self.connection:
        #    p.create(self.cursor)
        #    ProductSetItem.deleteall(self.cursor, 'product_set=?', [p.ID])
        self.product_sets_table()

    # ----------------------------------
    #   ACTIONS TABLE 
    # ----------------------------------
    def print_table(self):
        table = self.Table('table').mt(1)
        table.cls('table-hover', False)

        if self.работа_с_расчетными_акциями:
            for n in range(0, self.схема.расчетные_акции.размер):
                action_id = self.схема.расчетные_акции.акция_ID(n)
                action = Action.get(self.cursor, action_id)
                if action is None:
                    self.print_error_row(table, action_id, n)
                else:
                    self.print_row(table, action, n)
        else:
            for n in range(0, self.схема.послепродажные_акции.размер):
                action_id = self.схема.послепродажные_акции.акция_ID(n)
                action = Action.get(self.cursor, action_id)
                self.print_row(table, action, n)
    def сохранить_схему(self):
        with self.connection:
            self.схема.update(self.cursor)

    def add_base_action(self):
        action_id = self.get('action_id')
        with self.connection:
            action = Action.get(self.cursor, action_id) 
            self.набор_акций.вставить(0, action)
            self.схема.update(self.cursor)
        self.draw_tab_contence()
        self.write_protocol(f'Добавление основной акции {action.id} : {action.description}')

    def write_protocol(self, description):
        log.debug(f'write_protocol')
        values = {
            Protocol.user_id : self.user_id,
            Protocol.description : description,
            Protocol.schema_id : self.схема_ID
        }
        self.postgres.execute(Protocol.insert(values))

    def create_new_action(self):
        ACTION_TYPE = self.get('action_type')
        action_type = self.action_types[ACTION_TYPE]
        with self.connection:
            action = Action()
            #action.description = action_type.description()
            action.description = ''
            action.type = action_type.id
            action.схема_ID = self.схема.ID
            #action.pos = 0
            #action.after_sales_pos = 0
            action.create(self.cursor)
            self.набор_акций.вставить(0, action)
            self.схема.update(self.cursor)
        self.draw_tab_contence()

        self.write_protocol(f'Создание акции {action.id} : {action_type.id} : {action.description}')
        
    def copy(self):
        action_id = self.get('action_id')
        номер = int(self.get('номер'))
        with self.connection:
            action = Action.get(self.cursor, action_id)
            new_action = Action()
            new_action.type = action.type
            new_action.info = action.info
            new_action.status = action.status
            new_action.схема_ID = self.схема_ID
            new_action.create(self.cursor)
            if self.calc_tab:
                self.схема.расчетные_акции.вставить(номер, new_action)
            else:
                self.схема.послепродажные_акции.вставить(номер, new_action)
            self.схема.update(self.cursor)

        self.print_table()

    def delete(self):
        номер = int(self.get('номер'))
        with self.connection:
            if self.работа_с_расчетными_акциями:
                self.схема.расчетные_акции.удалить(номер)
            else:
                self.схема.послепродажные_акции.удалить(номер)
            self.схема.update(self.cursor)
        
        self.write_protocol(f'Удаление акции')
        #self.table('table').row(номер)
        self.print_table()

    def ondrop(self):
        что = int(self.get('from'))
        на_место_чего = int(self.get('to'))
        with self.connection:
            if self.calc_tab:
                self.схема.расчетные_акции.поставить_на_место(что, на_место_чего)
            else:
                self.схема.послепродажные_акции.поставить_на_место(что, на_место_чего)
            self.схема.update(self.cursor)
            self.connection.commit()
        self.print_table()

    def change_fixed_price(self):
        action_id = self.get('action_id')
        номер = self.get('номер')
        with self.connection:
            action = Action.get(self.cursor, action_id)
            action.fixed_price = not action.fixed_price
            action.update(self.cursor)
        self.print_row(self.table('table'), action, номер)
    
    def change_supplement(self):
        action_id = self.get('action_id')
        номер = self.get('номер')
        with self.connection:
            action = Action.get(self.cursor, action_id)
            action.supplement = not action.supplement
            action.update(self.cursor)
        self.print_row(self.table('table'), action, номер)

    def print_error_row(self, table, action_id, номер):
        row = table.row(номер)
        row.cell()
        row.cell()
        row.cell().text(f'{action_id}')
        row.cell()
        row.cell(style='color:red').text(f'НЕИЗВЕСТНАЯ АКЦИЯ [{номер}]')
        row.cell()
        кнопки = СтандартныеКнопки(row, params={'action_id':str(action_id), 'номер':номер})
        if self.ASSISTANT:
            кнопки.кнопка('удалить', 'delete', подсказка='Удалить акцию')

    def print_row(self, table, action, номер):
        СОБСТВЕННАЯ_АКЦИЯ = action.схема_ID == self.схема_ID
        action_type = self.action_types[action.type]
        row = table.row(номер)
        if self.ASSISTANT:
            row.ondrag({'from':номер})
            row.ondrop('.ondrop', {'to':номер})
        if action_type is None:
            return
        #-----------------------------------
        if action_type.CLASS == 0:
            cell = row.cell(width=2)
            if action_type.FIXED_PRICE:
                if action.fixed_price:
                    button = cell.icon_button('do_not_disturb', style='color:red', tooltip='Скидка по акции является ОКОНЧАТЕЛЬНОЙ и не подлежит изменению в результате выполнения последующих акций')
                    if СОБСТВЕННАЯ_АКЦИЯ and self.ASSISTANT:
                        button.onclick('.change_fixed_price', {'action_id':str(action.id), 'номер': номер})                    
                else:
                    button = cell.icon_button('do_not_disturb', style='color:lightgray', tooltip='Скидка по данной акции может быть УЛУЧШЕНА или ЗЕМЕНЕНА на другую в результате выполнения последующих акций ')
                    if СОБСТВЕННАЯ_АКЦИЯ and self.ASSISTANT:
                        button.onclick('.change_fixed_price', {'action_id':str(action.id), 'номер': номер})                    
            
            cell = row.cell(width=2)
            if action_type.SUPPLEMENT:
                if action.supplement:
                    button = cell.icon_button('add', style='color:blue', tooltip='Скидка по акции СУММИРУЕТСЯ со скидками предыдущих акций')
                    if СОБСТВЕННАЯ_АКЦИЯ and self.ASSISTANT:
                        button.onclick('.change_supplement', {'action_id':str(action.id), 'номер': номер})                    
                else:
                    button = cell.icon_button('add', style='color:rgb(220,220,210)', tooltip='Акция ЗАМЕЩАЕТ предыдущие акции, если скидка по данной акции выгоднее для покупателя')
                    if СОБСТВЕННАЯ_АКЦИЯ and self.ASSISTANT:
                        button.onclick('.change_supplement', {'action_id':str(action.id), 'номер': номер})                    

        elif action_type.CLASS == 1:
            cell = row.cell(width=2)
            cell = row.cell(width=2)
            row.style('background-color:#EAEDED')

        else:
            cell = row.cell(width=2)
            cell = row.cell(width=2)
        #-----------------------------------

        row.cell().html(f'{action.id}')
        row.cell().href(f'{action.type}', f'action_types/{action.type}.description_page', {'action_id':action.id})
        if СОБСТВЕННАЯ_АКЦИЯ:
            row.cell().href(action.полное_наименование(self.action_types), f'action_types/{action.type}.settings_page' , {'action_id':action.id})
        else:
            row.cell().link(action.полное_наименование(self.action_types)).style('font-weight: bold;').onclick(f'action_types/{action.type}.settings_page' , {'action_id':action.id})
        # ----------------------------------
        comments = []
        if action.start_date is not None:
            if action.start_date.minute == 0 and action.start_date.hour == 0:
                comments.append(f'c {action.start_date.format("YYYY-MM-DD")}')
            else:
                comments.append(f'c {action.start_date.format("YYYY-MM-DD HH:mm")}')
        if action.end_date is not None:
            if action.end_date.minute == 0 and action.end_date.hour == 0:
                comments.append(f'по {action.end_date.format("YYYY-MM-DD")}')
            else:
                comments.append(f'по {action.end_date.format("YYYY-MM-DD HH:mm")}')
        dept_code = action.info.get(Action.ПОДРАЗДЕЛЕНИЕ)
        if dept_code:
            comments.append(f'Подразделение "{self.get_dept_name(dept_code)}"')
        row.cell().text(' '.join(comments))
        # ----------------------------------
        кнопки = СтандартныеКнопки(row, params={'action_id':str(action.id), 'номер':номер})
        if self.ASSISTANT:
            кнопки.кнопка('копировать', 'copy', подсказка='Копировать акцию')
            кнопки.кнопка('удалить', 'delete', подсказка='Удалить акцию')


    # ----------------------------------
    # TABS 
    # ----------------------------------
    @property
    def набор_акций(self):
        if self.работа_с_расчетными_акциями:
            return self.схема.расчетные_акции
        else:
            return self.схема.послепродажные_акции
    @property
    def calc_tab(self):
        return self.tab_id == CALC_TAB

    @property
    def работа_с_расчетными_акциями(self):
        return self.tab_id == CALC_TAB

    @property
    def accept_tab(self):
        return self.tab_id == ACCEPT_TAB
    @property
    def tabs(self):
        return [
            [CALC_TAB, 'Расчетные акции'.upper()],
            [ACCEPT_TAB, 'Послепродажные акции'.upper()],
            [PRODUCT_SETS_TAB, 'Наборы товаров'.upper()],
            [TEST_CHECKS_TAB, 'Контрольные чеки'.upper()]
        ]

    def draw_tab(self):
        tab = self.Tabs('tab').mt(1)
        for item in self.tabs:
            tab.item().text(item[1]).active(self.tab_id == item[0])\
                .onclick('.on_change_tab', {'actions_tab_id':item[0]})

    def on_change_tab(self):
        self.draw_tab()
        self.draw_tab_contence()

    def get_action_types(self):
        types = []
        for action_type in self.action_types.types():
            if action_type.is_available():
                description = action_type.description()
                if self.calc_tab:
                    if action_type.hasCalculator:
                        types.append([str(action_type.id), f'{description}  ({action_type.id})'])
                elif self.accept_tab:
                    if action_type.hasAcceptor:
                        types.append([str(action_type.id), f'{description} ({action_type.id})'])
        return sorted(types, key = lambda t : t[1])

    def draw_tab_contence(self):
        if self.tab_id == PRODUCT_SETS_TAB:
            self.product_sets_tab()
        elif self.tab_id == TEST_CHECKS_TAB:
            self.test_checks_tab()
        elif self.tab_id != ACCEPT_TAB:
            toolbar = self.toolbar('toolbar').mt(1)
            if self.ASSISTANT:
                кнопка = КраснаяКнопкаВыбор(toolbar, 'Создать расчетную акцию')
                for t in self.get_action_types():
                    кнопка.item(t[1]).onclick('.create_new_action', {'action_type':t[0]}) 
                if not self.ОСНОВНАЯ_СХЕМА:
                    кнопка = КраснаяКнопкаВыбор(toolbar.item().ml(1), 'Добавить основную акцию')
                    base_schema = ДисконтнаяСхема.get(self.cursor, 0)
                    for action_id in base_schema.расчетные_акции.список_акций:
                        action = Action.get(self.cursor, action_id)
                        action_name = action.полное_наименование(self.action_types)
                        кнопка.item(action_name).onclick('.add_base_action', {'action_id':str(action_id)}) 
            self.print_table()
        else:
            toolbar = self.toolbar('toolbar').mt(1)
            if self.ASSISTANT:
                кнопка = КраснаяКнопкаВыбор(toolbar, 'Создать послепродажную акцию')
                for t in self.get_action_types():
                    кнопка.item(t[1]).onclick('.create_new_action', {'action_type':t[0]}) 
                if not self.ОСНОВНАЯ_СХЕМА:
                    кнопка = КраснаяКнопкаВыбор(toolbar.item().ml(1), 'Добавить основную акцию')
                    base_schema = ДисконтнаяСхема.get(self.cursor, 0)
                    for action_id in base_schema.послепродажные_акции.список_акций:
                        action = Action.get(self.cursor, action_id)
                        action_name = action.полное_наименование(self.action_types)
                        кнопка.item(action_name).onclick('.add_base_action', {'action_id':str(action_id)}) 
            self.print_table()
    # --------------------------
    # УТВЕРДИТЬ 
    # --------------------------
    def accept(self):
        try:
            msg = DS(self.account_id).accept(self.схема.ID)
            Protocol.create(self.postgres, self.user_id, msg, schema_id=self.схема.ID)
            self.message(msg)
        except Exception as ex:
            log.exception(__file__)
            self.error(ex)

    def __accept(self):
        if str(self.схема_ID) != "0":
            дата_утверждения = ДисконтнаяСхема.дата_утверждения(self.account_id, 0)
            if дата_утверждения is None:
                self.error('Прежде, чем утверждать какую либо дополнительную схему, следует утвердить ОСНОВНУЮ СХЕМУ')
                return 
        now = datetime.datetime.now()
        VERSION = now.strftime('%Y-%m-%d %H:%M:%S')
        папка = SCHEMES_FOLDER(self.account_id)
        os.makedirs(папка, exist_ok=True)
        БД = os.path.join(папка, f'{self.схема.ID}')
        БД_временная = os.path.join(папка, f'{self.схема.ID}.tmp')
        if os.path.exists(БД_временная):
            os.remove(БД_временная)
        try:
            src = DISCOUNT_DB(self.account_id)
            with sqlite3.connect(БД_временная) as conn:
                conn.executescript(f'''
                attach database "{src}" as src;

                create table emission as select * from src.emission;
                create table action_set_item as select * from src.action_set_item;
                create table dept_set as select * from src.dept_set;
                create table dept_set_item as select * from src.dept_set_item;
                create table product_set as select * from src.product_set;
                create table product_set_item as select * from src.product_set_item;
                create table complex_good_set_item as select * from src.complex_good_set_item;
                create table schema as select * from src.schema where src.schema.ID = {self.схема.ID};
                create table actions as select * from src.actions;
                create index if not exists product_set_item_on_product_set on product_set_item(product_set); 
                detach src;
                ''')
            os.rename(БД_временная, БД)
            with open(os.path.join(папка, 'VERSION'), 'w') as f:
                f.write(VERSION)
            msg = f'Утверждение дисконтной схемы'
            Protocol.create(self.postgres, self.user_id, msg, schema_id=self.схема.ID)
            self.message(msg)

        except BaseException as ex:
            log.exception(f'accept')
            self.error(f'{ex}')

    # --------------------------
    def open(self):
        self.title(f'{self.схема.наименование}')
        about = self.Panel('about')

        x = about.item().Text()
        #x.text(f'{self.ОСНОВНАЯ_СХЕМА} {self.схема_ID}')
        x.text('''
        Данный набор акций "вступает в силу" только после 
        УТВЕРЖДЕНИЯ дисконтной схемы.
        В этот момент 
        фиксируются все акции (общий состав, настройки и порядок выполнения) и 
        согласно этому фиксированному списку начинают применяться скидки.
        ''')
        #x = self.text_block()
        x.text('''
        Акции выполняются последовательно, согласно списка. 
        Для изменения позиции акции, следует "перетащить" акцию в нужное место с 
        помощью мышки
        ''')

        if self.BOSS:
            КраснаяКнопка(about,'УТВЕРДИТЬ').onclick('.accept')
        else:
            КраснаяКнопка(about,'УТВЕРДИТЬ').disabled(True)

            #self.toolbar().item().mt(1).mb(1).button('УТВЕРДИТЬ ДИСКОНТУЮ СХЕМУ').css('btn-danger').onclick('.утверждение')
        self.draw_tab()
        self.draw_tab_contence()

