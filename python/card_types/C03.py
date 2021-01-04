import flask, sqlite3, json, datetime, random
from domino.core import log
from discount.cards import Card, CardLog
from discount.series import Series, CardType
from discount.series_page import TheSeriesPage
#from application import Status
import xml.etree.cElementTree as ET

CLASS = 3

def description():
    return f'Подарочная карта'

def about(page, to_detail = False):
    t = page.text_block().text('''
    Подарочная карта (подарочный сертификат) не дает право на получение 
    каких либо скидок. Это своеобразное платежное средство. На нее кладутся
    денежные средства во время покупки через кассовый аппарат. В дальнейшем
    данные средства можно использовать при оплате покупок наряду с другими средствами оплаты.
    ''')
    if to_detail:
        t.href('Подробнее ...', f'card_types/C03.description_page')
    return t

def on_activate(series):
    pass

def on_create(series):
    series[Series.DIGITS] = 8
    series.prefix = f'{series.id:04}-'
    series[Series.SUFFIX] = f'-{series.id:04}'
    #series[Series.CASH] = 1000
    #series[Series.REUSABLE] = 0
    #series[Series.EXPIRATION] = Series.expiration_NONE
    series[Series.ACTIVATION_MODE] = Series.activation_mode_SALE
    series.description = f'Подарочная карта ({series.id})'

# ---------------------------------------
# CHECK CARD
# ---------------------------------------

def check_card(card, card_type):
    STATUS = ET.fromstring('<STATUS/>')
    if card.STATE == Card.CREATED:
        ET.SubElement(STATUS, 'status').text = 'success'
        price = card_type.cash
        #log.debug(f'{card_type.cash}')
        code = card_type.info.get('product_code')
        name = f'{card_type.полное_наименование}'
        ET.SubElement(STATUS, 'card', attrib = {'id':card.id, 'type':'gift-sale', 'price':f'{price}', 'product_code':f'{code}', 'name':f'{name}'})
    elif card.STATE == Card.ACTIVE:
        ET.SubElement(STATUS, 'status').text = 'success'
        cash = card.cash
        name = f'{card_type.полное_наименование}'
        if card.reusable:
            reusable = '1'
        else:
            reusable = '0'
        ET.SubElement(STATUS, 'card', attrib = {'id':card.id, 'type':'gift', 'cash':f'{cash}', 'reusable':f'{reusable}', 'name':f'{name}'})
    else:
        ET.SubElement(STATUS, 'status').text = 'error'
        ET.SubElement(STATUS, 'message').text = 'Карта недоступна для использования'

    return ET.tostring(STATUS, encoding='utf-8').decode('utf-8')

# ---------------------------------------
# THE_PAGE
# ---------------------------------------
class ThePage(TheSeriesPage):
    def __init__(self, application, request):
        super().__init__(application, request)
    
    def набор_основных_параметров(self):
        return ['наименование', 'префикс', 'суффикс', 'количество_цифр', 'способ_активации',
        'способ_генерации_номера', 'срок_действия', 'номинал', 'соответствующий_товар',
        'многоразовое_использование', 'следующий_номер', CardType.CODE_FORMAT]

    def settings_page(self):
        self.print_title()
        about(self, True)
        self.параметры()

    def description_page(self):
        self.title(f'{description()}')
        about(self)

