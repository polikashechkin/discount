
import sys, os, json, time
from domino.account import Account, find_account

from domino.databases.postgres import Postgres
from domino.databases.sqlite import Sqlite

from tables.sqlite.product_set import ProductSet
from tables.sqlite.product_set_item import ProductSetItem
from tables.Good import Good


if __name__ == "__main__":
    try:
        account_id = sys.argv[1]
    except:
        print('НЕ ЗАДАНА УЧЕТНАЯ ЗАПИСЬ')
        sys.exit(1)

    account = find_account(account_id)
    if account is None:
        error = f'Не найдена учетная запись'
        print(error)
        sys.exit(1)

    POSTGRES = Postgres.Pool().session(account_id)
    SQLITE = Sqlite.Pool().session(account_id, module_id='discount')
    
    print('=========')
    items = {}
    start = time.perf_counter()
    count = 0
    for item in SQLITE.query(ProductSetItem).limit(100000):
        count += 1
        #if count % 2:
        items[f'{item.e_code}'] = item
    print(f'========= {len(items)} {time.perf_counter() - start}')

    start = time.perf_counter()
    query = POSTGRES.query(Good)
    query = query.filter(Good.e_code.in_(items))
    goods = []
    for good in query.order_by(Good.name).limit(500):
        item = items[good.e_code]
        goods.append(good)

    print(f'========== {len(goods)} {time.perf_counter() - start}')
    #    print(product_set)

