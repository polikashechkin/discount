from domino.core import log
from . import Page as BasePage
from . import Title, Toolbar, Input, InputText, Button, Table, Row, IconButton, Select, CheckIconButton
from domino.tables.postgres.user import User
from domino.tables.postgres.grant import Grant
#from components.module import Module
from sqlalchemy import and_, or_
 
class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.module_id = self.attribute('module_id')
        #if self.module_id:
        #    self.module = Module(self.module_id)
        #else:
        #    self.module = None
        self.grant_id = self.attribute('grant_id')
        if self.grant_id:
            self.grant_id = int(self.grant_id)
        self.postgres = None

    def toggle_sysadmin(self):
        user_id = self.get('user_id')
        user = self.postgres.query(User).get(user_id)
        grant = self.postgres.query(Grant)\
            .filter(Grant.user_id == user.id, Grant.module_id == self.module_id, Grant.grant_id == self.grant_id)\
            .filter(Grant.NoObject)\
            .first()
        if grant:
            self.postgres.query(Grant)\
                .filter(Grant.id == grant.id, Grant.module_id == self.module_id)\
                .filter(Grant.NoObject)\
                .delete()
            granted = False
        else:
            grant = Grant(user_id = user.id, module_id = self.module_id, grant_id = self.grant_id, object_id = Grant.NOOBJECT)
            self.postgres.add(grant)
            granted = True
        row = Row(self, 'table', user.id)
        self.print_row(row, user, granted)

    def print_row(self, row, user, granted):
        cell = row.cell(width=2)
        CheckIconButton(cell, granted).onclick('.toggle_sysadmin', {'user_id':user.id})

        row.cell().text(user.name)
        row.cell().text(user.full_name)

    def print_table(self):
        table = Table(self, 'table').mt(1)
        
        granted_users = set()
        for user_id, in self.postgres.query(Grant.user_id)\
            .filter(Grant.module_id == self.module_id, Grant.grant_id == self.grant_id)\
            .filter(Grant.NoObject)\
            .filter():
            granted_users.add(user_id)

        #log.debug(granted_users)

        query = self.postgres.query(User)
        mode = self.get('mode')
        #if not mode:
        #    query = query.join(Grant, Grant.user_id == User.id)\
        #        .filter(Grant.grant_id == self.grant_id, Grant.module_id == self.module.grant_module_id)
        #else:
        #    query = query.outerjoin(Grant, Grant.user_id == User.id)\
        #        .filter(Grant.grant_id == self.grant_id, Grant.module_id == self.module.grant_module_id)

        #------------------------------------
        name = self.get('name')
        if name:
            query = query.filter(User.name.ilike(f'%{name}%'))
        #------------------------------------
        for user in query.order_by(User.name).limit(200):
            row = table.row(user.id)
            if not mode and user.id not in granted_users:
                continue
            if mode and user.id in granted_users:
                continue
            self.print_row(row, user, user.id in granted_users)

    def __call__(self):
        Title(self, f'{Grant.grant_name(self.grant_id)}')

        toolbar = Toolbar(self, 'toolbar')
        Input(toolbar.item(), label='Наименование', name='name')\
            .onkeypress(13, '.print_table', forms=[toolbar])
        select = Select(toolbar.item(ml='auto'), name='mode')
        select.option('', 'НАЗНАЧЕННЫЕ')
        select.option('1', 'НЕ НАЗНАЧЕННЫЕ')
        select.onchange('.print_table', forms=[toolbar])
        self.print_table()

