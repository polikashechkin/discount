import sqlite3
from . import log
from domino.page import Page
from discount.core import MODULE_ID
from discount.page import DiscountPage
from grants import Grants
from domino.tables.postgres.grant import Grant
from domino.tables.postgres.user import User
from discount.schemas import ДисконтнаяСхема

class SchemaGrantsPage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.schema_id = self.attribute('schema_id')
        self.schema = ДисконтнаяСхема.get(self.cursor, self.schema_id)        
        self.all_schemas = ДисконтнаяСхема.findall(self.cursor)
        self.schemas_names = {}
        for schema in self.all_schemas:
            self.schemas_names[str(schema.ID)] = schema.наименование
        self._grants = None

    @property
    def grants(self):
        if self._grants is None:
            self._grants = Grants(self.account_id, self.user_id)
        return self._grants
    
    def get_oject_name(self, object_id):
        return self.schemas_names.get(object_id)
    
    # -------------------------------
    # BASE GRANTS 
    # -------------------------------
    def base_grants_tab(self):
        table = self.Table('table').mt(1)
        for grant_id in [Grants.DS_MANAGER, Grants.DS_ASSISTANT, Grants.DS_WATCHING]:
            row = table.row(grant_id)
            cell = row.cell(width=2)
            if self.grants.match(grant_id, self.schema_id):
                button = cell.icon_button('check', style='color:green')
            else:
                button = cell.icon_button('check', style='color:lightgray')
            #if grant_id not in [Grant.BOSS, Grant.SYSADMIN]:
            button.onclick('.toggle_own_grant', {'grant_id': grant_id})
            row.cell(width=25).href(Grants.name(grant_id), 'pages/grant', {'grant_id':grant_id, 'schema_id':self.schema_id})

            users = []
            query = self.postgres.query(User.name).join(Grant, Grant.user_id == User.id)\
                .filter(Grant.grant_id == grant_id, Grant.object_id == self.schema_id)
            for user_name, in query:
                users.append(user_name)
            row.cell().text(', '.join(users))
            #cell = row.cell(width=2)
            #button = cell.icon_button('edit', style='color:gray')
            #button.onclick('pages/grant', {'grant_id':grant_id})
    
    def toggle_own_grant(self):
        grant_id = int(self.get('grant_id'))
        if self.grants.match(grant_id, self.schema_id):
            Grants.remove_grants(self.postgres, self.user_id, [grant_id], self.schema_id)
        else:
            Grants.add_grants(self.postgres, self.user_id, [grant_id], self.schema_id)
        self.postgres.commit()
        self._grants = None
        self.base_grants_tab()
        self.about()

    # -------------------------------
    # OPEN
    # -------------------------------
    def about(self):
        x = self.text_block('about')
        x.text(f'{self.grants.get_description(self.get_oject_name)}')

    def open(self):
        self.title(f'Штатное расписание "{self.schema.наименование}"')
        self.about()
        self.base_grants_tab()

