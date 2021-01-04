import flask, sqlite3, json, datetime, random
from domino.core import log
import discount.series
from discount.series import CardType
from discount.core import DISCOUNT_DB, CARDS
from discount.series_page import TheSeriesPage

from discount.cards import Card, CardLog
from discount.series import Series
import xml.etree.cElementTree as ET

CLASS = 1
#MIN_DIGITS = 6
#MAX_DIGITS = 12
#TRY_CREATE_COUNT = 10

def description():
    return f'Подарочный купон'

def about(page, to_detail=False):
    t = page.text_block().text('''
    Подарочный купон предоставляет право на получение одноразовой скидки
    на определённые товары либо услуги. Купоны могут быть созданы в результате 
    действия какой либо акции или созданы вручную. После получения скидки по купону,
    купон погашается (блокируется) и не может быть в дальнейшем использован.
    ''')
    if to_detail:
        t.href('Подробнее ...', f'card_types/C01.description_page')
    return t

def on_activate(series):
    pass

def on_create(series):
    series.info['digits'] = '5'
    series.prefix = f'{series.id:04}-'
    series.info[Series.GEN_MODE] = Series.gen_mode_RANDOM
    series.description = f'Подарочный купон ({series.id})'

# ---------------------------------------
# CHECK CARD
# ---------------------------------------

def check_card(card, series):
    STATUS = ET.fromstring('<STATUS/>')
    if card.STATE == Card.ACTIVE:
        ET.SubElement(STATUS, 'status').text = 'success'
        name = f'{series.полное_наименование}'
        ET.SubElement(STATUS, 'card', attrib = {'id':card.id, 'type':'coupon', 'name':name})
    else:
        ET.SubElement(STATUS, 'status').text = 'error'
        ET.SubElement(STATUS, 'message').text = 'Купон недоступен для использования'

    return ET.tostring(STATUS, encoding='utf-8').decode('utf-8')

# ---------------------------------------
# GENERATOR
# ---------------------------------------
def generate(cur, series, info):
    if series.gen_mode_random:
        card = Card()
        card.info = info
        card.series_id = series.id
        card.state = Card.ACTIVE
        card.generate(cur, series.prefix, series.suffix, series.digits)
        cardlog = CardLog(card_id=card.ID)
        cardlog.operation = CardLog.ACTIVATE
        cardlog.action_id = info.get('action_id')
        cardlog.check_id = info.get('check_id')
        cardlog.info = info
        cardlog.create(cur)
        return card
    else:
        raise Exception(f'Невозможно сгенерить купон : задана последовательная нумерация')
# ---------------------------------------
# THE_PAGE
# ---------------------------------------
class ThePage(TheSeriesPage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def набор_основных_параметров(self):
        return ['наименование', 'префикс', 'суффикс', 'количество_цифр',  
        'срок_действия', 'следующий_номер', 'количество_баллов', "процент_скидки", CardType.CODE_FORMAT, 'способ_генерации_номера'
        ]
 
    def settings_page(self):
        self.print_title()
        about(self, True)
        self.параметры()

    def description_page(self):
        self.title(f'{description()}')
        about(self)
        t = self.text_block().mt(1)
        t.text('''
        Код купона состоит из префикса, номера (число) и суффикса.
        Длина номера (количество цифр) задается при настроки типа купона.
        При генерации номера используется генератор случайных чисел. 
        ''')

