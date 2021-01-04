import os, sqlite3, json, datetime, arrow, time
from domino.core import log
from discount.core import DISCOUNT_DB, SCHEMES_FOLDER
from domino.page import Page as BasePage
from domino.page_controls import СтандартныеКнопки
from discount.schemas import ДисконтнаяСхема

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.account_id = self.request.account_id()

    def sheme_row(self, table, id, path):
        row = table.row(id)
        row.text(id)
        row.text(path)
        row.text(round(os.path.getsize(path) / (1024 * 1024), 3))
        row.text(ДисконтнаяСхема.дата_утверждения(self.account_id, id))
        
        try:
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            схема = ДисконтнаяСхема.get(cur, id)
            row.text(схема.наименование)
            conn.close()
        except BaseException as ex:
            row.text(f'{ex}')
        кнопки = СтандартныеКнопки(row)
        кнопки.кнопка('удалить', 'delete', {'scheme_id':id}).tooltip('Удалить')

    def goods_row(self, table, path):
        if os.path.exists(path):
            row = table.row('goods')
            row.text('goods')
            row.text(path)
            row.text(round(os.path.getsize(path) / (1024 * 1024), 3))
            row.text(arrow.get(os.path.getmtime(path)))
            row.text('Справочник товаров'.upper())

    def shemes_table(self):
        table = self.Table('shemes').mt(1)
        table.column('ID')
        table.column('Расположение')
        table.column('Размер (Мб)')
        table.column('Дата изменения')
        table.column('Описание')
        table.column('') 
        folder = SCHEMES_FOLDER(self.account_id)
        self.goods_row(table, os.path.join(folder, 'goods.json'))

        if os.path.exists(folder):
            for name in sorted(os.listdir(folder), reverse=False):
                if name.isdigit():
                    path = os.path.join(folder, name)
                    self.sheme_row(table, name, path)


    def новая_версия(self):
        now = datetime.datetime.now()
        VERSION = now.strftime('%Y-%m-%d %H:%M:%S')
        папка = SCHEMES_FOLDER(self.account_id)
        os.makedirs(папка, exist_ok=True)
        with open(os.path.join(папка, 'VERSION'), 'w') as f:
            f.write(VERSION)

    def delete(self):
        SCHEME_ID = self.get('scheme_id')
        path = os.path.join(SCHEMES_FOLDER(self.account_id), SCHEME_ID)
        os.remove(path)
        self.новая_версия()

        self.about()
        self.shemes_table()
        self.message(f'Удалена схема {SCHEME_ID}')
    
    def about(self):
        folder = SCHEMES_FOLDER(self.account_id)
        p = self.text_block('version')
        VERSION_FILE = os.path.join(folder, 'VERSION' )
        if os.path.isfile(VERSION_FILE):
            with open(VERSION_FILE) as f:
                VERSION = f.read()
            p.text(f'Версия набора "{VERSION}"')
        else:
            p.text(f'Версия набора НЕ ОПРЕДЕЛЕНА')

    def open(self):
        self.title(f'Утвержденные дисконтные схемы')
        p = self.text_block('about')
        p.text('''

        ''')
        self.about()
        self.shemes_table()
