import os, sys, flask, sqlite3, json, requests
from domino.core import log
from . import Page as BasePage, Title, Text

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def __call__(self):
        Title(self, f'Дисконтный сервер, версия {self.application.version}')
        data = {'product_id':'discount', 'version_id': str(self.application.version.draft())}
        r = requests.post('http://rs.domino.ru:88/api/product/desc', data=data)
        #text = r.text
        Text(self).text(r.text)
        #self.text_block().text(text)
