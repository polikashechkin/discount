import os, sys, json, requests
from domino.core import log
from domino.account import Account
from . import Page as BasePage, Title, Text

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def __call__(self):
        #account = Account(self.account_id)
        #if self.application.module_id == 'users_and_depts':
        #    name = account.info.name
        #else:
        name = self.application.module_name
        Title(self, f'{name}, версия {self.application.version}')
        data = {'product_id':f'{self.application.module_id}', 'version_id': str(self.application.version.draft())}
        r = requests.post('http://rs.domino.ru:88/api/product/desc', data=data)
        #text = r.text
        Text(self).text(r.text)
        #self.text_block().text(text)

