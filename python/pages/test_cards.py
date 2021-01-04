import flask, sqlite3, json, datetime, re
from domino.page_controls import print_std_buttons
from sqlalchemy import or_, and_, text as T, func as F

from domino.pages import Title, Table, Rows, Toolbar, Button, Select, Rows, TextWithComments
from domino.pages import DeleteIconButton, AddIconButton

from domino.core import log
from discount.core import CARDS, DISCOUNT_DB, Engine
from discount.series import CardType
#from discount.cards import Card
from domino.tables.postgres.discount_card import DiscountCard as Card
from discount.page import DiscountPage as BasePage
from domino.page_controls import Кнопка, ПрозрачнаяКнопка, СтандартныеКнопки, ПрозрачнаяКнопкаВыбор
from grants import Grants
from discount.pos import PosCheck

MAX_COUNT = 200

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self._card_types = None
        self.check_id = self.attribute('check_id')
        self._check = None
        self._check_cards = None

    @property
    def check(self):
        if self._check is None:
            self._check = PosCheck.load(self.account_id, self.check_id)
        return self._check
    @property
    def all_card_types(self):
        if self._card_types is None:
            self._card_types = {}
            for card_type in CardType.findall(self.cursor):
                self._card_types[card_type.ID] = card_type
        return self._card_types
    
    @property
    def check_cards(self):
        if self._check_cards is None:
            self._check_cards = {}
            for card_ID, card_info in self.check.cards.items():
                self._check_cards[card_ID] = card_info
        return self._check_cards

    def create_cards(self, card_type):
        #log.debug(f'create_cards({card_type}):')
        try:
            is_test = True
            random = card_type.gen_mode_random
            user_name = self.user_name
            activate = card_type.activation_mode == CardType.activation_mode_CREATE
            created = 0
            with self.connection:
                if random:
                    card = Card.create_card(self.postgres, card_type, user_name = user_name, is_test = is_test)
                else:
                    card_type.next_number += 1
                    card = Card.create_card(self.postgres, card_type, number = card_type.next_number, user_name = user_name, is_test = is_test)
                    card_type.update(self.cursor)
                    self.connection.commit()
                if activate:
                    card.activate(self.postgres, discount = card_type.discount, cash=card_type.cash, points=card_type.points, user_name = user_name, exp_days = card_type.exp_days)
                #conn.commit()
                #self.connection.commit()
                created += 1
            self.message(f'Создано {created} карт')

        except BaseException as ex:
            log.exception('')
            self.error(f'{ex}')
        #self.postgres.commit()

    def create_card(self):
        #log.debug('CREATE CARD')
        card_type_id = self.get('card_type_id')
        card_type = CardType.get(self.cursor, int(card_type_id))
        self.create_cards(card_type)
        self.postgres.commit()
        self.print_toolbar()
        self.print_table()
        #self.message(f'{card_type.наименование}')

    def delete_cards(self):
        card_type_id = self.get('card_type_id')
        with self.pg_connection:
            self.pg_cursor.execute('delete from discount_card where is_test=true and "type"=%s', [card_type_id])
        self.print_toolbar()
        self.print_table()
        #self.message(f'{card_type.наименование}')

    def удалить(self):
        card_id = self.get('card_id')
        self.postgres.query(Card).filter(Card.ID == card_id).delete()
        Rows(self, 'cards').row(card_id)

    def печать_статуса(self, row, card):
        cell = row.cell(width=2)
        if card.state:
            if card.state == Card.State.CREATED:
                cell.text('')
            elif card.state == Card.State.ACTIVE:
                cell.glif('circle', style="color:green;")
            elif card.state == Card.State.DISABLED:
                cell.glif('circle', style="color:red;")
            elif card.state == Card.State.CARD_REF:
                cell.glif('reply', style="color:gray;")

            else:
                cell.glif('circle', style="color:black;")

    def печать_номера(self, row, card):
        cell = row.cell()
        if card.marknum and card.marknum.strip():
            cell.href(card.marknum, 'pages/card', {'card_id':card.ID})
        else:
            cell.href(card.ID, 'pages/card', {'card_id':card.ID})
            
    def add_card_to_check(self):
        card_id = self.get('card_id')
        r = self.check.check_card(card_id, None)
        self._card_types = None
        if r.error:
            self.error(r.message)
            return
        self.check.save()
        row = Rows(self, 'cards').row(card_id)
        card = self.postgres.query(Card).get(card_id)
        self.print_row(row, card)
        self.message('Операция успешно выполнена')

    def print_row(self, row, card):
        self.печать_статуса(row, card)
        row.cell(style='white-space:nowrap').href(card.id, 'pages/card', {'card_id':card.id})
        # ----------------------------
        cell = row.cell(wrap=False)
        if card.state == Card.State.CARD_REF:
            cell.text(f'=> {card.pid}')
        else:
            card_type = self.all_card_types.get(card.TYPE)
            if card_type is not None:
                type_name = card_type.наименование
            else:
                type_name = f'Тип карты "{card.TYPE}"'

            params = [card.marknum]
            if card.ФИО:
                params.append(card.ФИО)
            if card.exp_date:
                params.append(f'до {card.exp_date}')
            if card.cash:
                params.append(f'остаток {card.cash}')
            if card.discount:
                params.append(f'скидка {card.discount}%')
            if card.points:
                params.append(f'баллов {card.points}')
            if card.checks:
                params.append(f'покупок {card.checks}')
            if card.total:
                params.append(f'на сумму {card.total}')
            params.append(f'создание {card.ctime}')
                #row.cell(align='right').text(f'{card.points}' if card.points else '')
            TextWithComments(cell, type_name, params)
        # ----------------------------
        cell = row.cell(width=4, align='right', style='white-space:nowrap')
        if card.id not in self.check_cards:
            Button(cell, 'Добавить').onclick('.add_card_to_check', {'card_id' : card.id})

        cell = row.cell(width=2, align='right', style='white-space:nowrap')
        DeleteIconButton(cell).onclick('.удалить', {'card_id' : card.ID})

    def print_table(self, finder = None):
        table = self.Table('cards').mt(1)

        query = self.postgres.query(Card).filter(Card.is_test == True)
        card_type = self.get('card_type')
        if card_type:
            query = query.filter(Card.TYPE == card_type)

        query = query.order_by(Card.modify_date.desc())
        for card in query:
            row = table.row(card.ID)
            self.print_row(row, card)

    def print_toolbar(self):
        used_card_types = {}
        cur = self.postgres.execute(T('select "type", count(*) from discount_card where is_test=true group by "type"'))
        for card_type_id, count in cur:
            used_card_types[card_type_id] = count

        toolbar = self.toolbar('toolbar')
        #----------------------------------------
        select  = Select(toolbar.item(), name='card_type').onchange('.print_table', forms=[toolbar])
        select.option('', '<Тип карты>')
        for card_type_id, count in used_card_types.items():
            card_type = CardType.get(self.cursor, card_type_id)
            select.option(card_type_id, f'{card_type.наименование}' if card_type else f'Неизвестный тип {card_type_id}')
        #----------------------------------------
        button = Button(toolbar.item(ml='auto'), 'Создать')
        for card_type in CardType.findall(self.cursor):
            # card_type.наименование and card_type.activation_mode == CardType.activation_mode_CREATE:
            if card_type.наименование:
                button.item(card_type.наименование).onclick('.create_card', {'card_type_id':card_type.ID})
        #----------------------------------------
        button = Button(toolbar.item(ml=1), 'Удалить', ml='auto').onclick('.delete_test_cards')
        for card_type_id, count in used_card_types.items():
            card_type = CardType.get(self.cursor, card_type_id)
            card_type_name = card_type.наименование if card_type else f'<{card_type_id}>'
            #card_type = CardType.get(self.cursor, card_type_id)
            button.item(f'{card_type_name} ({count})').onclick('.delete_cards', {'card_type_id':card_type_id})

        #cur = self.postgres.execute(T('select "type", count(*) from discount_card where is_test=true group by "type"'))
        #for card_type_id, count in cur:
        #    card_type = CardType.get(self.cursor, card_type_id)
        #    button.item(f'{card_type.наименование} ({count})').onclick('.delete_cards', {'card_type_id':card_type.ID})
        #----------------------------------------

    def open(self):
        Title(self, f'Тестовые карты, {self.check.name}')
        self.print_toolbar()
        self.print_table()
