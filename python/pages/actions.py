import flask, sqlite3, json, datetime, os
from domino.page import Page
from domino.page_controls import print_check_button
from domino.core import log
from discount.action_types import ActionTypes
import discount.actions
from discount.core import DISCOUNT_DB, SCHEMES_FOLDER
from discount.actions import Action
from discount.schemas import ДисконтнаяСхема
from discount.page import DiscountPage

CALC_TAB = 'calc'
ACCEPT_TAB = 'accept'

class ThePage(DiscountPage):
    def __init__(self, application, request):
        super().__init__(application, request)
        #self.account_id = self.request.account_id()
        self.action_types = self.application['action_types']
        self.action_id = self.attribute('action_id')
        self._action = None
        self.tab_id = self.attribute('actions_tab_id', CALC_TAB)
    @property
    def calc_tab(self):
        return self.tab_id == CALC_TAB

    @property
    def accept_tab(self):
        return self.tab_id == ACCEPT_TAB
    
    @property
    def action(self):
        if self._action is None:
            self._action = Action.get(self.cursor, self.action_id)
        return self._action

    def cancel(self):
        self.print_row(self.table('actions'), self.action)

    def edit(self):
        self.print_row(self.table('actions'), self.action, edit=True)

    def copy(self):
        with self.connection:
            action = Action()
            action.type = self.action.type
            action.info = self.action.info
            action.pos = self.action.pos + 1
            action.status = self.action.status
            action.create(self.cursor)
        self.print_table()
        self.message(self.action_id)

    def схема_в_которой_присутствует_акция(self, ID):
        for схема in ДисконтнаяСхема.findall(self.cursor):
            if схема.расчетные_акции.есть_акция_ID(ID):
                return схема
            if схема.послепродажные_акции.есть_акция_ID(ID):
                return схема
        return None
        
    def delete(self):
        схема = self.схема_в_которой_присутствует_акция(self.action_id)
        if схема is not None:
            self.error(f'Данная акция используется а дисконтой схеме "{схема.наименование}"')
            return
        with self.connection:
            self.cursor.execute('delete from actions where id=?', [self.action_id])
        self.table('actions').row(self.action_id)
        self.message(f'Удалена акция {self.action_id}')

    def toggle_status(self):
        with self.connection:
            if self.action.status >= 0:
                self.action.status = -1
            else:
                self.action.status = 0
            self.action.update(self.cursor)
            self.renumerate()
            self.print_row(self.table('actions'), self.action)

    def ondrop(self):
        move = Action.get(self.cursor, self.get('moved'))
        with self.connection:
            self.renumerate()
            if self.calc_tab:
                if self.action.pos > move.pos:
                    move.pos = self.action.pos + 1
                else:
                    move.pos = self.action.pos - 1
                move.update(self.cursor)
            else:
                if self.action.after_sales_pos > move.after_sales_pos:
                    move.after_sales_pos = self.action.after_sales_pos + 1
                else:
                    move.after_sales_pos = self.action.after_sales_pos - 1
                move.update(self.cursor)
            self.connection.commit()
        self.print_table()

    def print_row(self, table, action, edit=False):
        action_type = self.action_types[action.type]
        row = table.row(action.id)\
            .ondrag({'moved':action.id})\
            .ondrop('.ondrop', {'action_id':action.id})
        if action_type is None:
            return
        print_check_button(row,'toggle_status', action.status >= 0, params={'action_id':action.id}, size='small')
        cell = row.cell()
        opacity = ''

        if action_type.CLASS == 0:
            if action.fixed_price:
                cell.glif('circle', style=f'color:tomato;font-size:0.5em; {opacity}')
        else:
            cell.glif('circle', style=f'color:gray;font-size:0.5em; {opacity}')

        
        #row.href(f'{action_type.description()} {action.description}', f'action_types/{action.type}.settings_page' , {'action_id':action.id})
        row.href(f'-{action.полное_наименование(self.action_types)}', f'action_types/{action.type}.settings_page' , {'action_id':action.id})
        period = []
        if action.start_date is not None:
            if action.start_date.minute == 0 and action.start_date.hour == 0:
                period.append(f'c {action.start_date.format("YYYY-MM-DD")}')
            else:
                period.append(f'c {action.start_date.format("YYYY-MM-DD HH:mm")}')
        if action.end_date is not None:
            if action.end_date.minute == 0 and action.end_date.hour == 0:
                period.append(f'по {action.end_date.format("YYYY-MM-DD")}')
            else:
                period.append(f'по {action.end_date.format("YYYY-MM-DD HH:mm")}')
        row.cell().text(' '.join(period))
        cell = row.cell(cls='text-right')
        if action.status >= 0:
            pass
            #row.text('')
        else:
            cell.button().glif('trash',style='color:tomato').small().cls('bg-white mr-1 -text-danger').onclick('.delete', {'action_id':action.id})
        cell.button().glif('copy').small().cls('bg-white text-info').onclick('.copy', {'action_id':action.id})
         
    def actions(self):
        if self.calc_tab:
            return Action.calc_actions(self.cursor, self.action_types)
        else:
            return Action.accept_actions(self.cursor, self.action_types)

    def print_table(self):
        table = self.table('actions', hole_update=True).mt(1)
        with self.connection:
            self.renumerate()
        for action in self.actions():
            self.print_row(table, action)

    def create_new_action(self):
        ACTION_TYPE = self.get('action_type')
        action_type = self.action_types[ACTION_TYPE]
        with self.connection:
            action = Action()
            #action.description = action_type.description()
            action.description = ''
            action.type = action_type.id
            action.pos = 0
            action.after_sales_pos = 0
            action.create(self.cursor)
            self.print_table()

    def renumerate(self):
        num = 0
        for action in self.actions():
            num += 10
            if self.calc_tab:
                action.pos = num
            else:
                action.after_sales_pos = num 
            action.update(self.cursor)

    @property
    def tabs(self):
        return [
            [CALC_TAB, 'Расчетные акции'],
            [ACCEPT_TAB, 'Послепродажные акции (действия)']
        ]

    def draw_tab(self):
        tab = self.tab('tab').mt(1)
        for item in self.tabs:
            tab.item().text(item[1]).active(self.tab_id == item[0])\
                .onclick('.on_change_tab', {'actions_tab_id':item[0]})

    def on_change_tab(self):
        self.draw_tab()
        self.draw_tab_contence()

    def get_action_types(self):
        types = []
        for action_type in self.action_types.types():
            if action_type.is_available():
                description = action_type.description()
                if self.calc_tab:
                    if action_type.hasCalculator:
                        types.append([str(action_type.id), f'{description}'])
                elif self.accept_tab:
                    if action_type.hasAcceptor:
                        types.append([str(action_type.id), f'{action_type.id} {description}'])
        return sorted(types, key = lambda t : t[1])

    def draw_tab_contence(self):
        p = self.toolbar('toolbar').mt(1)
        d = p.item().drop_down('Создать новую акцию', cls='btn-outline-secondary')
        for t in self.get_action_types():
            d.item(t[1]).onclick('.create_new_action', {'action_type':t[0]}) 
        
        self.print_table()

    def open(self):
        self.title(f'Набор акций')
        about = self.text_block()

        self.draw_tab()
        self.draw_tab_contence()

