import os, datetime, sqlite3
from domino.core import log
from domino.page import Page, Filter, Toolbar, Table, PageControl, Panel


class FormControl(PageControl):
    class Param:
        def __init__(self, ID, description, type='text', default=None, undefined = None, min=0, max=0):
            self.ID = ID
            self.PARENT = None
            self.TYPE = type
            self.description = description
            self.width = 20
            self.options = []
            self.default = default
            self.undefined = undefined
            self.style = ''
            self.undefined_style = ''
            self.min = min
            self.max = max
        def __str__(self):
            return f'<FormControl.Param {self.ID}>'
        def to_float(self, value, default = None):
            #if default is None:
            #    default = self.default
            if value is None:
                return default
            else:
                try:
                    return float(value)
                except:
                    return default
        def to_int(self, value, default = None):
            #if default is None:
            #    default = self.default

            if value is None:
                return default
            else:
                try:
                    return int(value)
                except:
                    return default      
        def get_option_name(self, page, value):
            for opt_value, text in self.get_options(page):
                if value == opt_value:
                    return text
            return None
        def get_options(self, page):
            return self.options
        def print(self, page, cell):
            is_default = self.is_default(page)
            if is_default:
                cell.style(self.undefined_style)
                if self.undefined:
                    cell.html(self.undefined)
                    return
            else:
                cell.style(self.style)

            value = self.get_value(page)
            if value is None:
                value = self.default
            if self.TYPE == 'select' or self.TYPE == 'radio':
                name = self.get_option_name(page, value)
                if name is None:
                    cell.html(self.undefined if self.undefined is not None else '')
                else:
                    cell.html(name)
            elif self.TYPE == 'number':
                if self.undefined and self.default and value == self.default:
                    cell.html(self.undefined)
                else:
                    cell.html(f'{value}' if value else '')
            else:
                if self.undefined is not None and  (value is None or value == ''):
                    cell.html(self.undefined)
                else:
                    cell.html(value)
        def edit(self, page, cell):
            value = self.get_value(page)

            if self.TYPE == 'select':
                select = cell.select(name = self.ID, value = value)
                for option in self.get_options(page):
                    select.option(f'{option[0]}', f'{option[1]}')

            elif self.TYPE == 'radio':
                p = cell.toolbar()
                for option in self.get_options(page):
                    кнопка = ПрозрачнаяКнопка(p, option[1])
                    if self.PARENT is not None:
                        кнопка.onclick(f'.{self.PARENT.ID}.onsave', {'param_id':self.ID, self.ID : option[0]})

            elif self.TYPE == 'number':
                cell.input(name = self.ID, value = value, type=self.TYPE).style('width:10rem')

            else:
                cell.input(name = self.ID, value = value, type=self.TYPE)
        def readonly(self, page):
            return False
        def editable(self, page):
            return True
        def visible(self, page):
            return True
        def is_default(self, page):
            return not self.get_value(page)
            #value = self.get_value(page)
            #if value:
            #   return True
            #else:
            #    return False
        def get_value(self, page):
            return ''
        def save(self, page):
            pass
        def form_update(self, page):
            self.PARENT.__call__(page)
    def __init__(self, ID , width = 20, used_params = None, **kwargs):
        super().__init__(ID)
        self.params = []
        self.width = width
        self.used_params = used_params
        self.kwargs = kwargs
    def append(self, param):
        self.params.append(param)
        param.PARENT = self
    def get_param(self, param_id):
        for param in self.params:
            if param.ID == param_id:
                return param
        return None
    def print_row(self, page, row, param):
        cell = row.cell(width = self.width).text(param.description)
        #cell.style('background:#E5E8E8')
        #cell.style('text-align:right; font-weight: bold')
        cell.style('padding-left:0.5rem;')
        cell = row.cell()
        #cell.css('form-control')
        #cell.style('-margin:0.5rem;padding:.375rem .75rem; border: 0.3rem solid #F4F6F6; background-color:white')
        #cell.css('form-control')
        #cell.style('backgroung-color:white')
        try:
            param.print(page, cell)
        except BaseException as ex:
            log.exception(f'{self}.print_row')
            cell.text(f'{ex}').style('color:red')
        кнопки = СтандартныеКнопки(row, width=10)
        if param.readonly(page):
            кнопки.кнопка('')
        else:
            if hasattr(param, 'add'):
                add_tooltip = getattr(param, 'add_tooltip', None)
                if add_tooltip:
                    tooltip = add_tooltip(page)
                    if tooltip:
                        button = кнопки.кнопка('add', style='color:green').onclick(f'.{self.ID}.onadd', {'param_id':param.ID})
                        button.tooltip(tooltip)
            if hasattr(param, 'set_default') and not param.is_default(page):
                кнопки.кнопка('refresh', style='color:gray').onclick(f'.{self.ID}.ondelete', {'param_id':param.ID})\
                    .tooltip('УСТАНОВИТЬ ЗНАЧЕНИЕ ПО УМОЛЧАНИЮ')
            if param.editable(page):
                кнопки.кнопка('редактировать').onclick(f'.{self.ID}.onedit', {'param_id':param.ID})
                row.onclick(f'.{self.ID}.onedit', {'param_id':param.ID})
    def edit_row(self, page, row, param):
        row.css('table-warning')
        cell = row.cell(width = self.width).text(param.description)
        cell.style('padding-left:0.5rem;')
        #row.css('table-warning shadow', True)
        cell = row.cell()
        param.edit(page, cell)
        кнопки = СтандартныеКнопки(row, width=6)
        #if param.TYPE != 'select' and param.TYPE != 'radio':
        кнопки.кнопка('сохранить').onclick(f'.{self.ID}.onsave', {'param_id':param.ID}, forms=[row])
        кнопки.кнопка('отменить').onclick(f'.{self.ID}.oncancel', {'param_id':param.ID})
        if param.TYPE == 'select':
            cell.onchange(f'.{self.ID}.onsave', {'param_id':param.ID}, forms=[row])
        else:
            cell.onkeypress(13, f'.{self.ID}.onsave', {'param_id':param.ID}, forms=[row])
    def oncancel(self, page):
        param = self.get_param(page.get('param_id'))
        if param is not None:
            row = page.Row(self.ID, param.ID)
            self.print_row(page, row, param)
    def onedit(self, page):
        param = self.get_param(page.get('param_id'))
        if param is not None:
            row = page.Row(self.ID, param.ID)
            self.edit_row(page, row, param)
    def onsave(self, page):
        param = self.get_param(page.get('param_id'))
        if param is not None:
            try:
                param.save(page)
                row = page.Row(self.ID, param.ID)
                self.print_row(page, row, param)
            except BaseException as ex:
                log.exception(f'{self}.onsave')
                page.error(f'{ex}')
    def ondelete(self, page):
        param = self.get_param(page.get('param_id'))
        if param is not None:
            try:
                param.set_default(page)
                row = page.Row(self.ID, param.ID)
                self.print_row(page, row, param)
            except BaseException as ex:
                log.exception(f'{self}.onsave')
                page.error(f'{ex}')
    def onadd(self, page):
        param = self.get_param(page.get('param_id'))
        if param is not None:
            try:
                param.add(page)
                row = page.Row(self.ID, param.ID)
                self.print_row(page, row, param)
            except BaseException as ex:
                log.exception(f'{self}.onsave')
                page.error(f'{ex}')
    def __call__(self, page, params = None, **kwargs):
        #table = ПлоскаяТаблица(page, self.ID, **kwargs)
        table = page.Table(self.ID, css = 'table-sm table-borderless table-hover',  **self.kwargs)
        table.style('background-color:#F4F6F6;')
        #table.style('padding:0.3rem;')
        #table.cls('table-hover', False)
        table.style('border-radius:0.5rem')
        #table.style('border-color:gray')
        #table.style('border-width:1px')
        #table.css('shadow-sm')
        if self.used_params:
            USED_PARAMS = getattr(page, self.used_params)
            used_params = USED_PARAMS()
        else:
            used_params = params
        for param in self.params:
            param.PARENT = self
            if used_params:
                if param.ID not in used_params:
                    continue
            if not param.visible(page):
                    continue
            row = table.row(param.ID)
            self.print_row(page, row, param)

