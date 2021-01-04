import json, sqlite3, datetime, arrow, re
from domino.core import log, Bool
from discount.core import DISCOUNT_DB, MODULE_ID
from discount.actions import Action, ActionSetItem, ДеньНедели
from discount.product_sets import ProductSet
from domino.page import Page, PageControl
from domino.page_controls import TabControl, ПрозрачнаяКнопка as КраснаяКнопка, КраснаяКнопкаВыбор, СтандартныеКнопки, ПлоскаяТаблица
from domino.page_controls import print_check_button, print_std_buttons
from domino.page_controls import CheckButton, EditButton, CancelButton, SaveButton, DeleteButton
from domino.page_controls import ТабличнаяФорма
from domino.page_controls import Кнопка, КнопкаВыбор
from domino.page_controls import FormControl
from pages import IconButton, DeleteIconButton, Button
from discount.checks import TEXT_TEXT, TEXT_BOLD, TEXT_CODE, TEXT_EAN13
from discount.series import Series, ТипКарты
from discount.schemas import ДисконтнаяСхема

from grants import Grants
#from domino.databases.postgres import Postgres

from domino.tables.postgres.dept import Dept

from tables.sqlite.action_set_item import ActionSetItem as ActionSetItem_
from tables.sqlite.schema import Schema
from tables.sqlite.dept_set_item import DeptSetItem


# tab layout
TAB_TABLE = 'table'
TAB_TOOLBAR = 'tab_toolbar'
BASE_PARAMS_FORM = 'base_params_form'
TAB_ABOUT = 'tab_about'
#TAB_CONTAINER = 'tab_container'

class ОсновныеТовары:
    def __init__(self, id):
        self.id = id

    def __call__(self, page):
        fn = page.get('fn')
        if fn:
            getattr(self, fn)(page)
        else:
            self.print(page)

    def action_set_item_query(self, page):
        return page.sqlite.query(ActionSetItem_).filter(ActionSetItem_.action_id == page.action.ID)\
            .filter(ActionSetItem_.type_ == ActionSetItem_.ОСНОВНЫЕ_ТОВАРЫ)

    def print(self, page):
        page.text_block(TAB_ABOUT)
        self.print_toolbar(page)
        page.Table(BASE_PARAMS_FORM)
        self.print_table(page)

    def print_toolbar(self, page):
        toolbar = page.toolbar(TAB_TOOLBAR).mt(1)
        sets = set()
        for item in self.action_set_item_query(page):
            sets.add(item.set_id)

        #CLS = 'btn btn-outline-secondary'
        drop_down = Button(toolbar, 'Добавить набор')
        for ps in sorted(ProductSet.findall(page.cursor), key=lambda ps : f'{ps.description}'):
            if ps.CLASS == 0 and ps.ID not in sets:
                if ps.description is not None and ps.description.strip() != '':
                    drop_down.item(ps.description).onclick(f'.{self.id}', {'fn':'add','set_id':ps.ID})

        Button(toolbar,'Создать набор для акции', ml=0.5)\
            .onclick(f'.{self.id}', {'fn':'create'})

    def print_table(self, page):
        table = page.Table(TAB_TABLE).mt(0.5).css('table-borderless')
        for item in self.action_set_item_query(page):
            set_id = item.set_id
            row = table.row(set_id)
            #print_check_button(row, '', set.excluded, params={'set_id':set_id}, size='small', icon='times', cls='text-danger')
            ps = ProductSet.get(page.cursor, set_id)
            if ps.CLASS == 2:
                row.cell().text(ps.description)
            else:
                row.cell().href(ps.description, 'pages/product_set', {'set_id':set_id})
            DeleteIconButton(row.cell(width=2))\
                .onclick(f'.{self.id}', {'fn':'delete', 'set_id':set_id})

    def delete(self, page):
        set_id = page.get('set_id')
        self.action_set_item_query(page).filter(ActionSetItem_.set_id == int(set_id)).delete()
        page.sqlite.commit()
        self.print(page)

    def add(self, page):
        set_id = page.get('set_id')
        #набор = self.action.sets.create_set('основные_товары', set_id)
        page.sqlite.add(ActionSetItem_(action_id = page.action.ID, set_id = int(set_id), type_ = ActionSetItem_.ОСНОВНЫЕ_ТОВАРЫ))
        page.sqlite.commit()
        self.print(page)
        #self.message(f'{tax_by_products.sets}')

    def create(self, page):
        ps = ProductSet(CLASS=1)
        ps.info['action_id'] = page.action_id
        ps.info['description'] = 'Индивидуальный набор для акции'
        with page.connection:
            ps.create(page.cursor)
        page.sqlite.add(ActionSetItem_(action_id = page.action.ID, set_id = ps.ID, type_ = ActionSetItem_.ОСНОВНЫЕ_ТОВАРЫ))
        page.sqlite.commit()
        self.print(page)

ОСНОВНЫЕ_ТОВАРЫ = ОсновныеТовары('основные_товары')
#ОСНОВЫЕ_ТОВАРЫ(self)

class ActionTabControl(TabControl):
    def __init__(self):
        super().__init__('action_tabs', visible = 'tab_visible', наименование_закладки = 'наименование_закладки')
        self.append('base_params', 'Основные параметры', 'print_base_params_tab')
        self.append('params', 'Дополнительные условия', 'print_params')
        #self.append('исключенные_товары', 'Исключенные товары', 'excluded_products_tab')
        self.append('основные_товары', 'Наборы товаров', 'основные_товары')
        self.append('скидка_на_товары', 'Скидка на товары', 'print_tax_by_products')
        #self.append('реестр_цен', 'Цены', 'реестр_цен')
        self.append('percent_of_sum', 'Процент от суммы', 'print_percent_of_sum')
        #self.append('used_cards', 'Карты', 'print_used_cards')
        self.append('used_actions', 'Акции', 'print_used_actions')
        self.append('add_discount', 'Скложение скидок', 'print_add_discount')
        self.append('weekdays', 'Дни недели и время', 'print_weekdays')
        self.append('print', 'Печать', 'print_print_params')
 
base_action_tabs = ActionTabControl()

PERCENT_SCALE_SIZE = 'A3_size'
def PERCENT_NAME(i) : return f'A3_p{i}'
def SUM_NAME(i) : return f'A3_s{i}'

def get_dept_options(page, schema_id):
    #log.debug(f'get_dept_options(page, {schema_id}):')
    options = []
    schema = page.sqlite.query(Schema).get(schema_id)
    if schema is None:
        log.error(f'Не найдена схема {schema_id}')
        return options

    #log.debug(f'{schema}')
    
    if schema.id == 0: # основная схема
        #log.debug('BASE SCHEMA')
        all_codes = DeptSetItem.get_all_codes(page.sqlite)
        #log.debug(f'all_codes = {all_codes}')
        for dept in page.postgres.query(Dept).filter(Dept.id.notin_(all_codes)).order_by(Dept.name):
            options.append([dept.id, dept.name])
    else:
        #log.debug('NONE BASE SCHEMA')
        codes = schema.get_dept_codes(page.sqlite)
        #log.debug(f'codes = {codes}')
        for dept in page.postgres.query(Dept).filter(Dept.id.in_(codes)).order_by(Dept.name):
            options.append([dept.id, dept.name])
    return options

class PRINT_MODE(FormControl.Param):
    def __init__(self):
        super().__init__(Action.PRINT_MODE, 'Расположение печати в чеке', type='select')
        self.options = [
                [Action.print_mode_FOOTER, 'Печать сообщения в конце чека'],
                [Action.print_mode_HEADER, 'Печать сообщения в начале чека'],
                [Action.print_mode_COUPON, 'Печать в виде отрывного купона']
            ]
        self.default = Action.print_mode_FOOTER
        self.style = 'font-weight:bold'
        
    def get_value(self, page):
        return page.action.info.get(self.ID, self.default)

    def is_default(self, page):
        return self.get_value(page) == self.default

    def set_default(self, page):
        with page.connection:
            if self.ID in page.action.info:
                del page.action.info[self.ID]
                page.action.update(page.cursor)

    def save(self, page):
        value = page.get(self.ID)
        with page.connection:
            page.action.info[self.ID] = value
            page.action.update(page.cursor)

    def readonly(self, page):
        return page.READONLY

class Цифра_на_которую_оканчивается_цена(FormControl.Param):
    def __init__(self):
        super().__init__(Action.ЦИФРА_НА_КОТОРУЮ_ОКАНЧИВАЕТСЯ_ЦЕНА, 'Цифра на которую оканчивается цена', type='select')
        #self.undefined = 'ДЛЯ ВСЕХ ПОДРАЗДЕЛЕНИЙ'
        #self.style = 'font-weight:bold'
        self.options = []
        for i in range(10):
            self.options.append([str(i), str(i)])

    def get_value(self, page):
        return page.action.info.get(self.ID)

    def save(self, page):
        value = page.get(self.ID)
        with page.connection:
            page.action.info[self.ID] = value
            page.action.update(page.cursor)

    def readonly(self, page):
        return page.READONLY

