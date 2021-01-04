from domino.core import log
from . import Page as BasePage
from . import Title, Text

class MainMenu:

    NEW_PAGE = 'NEW_PAGE'
    DOWNLOAD = 'DOWNLOAD'
    NEW_WINDOW = 'NEW_WINDOW'

    class Group:
        def __init__(self, name):
            self.is_group = True
            self.name = name
            self.items = []
        def item(self, name, url, target = None):
            item = MainMenu.Item(name = name, url = url, target = target)
            self.items.append(item)
            return item

    class Item:
        def __init__(self, name, url, target = None):
            self.is_group = False
            self.name = name
            self.url = url
            self.target = target if target is not None else MainMenu.NEW_PAGE

    def __init__(self):
        self.items = []
    
    def group(self, name):
        group = MainMenu.Group(name)
        self.items.append(group)
        return group

    def item(self, name, url, target = None):
        item = MainMenu.Item(name = name, url = url, target = target)
        self.items.append(item)
        return item

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
    
    def create_menu(self, menu):
        pass
    
    def print_menu(self):
        menu = MainMenu()
        self.create_menu(menu)
        for item in menu.items:
            if item.is_group:
                Text(self).style('font-size:-large; font-style: italic').mt(1).text(item.name)
                for subitem in item.items:
                    Text(self).mt(0.5).link(subitem.name.upper()).onclick(subitem.url, target=subitem.target)
            else:
                Text(self).mt(0.5).link(item.name.upper()).onclick(item.url, target=item.target)

    def print_version(self, show_history = True):
        if show_history:
            Text(self).href(f'Версия {self.application.version}', 'domino/pages/version_history')
        else:
            Text(self).text(f'Версия {self.application.version}')

    def __call__(self):
        Title(self, f'{self.application.module_name}')
        #self.print_version(True)
        self.print_menu()
