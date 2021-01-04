from domino.core import log
from discount.page import DiscountPage as BasePage
from tables.postgres.protocol import Protocol
from domino.tables.postgres.user import User
from dicts.schema import Schema

class TheToolbar:
    def __init__(self, page):
        self.id = 'toolbar'
        toolbar = page.toolbar(self.id)
        select = toolbar.item().select(name='user_id', label='Пользователь')\
            .onchange('.print_table', forms=[toolbar])
        select.option('','')

        for user in page.postgres.query(User).distinct()\
            .join(Protocol, Protocol.user_id == User.id)\
            .order_by(User.name):
            select.option(user.id, user.name)

        select = toolbar.item().ml(1).select(name='schema_id', label='Дисконтная схема')\
            .onchange('.print_table', forms=[toolbar])
        select.option('','')
        for key, value in page.schema_dict.options():
            select.option(key, value)

class TheTable:
    def __init__(self, page):
        self.id = 'table'
        query = page.postgres.query(Protocol, User)\
            .filter(Protocol.module_id=='discount')\
            .outerjoin(User, Protocol.user_id == User.id)\
            .order_by(Protocol.ctime.desc())
        
        user_id = page.get('user_id')
        if user_id:
            query = query.filter(Protocol.user_id == user_id)

        schema_id = page.get('schema_id')
        if schema_id:
            query = query.filter(Protocol.schema_id == schema_id)

        query = query.limit(200)

        table = page.Table(self.id).mt(1)
        table.column('Пользователь')
        table.column('Дисконтная схема')
        table.column('Операция')
        table.column('Врeмя')

        for protocol, user in query:
            row = table.row(protocol.id)
            row.cell().text(user.name)
            cell = row.cell()
            if protocol.schema_id is not None:
                name = page.schema_dict.get_name(protocol.schema_id)
                cell.text(f'{name}')
            else:
                cell.text(f'ОСНОВНАЯ СХЕМА')

            row.cell().text(f'{protocol.description}')
            row.cell().text(protocol.ctime)

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.schema_dict = Schema(self.account_id)

    def print_table(self):
        TheTable(self)

    def __call__(self):
        self.title('Протокол')
        TheToolbar(self)
        TheTable(self)