class Подразделение(FormControl.Param):
    def __init__(self):
        super().__init__(Action.ПОДРАЗДЕЛЕНИЕ, 'Подразделение', type='select')
        self.undefined = 'АКЦИЯ ДЕЙСТВУЕТ ДЛЯ ВСЕХ ПОДРАЗДЕЛЕНИЙ'
        self.style = 'font-weight:bold'

    def get_value(self, page):
        return page.action.info.get(Action.ПОДРАЗДЕЛЕНИЕ, '')

    def get_options(self, page):
        return get_dept_options(page, page.action.схема_ID)
    
    def set_default(self, page):
        with page.connection:
            if self.ID in page.action.info:
                del page.action.info[self.ID]
                page.action.update(page.cursor)
    def save(self, page):
        value = page.get(self.ID)
        if value:
            with page.connection:
                page.action.info[self.ID] = value
                page.action.update(page.cursor)
        else:
            self.set_default(page)

    def readonly(self, page):
        return page.READONLY

class ФормулаВычисленияПодарка(FormControl.Param):
    def __init__(self):
        super().__init__('формула_вычисления_подарка', 'Формула вычисления подарка', type='select')
        self.options = [
            [2, '1+1 : При покупке 2-х товаров, один из них в подарок'.upper()],
            [3, '2+1 : При покупке 3-х товаров, один из них в подарок'.upper()],
            [4, '3+1 : При покупке 4-х товаров, один из них в подарок'.upper()],
            [5, '4+1 : При покупке 5 товаров, один из них в подарок'.upper()],
            [6, '5+1 : При покупке 6 товаров, один из них в подарок'.upper()]
            #[5, '4+1 : При покупке 5 товаров - один в подарок']
        ]

    def get_value(self, page):
        return page.action.формула_вычисления_подарка

    def save(self, page):
        with page.connection:
            page.action.формула_вычисления_подарка = page.get(self.ID)
            page.action.update(page.cursor)
    
    def readonly(self, page):
        return page.READONLY

class ДисконтнаяКарта(FormControl.Param):
    def __init__(self):
        super().__init__(Action.ДИСКОНТНАЯ_КАРТА, 'Дисконтная карта', type='select')

    def get_value(self, page):
        return page.action.info.get(Action.ДИСКОНТНАЯ_КАРТА, 0)
    
    def get_options(self, page):
        options = []
        for тип_карты in ТипКарты.findall(page.cursor):
            if тип_карты.это_дисконтная_карта or тип_карты.это_персональная_карта or тип_карты.это_купон:
                options.append([str(тип_карты.id), тип_карты.полное_наименование])
        return options
    
    def get_option_name(self, page, value):
        тип_карты = ТипКарты.get(page.cursor, value)
        if тип_карты is not None:
            return тип_карты.полное_наименование
        else:
            return f'{value}'

    def save(self, page):
        with page.connection:
            page.action.info[Action.ДИСКОНТНАЯ_КАРТА] = page.get(self.ID)
            page.action.update(page.cursor)

    def readonly(self, page):
        return page.READONLY

class ПроцентНачисленияБаллов(FormControl.Param):
    def __init__(self):
        super().__init__(Action.ПРОЦЕНТ_НАЧИСЛЕНИЯ_БАЛЛОВ, 'Базовый процент начисления', type='number')

    def get_value(self, page):
        return page.action.info.get(self.ID, 0.0)
    
    def save(self, page):
        with page.connection:
            page.action.info[self.ID] = float(page.get(self.ID))
            page.action.update(page.cursor)

    def readonly(self, page):
        return page.READONLY

class ОкруглениеБонуса(FormControl.Param):
    def __init__(self):
        super().__init__(Action.ОКРУГЛЕНИЕ_БОНУСА, 'Округление баллов', type='select')
        self.options=[
            (0, 'до копеек'.upper()),
            (100, 'до рублей'.upper())
        ]

    def is_default(self, page):
        return self.get_value(page) == 0

    def get_value(self, page):
        return page.action.info.get(self.ID, 0)

    def set_default(self, page):
        with page.connection:
            page.action.info[self.ID] = 0
            page.action.update(page.cursor)

    def save(self, page):
        with page.connection:
            page.action.info[self.ID] = int(page.get(self.ID))
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class ОкруглениеЦены(FormControl.Param):
    def __init__(self):
        super().__init__('округление_цены', 'Округление цены', type='select')
        self.options=[
            (100, 'до копеек'.upper()),
            (10000, 'до рублей'.upper()),
            (100000, 'до 10 рублей'.upper()),
            (1000000, 'до 100 рублей'.upper())
        ]

    def is_default(self, page):
        value = self.get_value(page)
        return not value or value == 100

    def get_value(self, page):
        return page.action.округление
    
    def set_default(self, page):
        with page.connection:
            page.action.округление = 100
            page.action.update(page.cursor)

    def save(self, page):
        with page.connection:
            page.action.округление = page.get(self.ID)
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class НаименованиеАкции(FormControl.Param):
    def __init__(self):
        super().__init__('description', 'Наименование')

    def get_value(self, page):
        return page.action.полное_наименование(page.action_types)
    
    def save(self, page):
        with page.connection:
            page.action.info['description'] = page.get(self.ID)
            page.action.update(page.cursor)
        page.print_title()
    def readonly(self, page):
        return page.READONLY

class Множитель(FormControl.Param):
    def __init__(self):
        super().__init__('множитель', 'Коеффициент умножения', type='number')

    def get_value(self, page):
        return page.action.info.get(Action.МНОЖИТЕЛЬ, 0)
    
    def save(self, page):
        with page.connection:
            page.action.info[Action.МНОЖИТЕЛЬ] = float(page.get(self.ID))
            page.action.update(page.cursor)
        page.print_title()
    def readonly(self, page):
        return page.READONLY

