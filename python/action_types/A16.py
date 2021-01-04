import flask, sqlite3, json, datetime
from domino.core import log
from discount.core import DISCOUNT_DB, CARDS
from discount.actions import Action
from .action_page import TheActionPage
from .action_base import ActionAcceptor
from discount.series import Series
from discount.cards import Card, CardLog
from discount.checks import Check

ID = 'A16'
CLASS = 1
DESCRIPTION = 'Стандартная обработка карт'
ABOUT = '''
    Погашаются купоны, предъявленные в чеке, но только в том случае, когда
    по ним были выданы какие либо скидки. В протовном случае купон
    не погашается и остается активным
    '''
IS_AVAILABLE = False

#def is_available():
#    return False

#def description():
#    return DESCRIPTION

#=============================================
# Description
#=============================================


def about(page, to_detail = False):
    x = page.text_block('about')
    x.text(ABOUT)
    if to_detail:
        x.href('Подробнее...', 'action_types/{ID}.description_page')
    return x

#=============================================
# Acceptor
#=============================================

class Acceptor():
    def __init__(self, worker, cursor, action, LOG, SQLITE):
        self.card_types = worker.card_types
        self.series_set = {}
        for series in Series.findall(cursor):
            self.series_set[int(series.id)] = series
    
    def __str__(self):
        return f'СТАНДАРТНАЯ ОБРАБОТКА КАРТ'

    def accept(self, engine, check):
        #cursor = engine.cursor
        #log.debug(f' accept series_set {self.series_set}')
        msg = []
        if check.TYPE:
            msg.append('ВОЗВРАТ')
        # активация купленных карт
        if not check.TYPE:
            for line in check.lines:
                if line.product_type == 'CARD':
                    card =  Card.get(engine, line.barcode)
                    if card is not None:
                        if card.STATE == Card.ACTIVE:
                            msg.append(f'карта {card.ID} уже активна')
                        elif card.STATE == Card.CREATED:
                            # активация карты ---------------------
                            card_type = self.series_set[card.TYPE]
                            try:
                                card.активировать(engine, card_type, check = check, operation=CardLog.ПОКУПКА)
                                msg.append(f'карта {card.ID} активирована')
                            except BaseException as ex:
                                log.exception(f'{self} : активация {card}')
                                msg.append(f'карта {card.ID} ошибка при активации "{ex}"')
                            # -------------------------------------
                        else:
                            msg.append(f'карта {card.ID} имеет недопустимый статус "{card.STATE}"')
                    else:
                        msg.append(f'карта {line.barcode} не найдена')
        # обработка предъявленных карт
        if check.TYPE: # ВОЗВРАТ
            for card_ID, card_info in check.cards.items():
                card = card_info.get(Check.CARD_CARD)
                if card:
                    card_type = self.series_set.get(card.TYPE)
                    if card_type.это_персональная_карта:
                        #статистика = card.статистика
                        БЫЛО_ПОКУПОК = card.checks
                        БЫЛО_СУММА = card.total
                        card.аннулировать_покупку(check)
                        СТАЛО_ПОКУПОК = card.checks
                        СТАЛО_СУММА = card.total
                        msg.append(f'карта {card.ID} покупок {СТАЛО_ПОКУПОК}={БЫЛО_ПОКУПОК}-1 на сумму {СТАЛО_СУММА}={БЫЛО_СУММА}-{check.total}')

                        card.update(engine)

        else:
            for card_ID, card_info in check.cards.items():
                card = card_info.get(Check.CARD_CARD)
                if card:
                    card_type = self.series_set.get(card.TYPE)
                    if card_type is None:
                        check.log.write(f'СТАНДАРТНАЯ ОБРАБОТКА КАРТ', f'карта {card.ID} : неизвестный тип карты {card.TYPE}')
                        #check.log.write(f'СТАНДАРТНАЯ ОБРАБОТКА КАРТ', f'{self.series_set}')
                        continue
                    #вид_карты = self.card_types[тип_карты.type]

                    USED_POINTS = card_info.get(Check.CARD_POINTS)
                    if USED_POINTS:
                        USED_POINTS = float(USED_POINTS)

                    if card_type.это_персональная_карта:
                        #статистика = card.статистика
                        БЫЛО_ПОКУПОК = card.checks
                        БЫЛО_СУММА = card.total
                        card.зафиксировать_покупку(check)
                        СТАЛО_ПОКУПОК = card.checks
                        СТАЛО_СУММА = card.total
                        msg.append(f'карта {card.ID} покупок {СТАЛО_ПОКУПОК}={БЫЛО_ПОКУПОК}+1 на сумму {СТАЛО_СУММА}={БЫЛО_СУММА}+{check.total}')

                        if USED_POINTS and USED_POINTS > 0:
                            было = card.points
                            card.списать_баллы(engine, USED_POINTS, check)
                            стало =  card.points
                            msg.append(f'баллов {стало}={было}-{USED_POINTS}')

                        card.update(engine)

                    elif card_type.это_купон:
                        if card.STATE == Card.ACTIVE:
                            card.погасить_купон(engine, check=check, points = USED_POINTS)
                            msg.append(f'купон {card.ID} погвшен')
                            #card.update(engine)
                        else:
                            msg.append(f'купон {card.ID} не активен')
                    elif card_type.это_дисконтная_карта:
                        if USED_POINTS and USED_POINTS > 0:
                            было = card.points
                            card.списать_баллы(engine, USED_POINTS, check)
                            стало =  card.points
                            msg.append(f'карта {card.ID} баллов {было} - {USED_POINTS} = {стало}')
                            #card.update(cursor)
                    elif card_type.это_подарочная_карта:
                        pass
            
        if not check.TYPE: # ПРОДАЖА
            # обработка оплат подарочными картами
            for payment in check.payments:
                TYPE = payment.get(Check.PAYMENT_TYPE)
                if TYPE == 'GIFT':
                    total = float(payment.get(Check.TOTAL))
                    card_ID = payment.get(Check.PAYMENT_CARD_ID)
                    card = Card.get(engine, card_ID)
                    if card is None:
                        msg.append(f'подарочная карта {card_ID} не найдена')
                    else:
                        msg.append(f'подарочная карта {card_ID} оплата {total}')
                        card.оплатить(engine, total, check = check)

        check.write_log('Стандартная обработка карт'.upper(),', '.join(msg))

#=============================================
# Settings 
#=============================================

class ThePage(TheActionPage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.print_tab_exists = False
    
    def settings_page(self):
        self.print_title()
        about(self).margin(1).href(f' Подробнее ...', f'action_types/{self.action.type}.description_page')

    def description_page(self):
        self.title(f'{ID}. {DESCRIPTION}')
        about(self)

