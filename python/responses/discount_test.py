import flask, os
from domino.core import log, DOMINO_ROOT
from . import Response as BaseResponse

class Response(BaseResponse):
    def __init__(self, application, request):
        super().__init__(application, request)

    def __call__(self):
        discount_test_py = os.path.join(DOMINO_ROOT, 'products', 'discount', 'active', 'python', 'discount_test', 'discount_test.py')
        #file = os.path.join(DOMINO_ROOT, 'jobs', job_id, file_name)
        #log.debug(f'download_job_file : {file} : {os.path.getsize(file)} : {file_name}')
        with open(discount_test_py, 'rb') as f:
            response  = flask.make_response(f.read())
        response.headers['Content-Type'] = 'application/octet-stream'
        response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = f'attachment; filename=discount_test.py'
        response.headers['Content-Length'] = os.path.getsize(discount_test_py)
        return response
