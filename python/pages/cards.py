import flask, sqlite3, json, datetime, re
from sqlalchemy import or_, and_
from domino.page import Page, Filter
from domino.page_controls import print_std_buttons
from domino.core import log
from discount.core import CARDS, DISCOUNT_DB, Engine
from discount.series import Series
#from discount.cards import Card
from domino.tables.postgres.discount_card import DiscountCard  as Card
from domino.tables.postgres.dept import Dept
from discount.page import DiscountPage
from domino.page_controls import Кнопка, ПрозрачнаяКнопка, СтандартныеКнопки, ПрозрачнаяКнопкаВыбор
from grants import Grants
from . import Title, Toolbar, Input, Button
from . import Page as BasePage

MAX_COUNT = 200

class ThePage(DiscountPage):
#class ThePage(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.series_id = self.attribute('series_id')
        self._series = None
    @property
    def series(self):
        if self._series is None:
            self._series = Series.get(self.cursor, self.series_id)
        return self._series
    @property
    def тип_карты(self):
        if self._series is None:
            self._series = Series.get(self.cursor, self.series_id)
        return self._series
    #def наименование_подразделения(self, код):
    #    #cur = self.db_cursor.connection.cursor()
    #    self.pg_cursor.execute('select name from dept where "id"=%s', [код])
    #    r = self.pg_cursor.fetchone()
    #    if r is None:
    #        return None
    #    name, = r
    #    return name
    @property
    def CLASS(self):
        return self.card_types[self.series.type]
    def вывести_список_параметров_карты(self, row, card):
        параметры = []
        остаток = card.входящий_остаток_денежных_средств
        if остаток is not None and остаток != 0.0:
            параметры.append(f'остаток {остаток}')

        сумма_покупок = card.статистика.входящая_сумма_покупок
        if сумма_покупок is not None and сумма_покупок != 0.0:
            параметры.append(f'сумма покупок {сумма_покупок}')

        количество_покупок = card.статистика.входящее_количество_покупок
        if количество_покупок is not None and количество_покупок != 0.0:
            параметры.append(f'количество покупок {количество_покупок}')

        параметры.append(f'{card.ФИО.upper()}')

        row.cell().html(', '.join(параметры))
    def удалить(self):
        card_ID = self.get('card_ID')
        with self.db_connection, self.pg_connection:
            Card.delete(self.engine, 'ID=%s', [card_ID])

        self.Row('cards', card_ID)
    #def delete_test_cards(self):
    #    with self.db_connection, self.pg_connection:
    #        Card.deleteall(self.engine, 'IS_TEST=TRUE and TYPE=%s', [self.series.id])
    #    self.open()
    def печать_срока_действия(self, row, card):
        if card.exp_date:
            if card.exp_date < datetime.date.today():
                row.cell().html(f'<span style="white-space:nowrap;"><span style="color:red">{card.exp_date} </span></span>')
            else:
                row.cell().html(f'<span style="white-space:nowrap">{card.exp_date}</span>')
        else:
            row.cell()


        #cell = row.cell()
        #if card.marknum and card.marknum.strip():
        #    cell.href(card.marknum, 'pages/card', {'card_id':card.ID})
        #else:
        #    cell.href(card.ID, 'pages/card', {'card_id':card.ID})
        #row.cell(style='white-space:nowrap').text(card.ID)
    def печать_подразделения(self, row, card, dept):
        cell = row.cell()
        if dept:
            cell.text(dept.name)
        else:
            cell.text(card.dept_code)

        #if card.dept_code:
        #    наименование = self.наименование_подразделения(card.dept_code)
        #    if наименование is not None:
        #        cell.text(f'{наименование}')
        #    else:
        #        cell.text(f'{card.dept_code}')
    def печать_закрытия(self, row, card):
        параметры = []
        if card.deactivation_date:
            параметры.append(f'<span style="white-space:nowrap">с {card.deactivation_date}</span>')

        #подразделение_ID = card.закрытие_подразделение_ID
        #if подразделение_ID is not None:
        #    наименование = self.наименование_подразделения(подразделение_ID)
        #    if наименование is not None:
        #        параметры.append(f'{наименование}')
        #    else:
        #        параметры.append(f'?{подразделение_ID}')

        row.cell().html( ', '.join(параметры))
    def печать_статистики_покупок(self, row, card):
        checks = row.cell(align='right')
        total = row.cell(align='right')
        if card.state != Card.State.CARD_REF:
            if card.checks:
                checks.text(card.checks)
            if card.total:
                total.text(card.total)
            #s = []
        #сумма_покупок = card.статистика.общая_сумма_покупок
        #if сумма_покупок is not None and сумма_покупок != 0.0:
        #    s.append(f'{сумма_покупок}')
        # количество покупок
        #количество_покупок = card.статистика.общее_количество_покупок
        #if количество_покупок is not None and количество_покупок != 0.0:
        #    s.append(f'{количество_покупок}')
        #cell.text('/'.join(s))
    def печать_процента_скидки(self, row, card):
        if card.discount and card.discount != 0 and card.state != Card.State.CARD_REF:
            row.cell(align='right').text(f'{card.discount}%')
        else:
            row.cell()
    def печать_накопленных_баллов(self, row, card):
        cell = row.cell(align='right')
        if card.points and card.state != Card.State.CARD_REF:
            cell.text(f'{card.points}')
    def печать_остаток_денежных_средств(self, row, card):
        cell = row.cell(align='right')
        остаток = card.cash
        if остаток is not None and остаток != 0.0:
            cell.text(остаток)
    
    def print_row(self, row, card, dept):
        #-------------------------------------
        cell = row.cell(width=2, style='white-space:nowrap')
        font_size = '-font-size:0.8rem'
        #font_size = 'font-size:small'
        if card.state:
            if card.state == Card.State.CREATED:
                pass
            elif card.state == Card.State.ACTIVE:
                cell.glif('circle', style=f"color:green; {font_size}")
                comments = ['АКТИВНАЯ КАРТА']
                comments.append(f'Дата активации {card.activation_date}')
                if dept:
                    comments.append(f'Подразделение {dept.name}')
                cell.tooltip(', '.join(comments))
                
            elif card.state == Card.State.DISABLED:
                cell.glif('circle', style=f"color:red; {font_size}")
            elif card.state == Card.State.CARD_REF:
                cell.glif('reply', style=f"color:gray; {font_size}")
            else:
                cell.glif('circle', style=f"color:black; {font_size}")

        #cell = row.cell(width=1)
        if card.is_test:
            cell.glif('circle', style=f"color:orange; {font_size}")
        #-------------------------------------
        cell = row.cell(wrap=False)
        if not card.marknum or card.marknum == card.ID:
            cell.href(card.ID, 'pages/card', {'card_id':card.ID})
        else:
            cell.href(f'{card.ID} / {card.marknum}', 'pages/card', {'card_id':card.ID})
        #-------------------------------------
        if self.тип_карты.это_персональная_карта:
            cell = row.cell()
            comments = []
            if card.state == Card.State.CARD_REF:
                comments.append(f'см. {card.pid}')
            else:
                if card.phone:
                    comments.append(card.телефон_для_печати)
                comments.append(card.ФИО)
            cell.text(', '.join(comments))

        #-------------------------------------

        if self.тип_карты.это_персональная_карта:
            self.печать_статистики_покупок(row, card)
            self.печать_процента_скидки(row, card)
            self.печать_накопленных_баллов(row, card)

        elif self.тип_карты.это_подарочная_карта:
            #self.печать_закрытия(row, card)
            self.печать_срока_действия(row, card)
            self.печать_остаток_денежных_средств(row, card)

        elif self.тип_карты.это_дисконтная_карта:
            self.печать_срока_действия(row, card)
            self.печать_процента_скидки(row, card)
            self.печать_накопленных_баллов(row, card)

        elif self.тип_карты.это_купон:
            #self.печать_закрытия(row, card)
            self.печать_срока_действия(row, card)
            self.печать_процента_скидки(row, card)
            self.печать_накопленных_баллов(row, card)

    def print_table(self):
        table = self.Table('cards').mt(1)
        table.column()
        table.column().text('Код / Номер')
        if self.тип_карты.это_персональная_карта:
            table.column().text('Персональные данные')
            table.column(align='right').text('Покупок')
            table.column(align='right').text('на сумму')
            table.column(align='right').text('Скидка')
            table.column(align='right').text('Баллы')
            #table.column().text('Количество покупок')
        elif self.тип_карты.это_подарочная_карта:
            #table.column().text('Использование')
            table.column().text('Срок действия')
            table.column(align='right').text('Остаток')
        elif self.тип_карты.это_дисконтная_карта:
            table.column().text('Срок действия')
            table.column(align='right').text('Скидка')
            table.column(align='right').text('Баллы')
        elif self.тип_карты.это_купон:
            #table.column().text('Погашение')
            table.column().text('Срок действия')
            table.column(align='right').text('Скидка')
            table.column(align='right').text('Баллы')
        
        #if Grant.SYSADMIN in self.grants:
        #    table.column().text('Технические подробности')
        #table.column().text('')

        #table.column()
        query = self.postgres.query(Card, Dept).outerjoin(Dept, Dept.id == Card.dept_code)\
            .filter(Card.TYPE == self.series.id)

        finders = []
        finder = self.get('finder')
        if finder and finder.strip():
            for word in re.split(r'[ ]*', finder):
                finders.append(Card.ID.ilike(f'%{word}%'))
        if len(finders):
            query = query.filter(or_(*finders))

        #params = []
        #count = 0
        #строка_поиска = self.get('finder')
        #if строка_поиска is not None and строка_поиска.strip() != '': 
        #    строка_поиска = строка_поиска.strip().upper()
        #    слова =  re.split(r'[ ]*', строка_поиска)
        #    поисковые_условия = []
        #    for слово in слова:
        #        поисковые_условия.append(" ID like %s ") 
        #        params.append(f'%{слово}%')
        #        finders.append(Card.ID.ilike(f'%{слово}%'))

        #    sql = f''' ({' or '.join(поисковые_условия)}) and TYPE=%s and is_test is null'''
        #    params.append(self.series.id)
        #else:
        #    sql = f'TYPE=%s'
        #    params.append(self.series.id)

        
        есть_телефон = self.get('есть_телефон')
        if есть_телефон is not None and есть_телефон.strip() != '':
            if есть_телефон.strip() == '1':
                #sql = sql + ' and phone is not null '
                query = query.filter(Card.phone != None)
            else:
                query = query.filter(Card.phone == None)
                #sql = sql + ' and phone is null '

        фамилия = self.get('фамилия')
        if фамилия is not None and фамилия.strip() != '':
            #sql = sql + ' and NAME ilike %s'
            #params.append(f'%{фамилия.strip().upper()}%')
            query = query.filter(Card.фамилия.ilike(f'%{фамилия.strip()}%'))

        имя = self.get('имя')
        if имя and имя.strip():
            #sql = sql + ' and NAME1 ilike %s'
            #params.append(f'%{имя.strip().upper()}%')
            query = query.filter(Card.имя.ilike(f'%{имя.strip()}%'))

        отчество = self.get('отчество')
        if отчество and отчество.strip():
            #sql = sql + ' and NAME2 ilike %s'
            #params.append(f'%{отчество.strip().upper()}%')
            query = query.filter(Card.отчество.ilike(f'%{отчество.strip()}%'))

        #sql = sql + ' order by modify_date desc'

        query = query.order_by(Card.modify_date.desc()).limit(MAX_COUNT)
        #cards = Card.findall(self.engine, sql, params, max_records=MAX_COUNT)
        for card, dept in query:
            row = table.row(card.ID)
            self.print_row(row, card, dept)
            #pass

        #for card in cards:
        #    count += 1
        #    row = table.row(card.ID)
        #    self.print_row(row, card)
        #else:
        #    self.message(f'Отобрано {count} записей"')

    def open(self):
        if self.series.id == 0:
            self.title(f'{self.series.полное_наименование}')
        else:
            self.title(f'{self.series.id}, {self.series.полное_наименование}')
        #t = self.text_block()
        #t.href('Выгрузка данных в формате XML, Упорядоченная по дате чека'.upper(), 'download_cards', {'series_id':self.series_id})

        #card_count = Card.count(self.engine, 'TYPE=%s', [self.series.id])
        #card_test_count = Card.count(self.engine, 'IS_TEST = TRUE and TYPE=%s ', [self.series.id])
        #self.pg_cursor.execute('select ID from discount_card where is_test=true and TYPE=%s limit 1', [self.series.id])
        #card_test_exists = self.pg_cursor.fetchone()


        query = self.toolbar('query')
        query.item(width=25).input(label='Список кодов (через пробел)', name='finder')\
            .onkeypress(13, '.print_table', forms=[query])
        if self.тип_карты.это_персональная_карта:
            query.item(ml=0.5).select(label='есть телефон', name = 'есть_телефон')\
                .options([['',''], ['1', 'Да'], ['0', 'Нет']])\
                .onchange('.print_table', forms=[query])
            query.item(ml=0.5).input(label='Фамилия', name = 'фамилия').onkeypress(13, '.print_table', forms=[query])
            query.item(ml=0.5).input(label='Имя', name = 'имя').onkeypress(13, '.print_table', forms=[query])
            query.item(ml=0.5).input(label='Отчество', name = 'отчество').onkeypress(13, '.print_table', forms=[query])
        #панель_команд = self.toolbar('toolbar').mt(1)
        #Button(панель_команд, 'найти и показать по дате последнего изменения').onclick('.print_table', forms=[query])
        #ПрозрачнаяКнопка(панель_команд, 'найти и показать по дате последнего изменения').onclick('.print_table', forms=[query])
    

        #table = self.Table('cards').mt(1)
        self.print_table()
