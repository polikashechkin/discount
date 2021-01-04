from . import log
from domino.tables.postgres.report import Report
from domino.tables.postgres.report_line import ReportLine

from . import Page as BasePage
from . import Title, Button, Table, Toolbar, TextWithComments
from . import IconButton, DeleteIconButton

class Page(BasePage):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.postgres = None

    def delete(self):
        report_id = self.get('report_id')
        self.postgres.query(Report).filter(Report.id == report_id).delete()
        self.postgres.query(ReportLine).filter(ReportLine.report_id == report_id).delete()
        self.Row('table', report_id)

    def print_row(self, row, report):
        cell = row.cell(width=2)
        if not report.state:
            cell.glif('spinner', css='fa-pulse')
        row.cell().text(report.id)
        comments = [f'Дата создания "{report.ctime}"']
        comments.append(f'Строк {report.lines}')
 
        TextWithComments(row.cell(), report.name, comments)
        cell = row.cell(width=20, align='right')
        toolbar = Toolbar(cell, None)
        button = Button(toolbar.item(ml='auto', mr=1), 'Посмотреть')
        button.item('В формате HTML').onclick('report.show_html', {'account_id':self.account_id, 'report_id':report.id}, target='NEW_WINDOW')
        button.item('В формате XML').onclick('report.show_xml', {'account_id':self.account_id, 'report_id':report.id}, target='NEW_WINDOW')
        button = Button(toolbar.item(), 'Выгрузить')
        button.item('В формате XML').onclick('report.download_xml', {'account_id':self.account_id, 'report_id':report.id}, target='DOWNLOAD')
        button.item('В формате CSV (разделитель табуляция)').onclick('report.download_csv', {'account_id':self.account_id, 'report_id':report.id}, target='DOWNLOAD')
        button.item('В формате CSV (разделитель запятая)').onclick('report.download_csv', {'account_id':self.account_id, 'report_id':report.id, 'delimiter':','}, target='DOWNLOAD')
        button.item('В формате TXT (разделитель табуляция)').onclick('report.download_txt', {'account_id':self.account_id, 'report_id':report.id}, target='DOWNLOAD')
        button.item('В формате TXT (разделитель запятая)').onclick('report.download_txt', {'account_id':self.account_id, 'report_id':report.id, 'delimiter':','}, target='DOWNLOAD')
        DeleteIconButton(toolbar.item()).onclick('.delete', {'report_id':report.id})

    def print_table(self, ):
        table = Table(self, 'table')
        for report in self.postgres.query(Report).order_by(Report.ctime.desc()).limit(200):
            row = table.row(report.id)
            self.print_row(row, report)

    def __call__(self):
        Title(self, f'Справки')
        self.print_table()



