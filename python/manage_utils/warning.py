import logging, sys
from time import sleep
import arrow
import datetime

log = logging.getLogger()
hdlr = logging.FileHandler('logger.txt')
formatter = logging.Formatter('%(levelname)s\t%(asctime)s\t%(message)s')
formatter = logging.Formatter('%(levelname)s\t%(created)f\t%(message)s')
hdlr.setFormatter(formatter)
log.addHandler(hdlr) 
#log.setLevel(logging.INFO)
log.setLevel(logging.DEBUG)


for i in range(1,10):
    try:
        print(sys.argv[1] + ' '+  str(i))
        log.info(' ====\t ===')
        if i>8:
            a = 10 / 0
        if  i > 3:
            raise Exception('sssssss')
        sleep(0.1)
    except BaseException as ex:
        log.error(f'?{ex}?')
        log.exception('vvvvvvvvvvvvvААЦУЦААЦА')

with open('logger.txt') as f:
    now = datetime.datetime.now()
    for line in f:
        line = line.strip()
        try:
            #print(line)
            print('-')
            level, d, message = line.split('\t', 2)
            print(d)
            d = arrow.get(d)
            print(d)
            d = d.datetime
            print(d)
            print(d - now)
            print(f'{level} : {d} : {message}')
        except BaseException as ex:
            print(ex)
            

