import flask, json, os, sys
from domino.core import log
from . import Page as BasePage
from . import Title, Text, Toolbar, Select
from domino.page_controls import КраснаяКнопка, ПлоскаяТаблица
from tables.sqlite.schema import Schema

#from . import Grant, User
#from grants import Grants

#BIGSIZE = {
#    '' : 'ВСЕГДА ЗАГРУЖАТЬ НАБОРЫ В ПАМЯТЬ',
#    0  : 'НИКОГДА НЕ ЗАГРУЖАТЬ НАБОРЫ В ПАМЯТЬ',
#    1000 : 'ЗАГРУЖАТЬ В ПАМЯТЬ ЕСЛИ РАЗМЕР НАБОРА ДО 1000 ТОВАРОВ',
#    2000 : 'ЗАГРУЖАТЬ В ПАМЯТЬ ЕСЛИ РАЗМЕР НАБОРА ДО 2000 ТОВАРОВ',
#    5000 : 'ЗАГРУЖАТЬ В ПАМЯТЬ ЕСЛИ РАЗМЕР НАБОРА ДО 5000 ТОВАРОВ',
#    10000 : 'ЗАГРУЖАТЬ В ПАМЯТЬ ЕСЛИ РАЗМЕР НАБОРА ДО 10000 ТОВАРОВ'
#}

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.sqlite = None
    
    def onchange(self): 
        bigsize = self.get_int('bigsize')
        self.sqlite.query(Schema).update({'bigsize':bigsize}) 
        self.message(f'{bigsize}')

    def __call__(self):
        Title(self, 'Настройка')
        Text(self).mt(1).css('h5').text('Режим больших наборов')
        Text(self).mt(1).text('''
            При работе с товарными наборами, может оказаться так,
            что наборы содежжат большое количество отобранных товаров (10_000, 100_000).
            Это может приводить к негативным последствиям. Замедляется подготовка дисконтных
            схем (утверждение) и активно используется оперативная память сервера, поскольку по умолчанию,
            все отобранные товарв загружаются в рперативную память сервера для эффективной последующей
            обработки отчетов. Что бы уменьшить потребность в оперативной памяти и спользуется следующий режим,
            суть которого не загружать в ОП наборы а постоить для них специальную БД и обращаться к ней.
            Это позволяет спизитьпотребнойсть ОП за счет более медленной обработки запросов.
            Данные изменения всупают в силу только после утверждения дисконтных схем
            ''')
        schema = self.sqlite.query(Schema).get(0) 
        toolbar = Toolbar(self, 'toolbar').mt(1)
        select = Select(toolbar.item(), name='bigsize', value=schema.bigsize)\
            .onchange('.onchange', forms=[toolbar])
        select.option('', 'ВСЕГДА ЗАГРУЖАТЬ НАБОРЫ В ПАМЯТЬ')
        select.option('0', 'НИКОГДА НЕ ЗАГРУЖАТЬ НАБОРЫ В ПАМЯТЬ')
        select.option('1000', 'ЗАГРУЖАТЬ В ПАМЯТЬ ЕСЛИ РАЗМЕР НАБОРА ДО 1000 ТОВАРОВ')
        select.option('2000', 'ЗАГРУЖАТЬ В ПАМЯТЬ ЕСЛИ РАЗМЕР НАБОРА ДО 2000 ТОВАРОВ')
        select.option('5000', 'ЗАГРУЖАТЬ В ПАМЯТЬ ЕСЛИ РАЗМЕР НАБОРА ДО 5000 ТОВАРОВ')
        select.option('10000', 'ЗАГРУЖАТЬ В ПАМЯТЬ ЕСЛИ РАЗМЕР НАБОРА ДО 10000 ТОВАРОВ')


