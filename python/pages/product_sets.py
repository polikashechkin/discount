import sqlite3, json, arrow
from domino.core import log
from discount.core import DISCOUNT_DB
from discount.page import DiscountPage as BasePage
from discount.product_sets import ProductSet, ProductSetItem
from domino.page_controls import Кнопка, ПрозрачнаяКнопка, СтандартныеКнопки
 
class ThePage(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
    def actions_of_set(self, set_ID):
        actions = []
        sql = '''
            select distinct action_id from action_set_item where set_id = ?
        '''
        self.cursor.execute(sql, [set_ID])    
        for action_ID, in self.cursor:
            actions.append(str(action_ID))
        if len(actions) == 0:
            return None
        else:
            return actions

    def print_table(self):
        table = self.Table('table').mt(1)
        for p in sorted(ProductSet.findall(self.cursor), key=lambda p : f'{p.CLASS:02}{p.description}', reverse=True):
            if p.CLASS == 2:
                if p.ID in [ProductSet.ПОДАРОЧНЫЕ_КАРТЫ_ID, ProductSet.ДИСКОНТНЫЕ_КАРТЫ_ID, ProductSet.ПОСТОЯННО_ИСКЛЮЧЕННЫЕ_ТОВАРЫ_ID]:
                    row = table.row(p.ID)
                    #row.cell(width=3)
                    #row.cell().text(f'{p.schema_id}')
                    #row.cell()
                    row.href(p.наименование, 'pages/product_set', {'set_id':p.ID})
                    кнопки = СтандартныеКнопки(row)
                    кнопки.кнопка('', '')
    #def delete(self):
    #    set_id = int(self.get('set_id'))
    #    with self.connection:
    #        ProductSet.deleteall(self.cursor, 'ID=?', [set_id])
    #        ProductSetItem.deleteall(self.cursor, 'product_set=?', [set_id])
    #    self.table('table').row(set_id)
    #def create(self):
    #    p = ProductSet()
    #    p.info['description'] = ''
    #    with self.connection:
    #        p.create(self.cursor)
    #        ProductSetItem.deleteall(self.cursor, 'product_set=?', [p.ID])

    #    self.print_table()
    #def создать_реестр_цен(self):
    #    p = ProductSet()
    #    p.TYPE = 1
    #    p.info['description'] = ''
    #    with self.connection:
    #        p.create(self.cursor)
    #        ProductSetItem.deleteall(self.cursor, 'product_set=?', [p.ID])#
    #
    #    self.print_table()
    #def создать_живой_набор(self):
    #    p = ProductSet()
    #    p.TYPE = 2
    #    p.info['description'] = ''
    #    with self.connection:
    #        p.create(self.cursor)
    #        ProductSetItem.deleteall(self.cursor, 'product_set=?', [p.ID])
    #    self.print_table()
    def open(self):
        self.title('Специальные наборы товаров')
        #p = self.toolbar('toolbar').mb(1)
        #Кнопка(p, 'Создать набор').onclick('.create')
        #Кнопка(p, 'Создать живой набор', ml=0.5).onclick('.создать_живой_набор')
        #Кнопка(p, 'Создать тованый набор с ценами', ml=0.5).onclick('.создать_реестр_цен')
        #Кнопка(p, 'Очистить', ml='auto').onclick('.cleaning').tooltip('Удалить все наборы, которын не используются ни в одной акции')
        self.print_table()
