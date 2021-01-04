import os, sys, datetime, requests, pickle, json, uuid, arrow
import xml.etree.ElementTree as ET
from multiprocessing import Process, Queue
from time import sleep

#DIR = os.path.dirname(os.path.abspath(__file__))
DIR = '/DOMINO/data/test/discount/'
os.makedirs(DIR, exist_ok=True)
VALUES_FILE = os.path.join(DIR, 'calc_emi.def')
VALUES = {}
os.makedirs(os.path.dirname(VALUES_FILE), exist_ok=True)
try:
    with open(os.path.join(VALUES_FILE)) as f:
        VALUES = json.load(f)
except:
    pass

def question(q):
    old_value = VALUES.get(q, '')
    new_value = input(f'{q} [{old_value}] ? ')
    if new_value != '':
        VALUES[q] = new_value
        with open(VALUES_FILE, 'w') as f:
            json.dump(VALUES, f)
        return new_value
    else:
        return old_value

def print_check(check):
    print()
    text = ET.tostring(check).decode('UTF-8')
    print(text)
    print()

def calc_request(server, check):
    xml_file = ET.tostring(check, encoding='UTF-8')
    q = f'https://{server}/discount/active/python/calc'
    print(q)
    start = datetime.datetime.now()
    r = requests.post(f'https://{server}/discount/active/python/calc', data={'xml_file': xml_file})
    time_ms = round((datetime.datetime.now() - start).total_seconds() * 1000, 2)
    print(f'{time_ms} : {r.status_code}')
    return ET.fromstring(r.text)

def accept_request(server, check):
    q = f'https://{server}/discount/active/python/accept'
    xml_file = ET.tostring(check, encoding='UTF-8')
    print(f'{q}')
    #print(xml_file)
    start = datetime.datetime.now()
    r = requests.post(f'https://{server}/discount/active/python/accept', data={'xml_file': xml_file})
    time_ms = round((datetime.datetime.now() - start).total_seconds() * 1000, 2)
    print(f'{time_ms} {r.status_code}')
    #print(r.text)
    return ET.fromstring(r.text)

def pos_processing(server, check):
    calc_check = calc_request(server, check)
    #print_check(calc_check)
    changed_lines = {}
    xlines = calc_check.find('LINES')
    for xline in xlines.findall('LINE'):
        line_info = {}
        line_info['FINAL_PRICE'] = xline.attrib['FINAL_PRICE']
        line_info['CALC_INFO'] = xline.attrib['CALC_INFO']
        changed_lines[xline.attrib['LINE_ID']] = line_info
    print(f'{changed_lines}')

    xlines = check.find('LINES')
    for xline in xlines.findall('LINE'):
        line_id = xline.attrib['LINE_ID']
        print(line_id)
        line_info = changed_lines.get(line_id)
        if line_info is not None:
            xline.attrib['FINAL_PRICE'] = line_info['FINAL_PRICE']
            xline.attrib['CALC_INFO'] = line_info['CALC_INFO']
        else:
            xline.attrib['FINAL_PRICE'] = xline.attrib['PRICE']

    print_check(check)
    status = accept_request(server, check)
    print_check(status)

if __name__ == "__main__":
    
    server = question('Сервер')
    #account_id = question('Учетная запись')
    check_date = question('Дата чека')
    if check_date == '.':
        check_date = datetime.datetime.now()
    else:
        check_date = arrow.get(check_date).datetime
    print (f'{check_date:%Y-%m-%d %H:%M:%S}')
    filename = question('Имя файла чека')
    file = os.path.join(DIR,'calc', filename + '.xml')
    xml_file = open(file).read()
    xml_file = xml_file.format(GUID=uuid.uuid4(), DATE=check_date.strftime('%Y-%m-%d %H:%M:%S'))
    #xml_file = xml_file.replace('{DATE}', f'{check_date:%Y-%m-%d %H:%M:%S}')
    #xml_file = xml_file.replace('{GUID}', f'{check_date:%Y-%m-%d %H:%M:%S}')
    check = ET.fromstring(xml_file)
    
    pos_processing(server, check)
