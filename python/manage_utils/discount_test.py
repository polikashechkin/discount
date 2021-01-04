import os, sys, datetime, requests, pickle, json, uuid, random, arrow
from multiprocessing import Process, Queue
from time import sleep

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(DIR))

from discount.pos import PosCheck

VALUES_FILE = 'calc_emi.def'
VALUES = {}

try:
    with open(os.path.join(DIR, VALUES_FILE)) as f:
        VALUES = json.load(f)
except:
    pass

def question(q):
    old_value = VALUES.get(q, '')
    new_value = input(f'{q} [{old_value}] ? ')
    if new_value != '':
        VALUES[q] = new_value
        with open(os.path.join(DIR, VALUES_FILE), 'w') as f:
            json.dump(VALUES, f)
        return new_value
    else:
        return old_value

def h(text):
    print()
    print(text.upper())
    d = ('-'* len(text))
    print(d)
#-----------------------------------------------------------------------
def pos_test(q, pos, check, CHECK_COUNT, CHECK_TIMEOUT, LONG, DAYS):
    print(f'pos {pos:3} : процесс {os.getpid()} начальная дата {check.date}')

    calc_max = 0
    calc_min = None
    calc_time = 0
    calc_count = 0
    calc_error = 0
    calc_long = 0
    calc_try_count = 0
    calc_error_message = []

    accept_min = None
    accept_max = 0
    accept_time = 0
    accept_count = 0
    accept_error = 0
    accept_long = 0
    accept_try_count = 0
    accept_error_message = []

    check_date = check.date

    for day in range(DAYS):
        if check_date:
            check.date = check_date + datetime.timedelta(days = day)
            print(f'pos {pos} : новый день {check.date.date()}')

        for i in range(CHECK_COUNT):
            timeout = random.randrange(1, CHECK_TIMEOUT)
            sleep(timeout)
            #---------------------------------------
            check.next_check()
            #---------------------------------------
            try_count = 0
            ms = 0
            while True:
                r = check.calc()
                ms += r.ms
                if r.error:
                    try_count += 1
                    calc_error_message = r.message
                    print(f'pos {pos} чек {i:5} : повтор {check.timeout} : {try_count}/{check.try_count}')
                    if try_count < check.try_count:
                        sleep(check.SLEEP)
                    else:
                        break
                else:
                    break
            #---------------------------------------
            calc_time += ms
            calc_count += 1
            calc_try_count += try_count
            if ms > calc_max:
                calc_max = ms
            if calc_min is None or ms < calc_min:
                calc_min = ms
            if ms > LONG:
                calc_long += 1
            if r.error:
                calc_error += 1
                print(f'pos {pos:3} чек {i:5} : ОЩИБКА РАСЧЕТА : попыток {try_count + 1} : {ms} ms')
            else:
                #-----------------------------------------
                try_count = 0
                ms = 0
                while True:
                    r = check.accept()
                    ms += r.ms
                    if r.error:
                        try_count += 1
                        print(f'pos {pos} : повтор {try_count}/{check.try_count}')
                        if try_count < check.try_count:
                            sleep(check.SLEEP)
                        else:
                            break
                    else:
                        break
                #-----------------------------------------
                accept_count += 1
                accept_try_count += try_count
                accept_time += r.ms
                if r.ms > accept_max:
                    accept_max = r.ms
                if accept_min is None or r.ms < accept_min:
                    accept_min = r.ms
                if r.ms > LONG:
                    accept_long += 1
                if r.error:
                    accept_error += 1
                    print(f'pos {pos:3} check {i:5} : ОШИБКА  {r.ms + ms} ms')
                else:
                    date = check.date.date() if check.date else ''
                    print(f'pos {pos:3} : check {i:3} : {date} : {round(ms, 3)} mс, {round(r.ms, 3)} мс')

    res = {}
    res['pos'] = pos
    res['calc_count'] = calc_count
    res['calc_time'] = calc_time
    res['calc_min'] = calc_min
    res['calc_max'] = calc_max
    res['calc_long'] = calc_long
    res['calc_error'] = calc_error
    res['calc_try_count'] = calc_try_count

    res['accept_count'] = accept_count
    res['accept_time'] = accept_time
    res['accept_min'] = accept_min
    res['accept_max'] = accept_max
    res['accept_long'] = accept_long
    res['accept_error'] = accept_error
    res['accept_try_count'] = accept_try_count

    q.put(res)
    print(f'pos {pos:3} : end')

def get_test_check_json(server, account_id, ID):
    r = requests.get(f'https://{server}/discount/active/python/get_test_check_json?account_id={account_id}&id={ID}')
    if r.status_code != 200:
        print(f'{r.status_code} {r.text}')
        sys.exit(1)
    CHECK = PosCheck(account_id, ID)
    CHECK.from_json(r.text)
    return CHECK

