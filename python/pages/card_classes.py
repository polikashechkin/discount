from domino.core import log
from discount.card_types import CardTypes
from domino.page import Page as BasePage

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)

    def __call__(self):
        self.title(f'Виды карт')
        card_types = self.application['card_types']

        for card_type in card_types.types():
            self.text_block().mt(1).header(card_type.description())
            t = card_type.about(self)
            if t is None:
                t = self.text_block()
            t.href('Подробнее ...', f'card_types/{card_type.id}.description_page')

