import os, sys, json, sqlite3, datetime
from domino.core import log
from discount.core import DISCOUNT_DB, CARDS
from discount.series import Series, CardType
from discount.cards import Card, CardLog
from domino.page import Page
from domino.page_controls import Кнопка, ПлоскаяТаблица, ПрозрачнаяКнопка, СтандартныеКнопки
from domino.page_controls import КраснаяКнопка
from domino.page_controls import FormControl, TabControl
from discount.product_sets import ProductSet, ProductSetItem
from tables.sqlite.product_set import ProductSet as PS, ГотовыеНаборы
from grants import Grants
from discount.page import DiscountPage
from domino.tables.postgres.good import Good

class Наименование(FormControl.Param):
    def __init__(self):
        super().__init__('наименование', 'Наименование')
    def readonly(self, page):
        return page.readonly()
    def get_value(self, page):
        return page.series.полное_наименование
    def save(self, page):
        page.series.description = page.get(self.ID)
        page.save()
        page.print_title()
class ФорматКода(FormControl.Param):
    def __init__(self):
        super().__init__(CardType.CODE_FORMAT, 'Формат кода', type='select')
        self.options=[
            [CardType.code_format_DEFAULT, 'Произвольный набор символов'.upper()],
            [CardType.code_format_EAN13, 'EAN13'.upper()],
        ]
    def readonly(self, page):
        return page.readonly()
    def get_value(self, page):
        return page.series.code_format
    def save(self, page):
        page.series.code_format = page.get(self.ID)
        page.save()
        #page.создание_карт()
class Префикс(FormControl.Param):
    def __init__(self):
        super().__init__('префикс', 'Префикс')
    def get_value(self, page):
        return page.series.prefix
    def save(self, page):
        prefix = page.get(self.ID)
        if page.series.code_format_ean13:
            if len(prefix) > 11:
                raise Exception('Недопустимый префикс (слишком длинный)') 
            if not prefix.isdigit():
                raise Exception('Недопустимый префикс (должны быть только цифры)') 
        page.series.prefix = prefix
        page.series.digits = 12 - len(prefix)
        page.save()
        self.form_update(page)
    def readonly(self, page):
        return not page.CARD_MANAGER
class Суффикс(FormControl.Param):
    def __init__(self):
        super().__init__('суффикс', 'Суффикс')
    def get_value(self, page):
        return page.series.info.get(Series.SUFFIX)
    def save(self, page):
        page.series.info[Series.SUFFIX] = page.get(self.ID)
        page.save()
    def readonly(self, page):
        return not page.CARD_MANAGER
    def visible(self, page):
        return not page.series.code_format_ean13

class МаксимальноеКоличествоПокупок(FormControl.Param):
    def __init__(self):
        super().__init__('максимальное_количество_покупок', 'Максимальное количество покупок в день', type='number', min=0)
    def get_value(self, page):
        return page.series.today_count
    def print(self, page, cell):
        value = self.get_value(page)
        cell.text(value if value else 'БЕЗ ОГРАНИЧЕНИЙ')
    def set_default(self, page):
        page.series.today_count = None
        page.save()
    def save(self, page):
        page.series.today_count = page.get(self.ID)
        page.save()
    def readonly(self, page):
        return page.readonly()
class КоличествоБаллов(FormControl.Param):
    def __init__(self):
        super().__init__('количество_баллов', 'Начальное количество баллов', type='number', min=0)
    def readonly(self, page):
        return page.readonly()
    def get_value(self, page):
        return page.series.points
    def set_default(self, page):
        page.series.points = None
        page.save()
    def save(self, page):
        page.series.points = page.get(self.ID)
        page.save()
class ПроцентСкидки(FormControl.Param):
    def __init__(self):
        super().__init__('процент_скидки', 'Начальный процент скидки', type='number', min=0, max=100)
    def get_value(self, page):
        return page.series.discount
    def readonly(self, page):
        return page.readonly()
    def print(self, page, cell):
        value = self.get_value(page)
        cell.text(f'{value} %' if value else '')
    def save(self, page):
        page.series.discount = page.get(self.ID)
        page.save()