class Акция(FormControl.Param):
    def __init__(self):
        super().__init__('акция', 'Акция', type='select')

    def get_value(self, page):
        return page.action.акция
    
    def get_options(self, page):
        options = []
        схема_ID = page.action.схема_ID
        if схема_ID is None:
            return []
        схема = ДисконтнаяСхема.get(page.cursor, схема_ID)
        if схема is None:
            return []
        for n in range(0, схема.расчетные_акции.размер):
            action_id = схема.расчетные_акции.акция_ID(n)
            action = Action.get(page.cursor, action_id)

            action_type = page.action_types[action.type]
            if action_type.id == page.action_type.id:
                continue
            if action_type.CLASS == 0:
                name = action.полное_наименование(page.action_types)
                options.append([action.id, f'{action_id} {name}'])
        return options
    
    def get_option_name(self, page, value):
        action_ID = page.action.акция
        if action_ID is None:
            return f'<span style="color:red">НЕ ОПРЕДЕЛЕНА</span>'
        else:
            action = Action.get(page.cursor, action_ID)
            name = action.полное_наименование(page.action_types)
            return f'{action_ID} {name}'

    def save(self, page):
        with page.connection:
            page.action.info[Action.АКЦИЯ] = int(page.get(self.ID))
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class Validity(FormControl.Param):
    def __init__(self):
        super().__init__('validity', 'Период действия')

    def edit(self, page, cell):
        start_date = page.action.start_date
        end_date = page.action.end_date
        p = cell.toolbar()
        g = p.item().input_group()
        g.text('c')

        if start_date is None:
            if end_date is None:
                value = arrow.now()
            else:
                value = arrow.get(end_date)
        else:
            value = arrow.get(start_date)

        g.input(name='start', value=value.format("YYYY-MM-DDT00:00"), type='datetime-local')
        g = p.item().input_group()
        g.text('по')

        if end_date is None:
            if start_date is None:
                value = arrow.now()
            else:
                value = arrow.get(start_date)
        else:
            value = arrow.get(end_date)
        g.input(name='end', value=value.format("YYYY-MM-DDT00:00"), type='datetime-local')
    def is_default(self, page):
        start = page.action.start_date
        end = page.action.end_date
        return start is None and end is None
    def print(self, page, cell):
        start = page.action.start_date
        end = page.action.end_date
        txt = []
        if start is not None:
            if start.hour == 0 and start.minute == 0:
                txt.append(f'c {start.format("YYYY-MM-DD")}')
            else:
                txt.append(f'{start.format("YYYY-MM-DD HH:mm")}')
        if end is not None:
            if end.hour == 0 and end.minute == 0:
                txt.append(f'по {end.format("YYYY-MM-DD")}')
            else:
                txt.append(f'по {end.format("YYYY-MM-DD HH:mm")}')
        if len(txt) == 0:
            #cell.style('color:gray;')
            cell.text('ПОСТОЯННО ДЕЙСТВУЮЩАЯ АКЦИЯ')
        else:
            cell.text(' '.join(txt))
    def set_default(self, page):
        try:
            del page.action.info[Action.START_DATE]
        except:
            pass
        try:
            del page.action.info[Action.END_DATE]
        except:
            pass
        with page.connection:
            page.action.update(page.cursor)
    def save(self, page):
        start = page.get('start')
        page.action.info[Action.START_DATE] = start
        end = page.get('end')
        page.action.info[Action.END_DATE] = end
        if page.action.start_date is not None and page.action.end_date is not None:
            if page.action.start_date > page.action.end_date:
                raise Exception(f'Дата начала больше чем дата окончания')
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class ПериодДействияУпрощенный(FormControl.Param):
    def __init__(self):
        super().__init__('период_действия_упрощенный', 'Период действия')

    def edit(self, page, cell):
        start_date = page.action.start_date
        end_date = page.action.end_date
        p = cell.toolbar()
        g = p.item().input_group()
        g.text('c')

        if start_date is None:
            if end_date is None:
                value = arrow.now()
            else:
                value = arrow.get(end_date)
        else:
            value = arrow.get(start_date)

        g.input(name='start', value=value.format("YYYY-MM-DD"), type='date')
        g = p.item().input_group()
        g.text('по')

        if end_date is None:
            if start_date is None:
                value = arrow.now()
            else:
                value = arrow.get(start_date)
        else:
            value = arrow.get(end_date)
        g.input(name='end', value=value.format("YYYY-MM-DD"), type='date')
    def is_default(self, page):
        start = page.action.start_date
        end = page.action.end_date
        return start is None and end is None
    def print(self, page, cell):
        start = page.action.start_date
        end = page.action.end_date
        txt = []
        if start is not None:
            if start.hour == 0 and start.minute == 0:
                txt.append(f'c {start.format("YYYY-MM-DD")}')
            else:
                txt.append(f'{start.format("YYYY-MM-DD HH:mm")}')
        if end is not None:
            if end.hour == 0 and end.minute == 0:
                txt.append(f'по {end.format("YYYY-MM-DD")}')
            else:
                txt.append(f'по {end.format("YYYY-MM-DD HH:mm")}')
        if len(txt) == 0:
            #cell.style('color:gray;')
            cell.text('ПОСТОЯННО ДЕЙСТВУЮЩАЯ АКЦИЯ')
        else:
            cell.text(' '.join(txt))
    def set_default(self, page):
        try:
            del page.action.info[Action.START_DATE]
        except:
            pass
        try:
            del page.action.info[Action.END_DATE]
        except:
            pass
        with page.connection:
            page.action.update(page.cursor)
    def save(self, page):
        start = page.get('start')
        page.action.info[Action.START_DATE] = start
        end = page.get('end')
        page.action.info[Action.END_DATE] = end
        if page.action.start_date is not None and page.action.end_date is not None:
            if page.action.start_date > page.action.end_date:
                raise Exception(f'Дата начала больше чем дата окончания')
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class ПодарочныйКупон(FormControl.Param):
    def __init__(self):
        super().__init__(Action.ПОДАРОЧНЫЙ_КУПОН, 'Подарочный купон', type='select')

    def get_value(self, page):
        return page.action.info.get(Action.ПОДАРОЧНЫЙ_КУПОН)
    
    def get_options(self, page):
        options = []
        for тип_карты in ТипКарты.findall(page.cursor):
            if тип_карты.это_купон and тип_карты.gen_mode_random:
                options.append([str(тип_карты.id), тип_карты.полное_наименование])
        return options
    
    def get_option_name(self, page, value):
        try:
            тип_карты = ТипКарты.get(page.cursor, value)
            if тип_карты is not None:
                return тип_карты.полное_наименование
            else:
                return f'{value}'
        except:
            return f'<span style="color:red">НЕ ОПРЕДЕЛЕН</span>'

    def save(self, page):
        with page.connection:
            page.action.info[Action.ПОДАРОЧНЫЙ_КУПОН] = page.get(self.ID)
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class ПроцентОтПозиции(FormControl.Param):
    def __init__(self):
        super().__init__('процент_от_позиции', 'Процент скидки от позиции товара')

    def edit(self, page, cell):
        проценты = page.action.info.get(Action.ПРОЦЕНТ_ОТ_ПОЗИЦИИ)
        default = self.to_float(page.action.info.get(Action.ПРОЦЕНТНАЯ_СКИДКА), 0.0)
        if проценты is None:
            проценты = []
        p = cell.toolbar()
        for n in range(7):
            try:
                value = float(проценты[n])
            except:
                value = ''
            p.item(width=5).input(label=f'{n+1}-й товар', name=f'товар_{n}', value=value, type='number')

        p.item(width=5, ml=1).input(label=f'последующие', name=Action.ПРОЦЕНТНАЯ_СКИДКА, value=default, type='number')

    def print(self, page, cell):
        
        discounts = page.action.info.get(Action.ПРОЦЕНТ_ОТ_ПОЗИЦИИ)
        default = self.to_float(page.action.info.get(Action.ПРОЦЕНТНАЯ_СКИДКА), 0.0)
        count = None
        if discounts is not None:
            for pos in reversed(range(len(discounts))):
                discount = discounts[pos]
                if discount is not None:
                    #default = discount
                    count = pos + 1
                    break

        if count is None:
            cell.text('НЕОБХОДИМО ОПРЕДЕЛИТЬ').style('color:red')
        else:    
            msg = []
            for pos in range(count):
                discount = discounts[pos]
                msg.append(f'{pos + 1}-й товар {discount}%')
            msg.append(f'последующие товары {default}%')
            cell.text(' ,'.join(msg))

    def set_default(self, page):
        if Action.ПРОЦЕНТ_ОТ_ПОЗИЦИИ in page.action.info : 
            del page.action.info[Action.ПРОЦЕНТ_ОТ_ПОЗИЦИИ]
        if Action.ПРОЦЕНТНАЯ_СКИДКА in page.action.info : 
            del page.action.info[Action.ПРОЦЕНТНАЯ_СКИДКА]
        with page.connection:
            page.action.update(page.cursor)

    def save(self, page):
        discounts = []
        for pos in range(7):
            discounts.append(self.to_float(page.get(f'товар_{pos}')))
        
        # проверка правмльности задания
        # не должно быть "пустых" значений и значения должны быть в диапазоне 0 - 100
        next_exists = False
        for pos in reversed(range(7)):
            discount = discounts[pos]
            if discount is None:
                if next_exists:
                    raise Exception(f'Не задано значение скидки для {pos+1}-й позиции')
            else:
                if discount < 0.0 or discount > 100.0:
                    raise Exception(f'Не правильно задан процент для {pos+1}-й позиции')
                next_exists = True
        default = self.to_float(page.get(Action.ПРОЦЕНТНАЯ_СКИДКА), 0.0)
        if default < 0.0 or default > 100.0:
            raise Exception(f'Не правильно задан процент для последующих позиции')
        page.action.info[Action.ПРОЦЕНТ_ОТ_ПОЗИЦИИ] = discounts
        page.action.info[Action.ПРОЦЕНТНАЯ_СКИДКА] = default
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class ПроцентнаяСкидка(FormControl.Param):
    def __init__(self):
        super().__init__(Action.ПРОЦЕНТНАЯ_СКИДКА, 'Процент скидки', type='number')

    def print(self, page, cell):
        value = self.get_value(page)
        if value:
            cell.text(f'{value} %')
        else:
            cell.text(f'0 %')

    def get_value(self, page):
        return self.to_float(page.action.info.get(self.ID))

    def set_default(self, page):
        page.action.info[self.ID] = 0.0
        with page.connection:
            page.action.update(page.cursor)

    def save(self, page):
        page.action.info[self.ID] = self.to_float(page.get(self.ID))
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class Максимально_оплачиваемая_стоимость_чека(FormControl.Param):
    def __init__(self):
        super().__init__(Action.МАКСИМАЛЬНО_ОПЛАЧИВАЕМАЯ_СТОИМОСТЬ_ЧЕКА, 'Максимально оплачиваемая стоимость чека', type='number')

    def print(self, page, cell):
        value = self.get_value(page)
        if value > 0:
            cell.text(f'{value} %')
        else:
            cell.text(f'БЕЗ ОГРАНИЧЕНИЙ')

    def get_value(self, page):
        return self.to_float(page.action.info.get(self.ID, 99))

    def set_default(self, page):
        page.action.info[self.ID] = 99.0
        with page.connection:
            page.action.update(page.cursor)

    def save(self, page):
        value = self.to_float(page.get(self.ID))
        if value < 1 or value > 100:
            raise Exception(f'Недопустимое значение')
        page.action.info[self.ID] = value
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class НаборТоваров(FormControl.Param):
    def __init__(self, ID='набор_товаров', description='Набор товаров', SET=0, default_text=f'ВСЕ ТОВАРЫ, КРОМЕ ИСКЛЮЧЕННЫХ'):
        super().__init__(ID, description, type='select')
        self.SET = SET
        self.default_text = default_text
    def get_value(self, page):
        item = ActionSetItem.findfirst(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])
        return item.set_id if item is not None else None
    def is_personal_set(self, page):
        set_ID = self.get_value(page)
        if set_ID:
            ps = ProductSet.get(page.cursor, set_ID)
            if ps and ps.CLASS == 1:
                return True
        return False
    def get_options(self, page):
        schema_id = page.action.схема_ID
        options = []
        for ps in ProductSet.findall(page.cursor, 'CLASS = 0 and (schema_id=0 or schema_id=?)', [schema_id]):
            if ps.наименование and ps.наименование.strip():
                options.append([str(ps.ID), f'{ps.наименование}'])
        return options
    def print(self, page, cell):
        if self.is_personal_set(page):
            set_ID = self.get_value(page)
            cell.link(f'Индивидуальный набор {set_ID}')\
                .onclick('pages/product_set', {'set_id':f'{set_ID}'})
        else:
            super().print(page, cell)
    def editable(self, page):
        if self.is_personal_set(page):
            return False
        return True
    def get_option_name(self, page, value):
        if value is None :
            return self.default_text
        else:
            ps = ProductSet.get(page.cursor, value)
            if ps is None:
                return f'Неизвестный набор "{value}"'
            else:
                return ps.наименование
    def set_default(self, page):
        with page.connection:
            ActionSetItem.deleteall(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])
    def add(self, page):
        self.set_default(page)
        with page.connection:
            ps = ProductSet(CLASS = 1, TYPE = 0)
            ps.наименование = 'Индивидуальный набор'
            ps.create(page.cursor)
            item = ActionSetItem(TYPE = self.SET, action_id = page.action.ID, set_id=ps.ID)
            item.create(page.cursor)
    def add_tooltip(self, page):
        if not self.is_personal_set(page):
            return 'Создать индивидуальный набор для акции'.upper()
        else:
            return None
    def save(self, page):
        set_id = self.to_int(page.get(self.ID))
        with page.connection:
            if set_id is None:
                ActionSetItem.deleteall(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])
            else:
                item = ActionSetItem.findfirst(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])
                if item is None:
                    item = ActionSetItem(TYPE = self.SET, action_id= page.action.id, set_id = set_id)
                    item.create(page.cursor)
                else:
                    item.set_id = set_id
                    item.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class ОбязательныйНаборТоваров(FormControl.Param):
    def __init__(self, ID = 'обязательный_набор_товаров', description = 'Набор товаров', SET = 0):
        #super().__init__('обязательный_набор_товаров', 'Набор товаров', type='select')
        super().__init__(ID, description, type='select')
        self.SET = SET
    def get_value(self, page):
        item = ActionSetItem.findfirst(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])
        return item.set_id if item is not None else None
    def get_options(self, page):
        schema_id = page.action.схема_ID
        options = []
        #options.append(['', 'ВСЕ ТОВАРЫ'])
        for ps in ProductSet.findall(page.cursor, 'CLASS = 0 and (schema_id = 0 or schema_id=?)', [schema_id]):
            if ps.наименование and ps.наименование.strip():
                options.append([str(ps.ID), f'{ps.наименование}'])
        return options
    def get_option_name(self, page, value):
        if value is None :
            return f'<span style="color:red">НЕОБХОДИМО ВЫБРАТЬ</span>'
        else:
            ps = ProductSet.get(page.cursor, value)
            if ps is None:
                return f'Неизвестный набор "{value}"'
            else:
                return ps.наименование
    def set_default(self, page):
        with page.connection:
            ActionSetItem.deleteall(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])
    def save(self, page):
        set_id = self.to_int(page.get(self.ID))
        with page.connection:
            if set_id is None:
                ActionSetItem.deleteall(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])
            else:
                item = ActionSetItem.findfirst(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])
                if item is None:
                    item = ActionSetItem(TYPE = self.SET, action_id= page.action.id, set_id = set_id)
                    item.create(page.cursor)
                else:
                    item.set_id = set_id
                    item.update(page.cursor)
    def print(self, page, cell):
        if self.is_personal_set(page):
            set_ID = self.get_value(page)
            cell.link(f'Индивидуальный набор {set_ID}')\
                .onclick('pages/product_set', {'set_id':f'{set_ID}'})
        else:
            super().print(page, cell)
    def editable(self, page):
        if self.is_personal_set(page):
            return False
        return True
    def add(self, page):
        self.set_default(page)
        with page.connection:
            ps = ProductSet(CLASS = 1, TYPE = 0)
            ps.наименование = 'Индивидуальный набор'
            ps.create(page.cursor)
            item = ActionSetItem(TYPE = self.SET, action_id = page.action.ID, set_id=ps.ID)
            item.create(page.cursor)
    def add_tooltip(self, page):
        if not self.is_personal_set(page):
            return 'Создать индивидуальный набор для акции'.upper()
        else:
            return None
    def is_personal_set(self, page):
        set_ID = self.get_value(page)
        if set_ID:
            ps = ProductSet.get(page.cursor, set_ID)
            if ps and ps.CLASS == 1:
                return True
        return False
    def readonly(self, page):
        return page.READONLY

