import base64
import logging
import requests
from logging.handlers import HTTPHandler

class OpenObserveHTTPHandler(HTTPHandler):
    def __init__(self, host, url, username, password, method='POST', level=logging.NOTSET):
        super().__init__(host, url, method)
        self.level = level
        self.auth = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8')

    def emit(self, record):
        try:
            log_entry = self.format(record)
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + self.auth
            }
            job_name = getattr(record, 'custom_job_name', record.funcName)
            json_log = [{"level": record.levelname.lower(), "job": job_name, "log": log_entry}]
            response = requests.post(f'https://{self.host}{self.url}', headers=headers, json=json_log)
            if response.status_code != 200:
                print(f'Failed to send log to OpenObserve: {response.status_code} {response.content}')
        except Exception as e:
            print(f'Exception occurred while sending log: {e}')
