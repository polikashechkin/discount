import sys, os, arrow, datetime, re, redis, json
import io
from domino.core import log
from domino.account import find_account
import flask
import html as HTML

def make_download_file_responce(file, file_name=None):
    #log.debug(f'{self}.download("{file}", file_name="{file_name}")')
    if not os.path.isfile(file):
        return f'File "{file}" not found','404 File "{file}" not found'
    if file_name is None:
        file_name = os.path.basename(file)
    with open(file, 'rb') as f:
        response  = flask.make_response(f.read())
    response.headers['Content-Type'] = 'application/octet-stream'
    #response.headers['Content-Description'] = 'File Transfer'
    response.headers['Content-Disposition'] = 'attachment; filename={0}'.format(file_name)
    response.headers['Content-Length'] = os.path.getsize(file)
    return response
   
def make_show_file_responce(file):
    #log.debug(f'{self}.download("{file}", file_name="{file_name}")')
    if not os.path.isfile(file):
        return f'File "{file}" not found','404 File "{file}" not found'
    with open(file, 'rb') as f:
        response  = flask.make_response(f.read())
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    #response.headers['Content-Description'] = 'File Transfer'
    response.headers['Content-Disposition'] = 'inline'
    response.headers['Content-Length'] = os.path.getsize(file)
    return response

MAX_COLUMNS = 100

class Filter:
    def __init__(self, filter = None):
        if filter is not None:
            self.filter = str(filter).strip().upper()
            if self.filter == '':
                self.filter = None
        else:
            self.filter = None

    def match(self, *names):
        if self.filter is None:
            return True
        for name in names:
            if str(name).upper().find(self.filter) != -1:
                return True
        return False

    def __bool__(self):
        return self.filter is not None

    def __str__(self):
        return self.filter if self.filter is not None else ''

BOOTSTRAP4 = 'B4'
MATERIAL_BOOTSTRAP = 'MB'
MATERIAL_DISAGN_LITE = 'MDL'
MDL = 'MDL'

class PageControl:
    def __init__(self, ID):
        self.ID = ID
    def make_response(self, fn, page):
        #log.debug(f'PageControl({self.ID}).make_response({fn})')
        f = getattr(self, fn, None)
        if f is not None:
            f(page)
            return True
        else:
            return False

class Request:
    def __init__(self, flask_request, application):
        self.request = flask_request
        self.flask_request = flask_request
        self.application = application
        self._sk_info = None

    @property
    def sk_info(self):
        if self._sk_info is None:
            SK = self.request.args['sk']
            r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
            self._sk_info = r.hgetall(SK)
        return self._sk_info
    
    @property
    def user_name(self):
        return self.sk_info.get('domino_user_name', '')
    
    @property
    def user_id(self):
        return self.sk_info.get('domino_user_id')
         
    @property 
    def url(self):
        return self.request.url
    @property
    def args(self):
        return self.request.args
    @property
    def form(self):
        return self.request.form
    @property
    def files(self):
        return self.request.files
 
    def get(self, *names):
        for name in names:
            value = self.flask_request.args.get(name)
            if value is None and self.flask_request.method == 'POST':
                value = self.flask_request.form.get(name)
            if value is not None:
                return value
        return None

    def get_int(self, name, default=None):
        try:
            return int(self.get(name))
        except:
            return default
 
    def arg(self, name):
        value = self.request.args.get(name)
        if value is None and self.request.method == 'POST':
            value = self.request.form.get(name)
        return value

    def account(self):
        account = find_account(self.account_id())
        if account is None:
            raise Exception('Соединение аннулировано. Требуется перезагрузка.')
        return account 

    def account_id(self):
        account_id = self.request.args.get('account_id')
        if account_id is not None:
            return account_id
        return self.sk_info.get('account')

    def download(self, file, file_name = None):
        return make_download_file_responce(file, file_name)

    def __str__(self):
        return f'Request()'