class СледующийНомерКарты(FormControl.Param):
    def __init__(self):
        super().__init__('следующий_номер', 'Следующий последовательный номер', type='number', min=0)
    def get_value(self, page):
        return page.series.next_number
    def save(self, page):
        page.series.next_number = page.get(self.ID)
        page.save()
    def visible(self, page):
        return not page.series.gen_mode_random
    def readonly(self, page):
        return not page.CARD_MANAGER
class СпособГенерацииНомера(FormControl.Param):
    def __init__(self):
        super().__init__('способ_генерации_номера', 'Способ генерации номера', type='select')
        self.options=[
            [Series.gen_mode_SEQUENCE, 'Последовательные номера'.upper()],
            [Series.gen_mode_RANDOM, 'Случайные номера'.upper()],
        ]
    def readonly(self, page):
        return page.readonly() or page.series.это_купон
    def get_value(self, page):
        return page.series.info.get(Series.GEN_MODE, Series.gen_mode_SEQUENCE)
    def save(self, page):
        page.series.info[Series.GEN_MODE] = page.get(self.ID)
        page.save()
class СрокДействия(FormControl.Param):
    def __init__(self):
        super().__init__('срок_действия', 'Срок действия с момента активации (дней)', type='number', min=0)
    def readonly(self, page):
        return page.readonly()
    def get_value(self, page):
        return page.series.exp_days
    def print(self, page, cell):
        exp_days = self.get_value(page)
        if not exp_days:
            cell.text('НЕ ОГРАНИЧЕНО')
            #cell.style('color:gray')
        else:
            cell.text(f'{exp_days}')
    #def edit(self, page, cell):
    #    exp_days = page.series.exp_days
    #    cell.input(value=exp_days, name=self.ID, type='number')
    def save(self, page):
        page.series.exp_days = page.get(self.ID)
        if page.series.exp_days:
            if page.series.exp_days <= 0:
                page.series.exp_days = None
        page.save()
class КоличествоЦифр(FormControl.Param):
    def __init__(self):
        super().__init__('количество_цифр', f'Количество цифр в номере', type='number')
    def get_value(self, page):
        return page.series.digits
    def set_default(self, page):
        page.series.digits = 0
        page.save()
    def save(self, page):
        page.series.digits = page.get(self.ID)
        page.save()
    def readonly(self, page):
        return not page.CARD_MANAGER or page.series.code_format_ean13
class Номинал(FormControl.Param):
    def __init__(self):
        super().__init__('номинал', 'Номинал', type='number', min=0)
    def readonly(self, page):
        return page.readonly()
    def get_value(self, page):
        return page.series.cash
    def print(self, page, cell):
        value = self.get_value(page)
        if value:
            cell.text(value)
        else:
            cell.text('НЕ ОПРЕДЕЛЕНО')
            cell.style('color:red')

    def save(self, page):
        page.series.cash = page.get(self.ID)
        page.save()
class МногоразовоеИспользование(FormControl.Param):
    def __init__(self):
        super().__init__('многоразовое_использование', 'Многоразовое использование', type='select')
        self.options = [
            ['1', 'Да'],
            ['', 'Нет']
        ]
    def readonly(self, page):
        return page.readonly()

    def get_value(self, page):
        reusable = page.series.reusable
        return '1' if reusable else ''
    def save(self, page):
        page.series.reusable = page.get(self.ID)
        page.save()
class СпособАктивации(FormControl.Param):
    def __init__(self):
        super().__init__('способ_активации', 'Способ активации', type='select')
        self.options = [
            [Series.activation_mode_SALE, 'Активация при покупке'.upper()],
            [Series.activation_mode_CREATE, 'Активация при создании'.upper()]
        ]
    def readonly(self, page):
        return page.readonly()
    def get_value(self, page):
        return page.series.info.get(Series.ACTIVATION_MODE, Series.activation_mode_CREATE)
    def save(self, page):
        page.series.info[Series.ACTIVATION_MODE] = page.get(self.ID)
        page.save()
        self.form_update(page)
