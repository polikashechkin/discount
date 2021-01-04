import flask, sqlite3, json, datetime, arrow
#from domino.page import Page, Filter
from sqlalchemy import or_, and_
from domino.core import log
from discount.core import CARDS, DISCOUNT_DB
from discount.series import Series, ТипКарты
from discount.cards import Card, CardLog
from discount.page import DiscountPage
from domino.page_controls import TabControl, ПрозрачнаяКнопка as КраснаяКнопка, ПлоскаяТаблица
from domino.page_controls import ОсновнаяКнопка
from . import Button, Toolbar, Title, Input, Select, Table

LIMIT = 6

ПоисковыеЗакладки = TabControl('TheTabs', mt=1)
ПоисковыеЗакладки.append('tab1', 'Поиск по номеру или коду', 'поиск_по_номеру')
ПоисковыеЗакладки.append('tab2', 'Поиск по телефону', 'поиск_по_телефону')
ПоисковыеЗакладки.append('tab3', 'Поиск по персональным данным', 'поиск_по_персональным_данным')

class Page(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request, controls=[ПоисковыеЗакладки])

    #def error_show(self, msg):
        #t = self.table('cards', css='table-borderless', hole_update=True)
        #t.row().text(msg).style('color:red; font-size:large')
    #    t = self.text_block('cards').style('color:red; -font-size:large').mt(1)
    #    t.text(msg)

    #def print_cards(self):

        #CARD_ID = self.get('card_id')
        #FIO = self.get('fio')
        #YEAR = self.get('year')
        #PHONE = self.get('phone')
        #EMAIL = self.get('email')

        #query = self.postgres.query(Card)
        #if CARD_ID:
        #    query = query.filter(or_(Card.ID == CARD_ID, Card.marknum == CARD_ID))

        #cards = query.limit(11)

        #if len(cards) == 0:
        #    self.error_show(f'Не найдено ни одной карточки, соответствующей запросу {FIO} {PHONE} {EMAIL}'.upper())
        #elif len(cards) > 10:
        #    self.error_show(f'Найдено слишком много карточек, уточните запрос'.upper())
        #else:
        #    table = self.table('cards', hole_update=True).mt(1)
        #    table.column().text('Номер')
        #    table.column().text('Фио')
        #    table.column().text('Год')
        #    table.column().text('Телефон')
        #    table.column().text('Почта')
        #    cur = sqlite3.connect(DISCOUNT_DB(self.account_id)).cursor()
        #    for card in cards:
        #        series = Series.get(cur, card.TYPE)
        #        row = table.row(card.id)
        #        row.href(f'{series.type_name} {card.id}', 'pages/card', {'card_id':card.id})
        #        row.text(card.info.get('fio',''))
        #        row.text(card.info.get('day',''))
        #        row.text(card.info.get('phone',''))
        #        row.text(card.info.get('email',''))
    #def find(self):
    #    self.print_cards()

    def поиск_по_персональным_данным(self):
        t = self.text_block('about').mt(1)
        t.text('''
        Для поиска следует ввести фамилию, имя, отчество, день рождения.
        Можно задать все вместе, можно по отдельности. Ищется по вхождению.
        Если задать мало параметров, то можно получить досточно много записей.
        В этом случае выдается соответствующее сообщение и следует уточнить запрос.
        Не имеет значение в каком регистре набирать текст.
        ''')

        query = ПлоскаяТаблица(self, 'query').cls('table-hover', False)
        x = query.row().cell().toolbar()
        x.item().input(label = 'Фамилия', name='фамилия')
        x.item().input(label = 'Имя', name='имя')
        x.item().input(label = 'Отчество', name='отчество')
        x.item().input(label = 'День рождения', name='день_рождения', type='date')

        f = self.toolbar('finder').mt(1)
        Button(f, 'Найти по персональным данным').onclick('.найти_карты_по_персональным_данным', forms=[query])
        self.Table('cards')

    def найти_карты_по_персональным_данным(self):
        #фильтр = ФильтрПоПерсональнымДанным(self)
        #sql = []
        #params = []

        фамилия = self.get('фамилия')
        имя = self.get('имя')
        отчество = self.get('отчество')
        try:
            DAY = self.get('день_рождения')
            day = arrow.get(DAY).date()
        except:
            day = None

        query = self.postgres.query(Card)
        if фамилия is not None and фамилия.strip() != '':
            query = query.filter(Card.фамилия.ilike(f'%{фамилия.strip()}%'))
            #sql.append('NAME ilike %s')
            #params.append(f'%{фамилия.strip().upper()}%')

        имя = self.get('имя')
        if имя and имя.strip():
            query = query.filter(Card.имя.ilike(f'%{имя.strip()}%'))
            #sql.append(' NAME1 ilike %s')
            #params.append(f'%{имя.strip().upper()}%')

        отчество = self.get('отчество')
        if отчество and отчество.strip():
            query = query.filter(Card.отчество.ilike(f'%{отчество.strip()}%'))
            #sql.append(' NAME2 ilike %s')
            #№params.append(f'%{отчество.strip().upper()}%')
        if day:
            query = query.filter(Card.день_рождения == day)

        cards = query.limit(LIMIT).all()
        self.выбрать_карту(cards)

    def поиск_по_телефону(self):
        t = self.text_block('about').mt(1)
        t.text('''
        Для поиска следует следует полный номер телефона в виде
        XXX XXX XXXX. Разделители можно использовать любые (или не использовать). 
        Номер должен быть задан точно (никаких вхождений не предполагается)
        ''')
        query = ПлоскаяТаблица(self, 'query').cls('table-hover', False)
        x = query.row().cell().toolbar().style('align-items:flex-end')
        x.item().Text().style('font-size:1.7rem; color:lightgray;white-space:nowrap').text('+7&nbsp;')
        x.item().input(label = 'Номер телефона', name='телефон').style('font-size:1.5rem')
        f = self.toolbar('finder').mt(1)
        Button(f, 'Найти карту по номеру телефона').onclick('.найти_карту_по_телефону', forms=[query])
        self.Table('cards')

    def найти_карту_по_телефону(self):
        телефон_ввод = self.get('телефон')
        if телефон_ввод is None or телефон_ввод.strip() == '':
            self.error(f'Не задан номер телефона')
            return

        телефон = Card.преобразовать_к_нормальному_виду(телефон_ввод)
        if телефон is None:
            self.error(f'Не правильно задан номер телефона "{телефон_ввод}"')
            return
        #self.message(телефон)
        #return
        #телефон_текст = Card.преобразовать_к_печатному_виду(телефон)
        #self.message(f'{телефон_текст}')
        #return 
        
        cards = self.postgres.query(Card).filter(Card.phone == str(телефон)).limit(LIMIT).all()
        self.выбрать_карту(cards)

    def поиск_по_номеру(self):
        t = self.text_block('about').mt(1)
        t.text('''
        Для поиска по номеру, следует задать 
        маркировочный номер карты. Он должен быть напечатан на карте и (или)
        указан в анкетных данных.
        В этом режиме можно найти данные по всем типам карт, используемых 
        в системе. Номер должен быть задан точно (никаких вхождений не используется)
        ''')
        query = ПлоскаяТаблица(self, 'query').cls('table-hover', False)
        x = query.row().cell().toolbar().mt(1)
        x.item(width=16).input(label = 'Номер или код карты', name='номер').style('font-size:1.5rem')
        f = self.toolbar('finder').mt(1)
        #ОсновнаяКнопка(f, 'Найти карту по номеру или коду').onclick('.найти_карту_по_номеру', forms=[query])
        Button(f, 'Найти карту по номеру или коду').onclick('.найти_карту_по_номеру', forms=[query])
        self.Table('cards')

    def найти_карту_по_номеру(self):
        номер = self.get('номер').strip()
        query = self.postgres.query(Card)
        query = query.filter(or_(Card.ID == номер, Card.marknum == номер))
        cards = query.limit(LIMIT).all()
        self.выбрать_карту(cards)

    def выбрать_карту(self, cards):
        t = Table(self, 'cards').mt(1)
        if len(cards) == 0:
            self.error('Не найдено ни одной карты')
        elif len(cards) >= LIMIT:
            self.error(f'Найдено слишком много карт (более {LIMIT-1}). Уточните запрос')
        else:
            t.column('Тип')
            t.column('Номер')
            t.column('Телефон')
            t.column('ФИО')
            t.column('День рождения')
            for card in cards:
                row = t.row()
                тип_карты = ТипКарты.get(self.cursor, card.TYPE)
                row.cell().text(тип_карты.полное_наименование)
                row.cell().href(card.marknum, 'pages/card.open', {'card_id':card.ID})
                row.cell().text(card.phone)
                row.cell().text(card.ФИО.upper())
                row.cell().text(card.день_рождения)
                #наименование = f'{тип_карты.type_name} {тип_карты.description}')

    def open(self):
        self.title(f'Поиск')
        ПоисковыеЗакладки(self)
