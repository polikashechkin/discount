import flask, sqlite3, json
#from domino.page_controls import print_std_buttons, print_check_button
from domino.page_controls import СтандартныеКнопки
from domino.page_controls import ПрозрачнаяКнопка as КраснаяКнопка
from domino.pages import Title, Button, Table, Rows, Toolbar, TextWithComments
from domino.core import log
from discount.core import DISCOUNT_DB
from discount.series import Series
from discount.page import DiscountPage as BasePage
#from discount.cards import Card
from grants import Grants
from tables.postgres.protocol import Protocol

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.account_id = self.request.account_id()
        self.series_id = self.get('series_id')
        self._series = None

    @property
    def series(self):
        if self._series is None:
            self._series = Series.get(self.cursor, self.series_id)
        return self._series

    def card_type_order(self, card_type):
        if card_type.type == 'C04':
            return ''
        elif card_type.type == 'C01':
            return f'1:{card_type.id:02}'
        elif card_type.type == 'C02':
            return f'2:{card_type.id:02}'
        elif card_type.type == 'C03':
            return f'3:{card_type.id:02}'
        return f'{card_type.type}:{card_type.id:02}'

    def print_table(self):
        series = Series.findall(self.cursor)
        table = self.Table('series').style('margin-top:1em;')

        #for s in sorted(series, key = lambda s : f'{s.type}:{s.id:02}', reverse=True) :
        last_printed_type = None
        for s in sorted(series, key = self.card_type_order) :
            if last_printed_type and last_printed_type != s.type:
                self.print_delimiter(table, s)
            last_printed_type = s.type
            self.print_row(table, s)

        self.close()

    def print_delimiter(self, table, card_type):
        row = table.row()
        row.style('background-color:lightgray')
        row.style('background-color:gray')
        row.cell()
        row.cell()
        name = ''
        if card_type.type == 'C01':
            name = f'Подарочные купоны'
        elif card_type.type == 'C02':
            name = 'Дисконтные карты'
        elif card_type.type == 'C03':
            name = 'Подарочные карты'
        row.cell(style='font-size:small;color:white').text(name)
        row.cell()
        row.cell()
        row.cell()

    def print_row(self, table, series):
        row = table.row(series.id)
        #-----------------------------------
        cell = row.cell(width=2)
        if series.status >= 0:
            button = cell.icon_button('fingerprint', style='color:green')
        else:
            button = cell.icon_button('fingerprint', style='color:lightgray')
        if (Grants.BOSS, Grants.CARD_MANAGER) in self.grants:
            button.onclick('.toggle_status', {'series_id':series.id})
        #-----------------------------------
        if series.id == 0:
            row.cell()
        else:
            row.cell(width=2).text(series.id)
        #-----------------------------------
        row.href(f'{series.полное_наименование}', f'card_types/{series.type}.settings_page', {'series_id': series.id})
        #-----------------------------------
        cell = row.cell()
        comments = []
        exp_days = series.exp_days
        if series.points:
            comments.append(f'начальное количество баллов {series.points}')
        if series.cash:
            comments.append(f'номинал {series.cash}')
        if series.discount:
            comments.append(f'скодка {series.discount}%')
        if exp_days is not None:
            comments.append(f'cрок действия {exp_days} дней')
        cell.text(', '.join(comments))
        #-----------------------------------
        cell = row.cell()
        cur = self.postgres.execute('select 1 from discount_card where "type"=:card_type limit 1', {'card_type':series.id})
        #self.pg_cursor.execute('select 1 from discount_card where TYPE=%s limit 1', [series.id])
        #count = self.pg_cursor.fetchone()
        count = cur.fetchone()
        if count:
            cell.href(f'Карты', 'pages/cards.open', {'series_id': series.id})
        #---------------------------------
        cell = row.cell(width=2)
        if series.status < 0 and series.id != 0 and count is None:
            button = cell.icon_button('close', style='color:red')
            button.onclick('.delete',{'series_id':series.id})
            #button.tooltip('Удалить тип карты')
        #кнопки = СтандартныеКнопки(row)
        #if series.status < 0 and series.id != 0 and count is None:
        #    кнопки.удалить('delete', {'series_id':series.id}, подсказка = 'Удалить тип карты')

    def toggle_status(self):
        with self.connection:
            if self.series.status == 0:
                self.series.status = -1
            else:
                self.series.status = 0
            self.series.update(self.cursor)
        self.print_row(self.table('series'), self.series)

    def delete(self):
        with self.connection:
            self.cursor.execute('delete from emission where rowid=?', [self.series_id])
        self.table('series').row(self.series_id)
        msg = f'Удаление типа карты {self.series_id}'
        Protocol.create(self.postgres, self.user_id, msg)
        self.message(msg)

    def create(self):
        CARD_TYPE_ID = self.get('card_type_id')
        card_types = self.application['card_types']
        card_type = card_types[CARD_TYPE_ID]
        series = Series()
        series.type = CARD_TYPE_ID
        series.status = -1
        series.prefix = ''

        with self.connection:
            series.create(self.cursor)
            card_type.on_create(series)
            series.update(self.cursor)

        msg = f'Создание типа карты {series.id} {card_type.description()}'
        Protocol.create(self.postgres, self.user_id, msg)
        self.message(msg)
        self.print_table()

    def open(self):
        #card_types = self.application['card_types']
        Title(self, 'Типы карт')
        about = self.text_block('about')
        about.text('''
            Тип "Персональная карта" изначально 
            создается при установке модуля и не может быть удален. 
            Это единственный тип, который подразумевает пeрсонализацию (связанные
            с картой данного типа ФИО, ТЕЛЕФОН, ДЕНЬ РОЖДЕНИЯ и пр.)
            Дополнительно, можно создать неограниченное число типов вида "Купон",
            "Дисконтная карта", "Подарочная карта". В чеке может быть предъявлена только
            одна карта типа "Персональная карта" и неограниченное количество карт других
            типов.
            ''')
        if (Grants.BOSS, Grants.CARD_MANAGER) in self.grants:
            panel = Toolbar(self, 'create_box').mt(1)
            Button(panel,'Создать купон').onclick('.create', {'card_type_id':'C01'})
            Button(panel,'Создать дисконтную карту', ml=0.5).onclick('.create', {'card_type_id':'C02'})
            Button(panel,'Создать подарочную карту', ml=0.5).onclick('.create', {'card_type_id':'C03'})

        self.print_table()
