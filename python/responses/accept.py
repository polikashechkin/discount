import os, sys, json, datetime
from lxml import etree as ET
from domino.core import log, DOMINO_ROOT
from responses import Response as BaseResponse 
from discount.checks import Check
from discount.calculator import AccountDeptWorker
from domino.account import find_account, find_account_id
from domino.application import Status

class Response(BaseResponse):
    def __init__(self, application, request):
        super().__init__(application, request)
        if request.method == 'GET': 
            raise Exception('Недопустимый метод GET, требуется POST')
        self.check = Check(CLASS = 1)
        self.xml_file = self.request.form.get('xml_file')
        self.xml = ET.fromstring(self.xml_file)
        self.check.load_for_accept(self.xml_file)
        self.account_id = self.check.account_id
        self.dept_code = self.check.dept_code
        if self.account_id is None:                    
            raise Exception(f'Нет учетной записи "{self.account_id}"')

    def _write_log(self, check):
        folder = os.path.join(DOMINO_ROOT, 'accounts', self.account_id, 'data', 'discount', 'calc', f'{check.date.year:04}', f'{check.date.month:02}', f'{check.date.day:02}', f'{check.dept_code}')
        os.makedirs(folder, exist_ok=True)
        file = os.path.join(folder, f'{check.ID}.accept.log')
        with open(file, 'w') as f:
            json.dump(check.log, f, ensure_ascii=False)
        #self.LOG(f'write {file} {check.log}')
        with open(os.path.join(folder, f'{check.ID}.accept.stop'), 'w') as f:
            f.write(f'{check.start},{datetime.datetime.now()}')

    def __call__(self):
        self.LOG.xml_file(self.xml_file)
        #self.LOG.comment(f'{self.check.ID}')
        IS_TEST = self.request.args.get('test', '0') == '1'
        if IS_TEST:
            self.LOG.is_test(True)
            self.LOG.comment(f'{self.check.pos_id}/{self.check.session_id}/{self.check.check_no}')
            worker = AccountDeptWorker(self.application, self.account_id, self.check.dept_code, self.LOG)
        else:
            worker = self.application['calculator']
        worker.accept(self.check, self.LOG, self.postgres)
        self._write_log(self.check)
        response = Status.success().xml()
        self.LOG.response_type('xml')
        self.LOG.end()
        return response

