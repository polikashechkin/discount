import flask, sqlite3, json, datetime, os, arrow
from lxml import etree as ET


from domino.core import log, DOMINO_ROOT
from discount.checks import Check, CheckLine
from discount.checks import TEXT_TEXT, TEXT_BOLD, TEXT_CODE, TEXT_EAN13
from domino.tables.postgres.dept import Dept

from discount.core import DISCOUNT_DB
from discount.page import DiscountPage
from domino.page_controls import TabControl
from domino.page_controls import ПлоскаяТаблица
from discount.series import Series
from discount.actions import Action
from discount.schemas import ДисконтнаяСхема
from discount.cards import Card
from . import Title, IconButton, Text

fs_check_tabs = TabControl('fs_check_tabs', mt=1)
fs_check_tabs.append('products', 'Товары', 'print_products')
fs_check_tabs.append('cards', 'Карты', 'print_cards')
fs_check_tabs.append('payments', 'Оплата', 'print_payments')
fs_check_tabs.append('print', 'Печать', 'print_print')
fs_check_tabs.append('calc', 'Последний расчет', 'print_calc_protocol')
fs_check_tabs.append('protocol', 'Послепродажные действия', 'print_protocol')

class ThePage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request, controls=[fs_check_tabs])
        self.check_id = self.attribute('check_id')
        #self.check = Check.pg_get(self.pg_cursor, self.account_id, self.check_id)
    
    def get_calc_print(self, check):
        WORK_FOLDER = self.work_folder(check)
        file = os.path.join(WORK_FOLDER, f'{check.ID}.calc.print') 
        if os.path.isfile(file):
            with open(file, 'r') as f:
                return json.load(f)
        return None

    def get_log(self, check):
        WORK_FOLDER = self.work_folder(check)
        file = os.path.join(WORK_FOLDER, f'{check.ID}.log') 
        if os.path.isfile(file):
            with open(file, 'r') as f:
                return json.load(f)
        return None

    def calc_xml_file(self, check):
        return Check.xml_file(self.account_id, check.check_date, check.dept_code, check.calc_check_id, ext='calc.xml')

    def calc_xml_cr_file(self, check):
        return Check.xml_file(self.account_id, check.check_date, check.dept_code, check.calc_check_id, ext='calc.r.xml')

    def xml_file(self, check):
        return Check.xml_file(self.account_id, check.check_date, check.dept_code, check.ID, ext='accept.xml')

    def drow_line_type_glif(self, cell, line_type):
        cell.style('width:2em')
        if line_type == TEXT_TEXT:
            cell.glif('font').style('color:darkgray')
        elif line_type == TEXT_BOLD:
            cell.glif('bold').style('color:darkgray')
        elif line_type == TEXT_CODE:
            cell.glif('qrcode').style('color:darkgray')
        elif line_type == TEXT_EAN13:
            cell.glif('barcode').style('color:darkgray')
        else:
            cell.text(f'{line_type}')

    def print_print_lines(self, xlines, table, description):
        if xlines:
            row = table.row()
            row.cell()
            row.cell(style='color:lightgray;').text(description.upper())
            for xline in xlines:
                row = table.row()
                self.drow_line_type_glif(row.cell(), xline.tag)
                row.cell().text(xline.text)

    def print_print(self):
        table = ПлоскаяТаблица(self, 'table')
        check = self.postgres.query(Check).get(self.check_id)
        try:
            xml = ET.parse(self.calc_xml_cr_file(check))
        except Exception as ex:
            table.row().cell().text(f'ДАННЫХ НЕ ОБНАРУЖЕНО {ex}')
            return
        
        self.print_print_lines(xml.find('HEADER'), table, 'начало чека')
        self.print_print_lines(xml.find('FOOTER'), table, 'окончание чека')
        xcoupons = xml.find('COUPONS')
        if xcoupons:
            for xcoupon in xcoupons:
                self.print_print_lines(xcoupon, table, '==================')

    def print_cards(self):
        table = self.Table('table').mt(1)
        CARDS = self.postgres.query(Check.cards).filter(Check.ID == self.check_id).scalar()
        if CARDS is not None:
            #table.column().text('Код')
            #table.column().text('Описание')
            for card_ID, card_info in CARDS.items():
                card = Card.get(self.engine, card_ID)
                row = table.row()
                if card is None:
                    row.text(f'{card_ID}')
                    row.cell(style='color:red').text('НЕ РАСПОЗНАНА')
                else:
                    тип_карты = Series.get(self.cursor, card.TYPE)
                    row.cell().href(f'{card.ID}', 'pages/card', {'card_id' : card.ID})
                    row.text(f'{тип_карты.полное_наименование}')

    def action_operation(self, operation):
        try:
            action_id = int(operation)
            if action_id > 0:
                return action_id
            else:
                return None
        except:
            return None

    def work_folder(self, check):
        return os.path.join(DOMINO_ROOT, 'accounts', self.account_id, 'data', 'discount', 'calc', f'{check.check_date.year}/{check.check_date.month:02}/{check.check_date.day:02}/{check.dept_code}')

    def print_calc_protocol(self):
        log.debug(f'print_calc_protocol')
        table = ПлоскаяТаблица(self, 'table').mt(1)
        check = self.postgres.query(Check).get(self.check_id)
        WORK_FOLDER = self.work_folder(check)
        CALC_ID = check.calc_check_id
        calc_log = None
        ex = None
        try:
            file = os.path.join(WORK_FOLDER, f'{CALC_ID}.calc.log') 
            if os.path.isfile(file):
                with open(file, 'r') as f:
                    calc_log = json.load(f)
        except:
            log.exception(__file__)

        #check = self.calc_check
        if calc_log is None:
            table.row().cell().text(f'НЕТ ДАННЫХ О ПОСЛЕДНЕМ РАСЧЕТЕ')
            table.row().cell().text(f'чек {check.ID}')
            table.row().cell().text(f'рачет {CALC_ID}')
            table.row().cell().text(f'{WORK_FOLDER}')
            table.row().cell().text(f'{ex}')
            return
        START, STOP = check.get_start_stop(self.account_id, calc=True)
        previous = START
        row = table.row()
        p = row.cell().text_block()
        p.text('НАЧАЛО&nbsp;')
        #log.debug(f'show_xml_file : {self.calc_xml_file(check)}')
        p.href('запрос', 'show_xml_file', {'xml_file' : self.calc_xml_file(check)}, new_window=True) 
        row.text(f'{START}')
        row.text('')
        for log_record in calc_log:
            row = table.row()
            DT, OPERATION, MSG = Check.read_log_record(log_record)
            action_id = self.action_operation(OPERATION)
            if action_id is not None:
                with sqlite3.connect(DISCOUNT_DB(self.account_id)) as conn:
                    cur = conn.cursor()
                    action = Action.get(cur, action_id)
                    action_type = self.action_types[action.TYPE]
                row.text(f'{action_id} ({action_type.id}) {action.полное_наименование(self.action_types)}')
            else:
                row.text(Check.operation_name(OPERATION))
            row.text(MSG)
            now = DT
            tm = round((now - previous).total_seconds() * 1000, 1)
            previous = now
            row.cell(style='white-space:nowrap; text-align:right').text(f'{tm} ms')
        
        row = table.row()
        cell = row.cell().text('СОХРАНЕНИЕ ДАННЫХ')
        row.cell()
        tm = round((STOP - previous).total_seconds() * 1000, 1)
        row.cell(style='white-space:nowrap; text-align:right').text(f'{tm} ms')

        row = table.row()
        cell = row.cell()
        t = cell.text_block()
        t.text('ОКОНЧАНИЕ&nbsp;')
        t.href('ответ', 'show_xml_file', {'xml_file' : self.calc_xml_cr_file(check)}, new_window=True) 
        row.text(f'{STOP}')
        delta = STOP - START
        tm = round(delta.total_seconds() * 1000, 1)
        row.cell(style='white-space:nowrap; text-align:right; font-weight: bold').text(f'{tm} ms')

    def print_protocol(self):
        table = ПлоскаяТаблица(self, 'table').mt(1)
        check = self.postgres.query(Check).get(self.check_id)
        #-------------------------
        check_log = None
        WORK_FOLDER = self.work_folder(check)
        file = os.path.join(WORK_FOLDER, f'{check.ID}.accept.log') 
        if os.path.isfile(file):
            with open(file, 'r') as f:
                check_log = json.load(f)
        #-------------------------
        #check_log = self.get_log(check)
        if check_log is None:
            table.row().cell().text(f'НЕТ ДАННЫХ {self.check_id} : {file}')
            return

        START, STOP = check.get_start_stop(self.account_id)
        previous = START
        row = table.row()
        p = row.cell().text_block()
        p.text('НАЧАЛО&nbsp;')
        p.href('запрос', 'show_xml_file', {'xml_file' : self.xml_file(check)}, new_window=True) 
        row.text(f'{START}')
        row.text('')
        for r in check_log:
            row = table.row()
            dt, operation, msg = Check.read_log_record(r)
            action_id = self.action_operation(operation)
            if action_id is not None:
                with sqlite3.connect(DISCOUNT_DB(self.account_id)) as conn:
                    cur = conn.cursor()
                    action = Action.get(cur, action_id)
                row.text(f'{action_id} : {action.полное_наименование(self.action_types)}')
            else:
                row.text(Check.operation_name(operation))
            row.text(msg)
            delta = dt - previous
            tm = round(delta.total_seconds() * 1000, 1)
            previous = dt
            row.cell(style='white-space:nowrap; text-align:right').text(f'{tm} ms')

        row = table.row()
        delta = STOP - previous
        tm = round(delta.total_seconds() * 1000, 1)
        row.text('СОХРАНЕНИЕ ДАННЫХ')
        row.cell()
        row.cell(style='white-space:nowrap; text-align:right').text(f'{tm} ms')

        row = table.row()
        row.text('ОКОНЧАНИЕ')
        row.text(f'{STOP}')
        delta = STOP - START
        tm = round(delta.total_seconds() * 1000, 1)

        row.cell(style='white-space:nowrap; text-align:right; font-weight: bold').text(f'{tm} ms')

    def print_products(self):
        comment = self.text_block('comment')
        comment.text('')
        table = self.Table('table').mt(1)
        table.column().text('ШК')
        table.column().text('Код')
        table.column().text('Тип')
        table.column().text('Наименование')
        table.column(align='right').text('Кол-во')
        table.column(align='right').text('Розничная цена')
        table.column(align='right').text('Цена со скидкой')
        table.column(align='right').text('Сумма')
        table.column(align='right').text('Скидка')
        table.column(align='right').text('%')
        check = self.postgres.query(Check).get(self.check_id)
        LINES = check.lines
        if LINES is not None:
            for line in LINES:
                log.debug(f'line : {line}')
                PRODUCT_CODE = line[CheckLine.PRODUCT_CODE]
                BARCODE = line[CheckLine.BARCODE]
                QTY = line[CheckLine.QTY]
                FINAL_PRICE = round(line[CheckLine.FINAL_PRICE]/100, 2)
                PRICE = round(line[CheckLine.PRICE] / 100, 2)
                ACTIONS = line[CheckLine.ACTIONS]

                row = table.row(PRODUCT_CODE)
                if BARCODE:
                    row.text(f'{BARCODE}')
                else:
                    row.text('')
                row.text(PRODUCT_CODE)
                row.text(line[CheckLine.PRODUCT_TYPE])
                row.text(self.get_product_name(PRODUCT_CODE))
                row.cell(align='right').text(QTY)
                
                if ACTIONS is not None:
                    row.cell(align='right').text(PRICE)
                    row.cell(align='right').text(FINAL_PRICE)
                    сумма = round(PRICE * QTY, 2)
                    сумма_со_скидкой = round(FINAL_PRICE * QTY, 2)
                    row.cell(align='right').text(f'{сумма_со_скидкой}').tooltip(f'розничная сумма {сумма}')

                    общая_скидка = сумма - сумма_со_скидкой
                    общая_сумма = (общая_скидка + сумма_со_скидкой)
                    процент = round(общая_скидка / общая_сумма * 100, 2)
                    row.cell(align='right', style='color:#CC6600').text(round(общая_скидка, 3))
                    row.cell(align='right').text(f'{процент}%')
                    #action_id = line.calc_info.action_id
                    #action = Action.get(self.cursor, action_id)
                    #action_type = self.action_types[action.type]
                    #row.text(f'{action_type.description()} {action.description}')
                else:
                    row.cell(align='right').text(PRICE)
                    row.cell(align='right').text(FINAL_PRICE)
                    row.text(FINAL_PRICE * QTY)
                    row.text('')
                    row.text('')
                    #row.text('')

                if ACTIONS:
                    for action in ACTIONS:
                        row = table.row()
                        row.text('')
                        row.text('')
                        row.text('')
                        ACTION_ID = action[Check.LINE_ACTION_ID]
                        DISCOUNT = round(action[Check.LINE_ACTION_DISCOUNT]/100,2)
                        #CARD_ID = action[Check.LINE_ACTION_CARD_ID]
                        #POINTS = action[Check.LINE_ACTION_POINTS]
                        action = Action.get(self.cursor, ACTION_ID)
                        #action_type = self.action_types[action.type]
                        row.cell().html(f'<span style="font-size:small;color:gray">{action.полное_наименование(self.action_types)}<span>')
                        скидка_по_акции = DISCOUNT
                        #row.text('')
                        row.text('')
                        row.text('')
                        row.text('')
                        row.text('')
                        row.cell(align='right').html(f'<span style="font-size:small;color:gray">{round(скидка_по_акции,3)}<span>')
                        процент = скидка_по_акции / общая_сумма
                        row.cell(align='right').html(f'<span style="font-size:small;color:gray">{процент:.1%}<span>')

    def print_payments(self):
        PAYMENTS = self.postgres.query(Check.payments).filter(Check.ID == self.check_id).scalar()
        table = self.Table('table').mt(1)
        if PAYMENTS is not None:
            for payment in PAYMENTS:
                row = table.row()
                row.text(payment[Check.TOTAL])
                params = []
                TYPE = payment[Check.PAYMENT_TYPE]
                if TYPE == Check.PAYMENT_CASH:
                    row.text('НАЛИЧНЫЕ')
                elif TYPE == Check.PAYMENT_GIFT:
                    row.text('ПОДАРОЧНАЯ КАРТА')
                    CARD_ID = payment.get(Check.PAYMENT_CARD_ID)
                    params.append(f'карта {CARD_ID}')
                elif TYPE == Check.PAYMENT_CARD:
                    row.text('КАРТА')
                    CARD_ID = payment.get(Check.PAYMENT_CARD_ID)
                    params.append(f'карта {CARD_ID}')
                    TERMINAL_ID = payment.get(Check.PAYMENT_TRMINAL_ID)
                    params.append(f'терминал {TERMINAL_ID}')
                    TRANS_NO = payment.get(Check.PAYMENT_TRANS_NO)
                    params.append(f'номер транзакции {TRANS_NO}')
                else:
                    row.text(TYPE)
                row.text(' ,'.join(params))
    
    def open(self):
        check = self.postgres.query(Check).get(self.check_id)
        if check is None:
            Title(self, f'Неизвестный чек "{self.check_id}"')
            #p = self.text_block().style('colot:red')
            #p.text('НЕТ ДАННЫХ ПО ЧЕКУ ')
            #p = self.text_block()
            #p.text(f'{self.check_id}')
            return 
 
        title = Title(self, f'Чек "{check.check_no}", Фискальный регистратор "{check.pos_id}", Смена "{check.session_id}"')
        #check_no = self.check.params.get('CHECK_ID')
        #self.title(f'Чек "{check.check_no}", Фискальный регистратор "{check.pos_id}", Смена "{check.session_id}"')
        if check.is_test:
            IconButton(title, None, 'fiber_manual_record', style='color:orange').tooltip('КОНТРОЛЬНЫЙ ЧЕК')

            #about.newline(style='margin-bottom:1rem;')
            #about.text(f'КОНТРОЛЬНЫЙ ЧЕК')
            #about.newline()

        #about = self.text_block('about')
        about = Text(self, 'about')
        #if check.is_test:
        #    about.newline(style='margin-bottom:1rem;')
        #    about.text(f'КОНТРОЛЬНЫЙ ЧЕК')
        #    about.newline()
        TOTAL = check.total
        about.text(f'Дата {check.check_date}')
        about.text(f', Подразделение {check.dept_code}')
        about.text(f', Сумма {TOTAL}')
        about.newline()
        about.text(f'Идентификатор чека "{check.ID}"')
        about.newline()
        FP = check.params.get('FP')
        FD = check.params.get('FD')
        about.text(f'Признак фискального документа "{FP}"')
        about.text(f', Номер фискального документа "{FD}"')
        URL_EGAIS = check.params.get('URL_EGAIS')
        if URL_EGAIS is not None and URL_EGAIS != '':
            about.newline()
            about.text(f'Ссылка на систему учета алкоголя')
            about.href(f' {URL_EGAIS}', URL_EGAIS)
        
        ORDER_ID = check.params.get('ORDER_ID')
        ORDER_TYPE = check.params.get('ORDER_TYPE')
        if ORDER_ID is not None and ORDER_ID != '':
            about.newline()
            about.text(f'Данный чек создан на основании заказа "{ORDER_ID}/{ORDER_TYPE}"')
        about.newline()
        схема_ID = check.params.get('schema_id')
        схема = ДисконтнаяСхема.get(self.cursor, схема_ID)
        наименование = схема.наименование if схема is not None else схема_ID
        about.text(f'''Дисконтная схема "{наименование}", версия "{check.params.get("VERSION")}"''')

        fs_check_tabs.print(self)
