from lxml import etree as ET
from domino.core import log
from responses import Response as BaseResponse 
from discount.checks import Check
from discount.calculator import AccountDeptWorker
from domino.account import find_account, find_account_id

class Response(BaseResponse):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.check = Check()
        #if request.method == 'GET': 
        #    raise Exception('Недопустимый метод GET, требуется POST')
        self.xml_file = self.request.form.get('xml_file')
        self.xml = ET.fromstring(self.xml_file)
        self.check.load_from_xml(self.xml)
        self.account_id = find_account_id(self.check.account_id)
        self.dept_code = self.check.dept_code
        if self.account_id is None:                    
            raise Exception(f'Нет учетной записи "{self.account_id}"')

    def __call__(self):
        self.LOG.xml_file(self.xml_file)
        is_test = self.request.args.get('test', '0') == '1'
        if is_test:
            self.LOG.comment('Тест')
            worker = AccountDeptWorker(self.application, self.account_id, self.dept_code, self.LOG)
        else:
            worker = self.application['calculator']
         
        keywords = []
        worker.get_keywords(keywords, self.check, self.LOG, self.postgres)
  
        #check.time = round((datetime.datetime.now() - start).total_seconds() * 1000,3)
        xml = ET.fromstring('<KEYWORDS/>')
        xml.attrib['scheme'] = f'{self.check.scheme}'
        ET.SubElement(xml, 'status').text = 'success'
        for keyword in sorted(keywords):
            #log.debug(f'{keyword}')
            ET.SubElement(xml, 'KEYWORD').text = keyword.strip()
        response = ET.tostring(xml, encoding='utf-8').decode(encoding='UTF-8')
        self.LOG.response_type('xml')
        return response