class Page:
    def __init__(self, application, request, controls = None, framework = None):
        self.application = application

        # REQUEST ------------
        self.ARGS = request.args
        self.FORM = request.form if request.method == 'POST' else None
        self.request = Request(request, application)

        # CONTROLS -----------
        if controls:
            self.CONTROLS = {}
            for control in controls:
                self.CONTROLS[control.ID] = control
        else:
            self.CONTROLS = None

        # FRAMEWORK ----------        
        if framework:
            self.FRAMEWORK = framework
        else:
            self.FRAMEWORK = application.framework

        # UPDATE ------------
        if request.args.get("_pu"):
            self.UPDATE = True
        else:
            self.UPDATE = False
        
        # SESSION_KEY -------
        SK = request.args.get('sk')
        self.redis = None
        if SK:
            self.SK = SK
            r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis = r
            SK_INFO = r.hgetall(SK)
            if SK_INFO:
                self.SK_INFO = SK_INFO
                self.account_id = SK_INFO.get('account')
                self.user_id = SK_INFO.get('domino_user_id')
                self.user_name = SK_INFO.get('domino_user_name')

        # PATH ---------------
        self.python = f'/{self.application.product_id}/active/python'
        self.attributes = {'sk': SK if SK else ''}
        self.path = request.path.split('.', 1)[0]
        self.path = self.path[1:]
        self.fullpath = os.path.join(self.python, self.path)

        # CONTEXT ------------
        #self.user_context = {}
        #if self.redis is not None: 
        #    user_context = self.redis.hget(self.SK, self.user_id)
        #    if user_context is not None:
        #        self.user_context = json.loads(user_context)


        # WIDGETS ------------
        self.TITLE = None
        self.MESSAGE = Message(self, 'page_message')
        self.NAVBAR = None
        #self.WIDGETS = []
        self._widgets = {}
        self.REFRESH = False

        # GRANTS ------------
        #self.grants = None
    
    #@property
    #def page(self):
    #    return self

    @property
    def WIDGETS(self):
        return self._widgets.values()

    def widget(self, wg):
        return self.append(wg)

    def append(self, wg):
        if wg.ID is None:
            wg.ID = f'__{len(self._widgets)}'
        self._widgets[wg.ID] = wg
        return wg

    def set_user_context(self, **kwargs):
        #for key, value in kwargs.items():
        #    self.user_context[key] = value
        #self.redis.hset(self.SK, self.user_id, json.dumps(self.user_context, ensure_ascii=False))
        pass

    def make_response(self, fn = None):
        #log.debug(f'PAGE.make_response ({fn})')
        try:
            make_response = False
            control_ID = None
            if fn:
                pos = fn.find('.')
                if pos != -1:
                    control_ID = fn[:pos]
                    control_fn = fn[pos+1:]
                    #log.debug(f'control_ID={control_ID}, control_fn={control_fn}, CONTROLS={self.CONTROLS}')
                    if self.CONTROLS is not None:
                        control = self.CONTROLS.get(control_ID)
                        if control is not None:
                            make_response = control.make_response(control_fn, self)
                
            if not make_response:
                if fn:
                    func = getattr(self, fn,  None)
                    #log.error(f'getattr(self, "{fn}" => {func}')
                else:
                    func = getattr(self, '__call__',  None)
                    if func is None:
                        func = getattr(self, 'open',  None)

                if func is None:
                    return None
                func()
                make_response = True

            if make_response:
                #log.debug(f'make_response I')
                if self.get('_pu'):
                    return self.update()
                else:
                    if self.NAVBAR is None:
                        self.application['navbar'](self)
                    response = flask.make_response(self.html())
                    response.headers['Cache-Control'] = 'no-store'
                    return response
            return None
        except BaseException as ex:
            log.exception(self.request.url)
            return f'{ex}', 500
    
    def get(self, name, default = None):
        value = self.ARGS.get(name)
        if value is None and self.FORM is not None:
            value = self.FORM.get(name)
        #if value is None:
        #    value = self.user_context.get(name)
        return value if value is not None else default

    def get_int(self, name, default = None):
        try:
            return int(self.get(name))
        except:
            return default

    def get_date(self, name, default = None):
        try:
            return arrow.get(self.get(name)).date()
        except:
            return default

    def attribute(self, name, default = None):
        value = self.get(name, default)
        if value is not None:
            self.attributes[name] = value
        return value

    def __getitem__(self, name):
        return self.attributes.get(name)
    def __setitem__(self, name, value):
        self.attributes[name] = value
    
    def url(self, href, params = {}, is_href=False):
        try:
            if href == None or href == '':
                return ''
            if href.find(':') != -1:
                # полный путь
                return href 

            if href[0] == '.':
                href = f'{self.fullpath}{href}'
            elif href[0] != '/':
                href = f'{self.python}/{href}'

            args = []

            url_params = {}
            for key, value in self.attributes.items():
                if is_href and key == '_pu':
                    continue
                if value is not None:
                    url_params[key] = str(value)

            if params is not None:
                for key, value in params.items():
                    url_params[key] = value

            for name, value in url_params.items():
                args.append(f'{name}={value}')
                
            if len(args) > 0:
                arglist = '&'.join(args)
                return f'{href}?{arglist}'
            else:
                return href
        except:
            log.exception(f'url({href})')
            return href
    def prepeare_for_update(self):
        if self.TITLE is not None:
            self.TITLE.prepeare_for_update()
        if self.NAVBAR is not None:
            self.NAVBAR.prepeare_for_update()
        if self.MESSAGE is not None:
            self.MESSAGE.prepeare_for_update()
        for widget in self.WIDGETS:
            widget.prepeare_for_update()
    def update(self):
        if self.REFRESH:
            return 'REFRESH'
        else:
            self.prepeare_for_update()
            return flask.render_template('page_update.html', page = self)
    def html(self):
        return flask.render_template('page.html', page = self)
    # Navbar
    def navbar(self):
        self.NAVBAR = Navbar(self, 'page_navbar')
        return self.NAVBAR
    # Title
    def title(self, text):
        return Title(self, text)
        #self.TITLE = Title(self, 'page_title')
        #self.TITLE.text(text)
        #return self.TITLE
        
    # Message
    def message(self, text):
        self.MESSAGE.text(text)
        self.MESSAGE.style('font-size:large')
        self.MESSAGE.css('bg-secondary text-white p-2')
        return self.MESSAGE
    # Error
    def error(self, text):
        self.MESSAGE.text(text)
        self.MESSAGE.style('font-size:large')
        self.MESSAGE.css('bg-danger text-white p-2')
        return self.MESSAGE
    # TextBlock
    def text(self, text):
        text_block = self.text_block()
        text_block.text(text)
        return text_block
    def text_block(self, id = None):
        text_block = TextBlock(self, id)
        #self.WIDGETS.append(text_block)
        #return text_block
        return self.widget(text_block)
    # Header
    def header(self, id = None):
        wg = Header(self, id)
        #self.WIDGETS.append(h)
        #return h
        return self.widget(wg)
    # Table
    def table(self, id, hole_update=False, css = None):
        table = Table(self, id = id, hole_update=hole_update)
        return self.widget(table)
        #self.WIDGETS.append(table)
        #return table
        
    def Table(self, id, **kwargs):
        table = Table(self, id = id, hole_update=True, **kwargs)
        return self.widget(table)
        #self.WIDGETS.append(table)
        #return table

    def Row(self, tableID, rowID, **kwargs):
        table = self.table(tableID)
        row = table.row(rowID, **kwargs)
        return row

    # textarea
    def textarea(self, id, cls=None, style=None, name=None):
        wg = TextArea(self, id=id, style=style, cls=cls, name=name)
        return self.widget(wg)
        #self.WIDGETS.append(w)
        #return w

    # ButtonGroup
    def button_group(self, id = None):
        wg = ButtonGroup(self, id)
        return self.widget(wg)
        #self.WIDGETS.append(bgroup)
        #return bgroup
    # Button
    def button(self, id = None,  text=text):
        button = Button(self, id)
        button.text(text)
        return self.widget(button)
        #self.WIDGETS.append(button)
        #return button
    # InputGroup
    def input_group(self, id = None):
        wg = InputGroup(self, id)
        return self.widget(wg)
        #self.WIDGETS.append(widget)
        #return widget
    # Tabs
    def tabs(self, id = None):
        wg = Tabs(self, id)
        return self.widget(wg)
        #self.WIDGETS.append(widget)
        #return widget
    # Tab
    def tab(self, id = None):
        return self.tabs(id)
        
        #widget = Tab(self, id)
        #wg = Tabs(self, id)
        #self.WIDGETS.append(widget)
        #return widget
    # Tab
    def Tabs(self, ID = None):
        wg = Tabs(self, ID)
        return self.append(wg)
        #self.WIDGETS.append(widget)
        #return widget
    # Toolbar
    def toolbar(self, id = None, **kwargs):
        wg = Toolbar(self, id, **kwargs)
        return self.widget(wg)
        #self.WIDGETS.append(widget)
        #return widget

    def Toolbar(self, ID = None, **kwargs):
        wg = Toolbar(self, ID, **kwargs)
        return self.widget(wg)
        #self.WIDGETS.append(widget)
        #return widget

    # Panel 
    def Panel(self, ID,  **kwargs):
        wg = Panel(self, ID, **kwargs)
        return self.widget(wg)
        #self.WIDGETS.append(widget)
        #return widget
        
