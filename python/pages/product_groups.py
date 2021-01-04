
from domino.core import log
from discount.core import Finder

def group_table(page, cur, finder):
    table = page.table('product_groups', hole_update=True)
    table.column('Код')
    table.column('UID')
    table.column('Описание')
    cur.execute('''
        select 
            rawtohex(C.id), 
            C.name, 
            G.name,
            C.code,
            DOMINO.DominoUIDToString(C.id)
        from 
            db1_classif C, db1_classif G
        where 
            C.name is not NULL and C.type=14745602 and C.pid = G.id
        order by G.name
        ''')
    for id, name, gname, code, uid in cur:
        if not finder.match(code, uid, name, gname):
            continue
        row = table.row(id)
        row.text(code)
        row.text(uid)
        row.text(f'{gname} :: {name}')

def find(page):
    page.application['navbar'](page)
    account_id = page.request.account_id()
    conn = page.application.account_database_connect(account_id)
    cur = conn.cursor()
    finder = Finder(page)
    group_table(page, cur, finder)
    conn.close()

def open(page):
    page.application['navbar'](page)
    account_id = page.request.account_id()
    finder = Finder(page)
    page.title('Товарные группы')
    toolbar = page.table('toolbar', css='table-borderless').row()
    finder.append(toolbar)
   
    #finder.input(name='toolbar')
    #finder.button().glif('search').on_click('.find', forms=[finder]).secondary()
    
    conn = page.application.account_database_connect(account_id)
    cur = conn.cursor()
    group_table(page, cur, finder)
    conn.close()