class ТабличнаяФорма:
    class Параметр:
        def __init__(self, id, description, request = 'ТабличнаяФорма_request', type='text'):
            self.ID = id
            self.TYPE = type
            self.description = description
            self.словарь = {}
            self.список = []
            self.request = f'.{request}'
            self.param_id = f'{self.ID}_ID'
            self.width = 20

        def __str__(self):
            return f'Параметр({self.ID})'

        def option(self, key, value):
            KEY = key
            self.список.append([KEY, value])
            self.словарь[KEY] = value

        def options(self, options):
            for option in options:
                self.список.append(option)
                self.словарь[option[0]] = option[1]
        
        def get_options(self, page):
            return self.список
        
        def print_value(self, page, row, value):
            if self.TYPE == 'select':
                row.text(self.словарь.get(value, value))
            else:
                row.text(value)

        def response(self, page):
            request = page.get('request')
                
        def readonly(self):
            return False
        
        def get_value(self, page):
            return ''

        def save(self, page):
            pass

        def __call__(self, table, edit_mode = False):
            page = table.page
            row = table.row(self.ID)
            row.cell(width=self.width).text(self.description)
            value = self.get_value(page)
            if edit_mode:
                cell = row.cell()
                кнопки = СтандартныеКнопки(row, width=6)
                if self.TYPE == 'select':
                    select = cell.select(name = self.ID, value = value)
                    for option in self.get_options(page):
                        select.option(option[0], option[1])
                    row.onchange(self.request, {'param_id' : self.param_id, 'request':'сохранить'}, forms=[row])
                else:
                    cell.input(name = self.ID, value= value, type=self.TYPE)
                    кнопки.кнопка('сохранить').onclick(self.request, {'param_id' : self.param_id, 'request':'сохранить'}, forms=[row])
                    row.onkeypress(13, self.request, {'param_id' : self.param_id, 'request':'сохранить'}, forms=[row])
                кнопки.кнопка('отменить').onclick(self.request, {'param_id' : self.param_id, 'request':'отменить'})
                row.on('onblur', self.request, {'param_id' : self.param_id, 'request':'отменить'})
                row.cls('table-warning', False)
            else:
                self.print_value(page, row, value)
                #if self.TYPE == 'select':
                #    row.text(self.словарь.get(value, value))
                #else:
                #    row.text(value)
                кнопки = СтандартныеКнопки(row, width=6)
                кнопки.кнопка('редактировать').onclick(self.request, {'param_id' : self.param_id, 'request': 'редактировать'})
                row.onclick(self.request, {'param_id' : self.param_id, 'request': 'редактировать'})

        def значение(self, cell, page):
            cell.text('')

        def форма_ввода(self, cell, page):
            cell.input(name=self.ID, value = '')

        def сохранить(self, page):
            pass

        def удалить(self, page):
            pass

        def можно_удалить(self, page):
            return None

    def __init__(self, ID):
        self.ID = ID
        self._параметры = []
        self.словарь = {}

    def __str__(self):
        return f'ТабличнаяФорма({self.ID})'
    
    @property
    def параметры(self):
        return self._параметры
    @параметры.setter
    def параметры(self, value):
        self._параметры = value
        self.словарь = {}
        for параметр in self.параметры:
            self.словарь[параметр.ID] = параметр

    def __call__(self, page):
        table = ПлоскаяТаблица(page, self.ID)
        for параметр in self.параметры:
            row = table.row(параметр.ID)
            self.параметр(row, параметр, page)

    def параметр(self, row, параметр, page):
        params={f'{self.ID}_param_id':параметр.ID}
        row.onclick(f'.{self.ID}_редактировать', params)
        row.cell(cls='align-middle', width=10).text(параметр.description)
        параметр.значение(row.cell(), page)
        кнопки = СтандартныеКнопки(row)
        удалить = параметр.можно_удалить(page)
        if удалить is not None:
            кнопки.кнопка('удалить', f'{self.ID}_удалить', params, подсказка=удалить)
        кнопки.кнопка('редактировать', f'{self.ID}_редактировать', params)
        #row.cell(cls='text-right').icon_button('aw/pen', size='small', style="font-size:0.9rem;color:gray")
    
    def responce(self, page):
        параметр_ID = page.get(f'param_id')
        if параметр_ID is None:
            параметр = self.словарь[параметр_ID]
            if параметр is not None:
                параметр.responce(page)

    def редактировать(self, page):
        param_id = page.get(f'{self.ID}_param_id')
        параметр = self.словарь[param_id]
        row = page.Row(self.ID, параметр.ID)
        row.cell(cls='align-middle', width=10).text(параметр.description)

        параметр.форма_ввода(row.cell(), page)
        #params={f'{self.ID}_param_id':параметр.ID}
        кнопки = СтандартныеКнопки(row, params={f'{self.ID}_param_id':параметр.ID})
        кнопки.кнопка('сохранить', f'{self.ID}_сохранить', forms=[row])
        кнопки.кнопка('отменить', f'{self.ID}_отменить')
        #print_std_buttons(row, width=6, cancel=f'{self.ID}_отменить', save=f'{self.ID}_сохранить', size='small', params=params, forms=[row])

    def отменить(self, page):
        param_id = page.get(f'{self.ID}_param_id')
        параметр = self.словарь[param_id]
        row = page.Row(self.ID, параметр.ID)
        self.параметр(row, параметр, page)

    def сохранить(self, page):
        try:
            param_id = page.get(f'{self.ID}_param_id')
            параметр = self.словарь[param_id]
            параметр.сохранить(page)
            row = page.Row(self.ID, параметр.ID)
            self.параметр(row, параметр, page)
        except BaseException as ex:
            log.exception(f'{self}.сохранить')
            page.error(f'{ex}')

    def удалить(self, page):
        try:
            param_id = page.get(f'{self.ID}_param_id')
            #log.debug(f'{self}.сохранить param_id={param_id}')
            параметр = self.словарь[param_id]
            параметр.удалить(page)
            row = page.Row(self.ID, параметр.ID)
            self.параметр(row, параметр, page)
        except BaseException as ex:
            log.exception(f'{self}.удалить')
            page.error(f'{ex}')


