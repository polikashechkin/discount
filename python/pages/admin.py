import flask, sqlite3, json, os, sys
#from domino.page import Page
from domino.core import log, DOMINO_LOG
from domino.application import Response
from domino.databases import Databases
from domino.account import find_account
from domino.page import Page
from domino.page_controls import КраснаяКнопка, ПлоскаяТаблица, Кнопка, ПрозрачнаяКнопка
from discount.core import DISCOUNT_DB, discount_log
from discount.users import Пользователь, Права, АДМИНИСТРАТОР, РУКОВОДИТЕЛЬ
from discount.page import DiscountPage

class TheResponse(Response):
    def __init__(self, application, request):
        super().__init__(application, request)
    
    def show_discoount_log(self):
        lines = []
        with open(os.path.join(DOMINO_LOG, 'discount.log')) as f:
            for line in f:
                lines.append(line)
        return self.make_show_string_response(''.join(lines))

class ThePage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request)
    
    def clear_protocol(self):
        file = os.path.join(DOMINO_LOG, 'discount.log')
        with open(file, 'w') as f:
            f.write('')
        self.message('протокол очищен')

    def open(self):
        self.title('Администратор')

        p = self.text_block()
        p.header('Протокол вызывов дисконтонго сервера')
        p = self.toolbar('toolbar').mt(1)
        Кнопка(p, 'Посмотреть в отдельном окне', mr=0.5).onclick('.show_discoount_log', target='new_window')
        Кнопка(p, 'Очистить протокол', mr=0.5).onclick('.clear_protocol')

        