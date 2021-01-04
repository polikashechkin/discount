import flask, sqlite3, json, datetime, os, pickle, uuid, requests, re, arrow, random, time
import xml.etree.cElementTree as ET
from . import Table, Button, Title, IconButton, TextWithComments
from . import DeleteIconButton
from domino.core import log, DOMINO_ROOT
from discount.checks import Check, CheckLine
from discount.pos import PosCheck
from discount.core import DISCOUNT_DB
from discount.series import Series
from domino.page import Page
from domino.page_controls import TabControl, print_std_buttons, СтандартныеКнопки, ПрозрачнаяКнопка as КраснаяКнопка, КраснаяКнопкаВыбор
from domino.page_controls import Кнопка, КнопкаВыбор, ПлоскаяТаблица, print_check_button, ПрозрачнаяКнопка

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

class ThePage(DiscountPage):
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

    def get_group_info(self, product_e_code):
        r = None
        with self.pg_connection:
            self.pg_cursor.execute(
                'select dictionary.e_code, dictionary.name  from dictionary, good where dictionary.code = good.local_group and good.e_code=%s and dictionary.class_id=%s and dictionary.type_id=%s',
                [product_e_code, 'good', 'local_group']
                )
            r = self.pg_cursor.fetchone()
        return (r[0], r[1]) if r is not None else (None, None)
    #------------------------------------------
    # CARDS
    #------------------------------------------
    def cards_table(self, panel = None):
        return Table(self, 'cards')
    
    def print_cards_table(self, panel = None):
        cards = self.cards_table(panel)
        cards.mt(1)
        cards.mr(0.5)
        for card_ID, card_info in self.check.cards.items():
            row = cards.row()
            card = Card.get(self.postgres, card_ID)
            card_type = card_info.TYPE
            card_name = card_info.name

            prim = []
            if card_info.points:
                prim.append(f'баллы "{card_info.points}"')
            if card_info.used_points:
                prim.append(f'используемые баллы "{card_info.used_points}"')
            if card_info.cash:
                prim.append(f'остаток {card_info.cash}')
            
            PRIM = " ".join(prim)

            cell = row.cell(width=2)
            if not card_type:
                cell.style(style='color:red').text(f"Не задан тип карты")
            elif card_type == 'gift':
                cell.icon_button('card_giftcard')\
                    .tooltip(f'Подарочная карта {card_ID} {PRIM}')
            elif card_type == 'coupon':
                cell.icon_button('credit_card').tooltip(f'Купон {card_ID} {PRIM}')
                
            elif card_type == 'discount':
                cell.icon_button('person').tooltip(f'Персональная карта {card_ID} {PRIM}')
            else:
                cell.style(style='color:red').text(f"Неизвестный тип '{card_type}'")
            if card:
                row.cell().href(f'{card_name} "{card_ID}" {PRIM}', 'pages/card', {'card_id' : card_ID})
                cell =row.cell(align='right')
                if card_info.points:
                    Button(cell, 'Использовать все')\
                        .onclick('.задать_используемые_баллы', {'баллы':card_info.points})

            else:
                row.cell(style='color:red').text(f'{card_name} "{card_ID}" {PRIM}')
                cell =row.cell(align='right')


            
            DeleteIconButton(row.cell(width=2)).onclick('.delete_card', {'card_id': card_ID})
            #кнопки = СтандартныеКнопки(row)
            #кнопки.кнопка('удалить').onclick('.delete_card', {'card_id': card_ID})

    def delete_card(self):
        card_ID = self.get('card_id')
        del self.check.cards[card_ID]
        self.check.save()
        self.товары_верхняя_панель()
        self.print_cards_table()

    #------------------------------------------
    # PRODUCTS
    #------------------------------------------
    def print_products(self, panel = None):
        self.print_cards_table(panel)
        text = self.text_block('totals')
        if self.check.totals:
            text.style('color:orange; border: 0.31rem solid orange; background-color:orange; color:white; border-radius:0.3rem')
            actions = []
            for action_id, total in self.check.totals.items():
                NAME = total.get('n', action_id)
                MARK = total.get('m')
                if MARK:
                    actions.append(f'{NAME} : {MARK}')
                DISCOUNT = total.get('d')
                if DISCOUNT:
                    actions.append(f'{NAME} : {DISCOUNT}')
            text.text(", ".join(actions))

        self.print_products_table(panel)

    def print_products_table(self, panel = None):
        table = self.Table('table').mt(0.5)
        for line in self.check.lines.values():
            self.print_line(table, line)

    def delete_all_cards(self):
        self.check.cards = {}
        self.check.save()
        self.print_products()
        self.protocol_table()
        self.основные_кассовые_операции()

    def товары_удалить_все_товары(self):
        lines = len(self.check.lines)
        self.check.clear_keyword()
        self.check.calc_clear()
        self.check.cards = {}
        self.check.lines = {}
        self.check.TYPE = int(self.get('type',0))
        self.check.save()
        self.товары_верхняя_панель()
        self.print_products()
        self.message(f'Удалено {lines} товаров')
        self.print_title()

    def add_product_by_code(self, CODE, price = 1000, qty = 1):
        sql = 'select "name", "local_group" from "good" where code = %s'
        self.pg_cursor.execute(sql, [CODE])
        r = self.pg_cursor.fetchone()
        if r is None:
            log.error(f'Нет товара с кодом {CODE}')
            return False
        else:
            NAME, G_CODE = r
            sql = 'select "e_code", "name" from "dictionary" where class_id=%s and type_id=%s and code=%s'
            self.pg_cursor.execute(sql, ['good', 'local_group', G_CODE])
            r = self.pg_cursor.fetchone()
            G_UID, G_NAME = r
            #line = PosCheck.Line(self.check, CODE, 1000, 1, group=G_UID)
            line = self.check.add_line(CODE, price, qty, group=G_UID)
            line.params['GROUP_NAME'] = G_NAME
            line.params['NAME'] = NAME
            self.check.save()
            return True

    def load_fs_check(self):
        fs_check_id = self.get('fs_check_id') 
        fs_check = self.postgres.query(Check).get(fs_check_id)
        self.товары_удалить_все_товары()
        if fs_check.lines:
            for line in fs_check.lines:
                product_code = line[CheckLine.PRODUCT_CODE]
                price = line[CheckLine.PRICE]
                qty = line[CheckLine.QTY]
                self.add_product_by_code(product_code, round(price/100, 2), qty)
        self.check.save()
        self.print_products()

    def delete_line(self):
        line_ID = self.get('line_uid')
        if line_ID in self.check.lines:
            del self.check.lines[line_ID]
        self.check.save()
        self.print_products()
        self.товары_верхняя_панель()

    def enable_line(self):
        ID = self.get('line_uid')
        #enable = self.get('enable')
        line = self.check.lines.get(ID)
        if line:
            line.enable = not line.enable
            self.check.save()
        self.print_products()
        #    self.message(f'Не найдено строки "{line_uid}"')

    def save_line(self):
        line_uid = self.get('line_uid')
        price = float(self.get('price'))
        qty = float(self.get('qty'))
        barcode = self.get('barcode')
        line = self.check.lines.get(line_uid)
        line.price = price
        line.qty = qty
        line.barcode = barcode
        self.check.save()
        self.print_products()

    def edit_line(self):
        line_uid = self.get('line_uid')
        line = self.check.lines.get(line_uid)
        self.check.calc_clear()
        self.check.save()
        self.print_line(self.table('table'), line, True)

        #self.message(f'edit_line {line_uid} {line.product}')
    
    def print_line(self, table, line, edit=False):
        row = table.row(line.ID)
        if edit:
            row.css('table-warning shadow')
        cell = row.cell()
        cell.style('width:2rem')
        if not edit:
            style = 'color:green' if line.enable else 'color:rgb(220,220,210)'
            button = cell.icon_button('check', style=style)
            button.onclick('.enable_line', {'line_uid':line.ID})
        
        is_card = False
        cell = row.cell(width=1)
        if line.product_type == 'CARD':
            cell.icon_button('card_giftcard').tooltip('КАРТА')
            is_card = True

        name = line.params.get('NAME')
        if name is None:
            name = self.get_product_name(line.product)
            line.params['NAME'] = name
            self.check.save()

        #cell = row.cell(style='white-space:nowrap')
        #if edit:
        #    cell.input(name='barcode', value=line.barcode)\
        #        .tooltip('Штриховой или QR код товара')
        #else:
        #    if line.barcode:
        #        html = f'''{line.product}<p style="font-size:0.7rem;color:gray; line-height: 1em">{line.barcode}</p>'''
        #       cell.html(html)
        #    else:
        #        cell.text(line.product)

        cell = row.cell()
        if edit:
            cell.input(name='barcode', value=line.barcode, label='Штриховой или QR код')
        else:
            info = [line.product]
            #info.append(f'ID {line.ID}')
            #cell.style('-font-size:1.2rem')
            #info.append(f'код "{line.product}"')
            if line.barcode and line.barcode.strip():
                info.append(f'ШК "{line.barcode}"')

            if line.group:
                g_name = line.params.get('GROUP_NAME', '')
                info.append(f'{g_name}')

            #if len(info) > 0:
            #    cell.tooltip(f'{", ".join(info)}')
            TextWithComments(cell, name, info)
        
        cell = row.cell(width=8)
        #cell.style('-font-size:1.2rem')
        #cell.style('width:6rem')
        if edit:
            cell.input(name='qty', value=line.qty, label='Количество')
        else:
            cell.align('right')
            cell.text(line.qty)
            if not is_card:
                cell.onclick('.edit_line', {'line_uid':line.ID})

        cell = row.cell(width=8)
        #cell.style('-font-size:1.2rem')
        #cell.style('width:8rem')
        if edit:
            cell.input(name='price', value=line.price, label='Цена')
        else:
            cell.align('right')
            if line.final_price and line.final_price != line.price:
                TextWithComments(cell, line.final_price, [f'{line.price}'])
                #cell.text(line.final_price)
                #cell.tooltip(f'розничная цена {line.price}')
            else:
                cell.text(line.price)
            if not is_card:
                cell.onclick('.edit_line', {'line_uid':line.ID})

        cell = row.cell(align='right')
        if not edit:
            if line.final_price and line.final_price != line.price:
                TextWithComments(cell, f'{line.final_price * line.qty}', [f'{line.price * line.qty}'])
                #cell.text(f'{line.final_price * line.qty}')
                #cell.tooltip(f'розничная сумма {line.price * line.qty}')
            else:
                cell.text(f'{line.price * line.qty}')

        cell = row.cell(style='color:red', align='right')
        if line.final_price and line.price != line.final_price:
            cell.text(f'{round((line.price - line.final_price)  * line.qty, 2)}')

        кнопки = СтандартныеКнопки(row, width=6, params={'line_uid':line.ID})
        if edit:
            кнопки.кнопка('сохранить', 'save_line', forms = [row])
            кнопки.кнопка('отменить', 'print_products')
        else:
            if not is_card:
                кнопки.кнопка('редактировать', 'edit_line')
            кнопки.кнопка('удалить', 'delete_line')

    #------------------------------------------
    # ПОЛУЧИТЬ КЛЮЧЕВЫЕ СЛОВА
    #------------------------------------------
    def получить_ключевые_слова(self):
        #msg_log = PosCheckLog(self.account_id, self.check_id).clear()
        msg_log = None
        r = self.check.get_keywords(msg_log)
        if r.error:
            self.error(r.message)
        else:
            self.message(f'Операция выполненя успешно. Получен набор ключевых слов {self.check.keywords}.')
        self.check.save()
        self.товары_верхняя_панель()

    #------------------------------------------
    # КАССОВЫЕ ОПЕРАЦИИ 
    #------------------------------------------
    def основные_кассовые_операции(self):
        toolbar = self.Toolbar('base_toolbar').mt(0.5).style('align-items:center; -border:1px solid lightgray').css('shadow-sm')
        #toolbar.style('background-color:#E2E5E8; -paggind:1rem')
        #toolbar.style('background-color:#2C3E50; -paggind:1rem')
        #toolbar.style('background-color:lightgray; -paggind:1rem')
        STYLE = 'background-color:gray; color:white; font-size:0.8rem'
        STYLE = ''

        toolbar.item(width=20).input(name='строка')\
            .style('font-size:large; background-color:gray; color:white; border:1px solid red')\
            .tooltip('Код товара или карты')\
            .onkeypress(13, '.ввод_строки', forms=[toolbar])


        #button = Кнопка(toolbar.item(), 'Добавить товары', mr=0.5).style(STYLE)
        #for ps in self.sqlite.query(PS).filter(PS.class_ == 0):
        #    button.item(ps.name).onclick('.товары_добавить_из_набора', {'набор_ID':ps.id})

        Кнопка(toolbar, 'Промокоды', ml=0.1).style(STYLE)\
            .onclick('.получить_ключевые_слова')

        Кнопка(toolbar, 'Подитог', ml=0.1).style(STYLE)\
            .onclick('.calc')

        Кнопка(toolbar, 'Пробить', ml=0.1).style(STYLE)\
            .onclick('.пробить_чек')\
            .tooltip('Вызвать ДС для проведения последнего расчета, обработать ответ и послать финальный чек.'.upper())

        params = {'check_id':self.check.GUID}
        Button(toolbar, 'Чек', ml=0.1).onclick('pages/fs_check', params)
        #params = {'check_id':self.check.GUID}
        #Кнопка(toolbar, 'Посмотреть', mr=0.5).style(STYLE)\
        #    .onclick('pages/fs_check', params)

        button = Кнопка(toolbar.item(ml='auto'), 'Продажа').style('background-color:green; color:white')\
            .onclick('.товары_удалить_все_товары', {'type':0})
        button = Кнопка(toolbar.item(ml=0.1), 'Возврат').style('background-color:red; color:white')\
            .onclick('.товары_удалить_все_товары', {'type':1})

        #button = Кнопка(toolbar.item(ml=0.1), 'Новый чек', ml=0.1, mr=0.5).style(STYLE)
        #        #.onclick('.товары_удалить_все_товары')
        #button.item('ПРОДАЖА').onclick('.товары_удалить_все_товары', {'type':0})
        #button.item('ВОЗВРАТ').onclick('.товары_удалить_все_товары', {'type':1})
    
    def товары_верхняя_панель(self, panel=None):
        if panel:
            toolbar = panel.item().Toolbar('toolbar').mt(1).style('items-align:center').css('shadow')
        else:
            toolbar = self.Toolbar('toolbar').mt(1).style('items-align:center').css('shadow-sm')
        
        toolbar.item(width=8, mr=0.5).input(disabled=True, value = self.check.check_no, label='Номер чека')
        toolbar.item(width=8, mr=0.5).input(disabled=True, value = self.check.total(), label='Сумма чека')

        points = None
        for card_info in self.check.cards.values():
            if card_info.TYPE == 'discount':
                points = card_info.used_points if card_info.used_points else card_info.points
    
        if points:
            toolbar.item(width=8, ml=0.5, mb=0.1).input(name='баллы', label='Исползуемые баллы', type='number')\
                .onkeypress(13, '.задать_используемые_баллы', forms=[toolbar])
        
        if len(self.check.keywords) != 0:
            select = toolbar.item(width=10, ml=0.5, mb=0.1).select(name='keyword', value = self.check.keyword, label='Ключевое слово')\
                .onchange('.задать_ключевое_слово', forms=[toolbar])
            select.option('', '')
            for keyword in self.check.keywords:
                select.option(keyword, keyword)

        #toolbar.item(width=10, ml=0.5, mb=0.1).input(name='keyword', value = self.check.keyword, label='Ключевое слово')\
        #    .onkeypress(13, '.задать_ключевое_слово', forms=[toolbar])
        
        #params = {'check_id':self.check.GUID}
        #Button(toolbar, 'Чек', ml='auto').style('font-size:0.8rem; background-color:gray; color:white').onclick('pages/fs_check', params)
        Button(toolbar, 'Сброс', ml='auto').style('font-size:0.8rem').onclick('.сбросить_расчет_и_обновить')
        checks = self.postgres.query(Check).filter(Check.dept_code == self.check.dept_code, Check.bookmark == True).limit(20).all()
        #if len(checks) > 0:
        button = Кнопка(toolbar.item(ml=0.1), 'чеки').style('font-size:0.8rem')
        for fs_check in checks:
            button.item(f'Дата {fs_check.date}, фр {fs_check.pos_id} смена {fs_check.session_id} номер {fs_check.check_no}').onclick('.load_fs_check', {'fs_check_id':fs_check.ID})

        Button(toolbar, 'Карты', ml=0.1).style('font-size:0.8rem')\
            .onclick('pages/test_cards', {'check_id':self.ID})\
            .tooltip('Создание, удаление тестовых карт, а также добавление в чек')
        Button(toolbar, 'Товары', ml=0.1).style('font-size:0.8rem')\
            .onclick('pages/test_goods', {'check_id':self.ID})
            #.tooltip('Создание, удаление тестовых карт, а также добавление в чек')
        #Button(toolbar, 'Протокол', ml=0.1).style('font-size:0.8rem').onclick('pages/test_log', {'check_id':self.check_id})
    
    def задать_используемые_баллы(self):
        points = self.get('баллы')
        for card_info in self.check.cards.values():
            if card_info.TYPE == 'discount':
                card_info.used_points = points
                self.message(f'Использовать {card_info.used_points} баллов')
        self.check.save()

        self.товары_верхняя_панель()
        self.print_products()
        self.основные_кассовые_операции()

    def задать_ключевое_слово(self):
        keyword = self.get('keyword')
        self.check.keyword = keyword
        self.check.save()
        self.message(f'Задано ключевое слово "{keyword}"')

        self.товары_верхняя_панель()
        self.основные_кассовые_операции()

    def сообщение(self, x, msg):
        x.row().cell(style='font-size:0.8rem; font-weight:bold').text(f'{msg.upper()}')

    def ввод_строки(self):
        строка = self.get('строка')
        self.ввод_строки_в_кассе(строка)

    def прокатать_карту(self):
        card_ID = self.get('card_ID')
        card = Card.get(self.engine, card_ID)
        if card is not None:
            self.ввод_строки_в_кассе(card.ID)

    def ввод_строки_в_кассе(self, строка):
        #msg_log = PosCheckLog(self.account_id, self.check_id).clear()
        msg_log = None
        if строка and строка.strip():
            if self.add_product_by_code(строка.strip()):
                self.message('Добавлен товар')
                self.товары_верхняя_панель()
                self.print_products()
                self.check.save()
                return

            r = self.check.check_card(строка, msg_log)
            if r.error:
                self.error(r.message)
                return
            else:
                self.message('Операция успешно выполнена')
                self.check.save()
                self.товары_верхняя_панель()
                self.print_products()
                return 

    def сбросить_расчет_и_обновить(self):
        self.check.calc_clear()
        self.check.save()
        self.сбросить_расчет()
        self.товары_верхняя_панель()
        self.print_products()

    def сбросить_расчет(self):
        self.check.calc_clear()
        self.check.save()

    def пробить_чек(self):
        #msg_log = PosCheckLog(self.account_id, self.check_id)
        msg_log = None

        self.check.next_check()
        self.check.save()

        START = time.perf_counter()

        r = self.check.calc(msg_log)
        if r.error:
            self.error(r.message)
            return

        r = self.check.accept(msg_log)
        if r.error:
            self.error(r.message)
            return
            
        STOP = time.perf_counter()
        ms = round((STOP - START) * 1000, 3)
        self.message(f'Операция успешно выполнена за {ms} мс')
        #self.check.save()

        self.основные_кассовые_операции()
        self.товары_верхняя_панель()
        self.print_products()

    def calc(self):
        #msg_log = PosCheckLog(self.account_id, self.check_id)
        msg_log = None

        #self.check.next_check()
        #self.check.save()

        START = time.perf_counter()

        r = self.check.calc(msg_log)
        if r.error:
            self.error(r.message)
            return

        #r = self.check.accept(msg_log)
        #if r.error:
        #    self.error(r.message)
        #    return
            
        STOP = time.perf_counter()
        ms = round((STOP - START) * 1000, 3)
        self.message(f'Операция успешно выполнена за {ms} мс')
        #self.check.save()

        self.основные_кассовые_операции()
        self.товары_верхняя_панель()
        self.print_products()
    
    #------------------------------------------
    # OPEN
    #------------------------------------------
    def print_title(self):
        text = []
        text.append(f'{self.check.name}')
        #text.append('ПРОДАЖА' if self.check.TYPE == 0  else 'ВОЗВРАТ')
        text.append(f'{self.get_dept_name(self.check.dept_code)}')
        try:
            value = self.check.date.strftime('%Y-%m-%d %H:%M')
            text.append(value)
        except:
            pass
            #value = 'Текущая дата и время'
        title = Title(self, ', '.join(text))
        if self.check.test_mode == 0:
            button = IconButton(title, None, 'fiber_manual_record', style='color:orange')
            button.tooltip('Проверка акций, ДО уверждения дисконтной схемы')
        else:
            button = IconButton(title, None, 'fiber_manual_record', style=f'color:lightgray')
            button.tooltip('Проверка акций, ПОСЛЕ уверждения дисконтной схемы.')
        if self.check.TYPE == 0:
            button = IconButton(title, None, 'fiber_manual_record', style='color:green')
            button.tooltip('ПРОДАЖА')
        else:
            button = IconButton(title, None, 'fiber_manual_record', style=f'color:red')
            button.tooltip('ВОЗВРАТ')

        #IconButton(title, None, 'star', style='color:red')

    def open(self):
        self.print_title()
        #ПараметрыЧека(self)
        self.основные_кассовые_операции()
        self.товары_верхняя_панель()
        self.print_products()