DISABLE_COLOR = 'rgb(220,220,210)'
КРАСНЫЙ_ЦВЕТ = 'rgb(255,64,129)'
КРАСНЫЙ_ЦВЕТ = 'red'
#КРАСНЫЙ_ЦВЕТ = 'tomato'
#КРАСНЫЙ_ЦВЕТ = '#F1948A'
#КРАСНЫЙ_ЦВЕТ = 'white'
СТИЛЬ_КРАСНОЙ_КНОПКИ = f'-font-size:0.8rem; background-color:red; color:white;'
#СТИЛЬ_КРАСНОЙ_КНОПКИ = f'font-size:0.9rem; background-color:gray; color:white;'
#СТИЛЬ_КРАСНОЙ_КНОПКИ = f'font-size:0.9rem; background-color:lightgray; color:#273746;'
ЦВЕТ_КРАСНОЙ_КНОПКИ = f'color:{КРАСНЫЙ_ЦВЕТ};'
ЦВЕТ_КРАСНОЙ_КНОПКИ = f'color:red;'


def _item_for_button(widget, **kwargs):
    if isinstance(widget, Toolbar):
        return widget.item(**kwargs)
    else:
        return widget
        
def __button(container, **kwargs):
    if isinstance(container, Toolbar):
        return container.item(**kwargs).button(**kwargs)
    elif isinstance(container, Panel):
        return container.item().Button(**kwargs)
    elif isinstance(container, Panel.Item):
        return container.Button(**kwargs)
    else:
        return container.button(**kwargs)

