import flask, sqlite3, json, datetime, os, pickle, uuid, requests, re, arrow, random, time
import xml.etree.cElementTree as ET
from . import Table, Button, TextWithComments
from . import DeleteIconButton, AddIconButton
from domino.core import log, DOMINO_ROOT
from discount.checks import Check, CheckLine
from discount.pos import PosCheck
from discount.core import DISCOUNT_DB
from discount.series import Series
#from domino.page import Page
from domino.page_controls import TabControl, print_std_buttons, СтандартныеКнопки, ПрозрачнаяКнопка as КраснаяКнопка, КраснаяКнопкаВыбор
from domino.page_controls import Кнопка, КнопкаВыбор, ПлоскаяТаблица, print_check_button, ПрозрачнаяКнопка

from sqlalchemy import and_, or_

from domino.page_controls import Кнопка as Button

from domino.page_controls import ТабличнаяФорма, FormControl
from discount.page import DiscountPage
from discount.cards import Card
from tables.Good import Good
from domino.tables.postgres.dictionary import Dictionary as DICT
#from tables.sqlite.product_set import ГотовыйНабор as НАБОР
from tables.sqlite.product_set import ГотовыеНаборы
from tables.sqlite.product_set import ProductSet as PS

from discount.series import ТипКарты
from discount.schemas import ДисконтнаяСхема

from discount.dept_sets import DeptSetItem
#from discount.grants import Grants

from discount.calculator import Engine
from settings import MODULE_ID
#from discount.pos_log import PosCheckLog

CHECK_FILE_NAME = 'check'

class Page(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.account_id = self.request.account_id()
        self._test_products = None
        self._nn = 0
        self.card_types = self.application['card_types']
        self.server = 'localhost'
        self.ID = self.attribute('ID')
        self.check_id = self.ID
        self.check = PosCheck.load(self.account_id, self.ID)
        self.схема_ID = self.check.schema_id
    @property
    def дисконтная_схема(self):
        return ДисконтнаяСхема.get(self.cursor, self.схема_ID)
    
    def get_dept_name(self, value):
        if value:
            try:
                self.pg_cursor.execute('''
                    select name from dept
                    where ID=%s
                    ''', [value])
                r = self.pg_cursor.fetchone()
                if not r:
                    return f'ПОДРАЗДЕЛЕНИЕ НЕ НАЙДЕНО {value}'     
                return r[0]
            except BaseException as ex:
                log.exception(f'{self}')
                return f'ПОДРАЗДЕЛЕНИЕ НЕ ОПРЕДЕЛЕНО {ex}'
        else:
            return f'ПОДРАЗДЕЛЕНИЕ НЕ ОПРЕДЕЛЕНО'

    def товары_добавить_из_набора(self):
        set_id = self.get('set_id')
        набор = ГотовыеНаборы(self.sqlite).готовый_набор(set_id)
        набор.prepeare()
        log.debug(f'НАБОР {набор.is_bigsize}, {набор._goods_sets}, {набор._goods}')
        
        goods = набор.query(self.postgres).limit(500).all()
        if len(goods) == 0:
            self.error(f'Пустой набор')
            return 
        k = 3 if len(goods) >= 3 else len(goods)
        sample_rows = random.sample(goods, k)
        added = 0
        for good in sample_rows:
            try:
                group = self.postgres.query(DICT).filter(DICT.TYPE == 'local_group', DICT.code == good.local_group).first()
                line = self.check.add_line(good.code, 1000, 1, group=group.e_code)
                line.params['GROUP_NAME'] = group.name
                line.params['NAME'] = good.name
                added += 1
            except:
                log.exception(__file__)
        self.check.save()
        #self.print_products()
        self.message(f'Добавлено {added} товаров')

    def print_good_sets(self):
        table = Table(self, 'table')
        #toolbar.style('background-color:#E2E5E8; -paggind:1rem')
        #toolbar.style('background-color:#2C3E50; -paggind:1rem')
        for ps in self.sqlite.query(PS)\
            .filter(PS.class_ == 0, or_(PS.schema_id == self.check.schema_id, PS.schema_id == 0))\
            .order_by(PS.schema_id.desc()):
            row = table.row(ps.id)
            row.cell().text(ps.id)
            #row.cell().text(ps.schema_id)
            row.cell().text(ps.name)
            row.cell(style='color:gray',align='right').text(ps.type_name.upper())
            #Button(row.cell(align='right'), 'Добавить').onclick('.товары_добавить_из_набора', {'set_id':ps.id})
            AddIconButton(row.cell(width=2,align='right')).onclick('.товары_добавить_из_набора', {'set_id':ps.id})
        #button = Кнопка(toolbar, 'Добавить карту', mr=0.5).style(STYLE)\
        #    .tooltip('Выбрать тестовую карты. Это аналогично, если ввести код карты в строку ввода')
        #for card in Card.findall(self.engine, 'IS_TEST=TRUE', limit=30):
        #    try:
        #        тип_карты = ТипКарты.get(self.cursor, card.TYPE)
        #        состояние = card.state_name
        #        описание = f'{тип_карты.полное_наименование} "{card.ID}" {состояние.upper()}' 
        #        button.item(описание).onclick('.прокатать_карту', {'card_ID' : card.ID})
        #    except:
        #        button.item(f'{card.ID}').onclick('.прокатать_карту', {'card_ID' : card.ID})

        #select = toolbar.item(mr=0.5).select(label='Ключевые слова').style(STYLE)
    
    
    def print_title(self):
        title = []
        title.append(f'{self.check.name}')
        #title.append(f'{self.get_dept_name(self.check.dept_code)}')
        title.append('Добавить товары')
        self.title(', '.join(title))

    def __call__(self):
        self.print_title()
        self.print_good_sets()

