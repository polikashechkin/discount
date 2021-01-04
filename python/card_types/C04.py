import flask, sqlite3, json, datetime, random
from domino.core import log
from discount.cards import Card, CardLog
from discount.series import Series, CardType
from discount.series_page import TheSeriesPage
#from application import Status
import xml.etree.cElementTree as ET
#from domino.page import Page

CLASS = 4

def description():
    return f'Персональная карта'

def about(page, to_detail = False):
    t = page.text_block().text('''
    Персональная карта дает право на получение 
    скидок на товары или услуги в зависимости от накопленных баллов.
    Правила расчета скидок и начисления баллов определяется набором акций, 
    связанных с данной картой. 
    Карта может быть как именной, так и безымянной.
    ''')
    if to_detail:
        t.href('Подробнее ...', f'card_types/C04.description_page')
    return t

def on_activate(series):
    pass

def on_create(series):
    series[Series.DIGITS] = 8
    series.prefix = f'{series.id:04}-'
    series[Series.SUFFIX] = f'-{series.id:04}'
    series[Series.ACTIVATION_MODE] = Series.activation_mode_CREATE
    series[Series.EXPIRATION] = Series.expiration_NONE

# ---------------------------------------
# CHECK CARD
# ---------------------------------------
def error(detail = None):
    STATUS = ET.fromstring('<STATUS/>')
    ET.SubElement(STATUS, 'status').text = 'error'
    ET.SubElement(STATUS, 'message').text = 'Карта недоступна для использования'
    if detail is not None:
        ET.SubElement(STATUS, 'detail').text = detail
    return ET.tostring(STATUS, encoding='utf-8')

def check_card(card, series):
    STATUS = ET.fromstring('<STATUS/>')
    if card.STATE == Card.CREATED:
        # Не активированная карта, можно либо продать либо отвергнуть
        if series.info.get(Series.ACTIVATION_MODE, '') == Series.activation_mode_SALE:
            # Карту надо продать, но проверить параметры
            try:
                price = float(series.info.get(Series.PRICE))
            except:
                #return error(f'Не задана цена продажи')
                return error(f'Карта не доступна для продажи (Не задана цена продажи)')
            code = series.info.get('product_code')
            if code is None:
                return error(f'Карта не доступна для продажи(Не задан код товара для продажи)')
            STATUS = ET.fromstring('<STATUS/>')
            ET.SubElement(STATUS, 'status').text = 'success'
            name = f'{series.полное_наименование}'
            ET.SubElement(STATUS, 'card', attrib = {'id':card.id, 'type':'discount-sale', 'price':f'{price}', 'product_code':f'{code}', 'name':name})
            #return ET.tostring(STATUS, encoding='utf-8')

    elif card.это_активная_карта:
        ET.SubElement(STATUS, 'status').text = 'success'
        name = f'{series.полное_наименование}'.strip()
        attrib = {'id':card.id, 'type' : 'discount', 'name':name}
        if card.points:
            attrib['points'] = f'{card.points}'
        ET.SubElement(STATUS, 'card', attrib = attrib)
    else:
        ET.SubElement(STATUS, 'status').text = 'error'
        ET.SubElement(STATUS, 'message').text = 'Карта недоступна для использования'

    return ET.tostring(STATUS, encoding='utf-8').decode('utf-8')

# ---------------------------------------
# SETTINGS
# ---------------------------------------
class ThePage(TheSeriesPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def набор_основных_параметров(self):
        return ['наименование', 'префикс', 'суффикс', 'количество_цифр', 
        'способ_генерации_номера', 'соответствующий_товар', 
        'способ_активации', "цена", "максимальное_количество_покупок", 
        "количество_баллов", "процент_скидки", "следующий_номер", CardType.CODE_FORMAT
        ]

    def print_title(self):
        self.title(f'{self.series.type_name} "{self.series.description}"')

    def settings_page(self):
        self.print_title()
        about(self, True)
        self.параметры()

    def description_page(self):
        self.title(f'{description()}')
        about(self)