def КраснаяКнопка(container, text='', **kwargs):
    button = __button(container, **kwargs)
    button.text(text)
    #item = _item_for_button(container, **kwargs)
    if container.FRAMEWORK == 'MDL':
        #button = item.button(text, **kwargs)
        #button.cls('btn')
        button.cls("mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent")
        #button.style('border: 1px solid lightgray ;')
        button.style('font-size:0.9rem')
        #button.style('border-radius: 1rem')
        #button.style('border-radius: 2rem')
        #button.style('font-weight:bold')
    #if isinstance(panel, Toolbar):
    #    item = panel.item(**kwargs)
    #else:
    #    item = panel
    else:
        #button = item.button(text) 
        button.cls('btn')

    #if panel.FRAMEWORK == 'MDL':
        #return item.button(text).style(f'{СТИЛЬ_КРАСНОЙ_КНОПКИ}').cls("mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent")
    return button
    #else:
    #    return item.button(text.upper()).cls('btn btn-danger')
def ОсновнаяКнопка(panel, text='', **kwargs):
    if isinstance(panel, Toolbar):
        item = panel.item(**kwargs)
    else:
        item = panel
    #if panel.FRAMEWORK == 'MDL':
        #return item.button(text).style(f'{СТИЛЬ_КРАСНОЙ_КНОПКИ}').cls("mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent")
    return item.button(text).cls("mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--primary")
    #else:
    #    return item.button(text.upper()).cls('btn btn-primary')
