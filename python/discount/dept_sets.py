import json, sqlite3, datetime, arrow, re
from domino.core import log, Time, Bool
from discount.core import DISCOUNT_DB
from discount.schemas import ДисконтнаяСхема

class DeptSetItem:

    @staticmethod
    def набор_кодов(курсор, TYPE=0):
        коды = set()
        for item in DeptSetItem.findall(курсор, 'TYPE=?', [TYPE]):
            try:
                коды.add(item.info['code'])
            except:
                log.exception(__file__)
        return коды

    def __init__(self, ID = None, TYPE = 0, набор=0, code = '', info = {}):
        self.ID = ID
        self.TYPE = TYPE 
        self.набор = набор
        self.info = info
        self.code = str(code)
        #log.debug(f'{self.ID}, TYPE, product_set, code, {self.info}')
    
    def __str__(self):
        return f'DeptSetItem({self.ID}, {self.набор}, {self.TYPE}, {self.code})'
    
    @property
    def dept_id(self):
        try:
            return self.info.get('code')
        except:
            return None

    @property
    def description(self):
        try:
            return self.info.get('description', '')
        except:
            return f'{self.info}'
    @description.setter 
    def description(self, value):
        self.info['description'] = value
     
    @staticmethod
    def _from_record(r):
        if r is None:
            return None
        else:
            ID, TYPE, набор, code, INFO = r
            #log.debug(f'_from_record {ID}, TYPE, product_set, code, {INFO}')
            try:
                info = json.loads(INFO)
            except:
                info = {}
        return DeptSetItem(ID, TYPE, набор, code, info)

    @staticmethod
    def get(cursor, ID):
        return DeptSetItem.findfirst(cursor, 'ID=?', [int(ID)])

    @staticmethod
    def findfirst(cursor, where_clause, params = []):
        q = f'select ID, TYPE, dept_set, code, info from dept_set_item where {where_clause}'
        cursor.execute(q, params)
        return DeptSetItem._from_record(cursor.fetchone())

    @staticmethod
    def findall(cursor, where_clause = None, params = []):
        items = []
        if where_clause is None:
            cursor.execute(f'select ID, TYPE, dept_set, code, info from dept_set_item')
        else:
            cursor.execute(f'select ID, TYPE, dept_set, code, info from dept_set_item where {where_clause}', params)
        for r in cursor:
            items.append(DeptSetItem._from_record(r))
        return items

    @staticmethod
    def count(cursor, where_clause = None, params = []):
        if where_clause is None:
            cursor.execute(f'select count(*) from dept_set_item')
        else:
            cursor.execute(f'select count(*) from dept_set_item where {where_clause}', params)
        return cursor.fetchone()[0]

    def create(self, cursor):
        cursor.execute('insert into dept_set_item(TYPE, dept_set, code, info) values (?,?,?,?)',
            [self.TYPE, self.набор, str(self.code), json.dumps(self.info, ensure_ascii=False)])
        self.ID = cursor.lastrowid

    def update(self, cursor):
        cursor.execute('update dept_set_item set TYPE=?, dept_set=?, code=?, info=? where ID=?',
            [self.TYPE, self.набор, str(self.code), json.dumps(self.info, ensure_ascii=False), self.ID])

    def delete(self, cursor):
        DeptSetItem.deleteall(cursor, 'ID=?', [self.ID])
    
    @staticmethod
    def deleteall(cursor, where_clause, params=[]):
        #log.debug(f'deleteall(cursor, {where_clause}, {params})')
        cursor.execute(f'delete from dept_set_item where {where_clause}', params)

#class ГотовыйНабор:
#    def __init__(self):
#        self.подразделения = {}#

#def добавить(self, курсор, набор_ID, value):
#        for item in DeptSetItem.findall(курсор, 'dept_set=?', [набор_ID]):
#            self.подразделения[item.code] = value
#    
#    def найти(self, строка, default = None):
#        return self.подразделения.get(строка.product, default)

