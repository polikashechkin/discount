import sqlite3, json, datetime, re, arrow

from domino.pages import Title, Text, Table, Rows, Button, IconButton, TextWithComments
#from domino.page import Page, BOOTSTRAP4, MDL
#from domino.page import Page, BOOTSTRAP4, MDL
from domino.page_controls import Кнопка, TabControl, ПрозрачнаяКнопка, КраснаяКнопка, ПлоскаяТаблица
from domino.tables.postgres.dept import Dept
from domino.core import log
from discount.core import DISCOUNT_DB
import discount.series
#from discount.cards import Card, CardLog
from domino.tables.postgres.discount_card import DiscountCard as Card
from domino.tables.postgres.discount_cardlog import DiscountCardLog as CardLog
from discount.series import Series
from action_types.action_page import CheckButton
from discount.page import DiscountPage as BasePage
#from discount.dept_sets import Подразделение
from domino.tables.postgres.dept import Dept
from grants import Grants

tabs = TabControl('tab_control', mt=1)
#tabs.append('tab_info', 'Общая информация'.upper(), 'print_info')
tabs.append('tab_form', 'Персональные данные'.upper(), 'print_form', visible='is_personal_card')
tabs.append('tab_log', 'Операции с картой'.upper(), 'print_card_log')
tabs.append('tab_checks', 'Покупки'.upper(), 'print_checks', visible='is_personal_card')
  
