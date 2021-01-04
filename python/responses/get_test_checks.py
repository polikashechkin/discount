import sys, os, json, datetime, arrow
from domino.core import log
from . import Response as BaseResponse 
from discount.checks import Check
from discount.pos import PosCheck

class Response(BaseResponse):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.sqlite = None

    def __call__(self):
        checks = []
        cur = self.sqlite.execute('select ID from TEST_CHECKS order by ID desc')
        for ID, in cur:
            try:
                check = PosCheck.load(self.account_id, ID)
                checks.append([ID, check.name])
            except:
                continue
        return json.dumps(checks, ensure_ascii=False)
