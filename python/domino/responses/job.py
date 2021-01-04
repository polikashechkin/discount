import flask
from domino.core import log, DOMINO_ROOT
from domino.responses import Response as BaseResponse

class Response(BaseResponse):
    def __init__(self, application, request):
        super().__init__(application, request)

    def download_file(self):
        job_id = self.get('job_id')
        file_name = self.get('file_name')
        file = os.path.join(DOMINO_ROOT, 'jobs', job_id, file_name)
        #log.debug(f'download_job_file : {file} : {os.path.getsize(file)} : {file_name}')
        with open(file, 'rb') as f:
            response  = flask.make_response(f.read())
        response.headers['Content-Type'] = 'application/octet-stream'
        response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = f'attachment; filename={file_name}'
        response.headers['Content-Length'] = os.path.getsize(file)
        return response
