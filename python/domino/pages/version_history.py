import os, sys, flask, sqlite3, json, requests
from domino.core import log, Version
from . import Page as BasePage, Title, Text

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def __call__(self):
        module_id = self.get('module_id',self.application.module_id)
        module_name = self.get('module_name', self.application.module_name)
        version = Version.parse(self.get('verion'))
        if not version:
            version = self.application.version

        Title(self, f'{module_name}, версия {self.application.version}')
        data = {'product_id':module_id, 'version_id': str(version.draft())}
        r = requests.post('http://rs.domino.ru:88/api/product/desc', data=data)
        #text = r.text
        Text(self).text(r.text)
        #self.text_block().text(text)