class DeptSet:
    class Запрос:
        def __init__(self, набор):
            try:
                self.запрос = набор.info.get('запрос')
            except:
                self.запрос = {}
            if self.запрос is None:
                self.запрос = {}
            
            #log.debug(f'{self.запрос}')
        def сохранить(self, набор):
            набор.info['запрос'] = self.запрос
        
        def добавить(self, тег, значение):
            self.запрос[тег] = значение
        def найти(self, тег):
            return self.запрос.get(тег)
        def изменить(self, тег, значение):
            self.запрос[тег] = значение
        def удалить(self, тег):
            try:
                del self.запрос[тег]
            except:
                pass
        def теги(self):
            return self.запрос.keys()

        def теги_и_значения(self):
            r = []
            for имя_тега, значение in self.запрос.items():
                тег = СловарьТегов.get(имя_тега)
                if тег is not None:
                    r.append([тег, значение])
            return r
            
        def неиспользуемые_теги(self):
            r = []
            for тег in СписокТегов:
                if self.найти(тег.имя) is None:
                    r.append(тег)
            return r
        
        def sql(self, поля):
            sql = f'select {поля} from db1_agent a where class=2 and type=40566786'
            for имя_тега, значение in self.запрос.items():
                тег = СловарьТегов.get(имя_тега)
                if тег is None:
                    continue
                критерий = тег.поисковый_критерий(значение)
                if критерий is not None:
                    sql += f' and {критерий} '    
            return sql

    DESCRIPTION = 'description'
    СОРТИРОВКА_ПО_КОДУ = 'a.code'
    СОРТИРОВКА_ПО_НАИМЕНОВАНИЮ = 'a.name'
    def __init__(self, ID = None, CLASS=0, TYPE= 0, state=0, info = {}):
        self.ID = ID
        self.CLASS = CLASS
        self.TYPE = int(TYPE)
        self.state = state
        self.info = info
        self._запрос = None
        self._ценовые_форматы = None
    
    def __str__(self):
        return f'DeptSet({self.ID})'
    @property
    def дисконтная_схема_ID(self):
        return self.info.get('дисконтная_схема')
    @дисконтная_схема_ID.setter
    def дисконтная_схема_ID(self,value):
        self.info['дисконтная_схема'] = value
    
    def ценовые_форматы(self, курсор):
        if self._ценовые_форматы is None:
            новый_курсор = курсор.connection.cursor()
            self._ценовые_форматы = ЦЕНОВОЙ_ФОРМАТ.словарь(новый_курсор)
            новый_курсор.close()
        return self._ценовые_форматы

    @property
    def список_полей(self):
        return f'rawtohex(a.id), code, name, rawtohex(a.{ЦЕНОВОЙ_ФОРМАТ.поле})'

    def разбор_запроса(self, курсор, dept):
        теги = {}
        if dept[3] is not None:
            теги['Ценовой формат'] = self.ценовые_форматы(курсор).get(dept[3] ,'?')
        return dept[0], dept[1], dept[2], теги

    def выполнить_запрос(self, курсор, сортировка = None):
        sql = f'select {self.список_полей} from db1_agent a where class=2 and type=40566786'
        for тег, значение in self.запрос.теги_и_значения():
            критерий = тег.поисковый_критерий(значение)
            if критерий is not None:
                sql += f' and {критерий} '    
        if сортировка is not None:
           sql +=  ' order by ' + сортировка
        log.debug(f'{sql}')
        курсор.execute(sql)

    def выполнить_запрос_по_uid(self, курсор, uid):
        sql = f'select {self.список_полей} from db1_agent a where id=:0'
        log.debug(f'{sql}')
        курсор.execute(sql, [uid])
 
    def добавить_запрос(self, курсор_бд, курсор, использованные_коды = set()):
        self.выполнить_запрос(курсор_бд)
        added = 0
        for dept in курсор_бд:
            uid, code, name, теги = self.разбор_запроса(курсор_бд, dept)
            if code not in использованные_коды:
                added += self.добавить_подразделение(курсор, uid, code, name, теги)
        return added

    def удалить_все_подразделения(self, курсор):
        DeptSetItem.deleteall(курсор, 'dept_set=? and TYPE=?', [self.ID, 0])

    def обновить(self, курсор_бд, курсор):
        self.удалить_все_подразделения(курсор)
        self.добавить_запрос(курсор_бд, курсор)

    def добавить_подразделение_по_uid(self, курсор_бд, курсор, uid):
        self.выполнить_запрос_по_uid(курсор_бд, uid)
        added = 0
        for dept in курсор_бд:
            uid, code, name, теги = self.разбор_запроса(курсор_бд, dept)
            added += self.добавить_подразделение(курсор, uid, code, name, теги)
        return added

    def добавить_подразделение(self, курсор, uid, code, name, теги):
        added = 0
        item = DeptSetItem(набор = self.ID)
        item.code = uid
        item.info = {'code' : code, 'uid':uid, 'description':name, 'теги' : теги}
        try:
            item.create(курсор)
            added += 1
        except:
            pass
        return added
    def количество_подразделений(self, курсор):
        return DeptSetItem.count('dept_set=?', [self.ID])
   