class Widget:
    def __init__(self, page, ID, css = None, style = None, cls=None, **kwargs):
        self.page = page
        self.ID = ID
        self._class = set()
        self.STYLE = style
        self.EVENTS = {}
        self.ONDRAG = None
        self._widgets = {}
        #self.WIDGETS = []
        self.TOOLTIP = None
        self.DISABLED = False
        self.css(css)
        self.cls(cls)
        #self.последний_номер = 0
        for key, value in kwargs.items():
            try:
                getattr(self, key)(value)
            except:
                log.exception(f'{key}={value}') 
    def __str__(self):
        return f'<Widget {self.WIDGET_TYPE} {self.ID}>'
    @property
    def WIDGETS(self):
        return self._widgets.values()

    def write(self, html):
        pass
    def HTML(self):
        html = io.StringIO()
        self.write(html)
        html_text = html.getvalue()
        html.close()
        return html_text
    @property
    def FRAMEWORK(self):
        return self.page.FRAMEWORK

    def widget(self, wg):
        return self.append(wg)

    def append(self, wg):
        if wg.ID is None:
            #self.последний_номер += 1
            #wg.ID = f'{self.ID}_{self.последний_номер}'
            wg.ID = f'{self.ID}__{len(self._widgets)}'
        self._widgets[wg.ID] = wg
        #self.WIDGETS.append(wg)
        return wg

    @property
    def WIDGET_TYPE(self):
        return self.__class__.__name__
    @property
    def CLASS(self):
        if len(self._class) > 0:
            return ' '.join(self._class)
        else:
            return None
    def disabled(self, value):
        self.DISABLED = True if value else False
    def tooltip(self, text = None):
        if text is not None:
            self.TOOLTIP = text
        return self
    def подсказка(self, text = None):
        if text is not None:
            self.TOOLTIP = text
        return self
    def css(self, cls, add=True): 
        if cls is not None:
            for c in cls.split(' '):
                if add:
                    self._class.add(c.strip()) 
                else:
                    self._class.discard(c.strip())
        return self
    def cls(self, cls, add=True): 
        return self.css(cls, add)
    def style(self, style):
        if style is not None:
            if self.STYLE is None:
                self.STYLE = style
            else:
                self.STYLE += ';' + style
        return self
    def style_rem(self, name, i):
        if i is not None:
            if type(i) == str:
                return self.style(f'{name}:{i}')
            else:
                return self.style(f'{name}:{i}rem')
        return self
    def width(self, n):
        return self.style_rem('width', n)
    def margin(self, n):
        return self.mt(n)
    def mt(self, n):
        return self.style_rem('margin-top', n)
    def mb(self, n):
        return self.style_rem('margin-bottom', n)
    def mr(self, n):
        return self.style_rem('margin-right', n)
    def ml(self, n):
        return self.style_rem('margin-left', n)
    def on(self, name, url, args = {}, forms = [], char = None, target=None):
        event = {'URL': self.page.url(url, args)}
        if char is not None:
            event['CHAR'] = char
        if target is not None:
            event['TARGET'] = target.strip().upper()
        else:
            if url.find('/') != -1:
                event['TARGET'] = 'NEW_PAGE'
        FORMS = []
        for form in forms:
            FORMS.append(f"'{form.ID}'")
        event['FORMS'] = FORMS
        event['FORMS_STRING'] = ','.join(FORMS)
        self.EVENTS[name] = event
        return self
    def onkeypress(self, char, url, args = {}, forms = [], **kwargs):
        return self.on('onkeypress', url, args, forms, char, **kwargs)
    def onchange(self, url, args = {}, forms = [], **kwargs):
        return self.on('onchange', url, args, forms, **kwargs)
    def onclick(self, url, args = {}, forms = [], **kwargs):
        return self.on('onclick', url, args, forms, **kwargs)
    def on_click(self, url, args = {}, forms = []):
        return self.on('onclick', url, args, forms)
    def ondblclick(self, url, args = {}, forms = [], **kwargs):
        return self.on('ondblclick', url, args, forms, **kwargs)
    def ondrop(self, url, args = {}):
        return self.on('ondrop', url, args)
    def ondrag(self, args = {}):
        url_params = []
        for name,value in args.items():
            url_params.append(f'{name}={value}')
        self.ONDRAG = {'URL': '&'.join(url_params)}
        return self

    # formatter -----------------------
    def write_tag(self, html, tag, css=None, attrib = None, **kwargs):
        html.write(f'<{tag}')
        if self.ID:
            html.write(f' id="{self.ID}"')
        self.write_class(html, css)
        self.write_style(html)
        self.write_events(html)
        self.write_tooltip(html)
        if self.DISABLED:
            html.write(' disabled')
        if attrib:
            for key, value in attrib.items():
                if value is not None:
                    html.write(f' {key}="{value}"')

        for key, value in kwargs.items():
            if value is not None:
                html.write(f' {key}="{value}"')
        html.write('>\n')
    def write_tooltip(self, html):
        # data-toggle="tooltip" data-placement="bottom" title="TOOLTIP"
        if self.TOOLTIP:
            html.write(f' data-toggle="tooltip" data-placement="bottom" title="{self.TOOLTIP}"')
    def write_style(self, html, style=None):
        if self.STYLE or style:
            html.write(f' style="')
            if self.STYLE:
                html.write(self.STYLE)
            if style:
                html.write(f';{style}')
            html.write(f'"')
                
    def write_class(self, html, css = None):
        if len(self._class) > 0 or css:
            html.write(' class="')
            html.write(f' {css} ')
            html.write(' '.join(self._class))
            html.write('"')
    def write_events(self, html):
        # IF ONDRAG
        #   draggable="true" ondragstart="drag(event,'ONDRAG.URL')"
        # FOR NAME, EVENT in EVENTS
        #   IF name=="ondrop"
        #      ondrop="drop(event, 'URL')" ondragover="allowDrop(event)"
        #   ELIF name=='onkeypress'
        #      onkeypress="page_keypress(event, CHAR, 'URL', ['FORMS'])"
        #   ELIF event.TARGET == 'NEW_WINDOW'
        #      NAME="page_new_window(event, 'URL', [FORMS])"
        #   ELIF event.TARGET == 'NEW_PAGE'
        #      NAME="page_new_page(event, 'URL', [FORMS])"
        #   ELIF event.TARGET == 'DOWNLOAD'
        #      NAME="page_download(event, 'URL', [FORMS])"
        #   ELSE
        #      NAME="page_update('URL', [FORMS]);return false"
        if self.ONDRAG is not None:
            URL = self.ONDRAG.get('URL')
            html.write(f''' draggable="true" ondragstart="drag(event,'{URL}')"''')
        for name, e in self.EVENTS.items():
            FORMS = e.get('FORMS_STRING', '')
            TARGET = e.get('TARGET', '')
            URL = e.get('URL')
            if name == 'ondrop':
                html.write(f''' ondrop="drop(event, '{URL}')" ondragover="allowDrop(event)"''')
            elif name == 'onkeypress':
                CHAR = e.get('CHAR')
                html.write(f''' onkeypress="page_keypress(event, {CHAR}, '{URL}', [{FORMS}])"''')
            elif TARGET == 'NEW_WINDOW':
                html.write(f''' {name}="page_new_window(event, '{URL}', [{FORMS}])"''')
            elif TARGET == 'NEW_PAGE':
                html.write(f''' {name}="page_new_page(event, '{URL}', [{FORMS}])"''')
            elif TARGET == 'DOWNLOAD':
                html.write(f''' {name}="page_download(event, '{URL}', [{FORMS}])"''')
            else:
                html.write(f''' {name}="page_update('{URL}', [{FORMS}]); return false"''')
    # ---------------------------------
    @staticmethod
    def update_id(widget):
        widget.ID = f'UPDATE_{widget.ID}'
    @staticmethod
    def update_class(widget):
        widget.cls('UPDATE')
    def prepeare_for_update(self):
        Widget.update_id(self)
        Widget.update_class(self)

class Panel(Widget):
    class Item:
        def __init__(self, panel, width = None, grow=None, shrink = None, height=None, **kwargs):
            self.panel = panel
            self.widget = None
            self.STYLE = ''
            if width:
                self.basis(width)
            if height:
                self.basis(height)
            if shrink:
                self.item_style(f'flex-shrink:{shrink}')
            if grow:
                self.item_style(f'flex-grow:{grow}')


            for key, value in kwargs.items():
                f = getattr(self, key, None)
                if f:
                    f(value)
            self.panel.items.append(self)
            self.index = len(self.panel.items) - 1
        def basis(self, value):
            if isinstance(value, int):
                self.item_style(f'flex-basis:{value}rem')
            else:
                self.item_style(f'flex-basis:{value}')

        def item_style(self, s):
            self.STYLE += s
            self.STYLE += ';'
        def __widget(self, widget):
            #if not widget.ID:
            #    widget.ID = f'{self.panel.ID}_{self.index}'
            self.widget = widget
            return widget
        def Panel(self, ID = None, **kwargs):
            return self.__widget(Panel(self.panel.page, ID , **kwargs))
        def Button(self, ID = None, **kwargs):
            return self.__widget(Button(self.panel.page, ID , **kwargs))
        def IconButton(self, ID = None, **kwargs):
            return IconButton(self, ID , **kwargs)
        def Table(self, ID = None, **kwargs):
            return self.__widget(Table(self.panel.page, ID, hole_update=True, **kwargs))
        def Text(self, ID = None, **kwargs):
            return self.__widget(TextBlock(self.panel.page, ID, **kwargs))
        def Link(self, ID, **kwargs):
            return self.__widget(Link(self.panel.page, ID = None, **kwargs))
        def Input(self, ID = None, **kwargs):
            return self.__widget(Input(self.panel.page, ID, **kwargs))
        def Select(self, ID, **kwargs):
            return self.__widget(Select(self.panel.page, ID, **kwargs))
        def Tabs(self, ID, **kwargs):
            return self.__widget(Tabs(self.panel.page, ID, **kwargs))
        def Toolbar(self, ID=None, **kwargs):
            return self.__widget(Toolbar(self.panel.page, ID, **kwargs))
    def __init__(self, page, ID = None, direction = None, **kwargs):
        super().__init__(page, ID = ID, **kwargs)
        self.items = []
        if direction:
            self.style(f'flex-direction:{direction}')
    def item(self, **kwargs):
        return Panel.Item(self, **kwargs)

class DropDownItem(Widget):
    def __init__(self, page, id, text = None, **kwargs):
        super().__init__(page, id, **kwargs)
        self.TEXT = text
class DropDown(Widget):
    def __init__(self, page, id, text = None, **kwargs):
        super().__init__(page, id, **kwargs)
        self.TEXT = text

    def item(self, text = None, **kwargs):
        i = DropDownItem(self.page, None, text=text, **kwargs)
        return self.widget(i)
        #return i