class Набор_товаров_и_цен(FormControl.Param):
    def __init__(self, ID = 'набор_товаров_и_цен', description = 'Набор товаров c ценами', SET = 0):
        super().__init__(ID, description, type='select')
        self.SET = SET

    def get_value(self, page):
        item = ActionSetItem.findfirst(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])
        return item.set_id if item is not None else None
    
    def get_options(self, page):
        schema_id = page.action.схема_ID
        options = []
        #options.append(['', 'ВСЕ ТОВАРЫ'])
        for ps in ProductSet.findall(page.cursor, 'CLASS = 0 and TYPE=1 and (schema_id = 0 or schema_id=?)', [schema_id]):
            #if ps.наименование and ps.наименование.strip():
            options.append([str(ps.ID), ps.полное_наименование])
        return options
    
    def get_option_name(self, page, value):
        if value is None :
            return f'<span style="color:red">НЕОБХОДИМО ВЫБРАТЬ</span>'
        else:
            ps = ProductSet.get(page.cursor, value)
            if ps is None:
                return f'Неизвестный набор "{value}"'
            else:
                return ps.полное_наименование
    def print(self, page, cell):
        if self.is_personal_set(page):
            set_ID = self.get_value(page)
            cell.link(f'Индивидуальный набор {set_ID}')\
                .onclick('pages/product_set', {'set_id':f'{set_ID}'})
        else:
            super().print(page, cell)

    def set_default(self, page):
        with page.connection:
            ActionSetItem.deleteall(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])

    def save(self, page):
        set_id = self.to_int(page.get(self.ID))
        with page.connection:
            if set_id is None:
                ActionSetItem.deleteall(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])
            else:
                item = ActionSetItem.findfirst(page.cursor, f'TYPE = {self.SET} and action_id = ?', [page.action.ID])
                if item is None:
                    item = ActionSetItem(TYPE = self.SET, action_id= page.action.id, set_id = set_id)
                    item.create(page.cursor)
                else:
                    item.set_id = set_id
                    item.update(page.cursor)
    def editable(self, page):
        if self.is_personal_set(page):
            return False
        return True
    def add(self, page):
        self.set_default(page)
        with page.connection:
            ps = ProductSet(CLASS = 1, TYPE = 1)
            ps.наименование = 'Индивидуальный набор'
            ps.create(page.cursor)
            item = ActionSetItem(TYPE = self.SET, action_id = page.action.ID, set_id=ps.ID)
            item.create(page.cursor)
    def add_tooltip(self, page):
        if not self.is_personal_set(page):
            return 'Создать индивидуальный набор для акции'.upper()
        else:
            return None
    def is_personal_set(self, page):
        set_ID = self.get_value(page)
        if set_ID:
            ps = ProductSet.get(page.cursor, set_ID)
            if ps and ps.CLASS == 1:
                return True
        return False
    def readonly(self, page):
        return page.READONLY

class Количество_сопутствующих_товаров(FormControl.Param):
    def __init__(self):
        super().__init__(Action.КОЛИЧЕСТВО_СОПУТСТВУЮЩИХ_ТОВАРОВ, 'Соотношение основных и сопутствующих товаров', type='select')
        self.options = [
            [0, 'НЕОГРАНИЧЕННОЕ КОЛИЧЕСТВО СОПУТСТВУЮЩИХ ПРИ НАЛИЧИИ ХОТЬ ОДНОГО ОСНОВНОГО'],
            [1, 'НА КАЖДЫЙ ОСНОВНОЙ ОДИН СОПУТСТВУЮЩИЙ'],
            [2, 'НА КАЖДЫЙ ОСНОВНОЙ ДВА СОПУТСТВУЮЩИХ'],
            [3, 'НА КАЖДЫЙ ОСНОВНОЙ ТРИ СОПУТСТВУЮЩИХ'],
            [4, 'НА КАЖДЫЙ ОСНОВНОЙ ЧЕТЫРЕ СОПУТСТВУЮЩИХ'],
            [-2, 'ОДИН СОПУСТВУЮЩИЙ НА ДВА ОСНОВНЫХ'],
            [-3, 'ОДИН СОПУСТВУЮЩИЙ НА ТРИ ОСНОВНЫХ'],
            [-4, 'ОДИН СОПУСТВУЮЩИЙ НА ЧЕТЫРЕ ОСНОВНЫХ']
        ]
        #"Количество основных товаров для скидки на один сопутствующий товар"

    #def print(self, page, cell):
    #    value = self.get_value(page)
    #    if value:
    #       cell.text(value)
    #   else:
    #        cell.text(f'БЕЗ ОГРАНИЧЕНИЙ')

    def get_value(self, page):
        return self.to_int(page.action.info.get(self.ID))

    def set_default(self, page):
        page.action.info[self.ID] = 0
        with page.connection:
            page.action.update(page.cursor)

    def save(self, page):
        page.action.info[self.ID] = self.to_int(page.get(self.ID))
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class Количество_дней(FormControl.Param):
    def __init__(self, ID, name = 'Количество дней', options = None, default='БЕЗ ОГРАНИЧЕНИЙ', max=0):
        super().__init__(ID, name, type='select')
        self.default = default
        self.options = [[0, default]]
        if options is not None:
            for key, value in options:
                self.options.append([key, value])
        for day in range(max):
            self.options.append([day+1, f'{day+1}'])

    #def print(self, page, cell):
    #    value = self.get_value(page)
    #    if value:
    #        cell.text(value)
    #    else:
    #        cell.text(self.default)

    def get_value(self, page):
        return self.to_int(page.action.info.get(self.ID,0))

    def set_default(self, page):
        page.action.info[self.ID] = 0
        with page.connection:
            page.action.update(page.cursor)

    def save(self, page):
        page.action.info[self.ID] = self.to_int(page.get(self.ID))
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