class СоответствующийТовар(FormControl.Param):
    def __init__(self):
        super().__init__('соответствующий_товар', 'Соответствующий товар', type = 'select')
    def readonly(self, page):
        return page.readonly()

    def set_ID(self, page):
        if page.series.это_подарочная_карта:
            return ProductSet.ПОДАРОЧНЫЕ_КАРТЫ_ID
        else:
            return ProductSet.ДИСКОНТНЫЕ_КАРТЫ_ID
    def get_options(self, page):
        options = []
        if page.series.это_подарочная_карта:
            набор = ГотовыеНаборы(page.sqlite).готовый_набор(PS.ПОДАРОЧНЫЕ_КАРТЫ_ID)
        else:
            набор = ГотовыеНаборы(page.sqlite).готовый_набор(PS.ДИСКОНТНЫЕ_КАРТЫ_ID)
        набор.prepeare()
        goods = набор.query(page.postgres).limit(500).all()
        for good in goods:
            options.append([good.code, f'{good.name} ({good.code})'])

        #items = ProductSetItem.findall(page.cursor, 'TYPE=0 and product_set=?', [self.set_ID(page)])
        #for item in items :
        #    options.append([item.info['code'], item.наименование])
        return options
    def get_value(self, page):
        return page.series.info.get('product_code', '')
    def print(self, page, cell):
        code = page.series.info.get('product_code', '').strip()
        #name = page.series.info.get('product_name','')
        if not code:
            cell.text('НЕ ОПРЕДЕЛЕНО')
            cell.style('color:red')
        else:
            good = page.postgres.query(Good).filter(Good.code == code).first()
            cell.text(f'{good.name} ({code})')
    def save(self, page):
        CODE = page.get(self.ID)
        page.series.info['product_code'] = CODE
        page.save()
        #for code, name in self.get_options(page):
        #    if CODE == code:
        #        page.series.info['product_code'] = CODE
        #        page.series.info['product_name'] = name
        #        page.save()
    def visible(self, page):
        return page.series.info.get(Series.ACTIVATION_MODE, Series.activation_mode_CREATE) == Series.activation_mode_SALE
class Цена(FormControl.Param):
    def __init__(self):
        super().__init__('цена', 'Стоимость при продаже', type='number', min=100, max=100000)
    def readonly(self, page):
        return page.readonly()
    def visible(self, page):
        return page.series.info.get(Series.ACTIVATION_MODE, Series.activation_mode_CREATE) == Series.activation_mode_SALE
    def get_value(self, page):
        return page.series.price
    def print(self, page, cell):
        value = self.get_value(page)
        if value:
            cell.text(value)
        else:
            cell.text('НЕ ОПРЕДЕЛЕНО')
            cell.style('color:red')
    def save(self, page):
        page.series.price = page.get(self.ID)
        page.save()

ОсновныеПараметры = FormControl('параметры', width=25, mt=1, used_params='набор_основных_параметров')
ОсновныеПараметры.append(Наименование())
ОсновныеПараметры.append(МаксимальноеКоличествоПокупок())

ОсновныеПараметры.append(КоличествоБаллов())
ОсновныеПараметры.append(ПроцентСкидки())
ОсновныеПараметры.append(Номинал())
ОсновныеПараметры.append(МногоразовоеИспользование())
ОсновныеПараметры.append(СрокДействия())

ОсновныеПараметры.append(СпособАктивации())
ОсновныеПараметры.append(СоответствующийТовар())
ОсновныеПараметры.append(Цена())
ОсновныеПараметры.append(ФорматКода())
ОсновныеПараметры.append(СпособГенерацииНомера())

СозданиеПараметры = FormControl('создание_параметры', width=25, mt=1, used_params='набор_основных_параметров')
СозданиеПараметры.append(Префикс())
СозданиеПараметры.append(Суффикс())
СозданиеПараметры.append(КоличествоЦифр())
#СозданиеПараметры.append(СпособГенерацииНомера())
СозданиеПараметры.append(СледующийНомерКарты())

Закладки = TabControl('tabs')
Закладки.append('base_params', 'Основные параметры', 'основные_параметры')
Закладки.append('create_cards', 'Создание карт', 'создание_карт')