class Title(Widget):
    def __init__(self, page, text = None):
        super().__init__(page, 'page_titlle')
        self.TEXT = text
        page.TITLE = self

    def text(self, text):
        self.TEXT = text
    
    def HTML(self):
        html = io.StringIO()
        self.write(html)
        HTML = html.getvalue()
        html.close()
        return HTML

    def write(self, html):
        #<div id="ID" class="mt-3 mb-4 d-flex flex-row flex-nowrap CLASS">
        #   <h4>TEXT</h4>
        #   <button class="ml-auto mdl-button mdl-js-button mdl-button--icon" onclick="page_reload()">
        #       <i class="material-icons">autorenew</i>
        #   </button>
        #   <button class="mdl-button mdl-js-button mdl-button--icon" onclick="window.history.back()">
        #       <i class="material-icons">close</i>
        #   </button>
        #</div>
        #self.write_tag(html, 'div', css='-mt-3 -mb-4 -d-flex -flex-row -flex-nowrap', 
        self.write_tag(html, 'div', 
            style='font-size:1.5rem;display:flex; flex-wrap: nowrap; margin-top:1rem; margin-bottom:2rem; align-items:center'
            )
        for wg in self.WIDGETS:
            wg.write(html)
        #html.write(f'<h4>{self.TEXT}</h4>\n')
        html.write(f'{self.TEXT}\n')
        html.write(f'''<button class="ml-auto mdl-button mdl-js-button mdl-button--icon" onclick="page_reload()">\n''')
        html.write(f'''<i class="material-icons">autorenew</i>\n''')
        html.write('</button>\n')
        html.write(f'''<button class="mdl-button mdl-js-button mdl-button--icon" onclick="window.history.back()">\n''')
        html.write(f'''<i class="material-icons">close</i>\n''')
        html.write('</button>\n')
        html.write('</div>\n')

class Message(Widget):
    def __init__(self, page, id):
        super().__init__(page, id)
        self.TEXT = ''
    def text(self, text):
        self.TEXT = text

class TextBlock(Widget):
    def __init__(self, page, id):
        super().__init__(page, id)
        self.PARAGRAPHS = []
        self.HEADER = None

    def append(self, wg):
        return self._current.append(wg)

    def header(self, text):
        self.HEADER = text

    @property
    def _current(self):
        lines = len(self.PARAGRAPHS)
        if  lines == 0:
            return self.newline()
        else:
            return self.PARAGRAPHS[lines - 1]

    def newline(self, style=None, css=None):
        line = TextBlock.Line(self.page, style, css)
        self.PARAGRAPHS.append(line)
        return line

    def text(self, text):
        return self._current.text(text)

    def glif(self, glif, style = None, css=''):
        return self._current.glif(glif, style, css)

    def link(self, text):
        return self._current.link(text)

    def icon_button(self, icon, **kwargs):
        return self._current.icon_button(icon, **kwargs)

    def href(self, text, url = '', params = {}, css=None, new_window=False):
        return self._current.href(text, url, params, css=css, new_window=new_window)

    class Line:
        def __init__(self, page, style = None, css=None):
            self.page = page
            self.PHRASES = []
            self.STYLE = style if style is not None else ''
            self.CLASS = css if css is not None else ''
        
        def append(self, wg):
            self.PHRASES.append(wg)
            return wg

        def text(self, text, style=None):
            line = {'TEXT':text}
            if style is not None:
                line['STYLE'] = style
            self.PHRASES.append(line)
            return self
        
        def href(self, text, url = '', params = {}, **kwargs):
            self.PHRASES.append(Href(self.page, text, url, params, **kwargs))

            #url = self.page.url(url, params)
            #w = {'TEXT':text, 'URL':url}
            #if new_window:
            #    w['NEW_WINDOW':True]
            #if css is not None:
            #    w['CLASS'] = css
            #self.PHRASES.append(w)
            return self

        def glif(self, glif, style = None, css=''):
            if style is not None:
                self.PHRASES.append({'GLIF':glif, 'STYLE':style, 'CLASS':css})
            else:
                self.PHRASES.append({'GLIF':glif, 'CLASS':css})
            return self

        def link(self, text = ''):
            wg = Link(self.page, None)
            wg.text(text)
            self.PHRASES.append(wg)
            return wg

        def icon_button(self, icon, **kwargs):
            #wg = IconButton(self.page, None, icon, **kwargs)
            #return self.append(wg)
            return IconButton(self, None, icon, **kwargs)

class Header(Widget):
    def __init__(self, page, id):
        Widget.__init__(self, page, id)
        self.TEXT = ''

    def text(self, text):
        self.TEXT = text

class Chip(Widget):
    def __init__(self, container, **kwargs):
        super().__init__(container.page, None, **kwargs)
        container.append(self)

    def write(self, html):
        self.write_tag(html, 'div', css='d-flex', style='border:solid 1px lightgray; border-radius:10%')
        for wg in self.WIDGETS:
            wg.write(html)
        html.write('</div>\n') 

class IconButton(Widget):
    def __init__(self, container, id, icon, size = None, **kwargs):
        super().__init__(container.page, id, **kwargs)
        pos = icon.find('/') 
        if pos != -1:
            self.TYPE = icon[:pos].upper()
            self.ICON = icon[pos+1:]
        else:
            self.TYPE = None
            self.ICON = icon
        self.SIZE = size
        container.append(self)

    def HTML(self):
        html = io.StringIO()
        self.write(html)
        html_text = html.getvalue()
        html.close()
        return html_text

    def write(self, html):
        self.write_tag(html, 'div', css='mdl-button mdl-js-button mdl-button--icon align-middle')
        if self.TYPE == 'AW':
            html.write(f'<span class="fas fa-{self.ICON} fa-xs"></span>\n')
        else:
            html.write(f'<i class="material-icons {self.SIZE}">{self.ICON}</i>\n')
        html.write('</div>\n')

class Button(Widget):
    def __init__(self, page, ID, text = '', label='', **kwargs):
        super().__init__(page, ID, **kwargs)
        self.TEXT = text
        self.GLIF = None
        self.LABEL = label
        self.IS_DROPDOWN = False
        #self.cls('active')
    def text(self, text):
        if text is not None:
            self.TEXT = text
        return self
    def item(self, text = None, **kwargs):
        self.IS_DROPDOWN = True
        i = DropDownItem(self.page, None, text=text, **kwargs)
        self.widget(i)
        return i
    def small(self):
        self.css('btn-sm')
        return self
    def xsmall(self):
        self.css('btn-xs')
        return self
    def primary(self):
        self.css('btn-primary')
        return self
    def info(self):
        self.css('btn-info')
        return self
    def secondary(self):
        self.css('btn-secondary')
        return self
    def danger(self):
        self.css('btn-danger')
        return self
    def glif(self, glif, style='', css=''):
        self.GLIF = glif
        self.GLIF_STYLE = style
        self.GLIF_CLASS = css
        return self

    def write_mdl_dropdown(self, html):
        html.write('<div class="dropdown dropbottom">\n')
        html.write('<button type="button"')
        self.write_class(html, "btn dropdown-toggle")
        self.write_style(html)
        html.write(f' obclick="event.page_processed=true" data-toggle="dropdown">\n')
        if self.TEXT:
            html.write(self.TEXT)
        html.write('</button>\n')
        html.write('<div class="dropdown-menu">\n')
        for item in self.WIDGETS:
            if item.TEXT:
                html.write(f'<a class="dropdown-item" href="#" ')
                item.write_events(html)
                html.write(f'>')
                html.write(item.TEXT)
                html.write('</a>\n')
            else:
                html.write('<div class="dropdown-divider"></div>\n')
        html.write('</div>\n')
        html.write('</div>\n')
    def write_mdl_with_label(self, html):
        html.write('<div style="display:flex; flex-direction: column">\n')
        html.write(f'<div style="color:gray;font-size:0.8em; margin-bottom:0px">{self.LABEL}</div>\n')
        self.write_mdl(html)
        html.write('</div>\n')
    def write_mdl(self, html):
        self.write_tag(html, 'button')
        if self.TEXT:
            html.write(self.TEXT)
        if self.GLIF:
            html.write(f'<span class="fas fa-{self.GLIF} {self.GLIF_CLASS}" style="{self.GLIF_STYLE}"></span>')
        html.write('</button>\n')
    def write_b4(self, html):
        self.write_tag(html, 'button', css='btn')
        if self.GLIF:
            html.write(f'<span class="fas fa-{self.GLIF} {self.GLIF_CLASS}" style="{self.GLIF_STYLE}"></span>')
        if self.TEXT:
            html.write(self.TEXT)
        html.write('</button>\n')
    def write(self, html):
        if self.FRAMEWORK == 'MDL':
            if self.IS_DROPDOWN:
                self.write_mdl_dropdown(html)
            else:
                if self.LABEL:
                    self.write_mdl_with_label(html)
                else:
                    self.write_mdl(html)
        else:
            self.write_b4(html)

