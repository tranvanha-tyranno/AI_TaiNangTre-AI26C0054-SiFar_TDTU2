"""Exercise the real CLI/SDK against a local fake OpenRouter, no paid API.

Also run unchanged inside the submission Docker image:
docker run --rm --entrypoint python --mount type=bind,source=<tests>,target=/checks,readonly IMAGE -m unittest discover -s /checks -p test_submission_contract.py -v
"""
import csv
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

import openpyxl

ROOT=Path('/app') if Path('/app/main.py').exists() else Path(__file__).resolve().parents[1]
MODEL='qwen/qwen3.7-flash'
EXPECTED='Hà Nội, "Đông"'


def prepare_input(inputs):
    inputs=Path(inputs);books=inputs/'xlsx_files';books.mkdir(parents=True,exist_ok=True)
    book=openpyxl.Workbook();sheet=book.active;sheet.title='Data'
    sheet.append(['Code','Message']);sheet.append(['X',EXPECTED]);book.save(books/'fresh.xlsx');book.close()
    queries=[{'id':10,'file_name':'fresh.xlsx','query':'Return the Message for X. Answer with only the text.'},
             {'id':2,'file_name':'fresh.xlsx','query':'unanswerable-probe'},
             {'id':1,'file_name':'fresh.xlsx','query':'Return the Message for X. Answer with only the text.'}]
    (inputs/'queries.json').write_text(json.dumps(queries),encoding='utf-8')


class SubmissionContractTest(unittest.TestCase):
    def test_six_official_arguments_unicode_blank_answer_and_exit_zero(self):
        received=[]

        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def send_json(self,status,data):
                raw=json.dumps(data,ensure_ascii=False).encode('utf-8')
                self.send_response(status);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def do_GET(self):
                if self.path=='/api/v1/models':
                    self.send_json(200,{'data':[{'id':MODEL,'supported_parameters':['seed'],
                        'pricing':{'prompt':'0.0000001','completion':'0.0000001'}}]})
                else:self.send_json(404,{'error':{'message':'unexpected GET'}})
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                received.append((self.path,self.headers.get('Authorization'),payload))
                if 'unanswerable-probe' in json.dumps(payload['messages']):
                    self.send_json(400,{'error':{'message':'synthetic unavailable response','type':'invalid_request_error'}})
                    return
                schema=payload['tools'][0]['function']['parameters']
                if 'verdict' in schema.get('properties',{}):
                    answer={'verdict':'accept','issues':[]}
                else:
                    answer={'steps':[{'id':'v','op':'cell','table':'t1','row':2,'column':'B'}],
                            'output':{'step':'v'},
                            'answer_spec':{'answer_type':'text','answer_field':'Message','operation':'lookup'}}
                self.send_json(200,{'id':'synthetic-local-response','object':'chat.completion','created':0,'model':MODEL,
                    'choices':[{'index':0,'finish_reason':'tool_calls','message':{'role':'assistant','content':None,
                        'tool_calls':[{'id':'local-tool','type':'function','function':{
                            'name':'execute_spreadsheet_plan','arguments':json.dumps(answer,ensure_ascii=False)}}]}}],
                    'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150,'cost':0,
                             'completion_tokens_details':{'reasoning_tokens':0}}})

        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix='submission-contract-') as temp:
                base=Path(temp);inputs=Path(os.environ.get('SUBMISSION_SMOKE_INPUT',base/'input'))
                if not os.environ.get('SUBMISSION_SMOKE_INPUT'): prepare_input(inputs)
                books=inputs/'xlsx_files';output=Path(os.environ.get('SUBMISSION_SMOKE_OUTPUT',base/'output'))
                before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs.rglob('*') if p.is_file()}
                cmd=[sys.executable,str(ROOT/'main.py'),
                     '--xlsx-dir',str(books),'--queries',str(inputs/'queries.json'),
                     '--output',str(output/'submission.csv'),'--openrouter-key','synthetic-test-key',
                     '--openrouter-model',MODEL,'--openrouter-base-url',f'http://127.0.0.1:{server.server_port}/api/v1',
                     '--config',str(ROOT/'config/config.yaml'),
                     '--concurrency','2']
                env=dict(os.environ,MODEL_NAME='invalid-inherited-model',OPENROUTER_API_KEY='invalid-inherited-key')
                result=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,
                                      encoding='utf-8',errors='replace',timeout=60)
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-3000:])
                with (output/'submission.csv').open(encoding='utf-8',newline='') as stream:
                    reader=csv.DictReader(stream);self.assertEqual(reader.fieldnames,['id','answer']);rows=list(reader)
                self.assertEqual(rows,[{'id':'1','answer':EXPECTED},{'id':'2','answer':''},{'id':'10','answer':EXPECTED}])
                self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs.rglob('*') if p.is_file()})
                self.assertEqual({p.relative_to(output).as_posix() for p in output.rglob('*')}, {'submission.csv'})
                # Same input/output layout without any path/config arguments.
                # In Docker cwd=/ maps defaults directly onto the bind mounts;
                # on the host cwd=temp maps them onto temp/input and temp/output.
                defaults_cmd=[sys.executable,str(ROOT/'main.py'),
                    '--openrouter-key','synthetic-test-key','--openrouter-model',MODEL,
                    '--openrouter-base-url',f'http://127.0.0.1:{server.server_port}/api/v1']
                defaults_cwd=Path('/') if os.environ.get('SUBMISSION_SMOKE_INPUT') else base
                default_result=subprocess.run(defaults_cmd,cwd=defaults_cwd,env=env,capture_output=True,text=True,
                    encoding='utf-8',errors='replace',timeout=60)
                self.assertEqual(default_result.returncode,0,(default_result.stdout+default_result.stderr)[-3000:])
                with (output/'submission.csv').open(encoding='utf-8',newline='') as stream:
                    self.assertEqual(list(csv.DictReader(stream)),rows)
                self.assertEqual({p.relative_to(output).as_posix() for p in output.rglob('*')}, {'submission.csv'})
                self.assertTrue(received)
                self.assertTrue(all(path=='/api/v1/chat/completions' and auth=='Bearer synthetic-test-key'
                                    and payload['model']==MODEL for path,auth,payload in received))
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':unittest.main()