if __name__ == "__main__":
    QUEUE = []
    LONG = 200

    server = question('Сервер')
    account_id = question('Учетная запись')

    status_code = ''
    text = ''
    try:
        r = requests.get(f'https://{server}/discount/active/python/get_test_checks?account_id={account_id}')
        status_code = r.status_code
        text = r.text
        if status_code != 200:
            print(f'status_code : {status_code}, text : {text}')
        checks = r.json()
    except BaseException as ex:
        print(f'{ex} : {status_code} : {text}')
        sys.exit(1)
    
    for ID, name in checks:
        print(ID, name)

    CHECK_I = int(question('Чек'))
    CHECK = get_test_check_json(server, account_id, CHECK_I)
    #------------------------------------------
    CHECK.server = server
    CHECK.next_check()

    #------------------------------------------
    r = CHECK.calc()
    if r.error:
        print(f'ОШИБКА : {r.message}')
        sys.exit(1)
    r = CHECK.accept()
    if r.error:
        print(f'ОШИБКА {r.message}')
        sys.exit(1)
    #------------------------------------------
    
    for line in CHECK.lines.values():
        print(f'{line.ID} : {line.params.get("NAME")}')
    #------------------------------------------

    DATE = question('Дата чека ("." - теущая дата')
    DATE  = DATE.strip()
    if DATE == '.':
        CHECK.date = None
    else:
        CHECK.date = datetime.datetime.strptime(DATE, '%Y-%m-%d')
    if CHECK.date is not None:
        DAYS = int(question('Количество дней'))
    else:
        DAYS = 1
    POS_COUNT = int(question('Количество кассовых аппаратов'))
    CHECK_COUNT = int(question('Количество чеков в день'))
    CHECK_TIMEOUT = int(question('Среднее время на чек (с)'))
    TIMEOUT = float(question('Время ожидания исполнения запроса (с)'))
    CHECK.timeout = TIMEOUT
    CHECK.SLEEP = float(question('Время ожидания между попытепми запросов (с)'))
    TRY_COUNT = int(question('Количество повторов при ошибке запроса'))
    CHECK.try_count = TRY_COUNT
     
    print()
    check_total = DAYS * CHECK_COUNT * POS_COUNT
    print(f'Общее количество чеков {check_total:,}')
    check_time = (CHECK_TIMEOUT / 2 + 0.5)
    total_seconds = check_time * (DAYS * CHECK_COUNT)
    t = datetime.timedelta(seconds = total_seconds)
    print(f'Ориентировочная продолжительность теств  {t}')
    print(f'Ориентировочная интенсивноять  {round((check_total / total_seconds) * 60,0)} чек/мин')
    print()
    print('Для нечала теста нажмите любую клавишу ...')
    input()

    start = datetime.datetime.now()
    process = []
    for pos in range(0, POS_COUNT):
        q = Queue()
        QUEUE.append(q)
        p = Process(target=pos_test, args=(q, pos, CHECK, CHECK_COUNT, CHECK_TIMEOUT, LONG, DAYS))
        p.start()
        process.append(p)

    for p in process:
        p.join()
    end = datetime.datetime.now()

    total_calc_min = 0
    total_calc_max = 0
    total_calc_time = 0
    total_calc_count = 0
    total_calc_error = 0
    total_calc_long = 0
    total_calc_try_count = 0

    total_accept_min = 0
    total_accept_max = 0
    total_accept_time = 0
    total_accept_count = 0
    total_accept_error = 0
    total_accept_long = 0
    total_accept_try_count = 0

    for q in QUEUE:
        res = q.get()
        pos = res['pos']

        calc_min = res['calc_min']
        calc_max = res['calc_max']
        calc_long = res['calc_long']
        calc_time = res['calc_time']
        calc_count = res['calc_count']
        calc_error = res['calc_error']
        calc_try_count = res['calc_try_count']

        accept_min = res['accept_min']
        accept_max = res['accept_max']
        accept_long = res['accept_long']
        accept_time = res['accept_time']
        accept_count = res['accept_count']
        accept_error = res['accept_error']
        accept_try_count = res['accept_try_count']

        if calc_min > total_calc_min:
            total_calc_min = calc_min
        if calc_max > total_calc_max:
            total_calc_max = calc_max
        total_calc_count += calc_count
        total_calc_time += calc_time
        total_calc_error += calc_error
        total_calc_long += calc_long
        total_calc_try_count += calc_try_count

        if accept_min > total_accept_min:
            total_accept_min = accept_min
        if accept_max > total_accept_max:
            total_accept_max = accept_max
        total_accept_count += accept_count
        total_accept_time += accept_time
        total_accept_error += accept_error
        total_accept_long += accept_long
        total_accept_try_count += accept_try_count

    h('РЕЗУЛЬТАТ')
    print()
    print('РАСЧЕТЫ')
    print(f'Общее количество        {total_calc_count}')
    print(f'Долгие                  {total_calc_long} (более {LONG} мс)')
    print(f'Общее всемя             {total_calc_time} мс')
    print(f'Минимальное время       {total_calc_min} мс')
    print(f'Максимальное время      {total_calc_max} мс')
    print(f'Среднее время           {round(total_calc_time / total_calc_count, 3)}')
    print(f'Количество повторов     {total_calc_try_count}')
    print(f'Количество ошибок       {total_calc_error}')
    print()
    print('ПОСЛЕПРОДАЖНАЯ ОБРАБОТКА')
    print(f'Общее количество        {total_accept_count}')
    print(f'Долгие                  {total_accept_long} (более {LONG} мс)')
    print(f'Общее всемя             {total_accept_time} мс')
    print(f'Минимальное время       {total_accept_min} мс')
    print(f'Максимальное время      {total_accept_max} мс')
    print(f'Среднее время           {round(total_accept_time / total_accept_count, 3)}')
    print(f'Количество повторов     {total_accept_try_count}')
    print(f'Количество ошибок       {total_accept_error}')
    print()
    print('ОБЩИЕ ИТОГИ')
    print(f'Количество чеков        {total_accept_count}')
    print(f'Количество повторов     {total_accept_try_count + total_calc_try_count}')
    print(f'Количество ошибок       {total_accept_error + total_calc_error}')
    print(f'Начало теста            {start}')
    print(f'Окончание теста         {end}')
    print(f'Продолжительность       {end - start}')
    print(f'Интенсивность           {round( total_accept_count / (end - start).total_seconds()  * 60, 6)} чек/мин')