class Link(Widget):
    def __init__(self, page, id, text = '', **kwargs):
        super().__init__(page, id, **kwargs)
        self.TEXT = text
    def text(self, text):
        self.TEXT = text
        return self
    def write(self, html):
        #<a href="#" {{Class(wg)}} {{Style(wg)}} {{Events(wg)}}>{{wg.TEXT}}</a>
        self.write_tag(html, 'a', href='#')
        html.write(self.TEXT)
        html.write('</a>\n')

class Glif(Widget):
    def __init__(self, page, id, style=None, css=None):
        super().__init__(page, id, style=style, css=css)
        self.GLIF = ''

    def glif(self, glif):
        self.GLIF = glif
        return self
    
    def write(self, html):
        # IF GLIF == ':close'
        #   <span class="CLASS" style="STYLE" EVENTS>&#10005;</span>
        # ELSE
        #   <span class="fas fa-GLIF class="CLASS" style="STYLE" EVENTS></span>
        if self.GLIF == ':close':
            self.write_tag(html, 'span')
            html.write('&#10005;')
            html.write('</span>\n')
        else:
            self.write_tag(html, 'span', css=f'fas fa-{self.GLIF}')
            html.write('</span>\n')

class ButtonGroup(Widget):
    def __init__(self, page, id = None):
        super().__init__(page, id)
        self.BUTTONS = []
    
    def button(self, text = '', url='', params={}, widgets = []):
        button = Button(self.page, None)
        button.text(text)
        button.onclick(url, params , widgets)
        self.BUTTONS.append(button)
        return button
        
    def write(self, html):
        #<div class="btn-group CLASS STYLE>
        # FOR button in BUTTONS
        #   Button(button)
        #</div>
        self.write_tag(html, 'div', css='btn-group')
        for button in self.BUTTONS:
            button.write(html)
        html.write('</div>\n')

class Navbar(Widget):
    class Header:
        def __init__(self, page, text, href, params = {}):
            self.TEXT = text
            self.HREF = page.url(href, params)
    class Item:
        def __init__(self, page, text, href, params = {}):
            self.IS_GROUP = False
            self.TEXT = text
            self.HREF = page.url(href, params)
    class Group:
        def __init__(self, page, text):
            self.IS_GROUP = True
            self.TEXT = text
            self.ITEMS = []
            self.page = page

        def item(self, text, href, params = {}):
            item = Navbar.Item(self.page, text, href, params)
            self.ITEMS.append(item)
            return item

    def __init__(self, page, id):
        super().__init__(page, "NAVBAR")
        self.page = page
        self.HEADER = None
        self.ITEMS = []
    def header(self, text, href, params = {}):
        self.HEADER = Navbar.Header(self.page, text, href, params = {})
        return self.HEADER
    def item(self, text, href, params = {}):
        item = Navbar.Item(self.page, text, href, params)
        self.ITEMS.append(item)
        return item
    def group(self, text):
        item = Navbar.Group(self.page, text)
        self.ITEMS.append(item)
        return item

    def write(self, html):
        #<nav id="NAVBAR" class="navbar navbar-expand-sm bg-dark navbar-dark">
        #    <a class="navbar-brand" href="HEADER.HREF">HEADER.TEXT</a>
        #<ul class="navbar-nav mr-auto">
        #    FOR item IN ITEMS
        #       IF item.IS_GROUP
        #        <li class="nav-item dropdown">
        #            <a class="nav-link dropdown-toggle" href="#" id="navbardrop" data-toggle="dropdown">
        #            item.TEXT
        #            </a>
        #            <div class="dropdown-menu">
        #                for subitem in item.ITEMS 
        #                   <a class="dropdown-item" onclick="page_new_page(event,'subitem.HREF', [])" href=# _href="subitem.HREF">subitem.TEXT</a>
        #            </div>
        #        </li>
        #       ELSE
        #        <li class="nav-item">
        #           <a class="nav-link" href="item.HREF">item.TEXT</a>
        #        </li>
        #</ul>
        #</nav>
        self.write_tag(html, 'nav', css="navbar navbar-expand-sm bg-dark navbar-dark")
        #if self.HEADER is not None:
            #html.write(f'<a class="navbar-brand" href="{self.HEADER.HREF}"><i class="material-icons">home</i>{self.HEADER.TEXT}</a>')
        html.write(f'<a class="navbar-brand" href="{self.HEADER.HREF}" style="color:gray"><i  class="material-icons" title="{self.HEADER.TEXT}" >home</i></a>')
        html.write(f'<ul class="navbar-nav mr-auto">\n')
        for item in self.ITEMS:
            if item.IS_GROUP:
                html.write(f'<li class="nav-item dropdown">\n')
                html.write(f'<a class="nav-link dropdown-toggle" href="#" id="navbardrop" data-toggle="dropdown">{item.TEXT}</a>\n')
                html.write(f'<div class="dropdown-menu">\n')
                for subitem in item.ITEMS:
                    html.write(f'<a class="dropdown-item"')
                    html.write(f''' onclick="page_new_page(event,'{subitem.HREF}', [])"''')
                    html.write(f' href=# _href="{subitem.HREF}">{subitem.TEXT}</a>\n')
                html.write(f'</div>\n')
                html.write(f'</li>\n')
            else:
                html.write(f'<li class="nav-item">')
                html.write(f'<a class="nav-link" href="{item.HREF}">{item.TEXT}</a>')
                html.write(f'</li>\n')
        html.write('</ul>\n')
        html.write('</nav>\n')
    
class Href:
    def __init__(self, page, text, url = '', params = {}, new_window = False, css = None, style=None):
        self.page = page
        self.WIDGET_TYPE = 'Href'
        self.TEXT = text
        self.URL = self.page.url(url, params)
        self.NEW_WINDOW = new_window
        self.CLASS = css
        self.STYLE = style
    def write(self, html):
        #{% macro Href(e) -%}
        #{%- if e.NEW_WINDOW -%}
        #<a href="{{e.URL}}" target="_blank" {{Class(e)}} {{Style(e)}}> {{e.TEXT}} </a>
        #{%- else -%}
        #<a href="{{e.URL}}" {{Class(e)}} {{Style(e)}}> {{e.TEXT}} </a>
        #{%- endif -%}
        #{%- endmacro %}
        html.write(f'<a href="{self.URL}"')
        if self.NEW_WINDOW:
            html.write(' target="_blank"')
        if self.CLASS:
            html.write(f' class="{self.CLASS}"')
        if self.STYLE:
            html.write(f' style="{self.STYLE}"')
        html.write('>')
        if self.TEXT:
            html.write(self.TEXT)
        html.write('</a>')