SERIES_PARAM_ID = 'series_id'
COUNT_PARAM_ID = 'count'
SUMMA_PARAM_ID = 'summa'

class Наличие_карты_купона_(FormControl.Param):
    def __init__(self):
        super().__init__(Action.НАЛИЧИЕ_КАРТЫ_КУПОНА, 'Наличие карты/купона', type='select')
        self.undefined = 'НЕ ИМЕЕТ ЗНАЧЕНИЯ'
        self.style = 'font-weight:bold'

    def get_value(self, page):
        return page.action.info.get(self.ID)

    def get_options(self, page):
        options = []
        for t in Series.findall(page.cursor):
            if t.это_купон or t.это_дисконтная_карта or t.это_персональная_карта:
                options.append([str(t.id), t.полное_наименование])
        return options
    
    def set_default(self, page):
        try:
            del page.action.info[self.ID]
        except:
            pass
        with page.connection:
            page.action.update(page.cursor)

    def save(self, page):
        page.action.info[self.ID] = page.get(self.ID)
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class Шаблон_QR_кода(FormControl.Param):
    def __init__(self):
        super().__init__(Action.ШАБЛОН_QR_КОДА, 'Шаблон QR кода')
    def get_value(self, page):
        return page.action.info.get(self.ID)
    def print(self, page, cell):
        value = self.get_value(page)
        if value is None:
            cell.style('color:red')
            cell.text('НЕ ЗАДАНО')
        else:
            cell.text(value)
    def set_default(self, page):
        if Action.ШАБЛОН_QR_КОДА in page.action.info:
            del page.action.info[Action.ШАБЛОН_QR_КОДА]
            with page.connection:
                page.action.update(page.cursor) 
    def save(self, page):
        page.action.info[Action.ШАБЛОН_QR_КОДА] = page.get(self.ID)
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class Минимальное_количество_уникальных_товаров_(FormControl.Param):
    def __init__(self):
        super().__init__(Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_УНИКАЛЬНЫХ_ТОВАРОВ, 'Минимaльнo необходимое количество УНИКАЛЬНЫХ товаров в наборе', type='number', 
            min=0)
        self.undefined = 'НЕ ИМЕЕТ ЗНАЧЕНИЯ'
        self.style = 'font-weight:bold'
    def get_value(self, page):
        try:
            return int(page.action.info.get(self.ID, self.default))
        except:
            return 0
    def set_default(self, page):
        if self.ID in page.action.info: del page.action.info[self.ID]
        with page.connection:
            page.action.update(page.cursor) 

    def save(self, page):
        page.action.info[self.ID] = int(page.get(self.ID))
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class Минимальное_количество_товаров_(FormControl.Param):
    def __init__(self):
        super().__init__(Action.МИНИМАЛЬНОЕ_КОЛИЧЕСТВО_ТОВАРОВ, 'Минимaльнo необходимое КОЛИЧЕСТВО товаров в наборе', type='number', 
            min = 0)
        self.undefined = 'НЕ ИМЕЕТ ЗНАЧЕНИЯ'
        self.style = 'font-weight:bold'
    def print_default(self, page, cell):
        cell.text('НЕ ИМЕЕТ ЗНАЧЕНИЯ')
    def get_value(self, page):
        try:
            return int(page.action.info.get(self.ID, self.default))
        except:
            return 0
    def set_default(self, page):
        if self.ID in page.action.info: del page.action.info[self.ID]
        with page.connection:
            page.action.update(page.cursor) 
    def save(self, page):
        page.action.info[self.ID] = int(page.get(self.ID))
        with page.connection:
            page.action.update(page.cursor) 
    def readonly(self, page):
        return page.READONLY

class Способ_вычисления_суммы_чека(FormControl.Param):
    def __init__(self):
        super().__init__(Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА, 'Способ вычисления суммы чека', type='select')
        self.options = [
            ['', 'В розничных ценах (без скидок), без исключенных товаров'],
            ['+E', 'В розничных ценах (без скидок), вместе с исключенными товарами'],
            ['D', 'В фактических ценах (со скидками) на момент расчета акции, без исключенных товаров'],
            ['D+E', 'В фактических ценах (со скидками) на момент расчета акции, вместе с исключенными товарами']
        ]

    def get_value(self, page):
        return page.action.info.get(Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА, '')

    def set_default(self, page):
        with page.connection:
            page.action.info[Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА] = ''
            page.action.update(page.cursor)

    def save(self, page):
        with page.connection:
            page.action.info[Action.СПОСОБ_ВЫЧИСЛЕНИЯ_СУММЫ_ЧЕКА] = page.get(self.ID)
            page.action.update(page.cursor)
    
    def readonly(self, page):
        return page.READONLY

class Минимальная_сумма_чека_(FormControl.Param):
    def __init__(self):
        super().__init__(Action.МИНИМАЛЬНАЯ_СУММА_ЧЕКА, 'Минимaльнo нeoбxoдимая сумма чека (зависит от способа вычисления)', type='number', 
        min=0)
        self.undefined = 'НЕ ИМЕЕТ ЗНАЧЕНИЯ'
        self.style = 'font-weight:bold'
    def get_value(self, page):
        try:
            return float(page.action.info.get(self.ID, self.default))
        except:
            return self.default
    def set_default(self, page):
        if self.ID in page.action.info: del page.action.info[self.ID]
        with page.connection:
            page.action.update(page.cursor) 
    def save(self, page):
        page.action.info[self.ID] = page.get(self.ID)
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class Минимальная_сумма_товаров_(FormControl.Param):
    def __init__(self):
        super().__init__(Action.МИНИМАЛЬНАЯ_СУММА_ТОВАРОВ, 'Минимaльнo нeoбxoдимая розничная СУММА товаров в наборе', type='number', 
        min=0)
        self.undefined = 'НЕ ИМЕЕТ ЗНАЧЕНИЯ'
        self.style = 'font-weight:bold'

    def get_value(self, page):
        try:
            return float(page.action.info.get(self.ID, self.default))
        except:
            return self.default
    def set_default(self, page):
        if self.ID in page.action.info: del page.action.info[self.ID]
        with page.connection:
            page.action.update(page.cursor) 

    def save(self, page):
        page.action.info[self.ID] = float(page.get(self.ID))
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class НаличиеКлючевогоСлова(FormControl.Param):
    def __init__(self):
        super().__init__('наличие_ключевого_слова', 'Наличие ключевого слова (промокода)')
        self.undefined = 'НЕ ИМЕЕТ ЗНАЧЕНИЯ'
        self.style = 'font-weight:bold'
    def get_value(self, page):
        return page.action.info.get(Action.КЛЮЧЕВОЕ_СЛОВО)
    def set_default(self, page):
        if Action.КЛЮЧЕВОЕ_СЛОВО in page.action.info: del page.action.info[Action.КЛЮЧЕВОЕ_СЛОВО]
        with page.connection:
            page.action.update(page.cursor) 
    def save(self, page):
        page.action.info[Action.КЛЮЧЕВОЕ_СЛОВО] = page.get(self.ID).strip().upper()
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

class Минимальная_цена_товаров(FormControl.Param):
    def __init__(self):
        super().__init__('минимальная_цена_товаров', 'Минимaльнo нeoбxoдимая розничная цена товаров', type='number', 
        min=0)
        self.undefined = 'НЕ ИМЕЕТ ЗНАЧЕНИЯ'
        self.style = 'font-weight:bold'

    def get_value(self, page):
        try:
            return float(page.action.info.get(self.ID, self.default))
        except:
            return self.default
    def set_default(self, page):
        if self.ID in page.action.info: del page.action.info[self.ID]
        with page.connection:
            page.action.update(page.cursor) 

    def save(self, page):
        page.action.info[self.ID] = float(page.get(self.ID))
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY
class Стоимость_одной_подарочной_марки(FormControl.Param):
    def __init__(self):
        super().__init__(Action.СТОИМОСТЬ_ОДНОЙ_ПОДАРОЧНОЙ_МАРКИ, 'Стоимость одной подарочной марки', type='number', 
            min=0)
        self.undefined = 'НЕОБХОДИМО ЗАДАТЬ'
        #self.style = 'color:red'
        self.default = 0

    def get_value(self, page):
        return int(page.action.info.get(self.ID, 0))
    def print(self, page, cell):
        value = self.get_value(page)
        if value == self.default:
            cell.style('color:red')
            cell.text('НЕ ОПРЕДЕЛЕНО')
        else:
            cell.text(value)
    def set_default(self, page):
        if self.ID in page.action.info: del page.action.info[self.ID]
        with page.connection:
            page.action.update(page.cursor) 

    def save(self, page):
        value = int(page.get(self.ID))
        page.action.info[self.ID] = value if value > 0 else 0
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY
class Количество_товаров_для_получения_подарочной_марки(FormControl.Param):
    def __init__(self):
        super().__init__(Action.КОЛИЧЕСТВО_ТОВАРОВ_ДЛЯ_ПОЛУЧЕНИЯ_ПОДАРОЧНОЙ_МАРКИ, 'Количество товаров для получения подарочной марки', type='number', 
            min=0)
        self.undefined = 'НЕОБХОДИМО ЗАДАТЬ'
        #self.style = 'color:red'
        self.default = 0

    def get_value(self, page):
        return int(page.action.info.get(self.ID, 0))
    def print(self, page, cell):
        value = self.get_value(page)
        if value == self.default:
            cell.style('color:red')
            cell.text('НЕ ОПРЕДЕЛЕНО')
        else:
            cell.text(value)
    def set_default(self, page):
        if self.ID in page.action.info: del page.action.info[self.ID]
        with page.connection:
            page.action.update(page.cursor) 

    def save(self, page):
        value = int(page.get(self.ID))
        page.action.info[self.ID] = value if value > 0 else 0
        with page.connection:
            page.action.update(page.cursor)
    def readonly(self, page):
        return page.READONLY

