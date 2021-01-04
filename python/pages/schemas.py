import flask, sqlite3, json, datetime, os
from domino.page_controls import print_std_buttons, СтандартныеКнопки
from domino.page_controls import ПрозрачнаяКнопка as КраснаяКнопка
from domino.core import log
from discount.schemas import ДисконтнаяСхема
from discount.dept_sets import DeptSet, DeptSetItem
from discount.core import DISCOUNT_DB, SCHEMES_FOLDER
from discount.page import DiscountPage as BasePage
from grants import Grants
from settings import MODULE_ID
from tables.postgres.protocol import Protocol
from . import Toolbar, Button

from tables.sqlite.schema import Schema

 # page, worker on_activate() import procs.cleaning Job() def  DOWORK()

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.BOSS = Grants.BOSS in self.grants
        self.ASSISTANT = Grants.ASSISTANT in self.grants
        if self.BOSS:
            self.ASSISTANT = True

    def проверить_дисконтную_схему(self, схема):
        '''
            # Предварительное создание всх рабочик рассчетчиков
            for action in Action.calc_actions(self.cursor, self.action_types):
                if action.status < 0:
                    continue
                action_type = self.action_types[action.type]
                action_type.Calculator(self.application, self.cursor, action)
            # Предварительное создание всеx послепродажных действия на предмет ошибок инициаоизации
            for action in Action.accept_actions(self.cursor, self.action_types):
                if action.status < 0:
                    continue
                action_type = self.action_types[action.type]
                action_type.Acceptor(self.application, self.cursor, action)
            # 
        '''
        pass

    def утвердить(self):
        try:
            for схема in self.дисконтные_схемы():
                self.проверка_дисконтной_схемы(схема)
            account_id = self.account_id
            src_path = DISCOUNT_DB(account_id)
            folder = SCHEMES_FOLDER(account_id)
            os.makedirs(folder, exist_ok=True)
            now = datetime.datetime.now()
            name = now.strftime('%Y-%m-%d %H:%M:%S')
            path = os.path.join(folder, name)
            with sqlite3.connect(path) as conn:
                conn.executescript(f'''
                attach database "{src_path}" as src;
                create table emission as select * from src.emission;
                create table actions as select * from src.actions where status >= 0;
                create table action_set as select * from src.action_set;
                detach src;
                ''')
            self.message(f'Набор акций утвержден и вступает в действие с {name}')
        except BaseException as ex:
            log.exception(f'утвердить')
            self.error(f'{ex}')

    #def копировать(self):
    #    схема_ID = self.get('схема_ID')
    #    with self.connection:
    #        схема = ДисконтнаяСхема.get(self.cursor, схема_ID)
    #       новая_схема = ДисконтнаяСхема()
    #       новая_схема.info = схема.info
    #        новая_схема.create(self.cursor)
    #    self.таблица_дисконтных_схем()
        
    def on_delete(self):
        SCHEMA_ID = self.get('schema_id')
        with self.connection:
            schema = ДисконтнаяСхема.get(self.cursor, SCHEMA_ID)
            if schema.набор_подразделений_ID is not None:
                DeptSet.deleteall(self.cursor, 'ID=?', [schema.набор_подразделений_ID])
                DeptSetItem.deleteall(self.cursor, 'dept_set=?', [schema.набор_подразделений_ID])
            self.cursor.execute('delete from schema where id=?', [SCHEMA_ID])
            path = os.path.join(SCHEMES_FOLDER(self.account_id), SCHEMA_ID)
            if os.path.isfile(path):
                os.remove(path)
                self.новая_версия()
        
        Grants.remove_object(self.postgres, SCHEMA_ID)

        self.table('table').row(SCHEMA_ID)
        msg = f'Удаление дисконтой схемы {SCHEMA_ID}'
        self.message(msg)
        Protocol.create(self.postgres, self.user_id, msg)

    def on_edit(self):
        SCHEMA_ID = self.get('schema_id')
        schema = ДисконтнаяСхема.get(self.cursor, SCHEMA_ID)
        row = self.Row('table', SCHEMA_ID)
        self.schema_row(row, schema, True)

    def on_cancel(self):
        SCHEMA_ID = self.get('schema_id')
        schema = ДисконтнаяСхема.get(self.cursor, SCHEMA_ID)
        row = self.Row('table', SCHEMA_ID)
        self.schema_row(row, schema)

    def on_save(self):
        SCHEMA_ID = self.get('schema_id')
        NAME = self.get('schema_name')
        with self.connection:
            schema = ДисконтнаяСхема.get(self.cursor, SCHEMA_ID)
            schema.наименование = NAME
            schema.update(self.cursor)
        row = self.Row('table', SCHEMA_ID)
        self.schema_row(row, schema)

    def новая_версия(self):
        now = datetime.datetime.now()
        VERSION = now.strftime('%Y-%m-%d %H:%M:%S')
        папка = SCHEMES_FOLDER(self.account_id)
        os.makedirs(папка, exist_ok=True)
        with open(os.path.join(папка, 'VERSION'), 'w') as f:
            f.write(VERSION)

    def дисконтные_схемы(self):
        return ДисконтнаяСхема.findall(self.cursor)
    
    def schema_row(self, row, schema, edit=False):
        SCHEMA_ID = str(schema.ID)
        ОСНОВНАЯ_СХЕМА = schema.ID == 0
        # дата утверждения
        cell = row.cell(width=2)
        дата_утверждения = ДисконтнаяСхема.дата_утверждения(self.account_id, schema.ID)
        if дата_утверждения is None:
            cell.icon_button('fingerprint', style='color:lightgray')\
                .tooltip(f'Схема НЕ утверждена')
        else:
            cell.icon_button('fingerprint', style='color:green')\
                .tooltip(f'Схема утверждена {дата_утверждения}')

        # наименование схемы
        cell = row.cell()
        if edit:
            cell.input(name='schema_name', value=schema.наименование)\
                .onkeypress(13, '.on_save', {'schema_id':SCHEMA_ID}, forms=[row])
        else:
            cell.href(schema.наименование, 'pages/schema.open', {'схема_ID':SCHEMA_ID})

        # подразделения
        cell = row.cell()
        if schema.набор_подразделений_ID is not None:
                подразделений = DeptSetItem.count(self.cursor, 'dept_set=?', [schema.набор_подразделений_ID])
                if подразделений == 0:
                    cell.style('color:red').href(f'ПОДРАЗДЕЛЕНИЙ НЕТ', 'pages/dept_set', {'набор_ID':str(schema.набор_подразделений_ID)}, style='color:red')
                else:
                    cell.href(f'ПОДРАЗДЕЛЕНИЙ {подразделений}', 'pages/dept_set', {'набор_ID':str(schema.набор_подразделений_ID)})

        # действия
        cell = row.cell(width=6)
        if edit:
            cell.icon_button('check', style='color:green').onclick('.on_save', {'schema_id':SCHEMA_ID}, forms=[row])
            cell.icon_button('close', style='color:gray').onclick('.on_cancel', {'schema_id':SCHEMA_ID} )
        else:
            if self.BOSS and not ОСНОВНАЯ_СХЕМА:
                cell.icon_button('edit', style='color:lightgray').onclick('.on_edit', {'schema_id':SCHEMA_ID} )
                cell.icon_button('close', style='color:red').onclick('.on_delete', {'schema_id':SCHEMA_ID} )


    def таблица_дисконтных_схем(self):
        table = self.Table('table').mt(1)
        with self.connection:
            self.перенумеровать()
        for схема in self.дисконтные_схемы():
            if self.ASSISTANT \
                    or self.grants.match(Grants.DS_MANAGER, схема.ID) \
                    or self.grants.match(Grants.DS_ASSISTANT, схема.ID) \
                    or self.grants.match(Grants.DS_WATCHING, схема.ID) :
                row = table.row(схема.ID)
                self.schema_row(row, схема)

    def создать(self):
        with self.connection:
            набор = DeptSet()
            набор.CLASS = 1
            набор.create(self.cursor)

            схема = ДисконтнаяСхема()
            схема.наименование = 'Дополнительная схема'
            схема.набор_подразделений_ID = набор.ID
            схема.pos = 1
            схема.create(self.cursor)

            набор.дисконтная_схема_ID = схема.ID
            набор.update(self.cursor)
        
        base_schema = self.sqlite.query(Schema).get(0)
        schema = self.sqlite.query(Schema).get(схема.ID)
        schema.bigsize = base_schema.bigsize
        self.sqlite.commit()

        self.таблица_дисконтных_схем()
        Protocol.create(self.postgres, self.user_id, f'Создание дисконтой схемы {схема.ID}', schema_id=схема.ID)

    def перенумеровать(self):
        num = 0
        for схема in self.дисконтные_схемы():
            num += 10
            схема.позиция = num
            схема.update(self.cursor)

    def open(self):
        self.title(f'Дисконтные схемы')
        x = self.text_block()
        x.text('''
        Каждая дисконтная схема характеризуется набором подразделений для 
        которых она применяется. ОСНОВНАЯ СХЕМА применяется тогда, когда подразделение в чеке
        на связано ни с одной дисконтной схемой. ОСНОВНАЯ СХЕМА существует всегда, дополнительные схемы 
        можно создавать и удалять. 
        ''')
        if self.BOSS:
            toolbar = self.toolbar().mt(1)
            Button(toolbar.item(), 'Создать дополнительную дисконтную схему').onclick('.создать')
        self.таблица_дисконтных_схем()


