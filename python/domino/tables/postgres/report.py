import datetime, io
import xml.etree.cElementTree as ET
import xlsxwriter

from domino.core import log
from sqlalchemy import Column, String, BigInteger, DateTime, insert, Integer, SmallInteger
from sqlalchemy.dialects.postgresql import JSONB
from domino.databases.postgres import Postgres
from .report_line import ReportLine, ReportLineTable

class Report(Postgres.Base):

    DONE = 1

    __tablename__ = 'report'

    id              = Column(BigInteger, primary_key=True, autoincrement = True, nullable =False)
    class_          = Column('class', String, nullable=False)
    type_           = Column('type', String, nullable=False)
    state           = Column(SmallInteger)
    ctime           = Column(DateTime, nullable=False, default = datetime.datetime.now)
    name            = Column(String)
    lines           = Column(Integer)
    description     = Column(JSONB)
    info            = Column(JSONB)
    rows            = Column(JSONB)
    rows_size       = Column(BigInteger)
    module_id       = Column(String)

    def __init__(self, class_, type_, **kvargs):
        super().__init__(**kvargs)
        self.class_ = class_
        self.type_ =  type_

    def row(self, values):
        if self.rows is None:
            self.rows = []
        self.rows.append(values)
    
    @property
    def columns(self):
        try:
            return self.info['columns']
        except:
            return []

    def column(self, name, description = None):
        if self.info is None:
            self.info = {}
        columns = self.info.get('columns')
        if columns is None:
            columns = []
            self.info['columns'] = columns
        column = {'name' : name}
        if description:
            column['description'] = description
        columns.append(column)
    
    @property
    def file_name(self):
        try:
            return self.info.get('file_name', f'{self.id}')
        except:
            return f'{self.id}'
    @file_name.setter
    def file_name(self, value):
        if self.info is None:
            self.info = {}
        self.info['file_name'] = value

    def line(self, postgres, info):
        values = {
            ReportLineTable.c.report_id : self.id,
            ReportLineTable.c.info : info
        }
        postgres.execute(insert(ReportLineTable).values(values))

    def csv(self, delimiter=None):
        if self.rows is None:
            return ''
        csv = io.StringIO()
        if delimiter:
            for row in self.rows:
                first_value = True
                for value in row:
                    value = F'{value}'.replace('"', "'")
                    if first_value:
                        csv.write(f'"{value}"')
                        first_value = False
                    else:
                        csv.write(delimiter)
                        csv.write(f'"{value}"')
                csv.write('\n')
        else:
            for row in self.rows:
                line = "\t".join([f'{v}' for v in row])
                csv.write(f'{line}\n')
        out  = csv.getvalue()
        return out.encode('utf-8')

    def xml(self):
        xreport = ET.fromstring('<report/>')   
        if self.rows is not None:
            columns = self.columns
            for row in self.rows:
                xrow = ET.SubElement(xreport, 'row')
                i = 0
                for value in row:
                    column = columns[i]
                    i += 1
                    xrow.attrib[column['name']] = f'{value}'
        return ET.tostring(xreport)

    def xlsx(self, title = False):
        buf = io.BytesIO()
        workbook = xlsxwriter.Workbook(buf, {'in_memory':True})
        worksheet = workbook.add_worksheet()
        worksheet.set_column('A:A', 20)
        if self.rows is not None:
            i = 0
            if title:
                bold = workbook.add_format({'bold': True})
                j = 0
                for column in self.columns:
                    worksheet.write(i,j, column['name'], bold)
                    j += 1
                i += 1
            for row in self.rows:
                j = 0
                for value in row:
                    worksheet.write(i,j, f'{value}')
                    j += 1
            i += 1
        workbook.close()
        return buf.getvalue()

    def __repr__(self):
        return f'<Report(id={self.id}, name={self.name}, info={self.info})>'

ReportTable = Report.__table__

Postgres.Table(ReportTable)


