import sys, os, json, datetime, arrow
from lxml import etree as ET
from domino.core import log
from responses import Response as BaseResponse 
from discount.checks import Check
from discount.calculator import AccountDeptWorker
from domino.account import find_account, find_account_id
from flask import make_response

class Response(BaseResponse):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.postgres = None

    def __call__(self):
        ТЕСТ = self.get('test', '0') == '1'
        DATE = self.get('date')
        #log.debug(f'DATE={DATE}')
        if DATE:
            date = arrow.get(DATE).date()
        else:
            date = datetime.date.today()
        #log.debug(f'DATE={date}')
        if ТЕСТ:
            calculator = AccountDeptWorker(self.application, self.account_id, self.dept_code, self.LOG)
            prices = calculator.get_prices(self.dept_code, date, self.LOG, self.postgres)
        else:
            calculator = self.application['calculator']
            prices = calculator.get_prices(self.account_id, self.dept_code, date, self.LOG, self.postgres)
   
        xml = ET.fromstring('<PRICES/>')
        ET.SubElement(xml, 'status').text = 'success'
        for uid, price in prices.items():
            ET.SubElement(xml, 'product', attrib={'id':f'{uid}', 'price':f'{price}'})
        response = ET.tostring(xml, encoding='utf-8').decode("utf-8")
        #response = make_response(ET.tostring(xml, encoding='utf-8').decode('utf-8'))
        #response = make_response(ET.tostring(xml, encoding='utf-8').decode('utf-8'))
        #response.headers['Content-Type'] = 'application/xml; charset=utf-8'
        self.LOG.response_type('xml')
        return response
