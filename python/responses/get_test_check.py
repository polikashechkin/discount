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
        id = self.get('id')
        check = PosCheck.load(self.account_id, id)
        return json.dumps(check.to_js())
