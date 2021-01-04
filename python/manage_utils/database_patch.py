import os, sys, datetime, requests, pickle, json, sqlite3, arrow
import xml.etree.ElementTree as ET
python = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(python)

from domino.core import log
from discount.core import DISCOUNT_DB, CARDS, CARDS_LOG, Engine
from discount.series import ТипКарты
from discount.cards import Card
from domino.postgres import Postgres

'''
def импорт_старых_карт(c, e):
        print()
        print('ИМПОРТ СОЗДАННЫХ КАРТ ИЗ ДОМИНО')
        print('При переходе на Posgres остаются созданные в ORACLЕ карты')
        print('Их надо загрузить в Posgres если их там еще нет')
        engine = Engine(e.db_connection, e.pg_connection)

        for тип_карты in ТипКарты.findall(e.cursor):
            count = Card.ora_count(engine, 'TYPE=:0', [тип_карты.id])
            print(f'{тип_карты.id:3} {count:10} {тип_карты.полное_наименование:20}')
        TYPE_ID = input('Тип карт ? ')
        if TYPE_ID == '':
            return
        тип_карты = ТипКарты.get(e.cursor, TYPE_ID)
        print(f'{тип_карты.полное_наименование}')

        print()
        q = c.input('Подтвердите выполнение действия [Y/N]')
        if q != "Y":
            return

        count = 0       
        update = 0
        with e.connection, e.pg_connection:
            for card in Card.ora_findall(engine, 'TYPE=:0', [тип_карты.id]):
                print(card.ID)
                try:
                    card.pg_create(engine)
                    update += 1
                except BaseException as ex:
                    print(f'{ex}')

                count += 1
        print(f'просмотрено {count}, создано {update}')
'''

def корректировка_даты_активации(c, e):
        engine = Engine(e.db_connection, e.pg_connection)
        print()
        print('КОРРЕКТИРОВКА ДАТЫ АКТИВАЦИИ')
        for тип_карты in ТипКарты.findall(e.cursor):
            count = Card.count(engine, 'TYPE=:0', [тип_карты.id])
            print(f'{тип_карты.id:3} {count:10} {тип_карты.полное_наименование:20}')
        TYPE_ID = input('Тип карт ? ')
        if TYPE_ID == '':
            return
        тип_карты = ТипКарты.get(e.cursor, TYPE_ID)
        print(f'{тип_карты.полное_наименование}')

        print()
        q = input('Подтвердите выполнение действия [Y/N]')
        if q != "Y":
            return

        count = 0       
        update = 0
        not_exist = 0
        with e.db_connection:
            cursor = e.db_connection.cursor() 
            for card in Card.findall(engine, 'TYPE=:0', [тип_карты.id]):
                count += 1
                change=False
                if card.дата_активации is None:
                    not_exist += 1
                    date = card.info.get('check_date')
                    if date is not None:
                        card.дата_активации = arrow.get(date).datetime
                        change = True
                if card.код_подразделения is None:
                    card.код_подразделения = card.info.get('dept_code')
                    if card.код_подразделения is not None:
                        change = True
                if change:
                    card.update(cursor)
                    update += 1
        print(f'просмотрено {count}, нет даты {not_exist}, обновлено {update}')


def change_type(c, e):
        print()
        print('ИЗМЕНЕНИЕ ТИПА КАРТ')
        print('Изменение производится в бд ORACLE')
        engine = Engine(e.db_connection, e.pg_connection)
        for тип_карты in ТипКарты.findall(self.cursor):
            count = Card.ora_count(engine, 'TYPE=:0', [тип_карты.id])
            print(f'{тип_карты.id:3} {count:10} {тип_карты.полное_наименование:20}')
        TYPE_ID = input('Старый тип карт ? ')
        if TYPE_ID == '':
            return
        тип_карты = ТипКарты.get(e.cursor, TYPE_ID)
        print(f'{тип_карты.полное_наименование}')
        TYPE_NEW_ID = input('Новый тип карт ? ')
        if TYPE_NEW_ID == '':
            sys.exit(1)
        новый_тип_карты = ТипКарты.get(e.cursor, TYPE_NEW_ID)
        print(f'{новый_тип_карты.полное_наименование}')

        print()
        q = input('Подтвердите выполнение действия [Y/N]')
        if q != "Y":
            return
       
        with e.db_connection:
            sql = f''' update {CARDS} set TYPE={новый_тип_карты.id} where TYPE={тип_карты.id} '''
            print(sql)
            e.db_cursor.execute(sql)