class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request, controls=[tabs])
        self.account_id = self.request.account_id()
        self.card_id = self.attribute('card_id')
        self._connection = None
        self._cursor = None
        #self._card = None
        self._series = None
        self._card = None
    
    @property
    def card(self):
        if self._card == None:
            self._card = Card.find(self.postgres, self.card_id)
            #log.debug(self._card)
        return self._card
    
    def __getattr__(self, name):
        if name == 'series':
            with sqlite3.connect(DISCOUNT_DB(self.account_id)) as conn:
                value = Series.get(conn.cursor(), self.card.TYPE)
        elif name == 'card_class':
            value = self.application['card_types'][self.series.type]
        else:
            return super().__getattr__(name)
        self.__dict__[name] = value
        return value
    
    def get_card_type(self):
        with sqlite3.connect(DISCOUNT_DB(self.account_id)) as conn:
            series = Series.get(conn.cursor(), self.card.TYPE)
        return self.application['card_types'][series.type]

    @property
    def card_type(self):
        return self.application['card_types'][self.series.type]
    @property
    def тип_карты(self):
        return self.series
    @property
    def connection(self):
        if self._connection is None:
            self._connection = self.application.account_database_connect(self.account_id)
        return self._connection
    @property
    def cursor(self):
        if self._cursor is None:
            self._cursor = self.connection.cursor()
        return self._cursor
    #@property
    #def карта(self):
    #    return self.card
 
    #=============================================
    # ПЕРСОНАЛЬНЫЕ ДАННЫЕ
    #=============================================
    def print_form(self):
        top_toolbar = self.Toolbar('top_toolbar')
        card = self.card
        table = ПлоскаяТаблица(self, 'tab_table').mt(2)\
            .cls('table-hover', False)
        p = table.row().cell().toolbar()
        p.item(width=20).input(label='Фамилия', name='user_surname', value=card.фамилия)
        p.item(ml=1).input(label='Имя', name='user_name', value=card.имя)
        p.item(ml=1, width=20).input(label='Отчество', name='user_patronymic', value=card.отчество)
        p = table.row().cell().toolbar()
        if card.день_рождения is not None:
            год = card.день_рождения.year
            месяц = card.день_рождения.month
            день = card.день_рождения.day
        else:
            год = ''
            месяц = ''
            день = ''

        p.item().input(label='День рождения', name='день_рождения', type='date', 
            value=card.день_рождения)

        #p.item(width=6).input(label='Год', name='year', type='number', value=год)
        #p.item(ml=1, width=6).input(label='Месяц', name='month', type='number', value=месяц)
        #p.item(ml=1, width=6).input(label='День', type='number', name='day', value=день)
        пол = card.пол if card.пол is not None else ''
        p.item(ml=1, width=10).select(label='Пол', name='sex', value=пол, options=[['',''], ['1', 'МУЖСКОЙ'], ['0', 'ЖЕНСКИЙ']])
        #p.item(ml=1, width=10).input(label='Ключевое слово', name='password', value=card.info.get('password', ''))
        p = table.row().cell().toolbar()#style('align-items:flex-end')
        p.item().Text().style('font-size:1.7rem; color:lightgray;white-space:nowrap').text('+7&nbsp;')
        p.item().input(label='Телефон в формате XXX XXX XXXX', name='phone', value=card.телефон_для_ввода)
        p.item(ml=1, width=20).input(label = 'Электронная почта', name='email', value=card.email)
        p = table.row().cell().toolbar().style('align-items:center')
        #CheckButton('use_sms')(p.item(), card.info.get('use_sms', '') == '1', {'card_id':card.id})
        p.item().Text().text('Согласен на рассылку СМС сообщений')
        p.item( ml = 1).select(name='use_sms', value=card.рассылка_по_смс, options=[['1', 'ДА'], ['0', 'НЕТ']])
        #CheckButton('use_email')(p.item(ml=2), card.info.get('use_email', '') == '1', {'card_id':card.id})
        #p = table.row().cell().toolbar()
        p.item(ml=1).Text().text('Согласен на рассылку по электронной почте')
        p.item(ml=1).select(name='use_email', value=card.рассылка_по_почте, options=[['1', 'ДА'], ['0', 'НЕТ']])

        toolbar = self.toolbar('tab_toolbar')
        КраснаяКнопка(toolbar, 'Изменить персональные данные').onclick('.save', forms=[table])
    def save(self):
        card = self.card
        card.имя = self.get('user_name', '')
        card.фамилия = self.get('user_surname', '')
        card.отчество = self.get('user_patronymic', '')
        try:
            день_рождения = self.get('день_рождения')
            if день_рождения is None or день_рождения.strip() == '':
                card.день_рождения = None
            else:
                card.день_рождения = arrow.get(день_рождения).datetime
        except BaseException as ex:
            #raise Exception('Неправильно задан день рождения')
            self.error(f'Неправильно задан день рождения "{день_рождения}" : {ex}')
            return
        card.пол = self.get('sex')
        card.info['password'] = self.get('password')

        телефон_ввод = self.get('phone')
        if телефон_ввод is None or телефон_ввод.strip() == '':
            card.phone = None
        else:
            телефон = Card.преобразовать_к_нормальному_виду(телефон_ввод)
            if телефон is None:
                self.error(f'''Неправильный номер телефона "{телефон_ввод}"''')
                return
            else:
                card.phone = телефон

        card.email = self.get('email')
        card.рассылка_по_смс = self.get('use_sms')
        card.рассылка_по_почте = self.get('use_email')
        with self.pg_connection:
            card.update(self.engine)
            self.message(f'Данные изменены {card.phone}')
        self.print_form()

    def is_personal_card(self):
        return self.тип_карты.это_персональная_карта
    # =====================================
    # ИСТОРИЯ ОПЕРАЦИЙ
    # =====================================

    def enable(self):
        #card = self.postgres.query(Card).get(self.card_id)
        cardlog = CardLog(self.card.ID, CardLog.ENABLE)
        cardlog.user_name = self.user_name
        cardlog.STATE = Card.ACTIVE
        self.postgres.add(cardlog)

        self.card.state = Card.State.ACTIVE
        self.card.activation_date = datetime.datetime.now()
        self.print_title()
        self.print_card_info()
        self.print_card_log()

    def disable(self):
        #card = self.postgres.query(Card).get(self.card_id)
        cardlog = CardLog(self.card.ID, CardLog.DISABLE)
        cardlog.STATE = Card.DISABLED
        cardlog.user_name = self.user_name
        self.postgres.add(cardlog)

        self.card.state = Card.State.DISABLED
        self.card.deactivation_date = datetime.datetime.now()

        self.print_title()
        self.print_card_info()
        self.print_card_log()

    def change_card_params(self):
        points = self.get('points')
        discount = self.get('discount')
        #card = self.postgres.query(Card).get(self.card_id)
        card_log = None
        if points:
            points = round(float(points), 2)
            if points < 0:
                self.error(f'Количество балло не может быть меньше 0')
                return 
            card_log = CardLog(self.card_id, CardLog.CHANGE_PARAM)
            card_log.points = points
        if discount:
            discount = round(float(discount), 2)
            if discount < 0.0 or discount > 100.0:
                self.error('Скидка должна быть в диапазоне от 0% до 100%')
                return
            if card_log is None:
                card_log = CardLog(self.card_id, CardLog.CHANGE_PARAM)
            card_log.discount = discount
        if card_log is None:
            self.error(f'Не задан ни один параметр')
            return
        card_log.user_name = self.user_name
        card_log.creation_date = datetime.datetime.now()
        self.postgres.add(card_log)
        if card_log.points is not None:
            self.card.points = card_log.points
        if card_log.discount is not None:
            self.card.discount = card_log.discount
        #self.card.установить_параметры(self.engine, points, discount, self.user_name)
        #self.engine.pg_connection.commit()
        self.print_card_info()
        self.print_card_log()
        self.message(f'Баллы : {points}, Скидка {discount}')

    def print_card_log(self):
        card = self.card
        card_type = self.get_card_type()

        top_toolbar = self.Toolbar('top_toolbar')
        if card_type.это_персональная_карта:
            if Grants.BOSS in self.grants or Grants.ASSISTANT:
                top_toolbar.item(ml='auto').input(label = 'Скидка (%)', name='discount', type='number').width(5)
                top_toolbar.item(ml=0.5).input(label = 'Баллы', name='points', type='number').width(7)
                Кнопка(top_toolbar.item(ml=0.5), 'Изменить параметры карты').onclick('.change_card_params', forms=[top_toolbar])
                if card.это_активная_карта:
                    Кнопка(top_toolbar.item(ml=0.5), 'Заблокировать карту', ml='auto').onclick('.disable')
                elif card.это_заблокированная_карта:
                    Кнопка(top_toolbar.item(ml=0.5), 'Разблокировать карту', ml='auto').onclick('.enable')
        table = self.Table('tab_table')
        toolbar = self.toolbar('tab_toolbar')

        table.mt(1)

        table.column()
        table.column().text('Дата')
        table.column('Операция')
        if card_type.это_подарочная_карта:
            table.column('ДС')
        elif card_type.это_купон:
            table.column('Баллы')
        else:
            table.column('Баллы')
            table.column('Скидка')
        #table.column('')
        table.column().text('Подразделение')
        table.column('Оператор')
        table.column('Чек')
        #if Grant.SYSADMIN in self.grants:
        #    table.column('Технические подробности')

        #cardlogs = CardLog.findall(self.engine, 'card_id=%s order by id desc', [self.card.ID])
        cardlogs = self.postgres.query(CardLog, Dept).outerjoin(Dept, Dept.id == CardLog.dept_code).filter(CardLog.card_id == self.card.ID).order_by(CardLog.ID.desc()).limit(1000)
        for cardlog, dept in cardlogs:
            row = table.row(cardlog.ID)
            cell = row.cell(width=2)
            card_state = cardlog.STATE
            if card_state:
                if card_state == Card.DISABLED:
                    cell.glif('circle', style="color:red; -font-size:0.7rem")
                elif card_state == Card.ACTIVE:
                    cell.glif('circle', style="color:green; -font-size:0.7rem")

            row.cell(style='white-space:nowrap').text(f'{cardlog.creation_date.date()}')
            cell = row.cell()
            if cardlog.comment:
                TextWithComments(cell, cardlog.operation_name, [cardlog.comment])
            else:
                cell.text(cardlog.operation_name)
            if card_type.это_подарочная_карта:
                cash = cardlog.cash
                cell = row.cell()
                if cash is not None:
                    card = round(cash, 2)
                    if cash > 0.0:
                    
                        cell.text(f'+{cash}')
                    else:
                        cell.text(f'{cash}')
            elif card_type.это_купон:
                self.print_points(row, cardlog)
            else:
                self.print_points(row, cardlog)
                row.cell().text(f'{cardlog.discount} %' if cardlog.discount else '')

            cell  = row.cell()
            #if dept:
            #    cell.text(f'{cardlog.dept_code} : {dept.name}')
            #else:
            cell.text(cardlog.dept_code)

            row.cell().text(cardlog.user_name)

            check_id = cardlog.check_id
            #check_no = cardlog.check_no
            cell = row.cell(style='white-space:nowrap')
            if check_id is not None:
                #if check_no is None or check_no.strip() == '':
                    #check_no = 'чек'
                cell.href('чек', 'pages/fs_check', {'check_id':check_id})
            #№else:
            #    pass
                #row.cell().text(check_no)
            
            #if Grant.SYSADMIN in self.grants:
            #    row.cell().text(f'{cardlog.info}')
   
    def print_points(self, row, cardlog):
        cell = row.cell(align='right')
        if cardlog.points:
            points = round(cardlog.points, 2)
            if points > 0:
                cell.text(f'+{points}')
            else:
                cell.text(f'{points}')
    
    
    def печать_даты(self, row, date):
        try:
            date = arrow.get(date)
            row.cell().text(date.format('YYYY-MM-DD'))
        except:
            row.cell()
    #=============================================
    # ПОКУПКИ (ЧЕКИ)
    #=============================================
    def print_checks(self):
        top_toolbar = self.Toolbar('top_toolbar')
        table = self.Table('tab_table')
        toolbar = self.toolbar('tab_toolbar')
        table.mt(1)
        table.column('Дата чека')
        table.column('Тип')
        table.column('Подразделение')
        table.column('ФР')
        table.column('Смена')
        table.column('Номер')
        #table.column('Кассир')
        table.column('Сумма')
        sql = '''
            SELECT 
                discount_check.ID, 
                discount_check.type, 
                discount_check.dept_code, 
                discount_check.check_date,
                discount_check.total, 
                discount_check.pos_id, 
                discount_check.session_id, 
                discount_check.check_no,
                dept.name
            FROM discount_check LEFT OUTER JOIN dept ON (discount_check.dept_code = dept.ID)
            where discount_check.card_id=%s 
            order by discount_check.check_date desc limit 100
        '''
        self.pg_cursor.execute(sql, [self.card_id])
        for ID, TYPE, DEPT_CODE, CHECK_DATE, TOTAL, POS_ID, SESSION_ID, CHECK_NO, DEPT_NAME in self.pg_cursor:
            row = table.row(ID)
            row.cell().text(CHECK_DATE)
            row.cell().text('покупка' if TYPE == 0 else 'возврат')
            row.cell().text(DEPT_NAME)
            row.cell().text(POS_ID)
            row.cell().text(SESSION_ID)
            row.cell().text(CHECK_NO)
            row.cell().text(TOTAL)
            row.cell().href('чек', 'pages/fs_check', {'check_id':ID})

    # =====================================
    # INFO
    # =====================================
    def печать_показателя(self, table, наименование, значение):
        row = table.row()
        row.cell().text(наименование)
        row.cell().text(значение)
        
    def __print_info(self):
        card = self.card
        card_type = self.get_card_type()

        top_toolbar = self.Toolbar('top_toolbar')
        about = ПлоскаяТаблица(self, 'tab_table').mt(1).cls('table-hover table-sm table-borderless')
        toolbar = self.toolbar('tab_toolbar').mt(1)

        self.печать_показателя(about, f'Идентификатор карты (код на магнитной полосе)', card.ID)
        self.печать_показателя(about,'Состояние', card.state_name.upper())
        dept_code = card.dept_code
        if dept_code is not None:
            dept = self.postgres.query(Dept).get(dept_code)
            if dept:
                наименование = dept.name
            self.печать_показателя(about, f'Подразделение', f'{card.dept_code} {наименование}')
        if card.activation_date is not None:
            self.печать_показателя(about,'Дата активации', f'{card.activation_date}')
        exp_date = card.exp_date
        if exp_date is not None:
            self.печать_показателя(about, f'Строк действия', f'{exp_date}')
        #self.печать_показателя(about,'', '')
      
        if card_type.это_персональная_карта:
            self.печать_показателя(about,'Баллы', card.points)
            if card.discount:
                self.печать_показателя(about,'Скидка', f'{card.discount}%')
            params = []
            params.append(f'сумма покупок {card.total}')
            if card.входящая_сумма_покупок:
                params.append(f'(в т.ч входящая сумма {card.входящая_сумма_покупок})')
            params.append(f'количество покупок {card.checks}')
            if card.входящее_количество_покупок:
                params.append(f'(в т.ч. входящее количество {card.входящее_количество_покупок})')
            if card.checks:
                params.append(f'cредний чек {round(card.total / card.checks, 2)}')
            self.печать_показателя(about, 'Использование карты', ', '.join(params))

            параметры = []
            if card.дата_последней_покупки:
                параметры.append(f'Дата последней покупки "{card.дата_последней_покупки}"')
                параметры.append(f'Количество покупок за дату "{card.количество_покупок_за_последнюю_дату}"')
            else:
                параметры.append('НЕТ ПОКУПОК')
            
            self.печать_показателя(about,'Последняя покупка', ', '.join(параметры)) 
            
        elif card_type.это_подарочная_карта:
            if card.reusable:
                self.печать_показателя(about,'Многоразовая карта', 'Да')
            if card.STATE !=0:
                self.печать_показателя(about,'Остаток денежных средств (ДС)', card.cash)

        elif card_type.это_дисконтная_карта:
            if card.points:
                self.печать_показателя(about,'Баллы', card.points)
            if self.card.discount:
                self.печать_показателя(about,'Скидка', f'{card.discount}%')

        elif card_type.это_купон:
            if card.points:
                self.печать_показателя(about,'Баллы', card.points)

    # =====================================
    # TOOLBAR
    # =====================================
    def print_card_info(self):
        #card = self.postgres.query(Card).get(self.card_id)
        card = self.card
        card_type = self.get_card_type()

        if card_type.это_персональная_карта:
            info = []
            if card.ФИО != '':
                info.append(card.ФИО.upper())
            if card.phone:
                info.append(card.телефон_для_печати)

            #if card.is_test:
            #    info.append('Тестовая карта'.upper())

            if card.это_только_созданная_карта:
                info.append('Только созданная'.upper())
            elif card.это_активная_карта:
                pass
                #info.append('Активная'.upper())
            elif card.это_заблокированная_карта:
                info.append('Заблокирована'.upper())
            else:
                info.append('Неизвестное состояние'.upper())

            #p = self.toolbar('toolbar').mb(2).style('font-size:1.2rem')
            #p.item().Text().text(' ,'.join(info))
            p = self.text_block('header').style('font-size:1.2rem').mb(1)
            p.text(' ,'.join(info))

        p = self.text_block('about')
        params = []
        params.append(f'Код карты "{card.ID}"')
        params.append(f'Последнее изменение "{card.modify_date}"')
        #if card.is_test:
        #    params.append(f'Тестовая карта')
        p.newline()
        p.text(', '.join(params))

        params = []
        params.append(f'Состояние {card.state_name.upper()}')
        if card.activation_date is not None:
            params.append(f'Дата активации {card.activation_date}')
        if card.dept_code:
            params.append(f'Подразделение {card.dept_code}')
        exp_date = card.exp_date
        if exp_date is not None:
            params.append(f'Строк действия {exp_date}')
        if card.points:
            params.append(f'Баллы {round(card.points, 2)}')
        if card.discount:
            params.append(f'Скидка {round(card.discount, 2)}%')
        if card.reusable:
            params.append('Многоразовая карта')
        if card.cash:
            params.append(f'Остаток денежных средств (ДС) {round(card.cash, 2)}')

        p.newline()
        p.text(', '.join(params))

        #dept_code = card.dept_code
        #if dept_code is not None:
        #    наименование = Подразделение.наименование(self.engine.cursor, dept_code, '')
        #    self.печать_показателя(about, f'Подразделение', f'{card.dept_code} {наименование}')
        #self.печать_показателя(about,'', '')
      
        if card_type.это_персональная_карта:
            params = []
            params.append(f'Cумма покупок {card.total}')
            if card.входящая_сумма_покупок:
                params.append(f'(в т.ч входящая сумма {card.входящая_сумма_покупок})')
            params.append(f'Количество покупок {card.checks}')
            if card.входящее_количество_покупок:
                params.append(f'(в т.ч. входящее количество {card.входящее_количество_покупок})')
            if card.checks:
                params.append(f'cредний чек {round(card.total / card.checks, 2)}')
            #self.печать_показателя(about, 'Использование карты', ', '.join(params))

            #параметры = []
            if card.дата_последней_покупки:
                params.append(f'Дата последней покупки "{card.дата_последней_покупки}"')
                params.append(f'Количество покупок за дату "{card.количество_покупок_за_последнюю_дату}"')
            else:
                params.append('НЕТ ПОКУПОК')
            
            p.newline()
            p.text(', '.join(params))
            

    def print_title(self):
        alter_cards = []
        for alter_card in self.postgres.query(Card).filter(Card.pid == self.card.ID):
            alter_cards.append(alter_card.marknum)

        if len(alter_cards):
            title  = Title(self, f'{self.card.marknum} ({",".join(alter_cards)}), {self.series.полное_наименование}')
        else:
            title  = Title(self, f'{self.card.marknum}, {self.series.полное_наименование}')

        if self.card.state == Card.State.ACTIVE:
            IconButton(title, None, 'brightness_1', style='color:green')
        elif self.card.state == Card.State.DISABLED:
            IconButton(title, None, 'brightness_1', style='color:red')

        if self.card.is_test:
            IconButton(title, None, 'brightness_1', style='color:orange')


    # =====================================
    # OPEN
    # =====================================
    def open(self):
        self.print_title()
        self.print_card_info()
        tabs.print(self)

