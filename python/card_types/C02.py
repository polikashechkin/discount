import flask, sqlite3, json, datetime, random
import xml.etree.cElementTree as ET
from domino.core import log
from discount.core import DISCOUNT_DB, CARDS
from discount.cards import Card, CardLog
from discount.series import Series, CardType
from discount.series_page import TheSeriesPage

CLASS = 2

# ---------------------------------------
# DESCRIPTION
# ---------------------------------------

def description():
    return f'Дисконтная карта'

def about(page, to_detail=False):
    t = page.text_block().text('''
    Дисконтная карта (скидочная карта) дает право на получение 
    скидок на товары или услуги.Это определяется
    набором акций, связанных с данной картой
    Карта может быть как именной, так и безымянной.
    ''')
    if to_detail:
        t.href('Подробнее ...', f'card_types/C02.description_page')

def on_activate(series):
    pass

def on_create(card_type):
    card_type[Series.DIGITS] = 8
    card_type.prefix = f'{card_type.id:04}-'
    card_type[Series.SUFFIX] = f'-{card_type.id:04}'
    card_type.description = f'Дисконтная карта ({card_type.id})'


# ---------------------------------------
# CHECK CARD
# ---------------------------------------

def error(detail = None):
    STATUS = ET.fromstring('<STATUS/>')
    ET.SubElement(STATUS, 'status').text = 'error'
    ET.SubElement(STATUS, 'message').text = 'Карта недоступна для использования'
    if detail is not None:
        ET.SubElement(STATUS, 'detail').text = detail
    return ET.tostring(STATUS, encoding='utf-8').decode('utf-8')

def check_card(card, series):
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
            return ET.tostring(STATUS, encoding='utf-8').decode('utf-8')
        else:
            # Не активированная дисконтная картак - недопустима
            return error()
    elif card.STATE == Card.ACTIVE:
        STATUS = ET.fromstring('<STATUS/>')
        ET.SubElement(STATUS, 'status').text = 'success'
        name = f'{series.полное_наименование}'
        ET.SubElement(STATUS, 'card', attrib = {'id':card.id, 'type':'coupon', 'name':name})
        return ET.tostring(STATUS, encoding='utf-8').decode('utf-8')
    return error()

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
        "количество_баллов", "процент_скидки", "следующий_номер", "срок_действия", CardType.CODE_FORMAT
        ]

    def settings_page(self):
        self.print_title()
        about(self, True)
        self.параметры()

    def description_page(self):
        self.title(f'{description()}')
        about(self)

