
from domino.core import log
from discount.core import Finder

def group_table(page, cur, finder):
    table = page.table('departments', hole_update=True)
    table.column('UID')
    table.column('Код')
    table.column('Описание')
    cur.execute('''
        select 
            rawtohex(id), 
            code, 
            name
        from 
            db1_agent
        where 
            class=2 and type=40566786
        order by name
        ''')
    for id, code, name in cur:
        if not finder.match(id, code, name):
            continue
        row = table.row(id)
        row.text(id)
        row.text(code)
        row.text(f'{name}')

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
    page.title('Торговые подразделения')
    toolbar = page.table('toolbar', css='table-borderless').row()
    finder.append(toolbar)
   
    #finder.input(name='toolbar')
    #finder.button().glif('search').on_click('.find', forms=[finder]).secondary()
    
    conn = page.application.account_database_connect(account_id)
    cur = conn.cursor()
    group_table(page, cur, finder)
    conn.close()
