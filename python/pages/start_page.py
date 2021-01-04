from domino.core import log
from domino.pages.start_page import Page as BasePage
from . import Title, Text
from grants import Grants

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
    
    @property
    def grants(self):
        return Grants(self.account_id, self.user_id)
    
    def create_menu(self, menu):
        group = menu.group('Краткое описание')
        group.item('Полный список поддерживаемых видов карт', 'pages/card_classes')
        group.item('Полный список поддерживаемых типов акций', 'pages/action_types')

        if (Grants.SYSADMIN) in self.grants:
            group = menu.group('Администрирование и настройка')
            group.item('Настройка', 'pages/settings') 
            group.item('Процедуры', 'domino/pages/procs') 
            group.item('Протокл работы пользователей', 'pages/protocol')
            group.item('Специальные наборы товаров', 'pages/product_sets')
            group.item('Утвержденные дисконтные схемы', 'pages/shemes.open')
            group.item('Тест производительности', 'discount_test', target=menu.DOWNLOAD)
            group.item('Спецификации обмена', 'https://docs.google.com/document/d/1bPO4wXqwbesi7YskgdUIGrGEZ1jzZFiQ5Jthys4fE-Y/edit?usp=sharing', target=menu.NEW_WINDOW)
             
    def __call__(self):
        Title(self, self.application.module_name)
        #self.print_version((Grants.SYSADMIN, Grants.BOSS, Grants.ASSISTANT) in self.grants)
        Text(self).mt(1).text(self.grants.get_description())
        self.print_menu()