def Кнопка(container, text='', **kwargs):
    button = __button(container, **kwargs)
    button.text(text)
    #item = _item_for_button(container, **kwargs)
    if container.FRAMEWORK == 'MDL':
        #button = item.button(text, **kwargs)
        button.cls('btn')
        button.cls("mdl-button mdl-js-button -mdl-button--raised mdl-js-ripple-effect -mdl-button--primary")
        #button.style('border: 1px solid lightgray ;')
        button.style('border: 1px solid gray ;')
        #button.cls("mdl-button mdl-button mdl-js-button mdl-js-ripple-effect")
        #button.cls('shadow-sm')
        #button.style('background:#F8F9F9    ; color:white; font-size:0.8rem')
        #button.style('-background:#F2F3F4  ; border: 1px solid lightgray ; -color:white; font-size:0.8rem')
        button.style('font-size:0.9rem')
        button.style('border-radius: 0.3rem')
        #button.style('border-radius: 2rem')
        #button.style('font-weight:bold')
        button.style('font-size:0.8rem')
    else:
        #button = item.button(text) 
        button.cls('btn')
    return button
    
def КнопкаВыбор(container, text='', **kwargs):
    item = _item_for_button(container, **kwargs)
    if container.FRAMEWORK == 'MDL':
        button = item.drop_down(text.upper())
        button.cls('btn')
        button.cls("mdl-button mdl-js-button -mdl-button--raised mdl-js-ripple-effect -mdl-button--primary")
        #button.cls('shadow-sm')
        #button.style('background:#7A8A8A   ; color:white; font-size:0.8rem')
        #button.style('border: 1px solid lightgray ;')
        button.style('border: 1px solid gray ;')
        #button.style('border-radius: 2rem')
        button.style('border-radius: 0.3rem')
        #button.style('font-weight:bold')
        button.style('font-size:0.8rem')
    else:
        button = item.drop_down(text.upper())
        button.cls('btn btn-primary')
    return button 
def КраснаяКнопкаВыбор(panel, text='', **kwargs):
    return panel.item(**kwargs).drop_down(text.upper())\
            .cls('-btn -btn-secondary mdl-button mdl-js-button mdl-js-ripple-effect')\
            .style(f'-background-color:white; -color:black; -padding:0.6rem')

def ПрозрачнаяКнопка(container, text='', **kwargs):
    item = _item_for_button(container, **kwargs)
    if container.FRAMEWORK == 'MDL':
        button = item.button(text, **kwargs)
        button.cls("mdl-button mdl-js-button mdl-js-ripple-effect")
        button.style('font-size:0.8rem')
        #button.style('background:#85929E  ; color:white; font-size:1rem')
    else:
        button = item.button(text)
        button.cls('btn')
    return button

Button = Кнопка
#ПрозрачнаяКнопка = Кнопка
КраснаяКнопкаВыбор = КнопкаВыбор
ПрозрачнаяКнопкаВыбор = КнопкаВыбор
 
