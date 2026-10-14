import json
from pathlib import Path
import tempfile
import unittest
from scripts.analyze_run import analyze,compare
from src.run_context import run_context
from src.pipeline import answer_with_tools
from unittest.mock import patch
from src.workbook_index import Region

ROOT=Path(__file__).resolve().parents[1]


class RunReportingTest(unittest.TestCase):
    def test_http_402_is_reported_separately_from_solver_regression(self):
        old={'run':'old','rows':[{'id':'a','query':'Q','expected':'right','match':True}]}
        new={'run':'new','rows':[{'id':'a','query':'Q','expected':'right','match':False,'api_failed':True}]}
        report=compare(old,new)
        self.assertEqual(report['api_failed'],['a'])
        self.assertEqual(report['regressed'],[])
    def test_numeric_response_to_yes_no_question_is_repaired(self):
        region=Region('t1','Values',1,3,1,2,
            {(1,1):'Year',(1,2):'Amount',(2,1):2023,(2,2):20,(3,1):2024,(3,2):15},[],[],[1])
        class Client:
            prompt_cap=1;completion_cap=4;calls=0
            def complete(self,messages,ledger,purpose):
                self.calls+=1
                steps=[{'id':'old','op':'cell','table':'t1','row':2,'column':'B'},
                       {'id':'new','op':'cell','table':'t1','row':3,'column':'B'}]
                if self.calls==1: output='new'
                else:
                    steps.append({'id':'comparison','op':'calculate','expr':{'gt':[{'ref':'new'},{'ref':'old'}]}})
                    output='comparison'
                return json.dumps({'steps':steps,'output':{'step':output}})
        record={};client=Client()
        with patch('src.pipeline.load_regions',return_value=[region]):
            answer=answer_with_tools(Path('unused'),'Is the 2024 amount greater? Answer only Yes or No.',client,record,{})
        self.assertEqual(answer,'No')
        self.assertEqual(client.calls,2)
        self.assertIn('requires Yes or No',record['validation_errors'][0])

    def test_report_does_not_call_fixed_reference_a_solver_improvement(self):
        old={'run':'old','rows':[
            {'id':'a','query':'Q','expected':'right','match':False},
            {'id':'b','query':'Q2','expected':'old wrong reference','match':False}]}
        new={'run':'new','rows':[
            {'id':'a','query':'Q','expected':'right','match':True},
            {'id':'b','query':'Q2','expected':'fixed reference','match':True}]}
        report=compare(old,new)
        self.assertEqual(report['improved'],['a'])
        self.assertEqual(report['comparable_questions'],1)

    def test_saved_report_keeps_mismatch_despite_validated_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'metadata.json').write_text(json.dumps({'catalog':[{'id':'x','query':'Q','file_name':'a.xlsx'}],
                                                      'reference':{'x':'35'},'finished':True}),encoding='utf-8')
            (p/'questions.jsonl').write_text(json.dumps({'id':'x','answer':'86','validated':True,'status':'ok'}),encoding='utf-8')
            report=analyze(p)
            self.assertEqual(report['matched'],0)
            self.assertTrue(report['mismatches'][0]['validated'])

    def test_context_whitelists_settings_and_fingerprints_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'src').mkdir()
            (p/'main.py').write_text('# main',encoding='utf-8')
            (p/'src/a.py').write_text('# a',encoding='utf-8')
            (p/'queries.json').write_text('[]',encoding='utf-8')
            (p/'a.xlsx').write_bytes(b'fixture')
            args=(p,p/'queries.json',p,[{'file_name':'a.xlsx'}],
                  {'max_tokens_plan':3000,'api_key':'must not be recorded'},'offline',1,'model')
            before=run_context(*args)
            self.assertNotIn('api_key',before['settings'])
            (p/'src/a.py').write_text('# changed',encoding='utf-8')
            after=run_context(*args)
            self.assertNotEqual(before['source_sha256'],after['source_sha256'])
            self.assertEqual(before['workbook_sha256'],after['workbook_sha256'])

    def test_incomplete_scope_repairs_and_logs_failed_plan_trace(self):
        class Client:
            prompt_cap=1;completion_cap=4
            calls=0
            def complete(self,messages,ledger,purpose):
                self.calls+=1
                if self.calls==1:
                    steps=[{'id':'a','op':'cell','table':'t1','row':9,'column':'B'},
                           {'id':'b','op':'cell','table':'t1','row':11,'column':'B'}]
                else:
                    correction=json.loads(messages[-1]['content'])
                    self.assert_error=correction['validation_error']
                    steps=[{'id':'a','op':'sum_columns','table':'t1','row':9,'columns':list('BCDEFGHIJKLM')},
                           {'id':'b','op':'sum_columns','table':'t1','row':11,'columns':list('BCDEFGHIJKLM')}]
                return json.dumps({'steps':steps+[{'id':'diff','op':'calculate','expr':{'sub':[{'ref':'b'},{'ref':'a'}]}}],
                                   'output':{'step':'diff'}})
        client=Client();record={}
        answer=answer_with_tools(ROOT/'Public_data_1/xlsx_files/p4_t05.xlsx',
            'Difference across all industries? Answer with only the integer.',client,record,{})
        self.assertEqual(answer,'9017')
        self.assertEqual(client.calls,2)
        self.assertIn('scope is incomplete',client.assert_error)
        self.assertIn('tool_trace',record['plans'][0])
        self.assertIn('validation_error',record['plans'][0])
        self.assertTrue(record['previews'])
        self.assertTrue(record['validated'])


if __name__=='__main__': unittest.main()
