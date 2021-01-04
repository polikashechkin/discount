import sqlite3
from domino.core import log
from domino.page import Page, Filter
from domino.page_controls import TabControl, СтандартныеКнопки, ПрозрачнаяКнопка
from discount.core import DISCOUNT_DB, MODULE_ID
from grants import Grants
from discount.page import DiscountPage
from discount.schemas import ДисконтнаяСхема
from domino.tables.postgres.grant import Grant
from domino.tables.postgres.user import User



TheTabs = TabControl('grant_tabs', mt=1)
TheTabs.append('granted_users_tab', 'Назначенные', 'granted_users_tab')
TheTabs.append('reg_users_tab', 'Зарегистрированные', 'reg_users_tab')
TheTabs.append('all_users_tab', 'Общий список пользователей', 'all_users_tab')

class GrantPage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request, controls = [TheTabs])
        self.grant_id = int(self.attribute('grant_id'))
        self.schema_id = self.attribute('schema_id')
        if not self.schema_id:
            self.schema_id = ''

    # -----------------------------
    # REG USERS TAB
    # ----------------------------- 
    def reg_users_tab(self):
        query = self.toolbar('query').mt(1)
        #toolbar = self.toolbar('toolbar').mt(1)
        #query.item().input(label='Имя пользователя', name='filter').onkeypress(13, '.all_users_table', forms=[query])
        self.reg_users_table()
    
    def reg_users_table(self):
        table = self.Table('table').mt(1)

        #table.column()
        #table.column().text('Имя')
        #table.column().text('Полное наименование')
        #table.column()
        #granted_users = set()
        #GRANTED = 'select user_id from "grant" where module_id=%s and grant_id=%s and object_id=%s'
        #self.pg_cursor.execute(GRANTED, [MODULE_ID, self.grant_id, self.schema_id])
        #for user_id, in self.pg_cursor:
        #    granted_users.add(user_id)

        #FILTER = self.get('filter')
        #if not FILTER:
        #    return
        #if FILTER:
        #SQL = '''
        #select id, name, full_name from "user" 
        #where id in (select distinct user_id from "grant") 
        #order by name 
        #limit 200
        #'''
        #    PARAMS = [f'%{FILTER}%', f'%{FILTER}%']
        #else:
        #    SQL = 'select id, name, full_name from "user" order by name limit 200'
        #PARAMS = []

        for user in self.postgres.query(User).join(Grant, Grant.user_id == User.id)\
            .filter(Grant.module_id == MODULE_ID, Grant.grant_id == self.grant_id, Grant.object_id == self.schema_id):
            row = table.row(user.id)
            self.print_row(row, user, True)
    # -----------------------------
    # ALL USERS TAB
    # ----------------------------- 
    def all_users_tab(self):
        query = self.toolbar('query').mt(1)
        #toolbar = self.toolbar('toolbar').mt(1)
        query.item().input(label='Имя пользователя', name='filter').onkeypress(13, '.all_users_table', forms=[query])
        self.all_users_table()
    
    def all_users_table(self):
        table = self.Table('table').mt(1)

        #table.column()
        #table.column().text('Имя')
        #table.column().text('Полное наименование')
        #table.column()
        granted_users = set()
        for user_id in self.postgres.query(User.id).join(Grant, Grant.user_id == User.id)\
                .filter(Grant.module_id == Grants.module_id, Grant.grant_id == self.grant_id, Grant.object_id == self.schema_id):
            granted_users.add(user_id)
            
        #GRANTED = 'select user_id from "grant" where module_id=%s and grant_id=%s and object_id=%s'
        #self.pg_cursor.execute(GRANTED, [MODULE_ID, self.grant_id, self.schema_id])
        #for user_id, in self.pg_cursor:
        #    granted_users.add(user_id)

        query = self.postgres.query(User)
        FILTER = self.get('filter')
        if FILTER:
            query = query.filter(User.name.ilike(f'%{FILTER}%') )
        #if not FILTER:
        #    return
        #if FILTER:
        #    SQL = 'select id, name, full_name from "user" where (name ilike %s) or (full_name ilike %s) order by name limit 200'
        #    PARAMS = [f'%{FILTER}%', f'%{FILTER}%']
        #else:
        #    SQL = 'select id, name, full_name from "user" order by name limit 200'
        #    PARAMS = []
        #self.pg_cursor.execute(SQL, PARAMS)
        #for user_id, user_name, user_full_name in self.pg_cursor:
        for user in query.order_by(User.name).limit(200):
            row = table.row(user.id)
            self.print_row(row, user, user.id in granted_users)

    def print_row(self, row, user, user_granted):
        cell = row.cell(width=2)
        if user_granted:
            button = cell.icon_button('check', style='color:green')
        else:
            button = cell.icon_button('check', style='color:lightgray')
        button.onclick('.toggle_user_grant', {'user_id':user.id})
        row.text(user.name)
        row.text(user.full_name)

    def toggle_user_grant(self):
        user_id = self.get('user_id')
        user = self.postgres.query(User).get(user_id)
        row = self.Row('table', user.id)
        #self.pg_cursor.execute('select name, full_name from "user" where id=%s', [user_id])
        #user_name, user_full_name = self.pg_cursor.fetchone()
        grant = self.postgres.query(Grant)\
            .filter(Grant.module_id == Grants.module_id, Grant.user_id == user.id, Grant.grant_id == self.grant_id, Grant.object_id == self.schema_id)\
            .first() 
        if grant:
            self.postgres.query(Grant)\
                .filter(Grant.module_id == Grants.module_id, Grant.user_id == user.id, Grant.grant_id == self.grant_id, Grant.object_id == self.schema_id)\
                .delete()
            self.print_row(row, user, False)
        else:
            grant = Grant(module_id = Grants.module_id, user_id = user_id, grant_id = self.grant_id, object_id = self.schema_id)
            self.postgres.add(grant)
            self.print_row(row, user, True)
    
    # -----------------------------
    # GRANTED USERS TAB  [POSTGRES], Grants 
    # -----------------------------
    def granted_users_tab(self):
        #log.debug(f'granted_users_tab')
        self.toolbar('query').mt(1)
        self.toolbar('toolbar').mt(1)
        table = self.Table('table')
        #table.column().text('Пользователь')
        #table.column().text('Права и обязанности')
        #table.column()

        #USERS = '''
        #select "user".id, "user".name, "user".full_name 
        #from "user", "grant" 
        #where "grant".user_id = "user".id
        #and "grant".module_id = %s
        #and "grant".grant_id = %s
        #and "grant".object_id = %s
        #order by "user".name
        #'''
        #PARAMS = [MODULE_ID, self.grant_id, self.schema_id]

        for user in self.postgres.query(User).join(Grant, User.id == Grant.user_id)\
                .filter(Grant.grant_id == self.grant_id, Grant.object_id == self.schema_id):
            row = table.row(user.id)
            cell = row.cell(width=2)
            button = cell.icon_button('check', style='color:green')
            if self.grant_id not in [Grants.SYSADMIN, Grants.BOSS] or user.id != self.user_id:
                button.onclick('.remove_grant', {'user_id':user.id})
            row.cell().text(user.name)
            row.cell().text(user.full_name)

    def remove_grant(self):
        user_id = self.get('user_id')
        Grants.remove_grants(self.postgres, user_id, [self.grant_id], self.schema_id)
        self.Row('table', user_id)
    
    # -----------------------------
    # OPEN
    # ----------------------------- 
    def open(self): 
        grant_name = Grants.name(self.grant_id)
        if self.schema_id:
            schema = ДисконтнаяСхема.get(self.cursor, int(self.schema_id))
            self.title(f'{schema.наименование}, {grant_name}')
        else:
            self.title(f'{grant_name}')
            schema = None
        
        TheTabs(self)