def ПлоскаяТаблица(page, id = None, **kwargs):
    table = Table(page, id, hole_update = True, css = 'table-sm table-borderless table-hover')
    page.append(table)
    return table

class CheckButton:
    def __init__(self, id, size=None, cls=None, icon='check'):
        self.id = id
        self.size = size
        self.cls = cls
        self.icon = icon

    def __call__(self, item, checked, params = {}):
        return self.print_yourself(item,checked,params)

    def print_yourself(self, item, checked, params = {}):
        button = item.button().cls('btn bg-white')
        if self.size is not None and self.size == 'small':
            button.small()
        if self.cls is not None:
            item.cls(self.cls)
        params[self.id] = "1" if checked else "0"
        if checked:
            button.glif(self.icon, css = 'text-success').onclick(f'.{self.id}', params)
        else:
            button.glif(self.icon, style='color:rgb(220,220,210)').onclick(f'.{self.id}', params)
        return button

def print_check_button(row, ID, checked, params={}, size=None, icon='check', cls='text-success'):
    if isinstance(row, Toolbar):
        button = row.item().button().cls('btn bg-white')
    else:
        cell = row.cell(width=2, cls='align-middle')
        button = cell.button().cls('btn bg-white')
    if size is not None and size == 'small':
        button.small()
    params[ID] = "1" if checked else "0"
    
    if checked:
        button.glif(icon, css = cls).onclick(f'.{ID}', params)
    else:
        button.glif(icon, style='color:rgb(220,220,210)').onclick(f'.{ID}', params)
    return button

class СтандартныеКнопки:
    def __init__(self, row, params = {}, width = None, align=None): 
        self.row = row
        self.params = params
        if isinstance(row, Toolbar):
            self.cell = row.item(width=width)
        else:
            self.cell = row.cell(cls='align-middle')
            if align is None:
                self.cell.cls('text-right')
            else:
                align = align.upper()
                if align.find('RIGHT') != -1: 
                    self.cell.cls('text-right')
                elif align.find('LEFT') != -1:
                    self.cell.cls('text-left')
            #self.cell = row.cell(cls='text-right align-middle')
        if width is not None:
            self.cell.width(width)
        self.первая_кнопка = True
    
    def _onclick(self, button, url, params, forms = []):
        button.onclick(f'.{url}', params if params is not None else self.params, forms)

    def удалить(self, url, params = None, forms=[], подсказка = None):
        button = self.cell.icon_button('close').style(ЦВЕТ_КРАСНОЙ_КНОПКИ)
        self._onclick(button, url, params, forms)
        button.tooltip(подсказка)
        if not self.первая_кнопка:
            button.style('margin-left=0.5rem')
            self.первая_кнопка = False

    def сохранить(self, url, params = None, forms=[], подсказка = None):
        #self.row.cls('shadow table-warning')
        button = self.cell.icon_button('save')
        #.style(ЦВЕТ_КРАСНОЙ_КНОПКИ)
        self._onclick(button, url, params, forms)
        button.tooltip(подсказка)
        if not self.первая_кнопка:
            button.style('margin-left=0.5rem')
            self.первая_кнопка = False

    def кнопка(self, name = '', url = None, params = None, forms=[], подсказка = None, style = None):
        name = name.lower()
        if name == 'удалить':
            button = self.cell.icon_button('close').style(ЦВЕТ_КРАСНОЙ_КНОПКИ).style(style)
        elif name == 'сохранить':
            button = self.cell.icon_button('done').style('color:green').style(style)
            #self.row.cls('-mdl-shadow--3dp -shadow-sm table-warning')
            #.style(ЦВЕТ_КРАСНОЙ_КНОПКИ)
        elif name == 'добавить':
            button = self.cell.icon_button('add_circle').style(ЦВЕТ_КРАСНОЙ_КНОПКИ).style(style)
        elif name == 'редактировать':
            #button = self.cell.icon_button('edit').style('color:#E5E8E8').style(style)
            button = self.cell.icon_button('edit').style('color:lightgray').style(style)
        elif name == 'включено':
            button = self.cell.icon_button('check').style('color:green').style(style)
        elif name == 'выключено':
            button = self.cell.icon_button('check').style(f'color:{DISABLE_COLOR}').style(style)
        elif name == 'копировать':
            button = self.cell.icon_button('content_copy').style('color:gray').style(style)
        elif name == 'отменить':
            button = self.cell.icon_button('close').style(style)
        elif name == 'вперед':
            button = self.cell.icon_button('arrow_forward').style(style)
        #elif name == 'восстановить':
        #    button = self.cell.icon_button('clear_all').style('color:lightgray')
        else:
            button = self.cell.icon_button(name).style(style)
        if url is not None:
            button.onclick(f'.{url}', params if params is not None else self.params, forms)
        if подсказка is not None:
            button.tooltip(подсказка)
        if not self.первая_кнопка:
            button.style('margin-left=0.5rem')
            self.первая_кнопка = False
        return button

