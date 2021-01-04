import os, sys, datetime, requests, pickle, json, sqlite3, arrow

python = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(python)

from domino.core import log
from discount.actions import Action
from discount.schemas import Schema 

def общий_список_всех_акций(c, e):
    c.print_header('Дисконтные схемы')
    
    s_actions = {}

    for sh in Schema.findall(e.cursor):
        print(f'{sh.ID} {sh.наименование} {sh.расчетные_акции.список_акций} {sh.послепродажные_акции.список_акций}')
        for a in  sh.расчетные_акции.список_акций:
            if a not in s_actions:
                s_actions[a] = sh.ID
            else:
                print(f'Двойное использование {a} => {s_actions[a]}, {sh.ID}')
        for a in sh.послепродажные_акции.список_акций:
            if a not in s_actions:
                s_actions[a] = sh.ID
            else:
                print(f'Двойное использование {a} => {s_actions[a]}, {sh.ID}')
    print (f'{s_actions}')
    c.print_header('Висячие акции')
    count = 0
    d_actions = []
    for a in Action.findall(e.cursor):
        if a.ID not in s_actions:
            count += 1
            c.print_error(f'{a.ID:06} {a.схема_ID} {a.description}' )
            d_actions.append(a.ID)
        else:
            print(f'{a.ID:06} {a.схема_ID} {a.description}' )
    if count > 0:
        c.print_error(f'ОБНАРУЖЕНО {count} висячих акций')
        yes = input('Удалить [Y/N] ?')
        if yes == 'Y':
            c.print_header(f'Удаление висячих акций')
            with e.connection:
                for a_ID in d_actions:
                    e.cursor.execute('delete from actions where ID=?', [a_ID])
                    print(f'Удалена {a_ID}')


        