class Table(Widget):
    def __init__(self, page, id, hole_update = False, css = None, **kwargs):
        super().__init__(page, id, **kwargs)
        if css is not None:
            self.cls(css)
        else:
            #self.cls('table-sm table-hover shadow-sm')
            #self.cls('table-sm table-hover shadow-sm')
            self.cls('mdl-shadow--2dp -shadow table-sm -table-responsive -table-striped table-hover -table-bordered -table-borderless')
        self.COLUMNS = None
        self.ROWS = []
        self.rowid = 0
        self.hole_update = hole_update
        self.TBODY = {'ID': f'{id}_tbody'}
        #self.THEAD = {'CLASS':'thead-dark'}
        #self.THEAD = {'CLASS':'thead-light'}
        self.THEAD = {}

    def thead(self, style = None, css=None):
        if style is not None:
            self.THEAD['STYLE'] = style
        if css is not None:
            self.THEAD['CLASS'] = css

    def prepeare_for_update(self):
        table_ID = self.ID
        self.ID = f'UPDATE_{table_ID}'
        if self.hole_update:
            self.cls('UPDATE')
        else:
            self.TBODY['ID'] = f'UPDATE_{table_ID}_tbody'
            self.COLUMNS = []
            for row in self.ROWS:
                row.ID = f'UPDATE_{row.ID}'
                row.cls('UPDATE')
               
    def next_rowid(self):
        self.rowid += 1
        return f'{self.rowid}'

    def column(self, name = '', ID = None, align = None, **kwargs):
        column = Table.Column(self.page, name, ID, align=align, **kwargs)
        if self.COLUMNS is None:
            self.COLUMNS = [column]
        else:
            self.COLUMNS.append(column)
        return column

    def COLUMNS_HTML(self):
        if self.COLUMNS is None:
            return ''
        else:
            # <thead class="" style="">
            # <tr>
            #   COLUMNS
            # </tr>
            # </thead>
            html = io.StringIO()
            html.write(f'<thead')
            thead_class = self.THEAD.get('CLASS')
            if thead_class:
                html.write(f' class="{thead_class}"')
            thead_style = self.THEAD.get('STYLE')
            if thead_style:
                html.write(f' style="{thead_style}"')
            html.write('>\n')
            html.write('<tr>\n')
            for column in self.COLUMNS:
                column.write(html)
            html.write('</tr>\n</thead>\n')
            html_text = html.getvalue()
            html.close
            return html_text

    #def _COLUMNS_HTML(self):
    #    if self.COLUMNS is None:
    #        return ''
    #    else:
    #        html = []
    #        thead_style = self.THEAD.get('STYLE', '')
    #        thead_class = self.THEAD.get('CLASS', '')
    #        html.append(f'<thead class="{thead_class}" style="{thead_style}">')
    #        html.append('<tr>')
    #        for column in self.COLUMNS:
    #            html.append(column.HTML())
    #        html.append('</tr></thead>')
    #    return '\n'.join(html)

    def row(self, id = None, **kwargs):
        if id is None:
            #self.последний_номер += 1
            #id = f'{self.последний_номер}'
            id = f'{len(self.ROWS)}'

        row = Table.Row(self.page, f'{self.ID}_{id}', **kwargs)
        self.ROWS.append(row)
        return row
       
    class Column(Widget):
        def __init__(self, page, name = '', ID = None, align = None, **kwargs):
            super().__init__(page, ID, **kwargs)
            self.TEXT = name
            if align and align=='right':
                self.style('text-align:right; font-size:0.9rem; padding:0.8rem;')
            else:
                self.style('text-align=middle; font-size:0.9rem; padding:0.8rem;')

        def write(self, html):
            # <th class="" style="">TEXT</th>
            CLASS = self.CLASS
            STYLE = self.STYLE
            html.write('<th')
            if CLASS:
                html.write(f' class="{CLASS}"')
            if STYLE:
                html.write(f' style="{STYLE}"')
            html.write('>')
            html.write(f'{self.TEXT}')
            html.write('</th>\n')

        #def HTML(self):
        #    CLASS = self.CLASS
        #    STYLE = self.STYLE
        #    html = []
        #    html.append('<th')
        #    if CLASS:
        #        html.append(f' class="{CLASS}"')
        #    if STYLE:
        #       html.append(f' style="{STYLE}"')
        #    html.append('>')
        #    html.append(f'{self.TEXT}')
        #    html.append('</th>')
        #    return ''.join(html)

        def name(self, text):
            self.TEXT = text
            return self

        def text(self, text):
            self.TEXT = text
            return self

    class Cell(Widget):

        def __init__(self, page, style=None, align=None, css=None, colspan=None, wrap=True):
            super().__init__(page, None, style=style, css=css)
            self.TEXT = ''
            self.HTML = None
            self.HREF = None
            self.HREF_CLASS = None
            self.HREF_STYLE = None
            self.IMAGE = None
            if colspan is not None:
                self.COLSPAN = colspan
            self.middle()
            if align:
                self.align(align)
            if not wrap:
                self.style('white-space:nowrap')

        def align(self, align):
            if align == 'right':
                self.css('text-right')
            elif align == 'left':
                self.css('text-left')
            elif align == 'center':
                self.css('text-center')

        def right(self):
            return self.css('text-right')
        def left(self):
            return self.css('text-left')
        def center(self):
            return self.css('text-center')
        def middle(self):
            return self.css('align-middle')

        def text(self, text):
            self.TEXT = text if text is not None else ''
            return self
        
        def html(self, text):
            self.HTML = text
            return self

        def href(self, text, href, params = [], **kwargs):
            self.HREF = Href(self.page, text, href, params, **kwargs)
            #self.text(text)
            #self.HREF = {'TEXT':text, 'HREF':self.page.url(href, params)}
            #if new_window:
            #    self.HREF['NEW_WINDOW'] = True
            #if css is not None:
            #    self.HREF['CLASS'] = css
            #if style is not None:
            #    self.HREF['STYLE'] = style
            return self

        def image(self, image):
            self.IMAGE = f'/active/web/images/{image}'
            return self

        def input(self, label='', type='text', value='', name='', placeholder = ''):
            return self.widget(Input(self.page, None, label=label, type=type, name=name, value=value, placeholder=placeholder))

        def input_group(self):
            return self.widget(InputGroup(self.page, None))

        def button(self, text='', **kwargs):
            wg = Button(self.page, None, **kwargs)
            wg.text(text)
            return self.widget(wg)

        def icon_button(self, icon, size=None, **kwargs):
            #wg = IconButton(self.page, None, icon=icon, size=size, **kwargs)
            #return self.widget(wg)
            return IconButton(self, None, icon=icon, size=size, **kwargs)
            #return self.widget(wg)

        def link(self, text):
            wg = Link(self.page, None)
            wg.text(text)
            return self.widget(wg)
 
        def glif(self, glif, style=None, css=None):
            wg = Glif(self.page, None, style=style, css=css)
            wg.glif(glif)
            return self.widget(wg)

        def select(self, label='', value='', name=''):
            wg = Select(self.page, None, label=label, name=name, value=value)
            return self.widget(wg)

        def text_block(self):
            #wg = TextBlock(self.page, None)
            #self.WIDGETS.append(wg)
            return self.widget(TextBlock(self.page, None))

        def toolbar(self, id=None):
            return self.widget(Toolbar(self.page, id))

    class Row(Widget):
        def __init__(self, page, id, **kwargs):
            super().__init__(page, id, **kwargs)

        @property
        def FIELDS(self):
            return self.WIDGETS

        def drag(self, params={}):
            self.DRAG = True
            return self

        def __getitem__(self, key = None):
            return self.widget(Table.Cell(self.page))
            #if key is None:
            #    c = self.widget(Table.Cell(self.page))
                #self.FIELDS.append(c)
            #    return c
            #if type(key) == int:
            #    c = self.widget(Table.Cell(self.page))
            #    return c
                #if key < 0 or key > MAX_COLUMNS:
                #    raise Exception(f'Слишком большой номер колонки "{key}"')
                #while key >= len(self.FIELDS):
                #    self.FIELDS.append(Table.Cell(self.page))
                #return self.FIELDS[key]
        
        def new_cell(self):
            return self.widget(Table.Cell(self.page))

            #cell = Table.Cell(self.page)
            #self.FIELDS.append(cell)
            #return cell

        def cell(self, style = None, cls = None, width = None, colspan = None, **kwargs):
            return self.widget(Table.Cell(self.page, style=style, colspan=colspan, **kwargs).width(width).cls(cls))
            #self.последний_номер += 1
            #cell.id = f'{self.ID}_{self.последний_номер}'
            #self.FIELDS.append(cell)
            #return cell

        def text(self, text, style = None, name = None):
            cell = self.widget(Table.Cell(self.page, style=style))
            #cell = Table.Cell(page = self.page)
            cell.TEXT = text if text is not None else ''
            #f = { 'TEXT':text }
            #if style is not None:
            #    cell.STYLE = style
            #if name is not None:
            #    f['NAME'] = name
            #self.FIELDS.append(cell)
            return self

        def fields(self, *texts):
            for text in texts:
                self.new_cell().text(text)
                #self.FIELDS.append({'TEXT':text if text is not None else ''})
                #self.FIELDS.append(Table.Cell(self.page).text(text))

        def href(self, text, href, params = {}, **kwargs):
            self.cell().href(text, href, params, **kwargs)
            return self
            #self.FIELDS.append({'TEXT': text, 'HREF': self.page.url(href, params)})
            #self.FIELDS.append(cell)
 
        def image(self, image, style = None):
            cell = self.cell()
            cell.image(image)
            cell.style(style)
            return self
            #field = {'IMAGE' : f'/active/web/images/{image}'}
            #if style is not None:
            #    field['STYLE'] = style
            #self.FIELDS.append(field)

        def glif(self, glif, style = None, css=''):
            field = {'GLIF' : glif, 'CLASS':css}
            if style is not None:
                field['STYLE'] = style
            return self.widget(field)

        def button_group(self):
            buttons = ButtonGroup(self.page)
            return self.widget(buttons)

        def button(self, text=''):
            button = Button(self.page, None)
            button.text(text)
            return self.widget(button)

        def input_group(self):
            e = InputGroup(self.page, None)
            return self.widget(e)

        def input(self, **kwargs):
            input = Input(self.page, None, **kwargs)
            return self.widget(input)

        def select(self, label='', value='', name=''):
            input = Select(self.page, None, label=label, name=name, value=value)
            return self.widget(input)