БазовыеПараметры = FormControl(BASE_PARAMS_FORM, width=30, mt=1)
БазовыеПараметры.append(НаименованиеАкции())
БазовыеПараметры.append(Validity())
БазовыеПараметры.append(ПериодДействияУпрощенный())
БазовыеПараметры.append(Подразделение())
БазовыеПараметры.append(ФормулаВычисленияПодарка())
БазовыеПараметры.append(ДисконтнаяКарта())
БазовыеПараметры.append(Набор_товаров_и_цен()) 
БазовыеПараметры.append(НаборТоваров())
БазовыеПараметры.append(НаборТоваров('основные_товары', 'Набор товаров', SET=ActionSetItem.ОСНОВНЫЕ_ТОВАРЫ))
БазовыеПараметры.append(НаборТоваров('необходимый_набор_товаров', 'Необходимый набор товаров', default_text='НЕТ'))
БазовыеПараметры.append(ОбязательныйНаборТоваров())
БазовыеПараметры.append(Минимальная_цена_товаров())
БазовыеПараметры.append(ОбязательныйНаборТоваров('сопутствующие_товары', 'Набор СОПУТСТВУЮЩИХ товаров', SET=ActionSetItem.СОПУТСТВУЮЩИЕ_ТОВАРЫ))
БазовыеПараметры.append(НаборТоваров('excluded', 'Исключенные товары', default_text='НЕТ', SET=ActionSetItem.ИСКЛЮЧЕННЫЕ_ТОВАРЫ))
БазовыеПараметры.append(Акция())
БазовыеПараметры.append(ПодарочныйКупон())
БазовыеПараметры.append(Цифра_на_которую_оканчивается_цена())
БазовыеПараметры.append(ПроцентнаяСкидка())
БазовыеПараметры.append(Максимально_оплачиваемая_стоимость_чека())
БазовыеПараметры.append(Шаблон_QR_кода()),
БазовыеПараметры.append(ПроцентНачисленияБаллов())
БазовыеПараметры.append(ПроцентОтПозиции())
БазовыеПараметры.append(Множитель())
БазовыеПараметры.append(Количество_сопутствующих_товаров())
БазовыеПараметры.append(Количество_дней(Action.КОЛИЧЕСТВО_ДНЕЙ_ДО_ДНЯ_РОЖДЕНИЯ, 'Количество дней до дня рождения', default='НЕПОCРЕДСВЕННО В ДЕНЬ РОЖДЕНИЯ', options=[[100, 'ПОНЕДЕЛЬНИК']], max=10))
БазовыеПараметры.append(Количество_дней(Action.КОЛИЧЕСТВО_ДНЕЙ_ПОСЛЕ_ДНЯ_РОЖДЕНИЯ, 'Количество дней после дня рождения', default='НЕПОCРЕДСВЕННО В ДЕНЬ РОЖДЕНИЯ', options=[[100, 'ВОСКРЕСЕНЬЕ']], max=10))
БазовыеПараметры.append(ОкруглениеЦены())
БазовыеПараметры.append(ОкруглениеБонуса())
БазовыеПараметры.append(Стоимость_одной_подарочной_марки())
БазовыеПараметры.append(Количество_товаров_для_получения_подарочной_марки())
БазовыеПараметры.append(PRINT_MODE())

ДополнительныеУсловия = FormControl(TAB_TOOLBAR, width=40, mt=1)
for param in [
    Наличие_карты_купона_,
    НаличиеКлючевогоСлова,
    Минимальная_цена_товаров,
    Способ_вычисления_суммы_чека,
    Минимальная_сумма_чека_,
    Минимальное_количество_уникальных_товаров_,
    Минимальное_количество_товаров_,
    Минимальная_сумма_товаров_
    ]:
    ДополнительныеУсловия.append(param())