def print_std_buttons(row, params={}, forms=[], save=None, edit=None, cancel=None, delete=None, add=None, copy=None, size=None, width = None):
    cell = row.cell(cls='text-right align-middle')
    if width is not None:
        cell.width(width)
    #is_small = size is not None and size == 'small'
    is_first = True

    if save is not None:
        row.cls('shadow table-warning')
        button = cell.icon_button('save').style(ЦВЕТ_КРАСНОЙ_КНОПКИ)\
            .onclick(f'.{save}', params, forms)
        if not is_first:
            button.cls('ml-1')
        is_first = False

    if cancel is not None:
        button = cell.icon_button('close')\
            .onclick(f'.{cancel}', params)
        if not is_first:
            button.cls('ml-1')
        is_first = False

    if edit is not None:
        #row.onclick(f'.{edit}', params)
        button = cell.icon_button('edit').style('color:#F2F4F4')\
            .onclick(f'.{edit}', params)
        if not is_first:
            button.cls('ml-1')
        is_first = False

    if add is not None:
        button = cell.icon_button('add_circle').style(ЦВЕТ_КРАСНОЙ_КНОПКИ)\
            .onclick(f'.{add}', params)
        if not is_first:
            button.cls('ml-1')
        is_first = False

    if copy is not None:
        button = cell.icon_button('content_copy').style('color:gray')\
            .onclick(f'.{copy}', params)
        if not is_first:
            button.cls('ml-1')
        is_first = False

    if delete is not None:
        button = cell.icon_button('close').style(ЦВЕТ_КРАСНОЙ_КНОПКИ)\
            .onclick(f'.{delete}', params)
        button.tooltip('Удалить')
        if not is_first:
            button.cls('ml-1')
        is_first = False

    if is_first:
        button = cell.icon_button('')

class EditButton:
    def __init__(self, id, size=None, cls=None):
        self.id = id
        self.size = size
        self.cls = cls

    def __call__(self, item, params = {}):
        return self.print_yourself(item, params)

    def print_yourself(self, item, params = {}):
        button = item.button().cls('bg-white')
        if self.size is not None and self.size == 'small':
            button.small()
        if self.cls is not None:
            item.cls(self.cls)
        button.glif('pen', style='color:lightgray').onclick(f'.{self.id}', params)
        return button

class CancelButton:
    def __init__(self, id, size=None, cls=None):
        self.id = id
        self.size = size
        self.cls = cls

    def __call__(self, item, params = {}):
        return self.print_yourself(item, params)

    def print_yourself(self, item, params = {}):
        button = item.button().cls('bg-white')
        if self.size is not None and self.size == 'small':
            button.small()
        if self.cls is not None:
            item.cls(self.cls)
        button.glif('times', style='color:lightred').onclick(f'.{self.id}', params)
        return button

class SaveButton:
    def __init__(self, id, size=None, cls=None):
        self.id = id
        self.size = size
        self.cls = cls
    
    def __call__(self, item, params = {}, forms=[]):
        return self.print_yourself(item, params, forms)

    def print_yourself(self, item, params = {}, forms=[]):
        button = item.button().cls('bg-white')
        if self.size is not None and self.size == 'small':
            button.small()
        if self.cls is not None:
            item.cls(self.cls)
        button.glif('save').onclick(f'.{self.id}', params, forms)
        return button

