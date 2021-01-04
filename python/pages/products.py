
from domino.core import log
from discount.core import Finder
from domino.page import Page, Filter

class ThePage(Page):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.account_id = self.request.account_id()
        self.filter = self.attribute('filter')
        self.group = self.attribute('group')

    def product_groups(self):
        groups = []
        with self.application.account_database_connect(self.account_id) as conn:
            cur = conn.cursor()
            cur.execute('''
            select rawtohex(C.id), C.name, G.name
            from db1_classif C, db1_classif G
            where 
                C.name is not NULL and C.type=14745602 and C.pid = G.id
            order by G.name
            ''')
            for code, name, gname in cur:
                groups.append([code, f'{gname} :: {name}'])
        return groups

    def print_products(self):
        f = Filter(self.filter)
        table = self.table('products', hole_update=True)
        table.column('Код')
        table.column('Тип')
        table.column('Наименование')
        with self.application.account_database_connect(self.account_id) as conn:
            cur = conn.cursor()
            cur.execute('''
                    select TYPE, code, name from db1_product where local_group=hextoraw(:0)
                    ''', [self.group])
            count = 0
            for TYPE, code, name in cur:
                row = table.row(code)
                if f.match(code, name):
                    count += 1
                    row.text(code)
                    if TYPE == 55508993:
                        row.text('ПК') 
                    elif TYPE == 43122692:
                        row.text('ПС')
                    elif TYPE == 40566787:
                        row.text('ДК')
                    else:
                        row.text('') 
                    row.text(name)
                    if count > 400:
                        break

    def print_finder(self):
        finder = self.toolbar('finder').mt(1)
        groups = self.product_groups()
        if self.group is None:
            self.group = groups[0][0]
        finder.item().mr(2).select(value = self.group, name='group').small()\
                .options(groups)\
                .onchange('.find', forms=[finder])
        g = finder.item().css('ml-auto').input_group().small().width(20)
        g.input(value = self.filter, name='filter', placeholder='<Код или наименование товара>')
        g.button('Поиск').onclick('.find', forms=[finder])

    def find(self):
        self.print_products()

    def open(self):
        self.title(f'Справочник товаров')
        self.print_finder()
        self.print_products()

