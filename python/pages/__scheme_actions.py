import flask, sqlite3, json, datetime, os
from domino.page import Page
from domino.core import log
from discount.action_types import ActionTypes
import discount.actions
from discount.core import DISCOUNT_DB, SCHEMES_FOLDER
from discount.actions import Action

def action_row(table, action):
    row = table.row(action.id)
    row.text(action.status)
    row[1].text(f'{action.id}')
    row[2].text(f'{action.type}')
    row[3].text(action.description)
    row[4].text(action.start_date_string)
    row[5].text(action.end_date_string)
    row[6].text(f'{action.info}')
        
def action_table(page, cur):
    table = page.table('actions', hole_update=True)
    table.column('').style('-width:1rem;')
    table.column().text('Номер')
    table.column().text('Тип')
    table.column().text('Наименование / Описание')
    table.column().text('Начало')
    table.column().text('Окончание')
    table.column().text('Дополнительная информация')
    for action in sorted(Action.findall(cur), key = lambda action : action.pos):
        action_row(table, action)
    return table

def open(page):
    page.application['navbar'](page)
    action_types = page.application['action_types']
    account_id = page.request.account_id()
    SCHEME_ID = page.attribute('scheme_id')
    page.title(f'Акции')

    with sqlite3.connect(os.path.join(SCHEMES_FOLDER(account_id), SCHEME_ID)) as conn:
        cur = conn.cursor()
        action_table(page, cur).style('margin-top:0.5rem;')
    
