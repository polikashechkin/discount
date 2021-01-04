import sqlite3, json, datetime, re
from domino.core import log
from discount.actions import Action, ActionSetItem
from discount.core import DISCOUNT_DB
from domino.page_controls import print_std_buttons, КраснаяКнопка, ПрозрачнаяКнопка, ПлоскаяТаблица, СтандартныеКнопки
from domino.page_controls import Кнопка, КнопкаВыбор
from discount.product_sets import ProductSet, ProductSetItem
from discount.page import DiscountPage as BasePage
from domino.page_controls import FormControl
from domino.page_controls import TabControl
from grants import Grants
from tables.Good import Good, QueryColumn

#MAX_ROWS = 200
class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.product_set_id = int(self.attribute('product_set_id'))
        self.column_id = self.attribute('column_id')
        self.column = Good.QueryColumn(self.column_id)
        self.product_set = ProductSet.get(self.cursor, self.product_set_id)
        self.query = self.product_set.query
        self.names = self.column.get_names(self.pg_cursor)

    def save(self):
        with self.connection:
            self.product_set.update(self.cursor)

    def value_exists(self, code):
        for value in self.values:
            if value == code:
                return True
        return False
    
    def get_values(self):
        values = self.query.get(self.column.ID)
        v = []
        if values is not None:
            if isinstance(values, list):
                v = values
            elif values:
                v = [values]
        log.debug(f'get_values() : {values} : {v}')
        return v
    def set_values(self, values):
        if len(values) > 0:
            self.query[self.column.ID] = values
        else:
            if self.column.ID in self.query:
                del self.query[self.column.ID]
        self.save()

    def on_change(self):
        code = self.get('code')
        values = self.get_values()
        if code in values:
            values.remove(code)
        else:
            values.append(code)
        self.set_values(values)
        
        row = self.Row('table', code)
        self.print_row(row, code, self.names.get(code), values)

    def print_row(self, row, code, name, values):
        cell = row.cell(width=2)
        if code in values:
            button = cell.icon_button('check', style='color:green')
        else:
            button = cell.icon_button('check', style='color:lightgray')
        button.onclick('.on_change', {'code' : code})
        row.cell().text(name)

    def print_table(self):
        filter = self.get('filter')
        if filter:
            filter = filter.upper()
        table = ПлоскаяТаблица(self, 'table').mt(1)
        values = self.get_values()
        log.debug(f'values = {values}')
        for code, name in self.names.items():
            if filter:
                if name.upper().find(filter) == -1:
                    continue
            row = table.row(code)
            self.print_row(row, code, name, values)

    def __call__(self):
        self.title(self.column.name)
        toolbar = self.toolbar('toolbar')
        toolbar.item().input(label='Наименование', name='filter').onkeypress(13, '.print_table', forms=[toolbar])
        self.print_table()

