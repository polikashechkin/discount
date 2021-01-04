import os, datetime, sqlite3, arrow, json
from domino.core import log, DOMINO_ROOT
from . import Page as BasePage
from . import Title, Button, Text, Toolbar, Input, Select
from domino.jobs import JobReport, Задача, remove_job, JOBS_DB, Proc

class Shedule:
    def __init__(self, proc):
        self.proc = proc
        self._load()

    def _load(self):
        self.TIME = self.proc.info.get('TIME','')
        try:
            houer, minutes = self.proc.info.get('TIME',':').split(':')
            self.HOUER = int(houer)
            self.MINUTES = int(minutes)
        except:
            self.HOUER = ''
            self.MINUTES = ''
        self.days = []
        try:
            self.DAYS = self.proc.info.get('DAYS', '')
            self.days = []
            for day in self.DAYS.split(','):
                self.days.append(int(day))
        except:
            pass

    @property
    def description(self):
        if self.TIME:
            if self.DAYS:
                return f'{self.DAYS} числа каждого месяца в {self.TIME}'
            else:
                return f'Ежедневно в {self.TIME}'
        else:
            return 'РАСПИСАНИЕ НЕ ЗАДАНО'

    def change_day(self, day):
        day = int(day)
        if day in self.days:
            self.days.remove(day)
        else:
            self.days.append(day)
            self.days = sorted(self.days)
        self.DAYS = ",".join([str(d) for d in self.days])
        self.proc.info['DAYS'] = self.DAYS
        self.proc.save()

    def change_time(self, houer, minutes):
        HOUER = int(houer)
        if HOUER <0 or HOUER > 11:
            raise Exception(f'Неправлино задан час "{houer}"')

        if minutes:
            MINUTES = int(minutes)
            if MINUTES <0 or MINUTES > 59:
                raise Exception(f'Неправлино заданы минуты "{minutes}"')
        else:
            MINUTES = 0
        
        self.TIME = f'{HOUER:02}:{MINUTES:02}'
        self.proc.info['TIME'] = self.TIME
        self.proc.save()
        self._load()


class Page(BasePage):

    def __init__(self, application, request):
        super().__init__(application, request)

        self.proc_id = self.attribute('proc_id')
        self.proc = Proc.get_by_id(self.proc_id)
        self.shedule = Shedule(self.proc)

    def change_day(self):
        day = self.get('day')
        self.shedule.change_day(day)
        self.print_params()
        self.message(day)

    def change_params(self):
        self.shedule.change_time(self.get('houer'), self.get('minutes'))
        self.print_params()

    def delete(self):
        if 'TIME' in self.proc.info:
            del self.proc.info['TIME']
        if 'DAYS' in self.proc.info:
            del self.proc.info['DAYS']
        self.proc.save()
        self.shedule = Shedule(self.proc)
        self.print_params()

    def print_params(self):
        Text(self, 'shedule' ).style('font-size:2rem').text(self.shedule.description)
        Text(self, '001').css('h5').mt(1).text('Время запуска')
        time_toolabr = Toolbar(self, 'time_toolbar')
        houer = Select(time_toolabr.item(mr=0.5), name='houer', value=self.shedule.HOUER)\
            .onchange('.change_params', forms=[time_toolabr])
        houer.option('','')
        for h in range(12):
            houer.option(h, f'{h:02}')
        minutes = Select(time_toolabr.item(), name='minutes', value=self.shedule.MINUTES)\
            .onchange('.change_params', forms=[time_toolabr])
        minutes.option('','')
        for m in range(60):
            minutes.option(m, f'{m:02}')
        Button(time_toolabr.item(ml='auto'), 'Удалить расписание')\
            .onclick('.delete')

        Text(self,'002').css('h5').mt(1).text('Дни месяца')
        days = Toolbar(self, 'days', style='flex-wrap: wrap')
        for i in range(31):
            enable = i+1 in self.shedule.days
            button = Button(days.item(mr=0.5, mb=0.5), f'{i+1}')
            if enable:
                button.style('background-color:green; color:white')
            button.onclick('.change_day', {'day':i+1})


    def __call__(self):
        Title(self, f'{self.proc.ID}, {self.proc.info.get("description")}')
        self.print_params()
        
