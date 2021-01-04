import sqlite3
from lxml import etree as ET
from domino.core import log
from . import Response as BaseResponse 
#from discount.checks import Check
#from discount.calculator import AccountDeptWorker
#from domino.account import find_account, find_account_id
from domino.application import Status
#from discount.cards import Card
from domino.tables.postgres.discount_card import DiscountCard as Card
from discount.core import DISCOUNT_DB
from discount.series import CardType
import barcodenumber

class Response(BaseResponse):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.postgres = None

    def __call__(self):
        card_id = self.get('card_id')
        date = self.get('date')
        check_guid = self.get('check_guid')

        #card = Card.get(self.postgres, card_id)
        card = Card.find(self.postgres, card_id)
        self.LOG.comment(card_id)

        if card is None:                    
            response = Status.error(f'Неизвестная карта').xml()
            return response

        conn = sqlite3.connect(DISCOUNT_DB(self.account_id))
        card_type = CardType.get(conn.cursor(), card.TYPE)
        conn.close()
        card_classes = self.application['card_types']
        card_class = card_classes[card_type.type]
       
        response = card_class.check_card(card, card_type)
        self.LOG.response_type('xml')
        return response
            