class TheActionPage(Page):
    def __init__(self, application, request, TABS = base_action_tabs):
        super().__init__(application, request, controls = [TABS, БазовыеПараметры, ДополнительныеУсловия])
        self.account_id = self.request.account_id()
        self.action_id = self.attribute('action_id')
        self._connection = None
        self._cursor = None
        self._action = None
        self.ReadonlyParams = set()
        self._action_type = None
        self.TABS = TABS
        self.CLASSES = self.application['card_types']
        self.action_types = self.application['action_types']
        self.grants = Grants(self.account_id, self.user_id)
        self.DS_MANAGER   = self.grants.match(Grants.DS_MANAGER, str(self.action.схема_ID))
        self.DS_ASSISTANT = self.grants.match(Grants.DS_ASSISTANT, str(self.action.схема_ID))
        if self.DS_MANAGER:
            self.DS_ASSISTANT = True
        self.READONLY = not self.DS_ASSISTANT
    @property
    def action_type(self):
        if self._action_type is None:
            self._action_type = self.action_types[self.action.type]
        return self._action_type
    @property
    def param_id(self):
        return self.get('param_id')
    @property
    def connection(self):
        if self._connection is None:
            self._connection = sqlite3.connect(DISCOUNT_DB(self.account_id))
        return self._connection
    @property
    def cursor(self):
        if self._cursor is None:
            self._cursor = self.connection.cursor()
        return self._cursor
    @property
    def action(self):
        if self._action is None:
            self._action = Action.get(self.cursor, self.action_id)
        return self._action
    def print_title(self):
        self.title(f'{self.action.id}, {self.action.полное_наименование(self.action_types)}')
    #-----------------------------------------------
    # VISIBLE
    #-----------------------------------------------
    def param_visible(self, param_id):
        return True
    def params(self):
        return []
    def tab_visible(self, tab_id):
        #log.debug(f'tab_visible(self, {tab_id})')
        return True
    def набор_дополнительных_условий(self):
        options = []
        for param in self.params():
            options.append(param.id)
        return options
    def набор_базовых_параметров(self):
        params = []
        for param in БазовыеПараметры.params:
            if self.param_visible(param.ID):
                params.append(param.ID)
        return params

    #-----------------------------------------------
    # ДОПОЛНИТЕЛЬНЫЕ УСЛОВИЯ
    #-----------------------------------------------
    def print_params(self, input_param_id = None):
        self.text_block(TAB_ABOUT)
        self.text_block(BASE_PARAMS_FORM)
        ДополнительныеУсловия(self, self.набор_дополнительных_условий(), mt=1)
        self.Table(TAB_TABLE)
    #--------------------------
    # БАЗОВЫЕ ПАРАМЕТРЫ
    #-------------------------
    def print_base_params_tab(self):
        self.text_block(TAB_ABOUT)
        self.text_block(TAB_TOOLBAR)
        БазовыеПараметры(self, self.набор_базовых_параметров(), mt = 0.5)
        self.Table(TAB_TABLE)
    #------------------------
    # Параметры печати чека
    #------------------------
    def change_print_options(self):
        print_lines_count = self.get(Action.PRINT_LINES_COUNT)
        print_mode = self.get(Action.PRINT_MODE)
        with self.connection:
            self.action.info[Action.PRINT_LINES_COUNT] = print_lines_count
            self.action.info[Action.PRINT_MODE] = print_mode
            self.action.update(self.cursor)
            self.connection.commit()
        self.print_print_params()
    def line_types(self):
        return [
            [TEXT_TEXT, 'TEXT'],
            [TEXT_BOLD, 'BOLD'],
            [TEXT_CODE, 'QRCODE'],
            [TEXT_EAN13, 'EAN13'],
            ]
    def drow_line_type_glif(self, cell, line_type):
        if line_type == TEXT_TEXT:
            cell.glif('font')
        elif line_type == TEXT_BOLD:
            cell.glif('bold')
        elif line_type == TEXT_CODE:
            cell.glif('qrcode')
        elif line_type == TEXT_EAN13:
            cell.glif('barcode')
        else:
            cell.text(f'{line_type}')
    def change_print_line(self):
        line = self.get('line')
        line_type = self.get('line_type')
        line_text = self.get('line_text')
        with self.connection:
            self.action.info[f'line_type_{line}'] = line_type
            self.action.info[f'line_text_{line}'] = line_text
            self.action.update(self.cursor)
            self.connection.commit()
        self.print_print_lines()
    def edit_print_line(self):
        line = self.get('line')
        self.print_print_lines(line)
    def cancel_print_line(self):
        self.print_print_lines()
    def print_print_line(self, table, line, input_line):
        line = str(line)
        line_type = self.action.info.get(f'line_type_{line}', 'TEXT')
        line_text = self.action.info.get(f'line_text_{line}', '')
        row = table.row(line)
        type_cell = row.cell(width=10)
        text_cell = row.cell()
        кнопки = СтандартныеКнопки(row)
        #cmd_cell = row[2].width(12).right().middle()
        if input_line == line:
            row.css('shadow table-warning')
            type_cell.select(value = line_type, name = 'line_type').options(self.line_types())
            text_cell.input(value = line_text, name='line_text')
            кнопки.кнопка('сохранить', 'change_print_line', {'line':line}, forms=[row])
            кнопки.кнопка('отменить', 'cancel_print_line', {'line':line})
            #cmd_cell.button('Сохранить').css('mr-1').primary().small().onclick('.change_print_line', {'line':line}, forms=[row])
            #cmd_cell.button('Отменить').secondary().small().onclick('.cancel_print_line', {'line':line})
        else:
            #type_cell.text(self.line_type_name(line_type))
            self.drow_line_type_glif(type_cell, line_type)
            text_cell.text(line_text)
            if not self.READONLY:
                кнопки.кнопка('редактировать', 'edit_print_line', {'line':line})
            #row.onclick('.edit_print_line', {'line':line})
            #cmd_cell.text_block().glif('pen', style='color:lightgray')
    def print_macros(self):
        return []
    def print_print_lines(self, input_line=''):
        about = self.text_block('tab_about')
        macros = self.print_macros()
        if len(macros) > 0:
            about.mt(1)
            about.text('''
                В тексте строк можно использовать макросы. Они заключаются в фигурные скобки.
                Если в фигурных скобках не макрос, это трактуется как простой текст.
                Доступны следующие макросы : 
            ''')
            for macro in macros:
                about.text(f' {{{macro[0]}}}')
                about.text(f' {macro[1]}')

        table = self.table('table',  hole_update=True).mt(1).css('table-borderless')
        lines = self.action.print_lines_count
        for line in range(0, lines):
            self.print_print_line(table, line, input_line)
    def print_print_params(self, input_line = ''):
        self.text_block(BASE_PARAMS_FORM)
        toolbar = self.toolbar('tab_toolbar').mt(1)
        print_mode_options = []
        print_mode_options.append([Action.print_mode_HEADER, 'Печать сообщения в начале чека'])
        print_mode_options.append([Action.print_mode_FOOTER, 'Печать сообщения в конце чека'])
        print_mode_options.append([Action.print_mode_COUPON, 'Печать в виде отрывного купона'])
        button = toolbar.item().select(name = Action.PRINT_MODE, value=self.action.print_mode)
        button.options(print_mode_options)
        button.onchange('.change_print_options', forms=[toolbar])
        if self.READONLY:
            button.disabled(True)
        g = toolbar.item().ml(1).input_group()
        g.text('Количество строк')
        button = g.select(name = Action.PRINT_LINES_COUNT, value=self.action.print_lines_count)
        button.options(range(0, Action.print_lines_count_MAX))
        button.onchange('.change_print_options', forms=[toolbar])
        if self.READONLY:
            button.disabled(True)
        self.print_print_lines(input_line)
    #------------------------
    # WEEKDAYS
    #------------------------
    def print_weekdays(self):
        self.text_block('tab_about')
        self.text_block(BASE_PARAMS_FORM)

        toolbar = self.toolbar('tab_toolbar', style='align-items: baseline').mt(1)
        if self.action.ограничение_по_дням_недели.есть:
            button = toolbar.item().icon_button('check', style='color:green')
        else:
            button = toolbar.item().icon_button('check', style='color:lightgray')
        if not self.READONLY:
            button.disabled(True)
            button.onclick('.weekdays_enabled_switcher')

        #print_check_button(toolbar, 'weekdays_enabled_switcher'\
        #    , self.action.ограничение_по_дням_недели.есть,  size='small')
        toolbar.item().text_block().ml(0.5).text('Использовать ограничения по дням недели и времени')

        table = self.Table('table').mt(1)
        if self.action.ограничение_по_дням_недели.есть:
            table.column('')
            table.column('День недели')
            table.column('Начало')
            table.column('Окончание')
            table.column('')
            for день in range(0,7):
                день_недели = self.action.ограничение_по_дням_недели[день]
                row = table.row(день)
                cell = row.cell(width=2)
                if день_недели is not None:
                    button = cell.icon_button('check', style='color:green')
                    if not self.READONLY:
                        button.onclick('.weekday_enabled_switcher', {'day':f'{день}'})
                else:
                    button = cell.icon_button('check', style='color:lightgray')
                    if not self.READONLY:
                        button.onclick('.weekday_enabled_switcher', {'day':f'{день}'})
                #print_check_button(row, 'weekday_enabled_switcher', день_недели is not None, params={'day':f'{день}'}, size='small' )
                row.text(ДеньНедели.наименование(день).upper())
                if день_недели is not None:
                    cell = row.cell(width=10).text(str(день_недели.начало))
                    if not self.READONLY:
                        cell.onclick('.weekday_edit_mode', {'day':f'{день}'})
                    cell = row.cell(width=10).text(str(день_недели.окончание))
                    if not self.READONLY:
                        cell.onclick('.weekday_edit_mode', {'day':f'{день}'})

                    кнопки = СтандартныеКнопки(row, params={'day':f'{день}'})
                    if not self.READONLY:
                        кнопки.кнопка('редактировать', 'weekday_edit_mode')
                else:
                    row.cell(width=10).text('')
                    row.cell(width=10).text('')
                    row.cell(width=8).text('')

        about = self.text_block('tab_about')
    def weekdays_enabled_switcher(self):
        self.action.ограничение_по_дням_недели.есть = not self.action.ограничение_по_дням_недели.есть
        self.action_save()
        self.print_weekdays()
    def weekday_enabled_switcher(self):
        день = int(self.get('day'))
        день_недели = self.action.ограничение_по_дням_недели[день]
        if день_недели is None:
            self.action.ограничение_по_дням_недели[день] = ДеньНедели(день)
        else:
            self.action.ограничение_по_дням_недели[день] = None
        self.action_save()
        self.print_weekdays()
    def weekday_edit_mode_cancel(self):
        self.print_weekdays()
    def to_time(self, value):
        try:
            if value and value.strip():
                parts = re.split('[^0-9]*', value, maxsplit=1)
                if len(parts) == 0:
                    return None
                elif len(parts) == 1:
                    hour = int(parts[0])
                    minutes = 0
                else:
                    hour = int(parts[0])
                    minutes = int(parts[1]) if parts[1] else 0
                return arrow.get(1,1,1, hour, minutes).format('HH:mm')
            else:
                return ''
        except:
            log.exception(__name__)
            return None
    def weekday_edit_mode_save(self):
        день = int(self.get('day'))
        день_недели = self.action.ограничение_по_дням_недели[день]
        if день_недели is not None:
            start_time = self.get('start_time')
            end_time = self.get('end_time')
            start_time_impoved = self.to_time(start_time)
            if start_time_impoved is None:
                self.error(f'Недопустимое значение времени "{start_time}"')
                return
            день_недели.начало.fromstring(start_time_impoved)
            end_time_impoved = self.to_time(end_time)
            if end_time_impoved is None:
                self.error(f'Недопустимое значение времени "{end_time}"')
                return
            день_недели.окончание.fromstring(end_time_impoved)
        self.action_save()
        self.print_weekdays()
    def weekday_edit_mode(self):
        день = int(self.get('day'))
        день_недели = self.action.ограничение_по_дням_недели[день]
        row = self.table('table').row(день)
        row.text('')
        row.text(ДеньНедели.наименование(день))
        начало = str(день_недели.начало) if день_недели is not None else ''
        окончание = str(день_недели.окончание) if день_недели is not None else ''
        row.cell(width=10).input(name='start_time', value = начало).\
            onkeypress(13, '.weekday_edit_mode_save', {'day':f'{день}'}, forms=[row])
        row.cell(width=10).input(name='end_time', value = окончание).\
            onkeypress(13, '.weekday_edit_mode_save', {'day':f'{день}'}, forms=[row])
        кнопки = СтандартныеКнопки(row, params={'day':f'{день}'})
        кнопки.кнопка('сохранить', 'weekday_edit_mode_save', forms=[row])
        кнопки.кнопка('отменить', 'weekday_edit_mode_cancel')
    #--------------------------
    # Скидка на товары
    #-------------------------
    def print_tax_by_products(self):
        about = self.text_block(TAB_ABOUT)
        self.text_block(BASE_PARAMS_FORM)

        self.tax_by_products_toolbar()
        self.print_tax_by_products_table()
    def стандартные_наборы_для_товаров_с_процентами(self):
        return None
    def доступные_наборы_для_товаров_с_процентами(self):
        наборы = []
        стандартные_наборы = self.стандартные_наборы_для_товаров_с_процентами()
        for ps in sorted(ProductSet.findall(self.cursor), key=lambda ps : ps.ID):
            if ps.CLASS == 2 and not self.action.sets.exists_set('discount', ps.ID):
                if стандартные_наборы is None or ps.TYPE in стандартные_наборы:
                    наборы.append(ps)
        
        for ps in sorted(ProductSet.findall(self.cursor), key=lambda ps : ps.description):
            if ps.CLASS == 0 and not self.action.sets.exists_set('discount', ps.ID):
                if ps.description is not None and ps.description.strip() != '':
                    наборы.append(ps)
        return наборы
    def tax_by_products_toolbar(self):
        toolbar = self.toolbar(TAB_TOOLBAR).mt(1)
        #CLS = 'btn-outline-secondary'
        drop_down = КраснаяКнопкаВыбор(toolbar, 'Добавить набор')
        #drop_down = toolbar.item().drop_down('Добавить набор', cls=CLS)
        for ps in self.доступные_наборы_для_товаров_с_процентами():
            drop_down.item(f'{ps.description}').onclick('.tax_by_products_add_set', {'set_id':ps.ID})

        #for ps in sorted(ProductSet.findall(self.cursor), key=lambda ps : ps.description):
        #    if ps.CLASS == 0 and not self.action.sets.exists_set('discount', ps.ID):
        #        if ps.description is not None and ps.description.strip() != '':
        #            drop_down.item(ps.description).onclick('.tax_by_products_add_set', {'set_id':ps.ID})
        #drop_down = КраснаяКнопкаВыбор(toolbar, 'Выбрать стандартный набор', ml=0.5)
        #for ps in sorted(ProductSet.findall(self.cursor), key=lambda ps : ps.ID):
        #    if ps.CLASS == 2 and not self.action.sets.exists_set('discount', ps.ID):
        #        drop_down.item(ps.description).onclick('.tax_by_products_add_set', {'set_id':ps.ID})

        КраснаяКнопка(toolbar, 'Создать набор для акции', ml=0.5)\
            .onclick('.tax_by_products_create_set')
    def print_tax_by_products_table(self):
        table = self.table(TAB_TABLE,  hole_update=True).mt(1).css('-table-borderless')
        table.column().text('Товарный набор')
        table.column().text('Процент')
        table.column()
        for набор in self.action.sets.findall('discount'):
            set_id = str(набор.set_id)
            row = table.row(set_id)
            #print_check_button(row, 'tax_by_products_exclude', набор.excluded, params={'set_id':set_id}, size='small', icon='times', cls='text-danger')
            товарный_набор = ProductSet.get(self.cursor, set_id)
            #row.text(f'{set_id}')
            if товарный_набор is None:
                row.cell(style='color:red').text(f'НЕ НАЙДЕН')
            else:
                if товарный_набор.CLASS == 2:
                    row.cell().text(товарный_набор.description)
                else:
                    row.cell().href(товарный_набор.description, 'pages/product_set.open', {'set_id':set_id})
            скидка = f'{набор.скидка} %'
            row.cell(width=10).text(скидка)
            кнопки = СтандартныеКнопки(row, params={'set_id':set_id})
            кнопки.кнопка('удалить', 'tax_by_products_delete')
            кнопки.кнопка('редактировать', 'tax_by_products_edit')
    def tax_by_products_save(self):
        set_id = self.get('set_id')
        скидка = self.get('tax')
        self.action.sets.create_set('discount', set_id).скидка = скидка
        self.action_save()
        self.print_tax_by_products_table()
    def tax_by_products_edit(self):
        set_id = self.get('set_id')
        набор = self.action.sets.create_set('discount', set_id)
        row = self.table(TAB_TABLE).row(set_id)
        ps = ProductSet.get(self.cursor, set_id)            
        row.cell().text(ps.description)
        tax = набор.скидка
        g = row.cell(width=10).input_group()
        g.input(value=tax, name='tax')
        кнопки = СтандартныеКнопки(row, params={'set_id':set_id})
        кнопки.кнопка('сохранить', 'tax_by_products_save', forms=[row])
        кнопки.кнопка('отменить', 'print_tax_by_products_table')
    def tax_by_products_delete(self):
        набор_ID = self.get('set_id')
        with self.connection:
            товарный_набор = ProductSet.get(self.cursor, набор_ID)
            if товарный_набор is not None:
                if товарный_набор.это_персональный_набор:
                    товарный_набор.delete(self.cursor)
            self.action.sets.delete_set('discount', набор_ID)
            self.action.update(self.cursor)
        self.print_tax_by_products_table()
    def tax_by_products_add_set(self):
        set_id = self.get('set_id')
        self.action.sets.create_set('discount', set_id)
        self.action_save()
        self.print_tax_by_products_table()
        self.tax_by_products_toolbar()
        #self.message(f'{tax_by_products.sets}')
    def tax_by_products_create_set(self):
        ps = ProductSet(CLASS=1)
        ps.info['action_id'] = self.action_id
        ps.info['description'] = 'ИНДИВИДУАЛЬНЫЙ НАБОР'
        with self.connection:
            ps.create(self.cursor)
            self.action.sets.create_set('discount', ps.ID)
            self.action.update(self.cursor)
        self.tax_by_products_toolbar()
        self.print_tax_by_products_table()
    #----------------------------------
    # ADD DISOCUNT
    #----------------------------------
    def print_add_discount(self):
        table = self.table('table',  hole_update=True).mt(0.5).css('table-borderless')
        toolbar = self.toolbar('tab_toolbar').mt(1)
        about = self.text_block('tab_about')
        about.text('''
        Стандартно, текущая скидка (скидка по данной акции) ЗАМЕЩАЕТ (заменяет) 
        ранее сделанную скидку, если это более выгодно для покупателя.
        Но, если пометить акцию как "+", то к скиде по данной акции,
        текущая скидка будет ДОБАВЛЯТЬСЯ (суммироваться).
        ''')
        check = CheckButton('change_add_disocunt', size='small', icon='plus')
        for action in Action.calc_actions(self.cursor, self.action_types):
            action_type = self.action_types[action.type]
            if action_type.CLASS == 0 and action.pos < self.action.pos:
                row = table.row(action.id)
                used = action.id in self.action.used_actions
                cell = row.cell(width=2) 
                check(cell, used, {'used_action_id': action.id})
                row.text(action.full_name(self.action_types))
            #self.message(f'{self.action.info}')
    def change_add_disocunt(self):
        action_id = int(self.get('used_action_id'))
        if action_id in self.action.used_actions:
            self.action.used_actions.remove(action_id)
        else:
            self.action.used_actions.add(action_id)
        with self.connection:
            self.action.update(self.cursor)
        self.print_add_discount()
    # ------------------------------------
    # print_percent_of_sum
    # --------------------------------------
    def print_percent_of_sum(self):
        self.text_block('tab_about')
        self.text_block(BASE_PARAMS_FORM)
        toolbar = self.toolbar('tab_toolbar').mt(1)
        toolbar.item(width=40).input(label='Укажите пороги действия скидок через пробел', name='percent_of_sum_size', value=self.action.percents_of_sum.get_scale())\
            .onkeypress(13, '.change_percent_of_sum_size', forms=[toolbar])\
            .disabled(self.READONLY)

        table = self.Table('table').mt(1)
        percents_of_sum = self.action.percents_of_sum
        dim = percents_of_sum.dim
        for i in range(0, dim):
            row = table.row(i)
            row.cell(width=20).text(percents_of_sum.sum_name(i))
            row.cell(cls='text-left').text(f'{percents_of_sum.get_percent(i)} %')
            кнопки = СтандартныеКнопки(row)
            if not self.READONLY:
                кнопки.кнопка('редактировать', 'percent_of_sum_edit', {'i':str(i)})
                row.onclick('.percent_of_sum_edit', {'i':str(i)})
            #cell = row.cell(width=10)
            #edit_button(cell, {'i':str(i)})
    def action_save(self):
        with self.connection:
            self.action.update(self.cursor)
    def percent_of_sum_save(self):
        i = int(self.get('i'))
        percent = float(self.get('percent', 0))
        self.action.percents_of_sum.set_percent(i, percent)
        self.action_save()
        self.print_percent_of_sum()
    def percent_of_sum_edit(self):
        i = int(self.get('i'))
        #cancel_button = CancelButton('print_percent_of_sum', size='small', cls='text-right')
        #save_button = SaveButton('percent_of_sum_save', size='small', cls='text-right')
        table = self.table('table')
        row = table.row(i)
        #.cls('table-warning shadow-sm')
        row.cell(width=20).text(self.action.percents_of_sum.sum_name(i))
        row.cell().input(type='number', name=f'percent', value = self.action.percents_of_sum.get_percent(i))\
            .style('width:10rem')\
            .onkeypress(13, '.percent_of_sum_save', forms=[row])
        кнопки =СтандартныеКнопки(row, params={'i':str(i)})
        кнопки.кнопка('сохранить', 'percent_of_sum_save', forms=[row])
        кнопки.кнопка('отменить', 'print_percent_of_sum', forms=[row])
        #cell = row.cell(width=10)
        #save_button(cell, {'i':str(i)}, forms=[row])
        #cancel_button(cell)
    def change_percent_of_sum_size(self):
        scale = self.get('percent_of_sum_size')
        self.action.percents_of_sum.set_scale(scale)
        self.action_save()
        self.print_percent_of_sum()
        #self.message(scale)

    # ------------------------
    # Основные товары
    #-------------------------
    def основные_товары(self):
        ОСНОВНЫЕ_ТОВАРЫ(self)
    #--------------------------
    def print_tabs(self):
        self.TABS.print(self)
    def print_tab(self):
        self.TABS.print(self)

