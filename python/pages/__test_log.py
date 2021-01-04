import datetime, os, arrow

from domino.core import log, DOMINO_ROOT
from discount.page import Page

from domino.page_controls import ТабличнаяФорма, FormControl
from discount.pos_log import PosCheckLog
from discount.pos import PosCheck

class TestLogPage(Page):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.check_id = self.attribute('check_id')
        self.check = PosCheck.load(self.account_id, self.check_id)
    
    def __call__(self):
        self.title(f'{self.check.name}')
        table = self.Table('table').css('shadow-sm table-borderless').mt(1)

        msg_log = PosCheckLog(self.account_id, self.check_id)
        for TYPE, MESSAGE in msg_log.select():
            row = table.row()
            if TYPE == PosCheckLog.HEADER:
                row.cell(style='font-weight:bold').text(MESSAGE)
            elif TYPE == PosCheckLog.ERROR:
                row.cell(style='font-weight:bold; color:red').text(MESSAGE)
            else:
                row.cell().text(MESSAGE)