class TheSeriesPage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request, controls=[ОсновныеПараметры, СозданиеПараметры, Закладки])
        self.series_id = self.attribute('series_id')
        self.card_types = self.application['card_types']
        self._series = None
        self.CARD_MANAGER = (Grants.BOSS, Grants.CARD_MANAGER) in self.grants
        self.READONLY = (Grants.BOSS, Grants.CARD_MANAGER, Grants.ASSISTANT) not in self.grants

    def __getattr__(self, name):
        if name == 'user_name':
            user_name = self.request.sk_info.get('domino_user_name')
            self.__dict__[name] = user_name
            return user_name
        elif name == 'card_type':
            value = self.card_types[self.series.type]
            self.__dict__[name] = value
            return value
        return super().__getattr__(name)

    @property
    def series(self):
        if self._series is None:
            self._series = Series.get(self.cursor, self.series_id)
        return self._series
    def readonly(self):
        return self.series.status != -1 or self.READONLY
    def print_title(self):
        self.title(f'{self.series.id}, {self.series.полное_наименование}')
    def create_cards(self):
        try:
            is_test = self.get('test', '0') == '1'
            random = self.series.gen_mode_random
            user_name = self.user_name
            card_type = self.series
            activate = self.series.activation_mode == Series.activation_mode_CREATE

            if is_test:
                count = 1
            else:
                try:
                    count = int(self.get('count'))
                except:
                    self.error(f'Не задано количество создаваемых карт')
                    return
            if count < 1 or count > 1000:
                self.error(f'Слишком много карт "{count}"')
                return

            created = 0
            self.pg_connection.autocommit = True
            with self.pg_connection, self.connection:
                for n in range(count):
                    if random:
                        card = Card.создать_карту(self.engine, card_type, user_name = user_name, is_test = is_test)
                    else:
                        card = Card.создать_карту(self.engine, card_type, number = self.series.next_number, user_name = user_name, is_test = is_test)
                        self.series.next_number += 1
                        self.series.update(self.cursor)
                    if activate:
                        card.активировать(self.engine, card_type, user_name = user_name)
                    created += 1

            self.message(f'Создано {created} карт')
            self.создание_карт()
        except BaseException as ex:
            log.exception('')
            self.error(f'{ex}')
    def save(self):
        with self.connection:
            self.series.update(self.cursor)
    def набор_основных_параметров(self):
        return []
    
    def основные_параметры(self):
        ОсновныеПараметры(self)
        self.Table(СозданиеПараметры.ID)
        self.text_block('toolbar_about')
        self.text_block('toolbar')
        #self.print_toolbar()
    def создание_карт(self):
        log.debug(f'создание_карт')
        self.Table(ОсновныеПараметры.ID)
        СозданиеПараметры(self)
        self.print_toolbar()
    def параметры(self):
        Закладки(self)

    def print_toolbar(self):
        if self.CARD_MANAGER:
            if self.series.status == -1:
                self.text_block('about_toolbar').mt(1)
            else:
                if not self.series.gen_mode_random:
                    self.text_block('about_toolbar').mt(1).text('''
                    При создании карточек следует задать начальный номер и количество
                    карточек. Во избежании недоразумений, 
                    количество за один раз создаваемых карточек ограничено 1000.
                    ''')
                else:
                    self.text_block('about_toolbar').mt(1).text('''
                    При создании карточек следует задать количество
                    карточек. Номера карточек будут генерироватся случайным образом
                    Во избежании недоразумений, 
                    количество за один раз создаваемых карточек ограничено 1000.
                    ''')
                toolbar = self.toolbar('toolbar').mt(1)
                #if not self.series.gen_mode_random:
                #    toolbar.item().input(label='Начальный номер', name='first_number', type='number', value=self.series.info.get('next_number', ''))
                toolbar.item().input(name='count', label='Количество', type='number')
                if self.series.activation_mode == Series.activation_mode_CREATE:
                    КраснаяКнопка(toolbar, 'Создать и активировать', ml=0.5).onclick('.create_cards', forms=[toolbar])
                    #ПрозрачнаяКнопка(toolbar, 'создать и активировать тестовую карту', cls='ml-auto', ml=1)\
                    #    .onclick('.create_cards', {'test' : '1'},  forms=[toolbar])
                else:            
                    КраснаяКнопка(toolbar, 'Создать', ml=0.5).onclick('.create_cards', forms=[toolbar])
                    #ПрозрачнаяКнопка(toolbar, 'Создать тестовую карту', cls='ml-auto', ml=1)\
                    #    .onclick('.create_cards', {'test' : '1'}, forms=[toolbar])
    def settings_page(self):
        self.print_title()
        self.параметры()

