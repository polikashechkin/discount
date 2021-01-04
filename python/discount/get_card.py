import json, re
from discount.cards import Card

def error(msg):
    return json.dumps({'status':'error', 'message': msg }, ensure_ascii=False)        

def card_info(card):
    status = {'status':'success'}
    status['code'] = card.ID
    status['num'] = card.маркировочный_номер
    if card.телефон is not None:
        status['phone'] = str(card.телефон)
    name = card.ФИО
    if name != '':
        status['name'] = name
    if card.день_рождения is not None:
        status['day'] = str(card.день_рождения.date()) 
    почта = card.почта
    if почта is not None and почта.strip() != '':
        status['email'] = почта
    if card.пол is not None:
        status['пол'] = str(card.пол)
    status['sms'] = str(card.рассылка_по_смс)
    status['mailing'] = str(card.рассылка_по_почте)
    status['discount'] = str(card.процент_скидки)
    return json.dumps(status, ensure_ascii=False)

def get_card_responce(application, request):
    account_id = request.args.get('account_id')
    if account_id is None:
        return error('не задана учетная запись')
    with application.account_database_connect(account_id) as conn:
        cursor = conn.cursor()
        card = None
        phone = request.args.get('phone')

        if phone is not None:
            телефон = Card.преобразовать_к_нормальному_виду(phone)
            if телефон is None:
                return error(f'карта с телефоном "{phone}" не найдена')
            card = Card.findfirst(cursor, 'phone=:0', [phone])
            if card is None:
                return error(f'карта с телефоном {phone} не найдена')
            else:
                return card_info(card)

        code = request.args.get('code')
        if code is not None:
            card = Card.get(cursor, code)
            if card is None:
                return error(f'карта с кодом {code} не найдена')
            else:
                return card_info(card)
        
        num = request.args.get('num')
        if num is not None:
            card = Card.findfirst(cursor, 'TYPE=0 and MARKNUM=:0', [num.strip()])
            if card is None:
                return error(f'карта с номером {num} не найдена')
            else:
                return card_info(card)

    return error('карта не найдена')