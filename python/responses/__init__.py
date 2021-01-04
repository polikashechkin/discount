#from flask import make_response
from domino.core import log
from domino.responses import Response

'''
class Response:
    def __init__(self, application, request):
        self.application = application
        self.request = request
        self.account_id = self.request.args.get('account_id')
    
    def __str__(self):
        return f'<Response()>'
    
    def get(self, name, default=None):
        return self.request.args.get(name, default)
        
    def get_int(self, name, default=None):
        try:
            return int(self.request.args.get(name, default))
        except:
            return 0
    
    def __call__(self):
        return 'no response found', 500

    def make_response(self, fn = None):
        log.debug(f'{self}.make_response({fn})')
        if fn:
            return getattr(self, fn)()
        else:
            return self.__call__()

    def download(self, buf, file_name):
        response  = make_response(buf)
        response.headers['Content-Type'] = 'application/octet-stream'
        #response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = 'attachment; filename={0}'.format(file_name)
        response.headers['Content-Length'] = len(buf)
        return response

'''