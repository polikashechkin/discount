import os, sys, json, importlib
from domino.core import log
from domino.application import Status

class CardClass: 
    def __init__(self, module_name, module):
        self.id = module_name
        self.module = module
        self._check_card = getattr(self.module, 'check_card', None)
        self.ID = int(module_name[1:])
        
    #@property
    #def is_coupon(self):
    #    return self.id == 'C01'
    @property
    def это_купон(self):
        return self.id == 'C01'
    #@property
    #def is_discount_card(self):
    #    return self.id == 'C02'
    @property
    def это_дисконтная_карта(self):
        return self.id == 'C02'
    #@property
    #def is_gift_card(self):
    #    return self.id == 'C03'
    @property
    def это_подарочная_карта(self):
        return self.id == 'C03'
    @property
    def это_персональная_карта(self):
        return self.id == 'C04'

    def description(self):
        return self.module.description()

    def about(self, page):
        try:
            return self.module.about(page)
        except:
            return None

    def on_create(self, series):
        return self.module.on_create(series)

    def generate(self, card_database_cursor, series, info = {}):
        return self.module.generate(card_database_cursor, series, info)

    def __str__(self):
        return f'CardClass({self.ID})'

    def check_card(self, card, series):
        if self._check_card is None:
            if card.STATE < 0:
                return Status.error(f'Заблокированная карта или погашенный купон').xml()
            else:
                name = series.description if series is not None else f'Неизвестный выпуск'
                return Status.success({'name': name}).xml()
        else:
            return self._check_card(card, series)

CardType = CardClass

class CardClasses:
    def __init__(self, application):
        self._items = {}
        try:
            for name in os.listdir(os.path.join(application.python_path, 'card_types')):
                if name.endswith('.py'): 
                    name = name.replace('.py', '')
                    module = importlib.import_module(f'card_types.{name}')
                    card_class = CardClass(name, module)
                    self._items[card_class.id] = card_class
        except:
            log.exception(f'CardClasses')

    def __getitem__(self, name):
        return self._items.get(name)
    def values(self):
        return self._items.values()
    def types(self):
        return self._items.values()
    def __str__(self):
        return f'<CardClaases {[self._items]}>'
    
CardTypes = CardClasses