class DeleteButton:
    def __init__(self, id, size=None, cls=None):
        self.id = id
        self.size = size
        self.cls = cls
    
    def __call__(self, item, params = {}):
        button = item.button().cls('bg-white')
        if self.size is not None and self.size == 'small':
            button.small()
        if self.cls is not None:
            item.cls(self.cls)
        button.glif('trash', style='color:red').onclick(f'.{self.id}', params)
        return button

class TabControlItem:
    def __init__(self, id, text, fn=None, visible = None):
        self.id = id
        self.text = text.upper()
        self.fn = fn if fn else id
        self.visible_method = visible
    @property
    def ID(self):
        return self.id

    def __str__(self):
        return f'TabControlItem({self.id})'

class TabControl(PageControl):
    def __init__(self, ID , size=None, mt=None, visible=None, наименование_закладки = None):
        super().__init__(ID)
        self.size = size
        self.mt = mt
        self.items = []
        self.visible_method = visible
        self._наименование_закладки = наименование_закладки
        #log.debug(f'{self}.__init__({ID})')

    def __str__(self):
        return f'TabControl({self.ID})'

    def remove(self, tab_id):
        founded = None
        for i in range(0, len(self.items)):
            if self.items[i].id == tab_id:
                founded = i
                break
        if founded is not None:
            del self.items[founded]

    def append(self, id, text, fn, visible = None):
        self.items.append(TabControlItem(id, text, fn, visible))
    def insert(self, id, text, fn, visible = None):
        self.items.insert(0, TabControlItem(id, text, fn, visible))
    def item(self, id, text, fn = None):
        self.items.append(TabControlItem(id, text, fn))
    
    def default(self, page):
        for item in self.items:
            if self.is_item_visible(page, item):
                return item.id
        return None

    def is_item_visible(self, page, tab_item):
        #log.debug(f'{self}.is_item_visible(page, {tab_item})')
        if self.visible_method is not None:
            page_visible_method = getattr(page, self.visible_method, None)
            #log.debug(f'{page_visible_method} = getattr(page, {self.visible_method}, None)')
            if page_visible_method is not None:
                visible = page_visible_method(tab_item.id)
                if not visible:
                    #log.debug(f'{self}.is_item_visible(page, {tab_item}) = False')
                    return False
        if tab_item.visible_method is not None:
            page_visible_method = getattr(page, tab_item.visible_method, None)
            if page_visible_method is not None:
                visible = page_visible_method()
                if not visible:
                    #log.debug(f'{self}.is_item_visible(page, {tab_item}) = False')
                    return False
        #log.debug(f'{self}.is_item_visible(page, {tab_item}) = True')
        return True

    def наименование_закладки(self, page, закладка):
        if self._наименование_закладки is not None:
            try:
                method = getattr(page, self._наименование_закладки)
                if method is not None:
                    наименование = method(закладка.id)
                    if наименование is not None:
                        return наименование
            except:
                pass
        return закладка.text

    def print(self, page):
        self.__call__(page)

    def __call__(self, container):
        
        if isinstance(container, Panel):
            page = container.page
            tabs = container.item().Tabs(self.ID)
        else:
            page = container
            container = None
            tabs = page.Tabs(self.ID)

        active_tab_id = page.attribute(self.ID, self.default(page))
        if self.size is not None:
            if self.size == 'small':
                tabs.small()
        if self.mt is not None:
            tabs.mt(self.mt)
        active_item = None
        for item in self.items:
            if self.is_item_visible(page, item):
                is_active = active_tab_id == item.id
                if is_active: 
                    active_item = item
                tabs.item().text(self.наименование_закладки(page, item)).active(is_active)\
                    .onclick(f'.{self.ID}.print', {self.ID : item.id})
                #log.debug(f'PRINT .onclick({self.ID}.print)')

        if active_item is not None:
            try:
                page_print = getattr(page, active_item.fn)
                #log.debug(f'{self}.print(page).page_print({active_item.fn})')
                if container:
                    page_print(container)
                else:
                    page_print()
            except:
                log.exception(f'{self}.print(page)')
        return tabs

