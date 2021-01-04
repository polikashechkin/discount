import json, sqlite3, re, arrow
from discount.cards import Card, CardLog
from discount.core import DISCOUNT_DB 
from discount.series import ТипКарты

def error(msg):
    return json.dumps({'status':'error', 'message': msg }, ensure_ascii=False)  

def set_card_params(card, request):
    EMAIL = request.args.get('email')
    if EMAIL is not None:
        card.почта = EMAIL
        card.почта_подтверждена = 1
    card.фамилия = request.args.get('name')
    card.имя = request.args.get('name1')
    card.отчество = request.args.get('name2')
    DAY = request.args.get('day')
    if DAY is not None:
        card.день_рождения = arrow.get(DAY).datetime().date()
    SEX = request.args.get('sex')
    if SEX is not None:
        card.пол = SEX

    sms = request.args.get('sms')
    if sms is not None:
        card.рассылка_по_СМС = sms

    mailing = request.args.get('mailing')
    if mailing is not None:
        card.рассылка_по_почте = mailing

    TEST = request.args.get('test')
    if TEST == '1':
        card.это_тестовая_карта = True

def create_or_update_card_responce(application, request):
    account_id = request.args.get('account_id')
    if account_id is None:
        return error('не задана учетная запись')

    with application.account_database_connect(account_id) as db_connection\
            ,sqlite3.connect(DISCOUNT_DB(account_id)) as connection:
        курсор_БД = db_connection.cursor()
        курсор = connection.cursor()
        card = None
        phone = request.args.get('phone')
        телефон = None
        if phone is not None:
            телефон = Card.преобразовать_к_нормальному_виду(phone)
            if телефон is None:
                return error(f'ошибочный номер телефона "{phone}"')
            card = Card.findfirst(курсор_БД, 'phone=:0', [phone])
        
        if card is None:
            card = Card()
            card.телефон = телефон
            card.телефон_подтвержден = 1
            set_card_params(card, request)
            тип_карты = ТипКарты.get(курсор, 0)
            card.create_card(курсор_БД, курсор, тип_карты)
            status = {'status':'success'}
            status['code'] = card.ID
            status['num'] = card.маркировочный_номер
            status['created'] = 1
            #курсор.commit()
            #курсор_БД.commit()
        else:
            set_card_params(card, request)
            card.телефон_подтвержден = 1
            update_card(курсор_БД, card)
            status = {'status':'success'}
            status['code'] = card.ID
            status['num'] = card.маркировочный_номер
            status['updated'] = 1
            #курсор.commit()
            #курсор_БД.commit()

        return json.dumps(status, ensure_ascii=False)

    return json.dumps({'error':'success', 'message':'карта не создана'}, ensure_ascii=False)
'''
def create_card(db_cursor, cursor, card, тип_карты, user_name = None):
    card.TYPE = тип_карты.id
    if тип_карты.activation_mode == ТипКарты.activation_mode_CREATE:
        card.STATE = Card.ACTIVE
        exp_days = тип_карты.exp_days
        if exp_days is not None:
            exp_date = arrow.get()
            exp_date.shift(days = exp_days)
            card.дата_окончания_действия = exp_date.date()
    else: 
        card.STATE = Card.CREATED

    card.процент_скидки = тип_карты.начальная_процентная_скидка
    card.накопленные_баллы = тип_карты.начальнаое_количество_баллов

    if тип_карты.gen_mode_random:
        card.generate(db_cursor, тип_карты.prefix, тип_карты.suffix, тип_карты.digits)
    else:
        номер = тип_карты.следующий_номер
        card.generate(db_cursor, тип_карты.prefix, тип_карты.suffix, тип_карты.digits, тип_карты.следующий_номер)
        тип_карты.следующий_номер = номер + 1
        тип_карты.update(cursor)

    cardlog = CardLog(card_id = card.ID)
    if card.STATE == Card.ACTIVE:
        cardlog.operation = CardLog.ACTIVATE
    else:
        cardlog.operation = CardLog.CREATE
    if user_name is not None:
        cardlog.info = {'user_name' : user_name}
    cardlog.create(db_cursor)
'''

def update_domino_card(db_cursor, card):
    SEX = '0093000901390002' if card.sex == 0 else '0093000901390001'
    SMS = '07D2000307D20001' if card.рассылка_по_СМС else '07D2000307D20002'
    MAILING = '07D2000307D20001' if card.рассылка_по_почте else '07D2000307D20002'
    sql = ''' 
        update db1_document set
        name = :name, f14745642 :name1, f14745643  =:name2,
        f14811139 =:day,
        f14811160 = :SEX,
        f14745623  = :EMAIL,
        f56033328 = : PHONE,
        f3342345 = :SNS,
        f55771139 = :MAILING
        where type=54919179 and class=54919176 and code = :0
        '''
    db_cursor.execute(sql)

def update_card(db_cursor, card):
    card.update(db_cursor)