#    @property
#    def сортировка(self):
#        if self._сортировка is None:
#            self._сортировка = DeptSet.Сортировка(self)
#        return self._сортировка

    @property
    def запрос(self):
        if self._запрос is None:
            self._запрос = DeptSet.Запрос(self)
        return self._запрос
    
    @property
    def это_живой_набор(self):
        return self.TYPE == 2
    
    @property
    def description(self):
        return self.info.get(DeptSet.DESCRIPTION, '')

    @property
    def полное_наименование(self):
        if self.TYPE == 0:
            name = 'Набор'
        elif self.TYPE == 2:
            name = 'Живой набор'
        else:
            name = f'<{self.TYPE}>'

        description = self.info.get(DeptSet.DESCRIPTION)
        if description is None:
            return name
        elif description.strip() == '':
            return name
        else:
             return f'{name} "{description}"'
    
    @staticmethod
    def _from_record(r):
        if r is None:
            return None
        else:
            ID, CLASS, TYPE, state, INFO = r
            try:
                info = json.loads(INFO)
            except:
                info = {}
        return DeptSet(ID, CLASS, TYPE, state, info)

    @staticmethod
    def get(cursor, ID):
        return DeptSet.findfirst(cursor, 'ID=?', [int(ID)])

    @staticmethod
    def findfirst(cursor, where_clause, params = []):
        #log.debug(f'findfirst(cursor, {where_clause}, {params})')
        q = f'select ID, CLASS, TYPE, state, info from dept_set where {where_clause}'
        cursor.execute(q, params)
        return DeptSet._from_record(cursor.fetchone())

    @staticmethod
    def findall(cursor, where_clause = None, params = []):
        items = []
        if where_clause is None:
            cursor.execute(f'select ID, CLASS, TYPE, state, info from dept_set')
        else:
            cursor.execute(f'select ID, CLASS, TYPE, state, info from dept_set where {where_clause}', params)
        for r in cursor:
            items.append(DeptSet._from_record(r))
        return items

    @staticmethod
    def count(cursor, where_clause = None, params = []):
        if where_clause is None:
            cursor.execute(f'select count(*) from dept_set')
        else:
            cursor.execute(f'select count(*) from dept_set where {where_clause}', params)
        return cursor.fetchone()[0]

    def create(self, cursor):
        cursor.execute('insert into dept_set(CLASS, TYPE, state, INFO) values (?,?,?,?)',
            [self.CLASS, self.TYPE, self.state, json.dumps(self.info, ensure_ascii=False)])
        self.ID = cursor.lastrowid

    def update(self, cursor):
        if self._запрос is not None:
            self._запрос.сохранить(self)
        #if self._сортировка is not None:
        #    self._сортировка.сохранить(self)
        cursor.execute('update dept_set set CLASS=?, TYPE=?, state=?, info=? where ID=?',
            [self.CLASS, self.TYPE, self.state, json.dumps(self.info, ensure_ascii=False), self.ID])

    def delete(self, cursor):
        DeptSet.deleteall(cursor, 'ID=?', [self.ID])

    @staticmethod
    def deleteall(cursor, where_clause, params):
        cursor.execute(f'delete from dept_set where {where_clause}', params)

НаборПодразделений = DeptSet
