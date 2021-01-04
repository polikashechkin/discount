import sqlite3
from domino.core import log
from domino.page_controls import TabControl, СтандартныеКнопки, ПрозрачнаяКнопка
from discount.core import DISCOUNT_DB
from discount.page import DiscountPage as BasePage
from grants import Grants
from domino.tables.postgres.grant import Grant
from domino.tables.postgres.user import User
from discount.schemas import ДисконтнаяСхема
from settings import GRANT_MODULE_ID

TheTabs = TabControl('grants_tabs', mt=1)
TheTabs.append('base_grants', 'Основное', 'base_grants_tab')
TheTabs.append('by_discount_scheme', 'По дисконтным схемам', 'by_discount_scheme_tab')

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request, controls = [TheTabs])
        #self.grants = Grants(self.account_id, self.user_id)
        self.all_schemas = ДисконтнаяСхема.findall(self.cursor)
        self.schemas_names = {}
        for schema in self.all_schemas:
            self.schemas_names[str(schema.ID)] = schema.наименование
    
    def get_oject_name(self, object_id):
        return self.schemas_names.get(object_id)
    # -------------------------------
    # BASE GRANTS 
    # -------------------------------
    def base_grants_tab(self):
        table = self.Table('table').mt(1)
        for grant_id in [Grants.SYSADMIN, Grants.BOSS, Grants.ASSISTANT, Grants.OPERATOR, Grants.CARD_MANAGER]:
            # -----------------------------
            READONLY = True
            if Grants.SYSADMIN in self.grants:
                READONLY = grant_id != Grants.SYSADMIN
            if READONLY and Grants.BOSS in self.grants:
                READONLY = grant_id == Grants.SYSADMIN
            # -----------------------------
            row = table.row(grant_id)
            #row.cell().text(f'{READONLY} {grant_id}')
            # -----------------------------
            cell = row.cell(width=2)
            icon = 'face'

            if grant_id in self.grants:
                button = cell.icon_button(icon, style='color:green')
            else:
                button = cell.icon_button(icon, style='color:lightgray')
            if not READONLY and grant_id not in [Grants.SYSADMIN, Grants.BOSS]:
                button.onclick('.toggle_own_grant', {'grant_id': grant_id})
            # -----------------------------
            cell = row.cell(width=25)
            if READONLY or grant_id in [Grants.SYSADMIN, Grants.BOSS]:
                cell.text(Grants.name(grant_id))
            else:
                cell.href(Grants.name(grant_id), 'pages/grant', {'grant_id':grant_id})
            # -----------------------------
            query = self.postgres.query(User.name).join(Grant, Grant.user_id == User.id)\
                .filter(Grant.grant_id == grant_id, Grant.module_id == GRANT_MODULE_ID)
            users = []
            for user_name, in query.order_by(User.name):
                users.append(user_name)

            #USERS = 'select "user".name from "user", "grant" where "grant".grant_id = %s and "user".id = "grant".user_id;'
            #self.pg_cursor.execute(USERS, [grant_id])
            #for user_name, in self.pg_cursor:
            #    users.append(user_name)
            row.cell().text(', '.join(users))
            # -----------------------------
            #cell = row.cell(width=2)
            #if not READONLY:
            #    button = cell.icon_button('edit', style='color:gray')
            #    button.onclick('pages/grant', {'grant_id':grant_id})
    
    def toggle_own_grant(self):
        grant_id = int(self.get('grant_id'))
        if grant_id in self.grants:
            self.grants.remove_grant(self.postgres, self.user_id, grant_id)
        else:
            self.grants.add_grant(self.postgres, self.user_id, grant_id)
        self.base_grants_tab()
        self.about()

    # -------------------------------
    # BY DISCOUNT SCHEMA
    # -------------------------------
    def by_discount_scheme_tab(self):
        table = self.Table('table').mt(1)
        for schema in ДисконтнаяСхема.findall(self.cursor):
            READONLY = True
            if Grants.BOSS in self.grants or self.grants.match(Grants.DS_MANAGER, str(schema.ID)):
                READONLY = False
            # -----------------------------------
            row = table.row(schema.ID)
            cell = row.cell(width=2)
            #icon = 'check'
            icon = 'face'
            if self.grants.match(Grants.DS_MANAGER, str(schema.ID)):
                button = cell.icon_button(icon, style='color:green')
            else:
                button = cell.icon_button(icon, style='color:lightgray')
            if not READONLY:
                button.onclick('.toggle_own_ds_grant', {'schema_id': schema.ID})
            # -----------------------------------
            if READONLY:
                row.cell(width=25).text(schema.наименование)
            else:
                row.cell(width=25).href(schema.наименование, 'pages/schema_grants', {'schema_id':schema.ID})
            # -----------------------------------
            USERS = 'select "user".name from "user", "grant" where "grant".grant_id = %s and object_id=%s and "user".id = "grant".user_id;'
            self.pg_cursor.execute(USERS, [Grants.DS_MANAGER, str(schema.ID)])
            users = []
            for user_name, in self.pg_cursor:
                users.append(user_name)
            row.cell().text(', '.join(users))
            cell = row.cell(width=2)
            if not READONLY:
                button = cell.icon_button('edit', style='color:gray')
                button.onclick('pages/schema_grants', {'schema_id':schema.ID})

    def toggle_own_ds_grant(self):
        schema_id = self.get('schema_id')
        if self.grants.match(Grants.DS_MANAGER, schema_id):
            Grants.remove_grants(self.postgres, self.user_id, [Grants.DS_MANAGER], schema_id)
        else:
            Grants.add_grants(self.postgres, self.user_id, [Grants.DS_MANAGER], schema_id)
        self.postgres.commit()
        self._grants = None
        self.by_discount_scheme_tab()
        self.about()

    # -------------------------------
    # OPEN  
    # -------------------------------
    def about(self):
        x = self.text_block('about')
        x.text(f'{self.grants.get_description(self.get_oject_name)}')

    def open(self):
        self.title(f'Штатное расписание')
        self.about()
        TheTabs(self)