class Input(Widget):
    def __init__(self, page, id, type = 'text', label = '', value = '', name = '', placeholder='', pattern=None, disabled = False):
        super().__init__(page, id)
        self.NAME = name
        self.LABEL = label
        self.INPUT_TYPE = type
        self.VALUE = ''
        if value is None:
            self.VALUE = ''
        elif type == 'date':
            if value:
                if isinstance(value, str):
                    date = arrow.get(value).date()
                else:
                    date = value
                self.VALUE = date.strftime("%Y-%m-%d")
        elif type == 'datetime-local':
            if value is None or value.strip() == '':
                self.VALUE = ''
            else:
                try:
                    date = arrow.get(value)
                    self.VALUE = date.format("YYYY-MM-DDTHH:mm")
                except:
                    self.VALUE = ''
        else:
            self.VALUE = str(value)
        self.PLACEHOLDER = placeholder
        self.PATTERN = pattern
        self.DISABLED = ' disabled ' if disabled else ''

    def disabled(self, disabled):
        self.DISABLED = ' disabled ' if disabled else ''
    def name(self, name):
        self.NAME = name
        return self
    def value(self, value):
        self.VALUE = value
        return self
    def label(self, label):
        self.LABLE = label
        return self
    def small(self):
        self.css('corm-control-sm')
        return self
    def pattern(self, pattern):
        self.PATTERN = pattern
        return self

    def write_input(self, html):
        html.write('<input x-webkit-speech')
        self.write_tooltip(html)
        #self.write_style(html, 'border-color:transparent')
        self.write_style(html)
        self.write_class(html, 'form-control')
        self.write_events(html)
        if self.VALUE:
            #value = urllib.parse.quote(self.VALUE, safe='')
            value = HTML.escape(self.VALUE)
            html.write(f' value="{value}"')
        if self.INPUT_TYPE:
            html.write(f' type="{self.INPUT_TYPE}"')
        if self.NAME:
            html.write(f' name="{self.NAME}"')
        if self.DISABLED:
            html.write(' disabled')
        if self.PLACEHOLDER:
            html.write(f' placeholder="{self.PLACEHOLDER}"')
        if self.PATTERN:
            html.write(f' pattern="{self.PATTERN}"')
        html.write('>\n')
    def write(self, html):
        #{% macro Input(e) -%}
        #{%- if e.LABEL %}
        # <div style="display:flex; flex-direction: column;">
        # <div style="color:gray;font-size:0.8em; margin-bottom:0px">{{e.LABEL}}</div>
        # <div style="border-style: solid; border-width: thin; border-color: lightgray">
        #   <input {{Tooltip(e)}} {{e.DISABLED}} x-webkit-speech {{Events(e)}} 
        # style="border-color:transparent; {{e.STYLE}}" 
        # {{Pattern(e)}} class="form-control {{e.CLASS}}" 
        # name="{{e.NAME}}" value="{{e.VALUE}}" type="{{e.INPUT_TYPE}}" placeholder="{{e.PLACEHOLDER}}"/>
        # </div>
        # </div>
        # {% else -%}
        # input {{Tooltip(e)}} {{e.DISABLED}} x-webkit-speech {{Events(e)}} {{Style(e)}} {{Pattern(e)}} class="form-control {{e.CLASS}}" name="{{e.NAME}}" value="{{e.VALUE}}" type="{{e.INPUT_TYPE}}" placeholder="{{e.PLACEHOLDER}}"/>
        # {% endif -%}
        #%- endmacro %}
        if self.LABEL:
            html.write(f'<div style="display:flex; flex-direction: column;">\n')
            html.write(f'<div style="color:gray;font-size:0.8em; margin-bottom:0px">{self.LABEL}</div>\n')
            html.write(f'<div style="border-style: solid; border-width: thin; border-color: lightgray">\n')
            self.write_input(html)
            html.write('</div>\n')
            html.write('</div>\n')
        else:
            self.write_input(html)

class Select(Widget):
    class Option: 
        def __init__(self, value, text):
            self.VALUE = value
            self.TEXT = text
        def __str__(self):
            return self.TEXT

    def __init__(self, page, id, label='', name='', value='', options=None):
        super().__init__(page, id)
        self.NAME = name
        self.LABEL = label
        self.INPUT_TYPE = 'select'
        self.OPTIONS = []
        self.VALUE = value
        self.css('form-control -custom-select')
        if options is not None:
            self.options(options)
    def name(self, name):
        self.NAME = name
        return self
    def small(self):
        self.css('castom-select-sm')
        return self
    def options(self, options):
        for option in options:
            if isinstance(option, (list, tuple)):
                self.option(option[0], option[1])
            else:
                self.option(f'{option}')
        return self
    def option(self, value, text = None):
        option = Select.Option(value, text if text is not None else value)
        if self.VALUE is not None and value is not None and f'{self.VALUE}' == f'{value}':
            self.OPTIONS.insert(0, option)
        else:
            self.OPTIONS.append(option)
    def write(self, html):
        #   IF LABEL
        #       <label style="color:gray;font-size:0.8em; margin-bottom:0px">LABEL</label>
        #   <select TOOLTIP ID name="NAME" CLASS EVENTS>
        #   FOR option in OPTIONS
        #       <option value="option.VALUE">option.TEXT</option>
        #   </select>
        if self.LABEL:
            html.write(f'<label style="color:gray;font-size:0.8em; margin-bottom:0px">')
            html.write(self.LABEL)
            html.write(f'</label>\n')
        self.write_tag(html, 'select', attrib={'name':self.NAME})
        for option in self.OPTIONS:
            html.write(f'<option value="{option.VALUE}">{option.TEXT}</option>\n')
        html.write(f'</select>\n')


