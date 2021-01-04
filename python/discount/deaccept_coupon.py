import domino.database 
from domino.account import find_account_id
from domino.log import log
from datetime import datetime

def response(request):
    try:
        account_id = find_account_id(request.get('account_id'))
        if account_id is None:
            return 'Нет такой учетной записи', '400 Unknown account'

        coupon_id = request.get('coupon_id')
        if coupon_id is None:
            return 'Не задан купон', '400 Unknown coupon'
        conn = domino.database.connect(account_id)
        cur = conn.cursor()
        cur.execute(f"update coupon set state=0 where state=1 and id=:0",[coupon_id])
        accepted = cur.rowcount != 0
        if accepted:
            s = f'insert into coupon_log (coupon_id, creation_time, info) values(:0, sysdate, :1)'
            cur.execute(s, [coupon_id, f'Купон восстановлен'])
        conn.commit()
        conn.close()
        if not accepted:
            return f'Купон "{coupon_id}" недействитеный или не погашен', '400 Unknown coupon'
        else:
            return ''
    except BaseException as ex:
        log.exception(request.url)
        return f'Ошибка выполнения {ex}', f'500 {ex}'