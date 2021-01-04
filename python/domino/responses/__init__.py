import redis, json, time
from domino.core import log
from flask import make_response

class Response:
    class RequestLog:
        def __init__(self, response, start):
            self.start = start
            self.response = response

        def __call__(self, msg, start = None):
            self.message(msg, start)

        def message(self, msg, start=None):
            request_log = getattr(self.response, 'request_log', None)
            if request_log is None:
                return
            info = request_log.info
            if info is None:
                info = {}
            protocol = info.get('protocol')
            if protocol is None:
                protocol = []
                info['protocol'] = protocol
            if start:
                protocol.append([f'{msg}', time.perf_counter() - start])
            else:
                protocol.append(f'{msg}')
            request_log.info = info
            #log.debug(f'{request_log.info}')

        def error(self, msg, start=None):
            self.message(f'error:{msg}', start)

        def header(self, msg, start=None):
            self.message(f'header:{msg}', start)

        def xml_file(self, xml_file):
            request_log = getattr(self.response, 'request_log', None)
            if request_log:
                request_log.xml_file = xml_file

        def response_type(self, type_):
            request_log = getattr(self.response, 'request_log', None)
            if request_log:
                request_log.response_type = type_

        def comment(self, comment):
            request_log = getattr(self.response, 'request_log', None)
            if request_log:
                if request_log.comment:
                    request_log.comment = request_log.comment + ' ' + comment
                else:
                    request_log.comment = comment
        def end(self):
            request_log = getattr(self.response, 'request_log', None)
            if request_log:
                request_log.duration = time.perf_counter() - self.start
        
        def is_test(self, value):
            request_log = getattr(self.response, 'request_log', None)
            if request_log:
                request_log.is_test = bool(value)

    def __init__(self, application, request):
        start = time.perf_counter()
        self.application = application
        self.request = request

        # SK
        self.sk = self.get('sk')
        if self.sk:
            r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
            self.sk_data = r.hgetall(self.sk)
        else:
            self.sk_data = None
        
        # ACCOUNT_ID
        self.account_id = self.get('account_id')
        if not self.account_id:
            self.account_id = self.get('account')
        if not self.account_id and self.sk_data:
            self.account_id = self.sk_data.get('account')

        # DEPT_ID
        self.dept_code = self.get('dept')
        if not self.dept_code:
            self.dept_code = self.get('dept_code')
        if not self.dept_code and self.sk_data:
            self.dept_code = self.sk_data.get('guid')

        self.LOG = Response.RequestLog(self, start)

    def __repr(self):
        return f'<Response({self.request.url})>'
        
    def get(self, name, default=None):
        return self.request.args.get(name, default)

    def get_int(self, name, default=None):
        try:
            return int(self.request.args.get(name))
        except:
            return default

    def success(self, message = None):
        r = {'status' : 'success'}
        if message:
            r['message'] = message
        return r

    def error(self, message = None):
        r = {'status' : 'error'}
        if message:
            r['message'] = message
        self.LOG(f'ERROR : {message}')
        return r
       
    def __call__(self):
        return '__call__', 500

    def make_response(self, fn = None):
        if fn:
            f = getattr(self, fn)
            if f is None:
                return f'{fn}', 500
            response = f()
        else:
            response = self.__call__()
        if isinstance(response, (dict)):
            response = json.dumps(response, ensure_ascii=False)
        self.LOG.end()
        return response

    def download(self, buf, file_name):
        response  = make_response(buf)
        response.headers['Content-Type'] = 'application/octet-stream'
        #response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = 'attachment; filename={0}'.format(file_name)
        response.headers['Content-Length'] = len(buf)
        return response