class InputGroup(Widget): 
    def __init__(self, page, id, label=None, text=None):
        super().__init__(page, id)
        self.ITEMS = []
        self.TEXT = text
        self.BUTTONS = None
        self.LABEL = label

    def append(self, wg):
        if self.BUTTONS is None:
            self.BUTTONS = [wg]
        else:
            self.BUTTONS.append(wg) 
        return wg

    def text(self, text):
        self.TEXT = text
        return self

    def small(self):
        self.css('input-group-sm')
        return self

    def input(self, label = None, **kwargs):
        input = Input(self.page, None, **kwargs)
        self.ITEMS.append(input)
        return input

    def select(self, name = '', label=None, value=None, **kwargs):
        field = Select(self.page, None, name = name, value = value, **kwargs)
        self.ITEMS.append(field)
        return field

    def button(self, text = None):
        button = Button(self.page, None)
        button.text(text)
        if self.BUTTONS is None:
            self.BUTTONS = [button]
        else:
            self.BUTTONS.append(button) 
        return button

    def icon_button(self, icon, **kwargs):
        return IconButton(self, None, icon, **kwargs)

    def write(self, html):
        '''
        {%- if wg.LABEL -%}
            <div style='display:flex; flex-direction: column'>
            {%- if wg.LABEL != '-' -%}
                <div style="color:gray;font-size:0.8em; margin-bottom:0px">{{wg.LABEL}}</div>
            {%- endif -%}
            <div style="border-radius: 0.3rem; display:flex; flex-direction: row; align-items:center; border-style: solid; border-width: thin; border-color: lightgray; {{wg.STYLE}}">
            {%- if wg.TEXT -%}
            <div style='white-space:nowrap;color:gray;margin-left:0.5rem;'> {{wg.TEXT}} </div>
            {%- endif -%}
            {% for e in wg.ITEMS -%}
            {%- if e.WIDGET_TYPE == 'Input' -%}
            <input {{Tooltip(e)}} {{e.DISABLED}} x-webkit-speech {{Events(e)}} style="border-color:transparent; {{e.STYLE}}" {{Pattern(e)}} class="form-control {{e.CLASS}}" name="{{e.NAME}}" value="{{e.VALUE}}" type="{{e.INPUT_TYPE}}" placeholder="{{e.PLACEHOLDER}}"/>
            {% elif e.WIDGET_TYPE == 'Select' -%}
            <select style="margin-left:0.5rem; border-color:transparent; {{e.STYLE}}" id="{{e.ID}}" name="{{e.NAME}}" {{Class(e)}} {{Events(e)}}>
            <options>
            {% for option in e.OPTIONS -%}
            <option value="{{option.VALUE}}">{{option.TEXT}}</option>
            {%- endfor %}
            </select>
            {% endif -%}
            {%- endfor %}
            {%- if wg.BUTTONS -%}
            {% for button in wg.BUTTONS -%}
            {{ Widget(button) }}
            {%- endfor %}
            {%- endif -%}
            </div>
            </div>
        {%- else -%}
            <div class="input-group {{wg.CLASS}}" id="{{wg.ID}}" {{Style(wg)}}>
            {%- if wg.TEXT -%}
                <div class="input-group-prepend"> <span class="input-group-text">{{wg.TEXT}}</span> </div>
            {%- endif -%}
            {% for i in wg.ITEMS -%}
                {{ Widget(i) }} 
            {%- if wg.BUTTONS -%}
                <div class="input-group-append">
                {% for button in wg.BUTTONS -%}
                    {{ Widget(button) }}
                {%- endfor %}
                </div>
            {%- endif -%}
            </div>
        {%- endif -%}
        '''
        self.write_tag(html, 'div', css='input-group')
        if self.TEXT:
            html.write(f'<div class="input-group-prepend"> <span class="input-group-text">{self.TEXT}</span> </div>')
        for i in self.ITEMS:
              i.write(html)
        if self.BUTTONS:
            self.write_tag(html, 'div', css='input-group-append')
            for button in self.BUTTONS:
                button.write(html)
            html.write('</div>')
            
        html.write('</div>\n')


class Tabs(Widget): 
    class Item(Widget):
        def __init__(self, parent, id, active=False):
            super().__init__(parent.page, id)
            self.parent = parent
            self.TEXT = ''
            if active:
                self.ACTIVE = True
            else:
                self.ACTIVE = False
        def text(self, text):
            self.TEXT = text
            return self
        def write(self, html):
            #    {%- if i.ACTIVE -%}
            #        <a href="#{{i.ID}}" class="mdl-tabs__tab is-active" style="text-decoration: none" {{Events(i)}}>{{i.TEXT}}</a>
            #    {%- else -%}
            #        <a href="#{{i.ID}}" class="mdl-tabs__tab" style="text-decoration: none" {{Events(i)}}>{{i.TEXT}}</a>
            #    {%- endif -%}
            #log.debug(f'TABITEM {self.TEXT}, is_active={self.ACTIVE}')
            if self.ACTIVE:
                html.write(f'<a href="#{self.parent.ID}" class="mdl-tabs__tab is-active" style="text-decoration: none"')
                self.write_events(html)
                html.write(f'>{self.TEXT}</a>\n')
            else:
                html.write(f'<a href="#{self.parent.ID}" class="mdl-tabs__tab" style="text-decoration: none"')
                self.write_events(html)
                html.write(f'>{self.TEXT}</a>\n')
        def active(self, active):
            #if active:
            #    self.css('active')
            if active:
                self.ACTIVE = True
            else:
                self.ACTIVE = False
            return self

    def __init__(self, page, id):
        super().__init__(page, id)

        #self.WIDGETS = []

    #def tab(self, id, active=False):
    #    wg = Tabs.Item(self.page, id, active=active)
    #    self.WIDGETS.append(wg)
    #    return wg

    def item(self, active=False):
        wg = Tabs.Item(self, None, active = active)
        #self.WIDGETS.append(wg)
        #return wg
        return self.widget(wg)

    def write(self, html):
        #<div id="{{tabs.ID}}" class="mdl-tabs mdl-js-tabs -mdl-js-ripple-effect" {{Style(tabs)}} {{Events}}>
        #<div class="mdl-tabs__tab-bar" style='justify-content: flex-start'>
        #{% for i in tabs.WIDGETS -%}
        #    {%- if i.ACTIVE -%}
        #        <a href="#{{i.ID}}" class="mdl-tabs__tab is-active" style="text-decoration: none" {{Events(i)}}>{{i.TEXT}}</a>
        #    {%- else -%}
        #        <a href="#{{i.ID}}" class="mdl-tabs__tab" style="text-decoration: none" {{Events(i)}}>{{i.TEXT}}</a>
        #    {%- endif -%}
        #%- endfor %}
        #</div>
        #</div>
        html.write(f'<div id="{self.ID}" class="mdl-tabs mdl-js-tabs -mdl-js-ripple-effect"')
        self.write_style(html)
        self.write_events(html)
        html.write(f'>\n')
        html.write(f'<div class="mdl-tabs__tab-bar" style="justify-content: flex-start">\n')
        for i in self.WIDGETS:
            i.write(html)
        html.write(f'</div></div>\n')

class ToolbarItem(Widget): 
    def __init__(self, page, id):
        super().__init__(page, id)
        self.WIDGET = None

    def append(self, wg):
        self.WIDGET = wg
        return wg

    def right(self):
        self.css('ml-auto')
        return self
    def width(self, width):
        self.style(f'width:{width}rem')
        return self
    def input(self, **kwargs):
        self.WIDGET = Input(self.page, None, **kwargs)
        return self.WIDGET
    def input_group(self, **kwargs):
        self.WIDGET = InputGroup(self.page, None, **kwargs)
        return self.WIDGET
    def button(self, text='', **kwargs):
        self.WIDGET = Button(self.page, None, **kwargs)
        self.WIDGET.text(text)
        return self.WIDGET

    def icon_button(self, icon, size=None, **kwargs):
        #self.WIDGET = IconButton(self.page, None, icon=icon, size=size, **kwargs)
        #return self.WIDGET
        return IconButton(self, None, icon=icon, size=size, **kwargs)

    def button_group(self):
        self.WIDGET = ButtonGroup(self.page, None)
        return self.WIDGET
    def select(self, id = None, value='', name='', label=None, options=None):
        self.WIDGET = Select(self.page, id, value=value, name = name, label=label, options=options)
        return self.WIDGET
    def tab(self):
        self.WIDGET = Tabs(self.page, None)
        return self.WIDGET
    def text_block(self):
        self.WIDGET = TextBlock(self.page, None)
        return self.WIDGET
    def Text(self):
        self.WIDGET = TextBlock(self.page, None)
        return self.WIDGET
    def href(self, href, text, params = {}, css=None):
        t = self.text_block()
        t.href(href, text, params, css)
        return t
    def drop_down(self, text='', **kwargs):
        self.WIDGET = DropDown(self.page, None, text=text, **kwargs)
        return self.WIDGET

class Toolbar(Widget): 
    def __init__(self, page, id, wrap=None, style = None, **kwargs):
        super().__init__(page, id)
        if style:
            self.style(style)
        else:
            self.style('align-items:flex-end')
        if wrap is not None:
            if wrap:
                self.style('flex-wrap:wrap')
            else:
                self.style('flex-wrap:nowrap')

    def item(self, **kargs):
        item = ToolbarItem(self.page, None)
        for key, value in kargs.items():
            try:
                getattr(item, key)(value)
            except:
                log.exception(f'Toolbar.item ({key},{value})')
        return self.widget(item)

class TextArea(Widget):
    def __init__(self, page, id, name = None, **kwargs):
        Widget.__init__(self, page, id, **kwargs)
        self.NAME = name

    def write(self, html):
        self.write_tag(html, 'textarea', css='form-control', name=self.NAME)
        html.write('</textarea>\n')

    def HTML(self):
        html = io.StringIO()
        self.write(html)
        html_text = html.getvalue()
        html.close()
        return html_text
        
#class Panel(WidgetContainer):
#    def __init__(self, page, ID):
#        super.__init__(page, ID)
        

