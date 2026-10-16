import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from src.count_tool import compile_count, schema
from src.tools.executor import execute, PlanError
from src.workbook_index import Region
from src.variants import settings_for_mode, v3_version
from src.pipeline import answer_with_tools


class CountToolTest(unittest.TestCase):
    def region(self):
        rows=[('000321','8','2'),(123456,6,9),('+12345',7,2),('99999',9,1),
              ('abcdef',7,8),('123456.0',8,2),(None,'-',4),(123456.7,1,0)]
        cells={(1,1):'Code',(1,2):'Rate',(1,3):'Other'}
        for row,values in enumerate(rows,2):
            for col,value in enumerate(values,1):cells[(row,col)]=value
        return Region('t1','Dữ liệu',1,9,1,3,cells,[],[],[1])

    def request(self,conditions=None,**kwargs):
        return {'action':'count_rows','table':'t1','start_row':2,'end_row':9,'combine':'all',
                'missing':'exclude','conditions':conditions or [],**kwargs}

    def run_count(self,request,region=None):
        region=region or self.region()
        plan=compile_count(request,[region])
        return execute(plan,[region],reliability=True)

    def test_digits_are_not_text_length_and_preserve_leading_zero(self):
        request=self.request([{'column':'A','op':'digits','value':6},{'column':'B','op':'number_gt','value':5}])
        original=copy.deepcopy(request)
        result=self.run_count(request)
        self.assertEqual(result['answer'],'2')
        self.assertEqual(request,original)
        self.assertIn('Dữ liệu!A2',result['evidence_full'])
        self.assertEqual(result['trace'][-2]['row_count'],2)

    def test_column_comparison_and_numeric_text(self):
        result=self.run_count(self.request([{'column':'B','op':'number_gt','other_column':'C'}]))
        self.assertEqual(result['answer'],'5')

    def test_or_keeps_row_with_invalid_numeric_other_branch(self):
        r=self.region();r.cells[(8,1)]='keep'
        request=self.request([{'column':'B','op':'number_gt','value':100},
                              {'column':'A','op':'text_eq','value':'keep'}],combine='any')
        self.assertEqual(self.run_count(request,r)['answer'],'1')

    def test_missing_policy_is_explicit(self):
        conditions=[{'column':'B','op':'number_gt','value':5}]
        self.assertEqual(self.run_count(self.request(conditions))['answer'],'6')
        with self.assertRaises(PlanError):self.run_count(self.request(conditions,missing='error'))

    def test_zero_results_and_zero_values_are_valid(self):
        self.assertEqual(self.run_count(self.request([{'column':'B','op':'number_gt','value':100}]))['answer'],'0')
        self.assertEqual(self.run_count(self.request([{'column':'C','op':'number_eq','value':0}]))['answer'],'1')
        self.assertEqual(self.run_count(self.request())['answer'],'8')

    def test_invalid_parameters_do_not_get_guessed(self):
        requests=[self.request([{'column':'Z','op':'number_gt','value':5}]),
                  self.request([{'column':'B','op':'number_gt','value':5,'other_column':'C'}]),
                  self.request([{'column':'B','op':'number_gt','value':True}]),
                  self.request([{'column':'A','op':'digits','value':0}]),
                  self.request([{'column':'B','op':'number_gt','value':float('inf')}]),
                  self.request([{'column':'B','op':'is_number','value':5}]),
                  self.request(start_row=0),self.request(end_row=1000),self.request(start_row=True),
                  self.request(combine='any'),self.request(missing=[])]
        for request in requests:
            with self.subTest(request=request),self.assertRaises(PlanError):compile_count(request,[self.region()])

    def test_schema_keeps_standard_and_inspection_fallbacks(self):
        variants=schema()['anyOf']
        self.assertTrue(any('steps' in v.get('properties',{}) for v in variants))
        self.assertTrue(any('requests' in v.get('properties',{}) for v in variants))
        self.assertEqual(variants[0]['properties']['action']['enum'],['count_rows'])

    def test_reordered_rows_and_changed_column_positions(self):
        r=self.region();request=self.request([{'column':'A','op':'digits','value':6}])
        self.assertEqual(self.run_count(request,r)['answer'],'2')
        old=copy.deepcopy(r.cells)
        for destination,source in zip(range(2,10),range(9,1,-1)):
            r.cells[(destination,1)]=old[(source,2)];r.cells[(destination,2)]=old[(source,1)]
        request['conditions'][0]['column']='B'
        self.assertEqual(self.run_count(request,r)['answer'],'2')

    def test_pipeline_compiles_once_and_review_schema_is_reset(self):
        request=self.request([{'column':'A','op':'digits','value':6}]);calls=[]
        class Client:
            prompt_cap=.001;completion_cap=.001
            def complete(self,messages,ledger,purpose):
                calls.append((purpose,getattr(ledger,'response_schema',None)))
                return json.dumps({'verdict':'accept','issues':[]} if purpose=='review' else request)
        record={}
        with patch('src.pipeline.load_regions',return_value=[self.region()]):
            answer=answer_with_tools(Path('unused'),'How many records have a 6-digit code? Answer with only the integer.',
                Client(),record,settings_for_mode({'v3_reliability':True,'v3_count_tool':True},'llm-v3'))
        self.assertEqual(answer,'2')
        self.assertEqual([purpose for purpose,_ in calls],['plan','review'])
        self.assertIsNotNone(calls[0][1]);self.assertIsNone(calls[1][1])
        self.assertEqual(len(record['count_tool_requests']),1)
        self.assertEqual(record['pipeline_version'],'lmmv3-v2-count-tool-v1')

    def test_standard_count_plan_remains_a_valid_fallback(self):
        request=self.request([{'column':'B','op':'number_gt','value':100}])
        plan=compile_count(request,[self.region()])
        class Client:
            prompt_cap=.001;completion_cap=.001
            def complete(self,messages,ledger,purpose):
                return json.dumps({'verdict':'accept','issues':[]} if purpose=='review' else plan)
        record={}
        with patch('src.pipeline.load_regions',return_value=[self.region()]):
            answer=answer_with_tools(Path('unused'),'How many records have a Rate above 100? Answer with only the integer.',
                Client(),record,settings_for_mode({'v3_reliability':True,'v3_count_tool':True},'llm-v3'))
        self.assertEqual(answer,'0')
        self.assertTrue(record['count_tool_available'])
        self.assertNotIn('count_tool_requests',record)

    @patch('time.monotonic',return_value=100.0)
    def test_non_count_requests_are_identical_when_feature_enabled(self,_clock):
        r=self.region();r.cells[(2,2)]=8
        plan={'steps':[{'id':'s','op':'cell','table':'t1','row':2,'column':'B'}],
              'output':{'step':'s'},'answer_spec':{'answer_type':'number','answer_field':'Rate','operation':'lookup'}}
        class Client:
            prompt_cap=.001;completion_cap=.001
            def __init__(self):self.calls=[]
            def complete(self,messages,ledger,purpose):
                self.calls.append((messages,getattr(ledger,'response_schema',None)))
                return json.dumps({'verdict':'accept','issues':[]} if purpose=='review' else plan)
        clients=[]
        for enabled in [False,True]:
            client=Client();clients.append(client)
            with patch('src.pipeline.load_regions',return_value=[r]):
                self.assertEqual(answer_with_tools(Path('unused'),'What is the Rate in the first record? Answer with only the number.',
                    client,{},settings_for_mode({'v3_reliability':True,'v3_count_tool':enabled},'llm-v3')),'8')
        self.assertEqual(clients[0].calls,clients[1].calls)
        self.assertNotIn('v3_count_tool',settings_for_mode({'v3_count_tool':True},'llm-v2'))
        self.assertEqual(v3_version({'v3_reliability':True,'v3_count_tool':False}),'lmmv3-v2-reliability-v2')


if __name__=='__main__':unittest.main()
