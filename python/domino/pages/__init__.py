from domino.page import Page, IconButton, Title, Chip
import os, datetime
from domino.core import log
from domino.page_controls import Кнопка as Button, ПрозрачнаяКнопка as FlatButton, ПлоскаяТаблица as FlatTable
 
def Row(page, table_id, row_id):
    return page.Row(table_id, row_id)

class Rows:
    def __init__(self, page, id):
        self.page = page
        self.id = id

    def row(self, id):
        return Row(self.page, self.id, id)

#def IconButton(page, icon, **kwargs):
#    return page.icon_button(icon, **kwargs)

def BookmarkIconButton(page, checked=True):
    if checked:
        return IconButton(page, None, 'bookmark', style='color:brown')
    else:
        return IconButton(page, None, 'bookmark', style='color:lightgray')

def CheckIconButton(page, checked=True):
    if checked:
        return IconButton(page, None, 'check', style='color:green')
    else:
        return IconButton(page, None, 'check', style='color:lightgray')

def EditIconButton(page):
    return IconButton(page, None, 'edit', style='color:lightgray')

def DeleteIconButton(page):
    return IconButton(page, None, 'close', style='color:red')

def AddIconButton(page):
    return IconButton(page, None, 'add', style='color:green')

def RemoveIconButton(page):
    return IconButton(page, None, 'remove', style='color:red')

def RefreshIconButton(page):
    return IconButton(page, None, 'refresh', style='color:gray')

#def Title(page, text):
#    return page.title(text)

def Toolbar(page, ID, **kwargs):
    return page.toolbar(ID, **kwargs)

def Input(page, **kwargs):
    return page.input(**kwargs)

def Select(page, **kwargs):
    return page.select(**kwargs)

def InputDate(page, **kwargs):
    return page.input(type='date', **kwargs)

def Table(page, ID, **kwargs):
    return page.Table(ID, **kwargs)

def InputText(page, ID = None, height=10, **kwargs):
    return page.textarea(ID, **kwargs).style(f'height:{height}rem')

def TextWithComments(cell, text, comments):
    if comments is not None and len(comments) > 0:
        comments_ = ', '.join([f'{c}' for c in comments])
        cell.html(f'<span style="white-space:nowrap">{text}</span><p style="font-size:small;color:gray; line-height: 1em">{comments_}</p>')
    else:
        cell.text(text)

def Text(page, ID = None, **kwargs):
    if ID:
        return page.text_block(ID, **kwargs)
    else:
        return page.text_block(**kwargs)
