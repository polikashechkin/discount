import io, html
import xml.etree.cElementTree as ET
from flask import make_response
from domino.core import log
from responses import Response as BaseResponse 
from domino.tables.postgres.report import Report
from domino.tables.postgres.report_line import ReportLine

class Response(BaseResponse):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.report_id = self.get('report_id')
        self.postgres = None
        
    def download_xml(self):
        self.report = self.postgres.query(Report).get(self.report_id)
        #xcards = ET.fromstring('<cards/>')   
        #xcards.attrib['type'] = f'{report.info.get("card_type_id")}'
        #xcards.attrib['type_name'] = f'{report.info.get("card_type_name")}'
        #xcards.attrib['create'] = f'{report.ctime}'

        #for report_line in self.postgres.query(ReportLine)\
        #        .filter(ReportLine.report_id == self.report_id)\
        #        .order_by(ReportLine.id):
            #log.debug(f'info={info}')
        #    xcard = ET.SubElement(xcards, 'card')
        #    for key, value in report_line.info.items():
        #        xcard.attrib[key] = f'{value}'

        #out  = ET.tostring(xcards, encoding='utf-8').decode('utf-8')
        out = self._get_xml_text()
        response  = make_response(out)
        response.headers['Content-Type'] = 'application/xml'
        #response.headers['Content-Type'] = 'text/xml'
        #response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = f'attachment; filename={self.report.id}.xml'
        response.headers['Content-Length'] = len(out)
        return response

    def download_txt(self):
        self.report = self.postgres.query(Report).get(self.report_id)
        delimiter = self.get('delimiter', '\t')
        if delimiter == ',':
            return self._download_quote('txt')
        else:
            return self._download_tabs('txt')

    def download_csv(self):
        self.report = self.postgres.query(Report).get(self.report_id)
        delimiter = self.get('delimiter', '\t')
        if delimiter == ',':
            return self._download_quote('csv')
        else:
            return self._download_tabs('csv')
    
    def _download_tabs(self, ext):
        csv = io.StringIO()
        for report_line in self.postgres.query(ReportLine)\
                .filter(ReportLine.report_id == self.report_id)\
                .order_by(ReportLine.id):
            values = report_line.info.values()
            line = "\t".join(values)
            csv.write(f'{line}\n')
        out  = csv.getvalue()
        out = out.encode('utf-8')

        response  = make_response(out)
        response.headers['Content-Type'] = 'application/octet-stream'
        #response.headers['Content-Type'] = 'text'
        #response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = f'attachment; filename={self.report.id}.{ext}'
        response.headers['Content-Length'] = len(out)
        return response
    
    def _download_quote(self, ext):
        csv = io.StringIO()
        for report_line in self.postgres.query(ReportLine)\
                .filter(ReportLine.report_id == self.report_id)\
                .order_by(ReportLine.id):
            first_value = True
            for value in report_line.info.values():
                value = value.replace('"', "'")
                if first_value:
                    csv.write(f'"{value}"')
                    first_value = False
                else:
                    csv.write(',')
                    csv.write(f'"{value}"')
            csv.write('\n')

        out  = csv.getvalue()
        out = out.encode('utf-8')

        response  = make_response(out)
        #response.headers['Content-Type'] = 'application/octet-stream'
        response.headers['Content-Type'] = 'text/plain; charset=uft-8'
        #response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = f'attachment; filename={self.report.id}.{ext}'
        response.headers['Content-Length'] = len(out)
        return response

    def show_html(self):
        report = self.postgres.query(Report).get(self.report_id)
        h = io.StringIO()
        h.write('<html>\n')
        h.write('<head>\n')
        h.write('<style>\n')
        h.write('table, td, th { border: 1px solid lightgray; border-collapse: collapse}\n')
        h.write('td, th { border: 1px solid lightgray; padding: 5px; text-align: left;}\n')
        h.write('</style>\n')
        h.write('</head>\n')
        h.write('<body>\n')
        h.write('<table>\n')
        #xcards = ET.fromstring('<cards/>')   
        #xcards.attrib['type'] = f'{report.info.get("card_type_id")}'
        #xcards.attrib['type_name'] = f'{report.info.get("card_type_name")}'
        #xcards.attrib['create'] = f'{report.ctime}'

        for info, in self.postgres.query(ReportLine.info)\
                .filter(ReportLine.report_id == self.report_id)\
                .order_by(ReportLine.id):
            h.write('<tr>')
            #xcard = ET.SubElement(xcards, 'card')
            for key, value in info.items():
                #xcard.attrib[key] = f'{value}'
                h.write(f'<td>{html.escape(value)}</td>')
            h.write('</tr>\n')

        h.write('</table>')
        h.write('</body></html>')
        #out  = ET.tostring(xcards, encoding='utf-8').decode('utf-8')
        response  = make_response(h.getvalue())
        #response.headers['Content-Type'] = 'text/html'
        #response.headers['Content-Type'] = 'text/html'
        #response.headers['Content-Type'] = 'application/xml'
        #response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = f'inline'
        #response.headers['Content-Disposition'] = f'attachment; filename={report.id}.xml'
        #response.headers['Content-Length'] = len(out)
        return response

    def _get_xml_text(self):
        xcards = ET.fromstring('<cards/>')   
        xcards.attrib['type'] = f'{self.report.info.get("card_type_id")}'
        xcards.attrib['type_name'] = f'{self.report.info.get("card_type_name")}'
        xcards.attrib['create'] = f'{self.report.ctime}'

        for info, in self.postgres.query(ReportLine.info)\
                .filter(ReportLine.report_id == self.report_id)\
                .order_by(ReportLine.id):
            xcard = ET.SubElement(xcards, 'card')
            for key, value in info.items():
                xcard.attrib[key] = f'{value}'

        #return ET.tostring(xcards, encoding='utf-8').decode('utf-8')
        return ET.tostring(xcards)

    def show_xml(self):
        self.report = self.postgres.query(Report).get(self.report_id)
        
        #xcards = ET.fromstring('<cards/>')   
        #xcards.attrib['type'] = f'{report.info.get("card_type_id")}'
        #xcards.attrib['type_name'] = f'{report.info.get("card_type_name")}'
        #xcards.attrib['create'] = f'{report.ctime}'

        #for info, in self.postgres.query(ReportLine.info)\
        #        .filter(ReportLine.report_id == self.report_id)\
        #        .order_by(ReportLine.id):
        #    xcard = ET.SubElement(xcards, 'card')
        #    for key, value in info.items():
        #        xcard.attrib[key] = f'{value}'

        #out  = ET.tostring(xcards, encoding='utf-8').decode('utf-8')
        
        out  = self._get_xml_text()

        response  = make_response(out)
        #response.headers['Content-Type'] = 'text/xml'
        response.headers['Content-Type'] = 'application/xml'
        #response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = f'inline'
        #response.headers['Content-Disposition'] = f'attachment; filename={report.id}.xml'
        #response.headers['Content-Length'] = len(out)
        return response
