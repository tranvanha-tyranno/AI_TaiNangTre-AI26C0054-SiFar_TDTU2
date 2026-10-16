import json
import unittest
from pathlib import Path
from unittest.mock import patch
from src.llmv4 import infer_contract, prompt, regions_v4, normalize_review
from src.llmv4_reasoning import question_spec, metadata, retrieve_structured, check_plan, execution_audit
from src.workbook_index import Region
from src.tools.executor import execute, PlanError
from src.pipeline import answer_with_tools
from src.variants import settings_for_mode


class ReasoningTest(unittest.TestCase):
    def region(self, ident='t1', sheet='Sales', title='Revenue (tỷ đồng)'):
        return Region(ident,sheet,1,5,1,2,{(1,1):title,(1,2):title,(2,1):'Product',(2,2):'Revenue',
            (3,1):'A',(3,2):2,(4,1):'B',(4,2):3,(5,1):'C',(5,2):5},[],['A1:B1'],[1,2])

    def plan(self, end=5):
        return {'steps':[{'id':'r','op':'read','table':'t1','start_row':3,'end_row':end},
                         {'id':'s','op':'aggregate','input':'r','metric':'sum','expr':{'col':'B'}}],
                'output':{'step':'s'},'answer_spec':{'answer_type':'number','answer_field':'Revenue','operation':'sum'}}

    def test_prompt_replaces_conflicting_contract_in_same_call(self):
        q='Xác định năm có tổng số dưới 10. Chỉ trả lời năm.'
        c=infer_contract(q)
        request=[{'role':'user','content':json.dumps({'question':q,'answer_contract':{'reduction':'sum'}})}]
        prepared=prompt(request,c)
        data=json.loads(prepared[1]['content'])
        self.assertIsNone(data['answer_contract']['reduction'])
        self.assertEqual(data['question_spec']['output'],data['answer_contract'])
        self.assertEqual(json.loads(request[0]['content'])['answer_contract'],{'reduction':'sum'})

    def test_metadata_keeps_currency_source_and_separates_energy_power(self):
        r=regions_v4([self.region()])[0]
        facts=metadata(r)['unit_candidates']
        self.assertTrue(any(f['scale']==1000000000 and f['source']=='Sales!A1' for f in facts))
        spec=question_spec('Năm 2032, trả lời bằng triệu đồng.',{})
        self.assertEqual(spec['period_mentions'],['2032'])
        self.assertEqual(spec['unit_mentions'][0]['scale'],1000000)
        self.assertIn('structure',r.preview('Revenue'))

    def test_structured_retrieval_selects_quoted_header_not_noise(self):
        relevant=regions_v4([self.region(title='Operating Revenue')])[0]
        noise=regions_v4([self.region('t2','Archive','Historical Population')])[0]
        selected,catalog=retrieve_structured([noise,relevant],'What is "Operating Revenue"?',1)
        self.assertEqual(selected[0].id,'t1')
        self.assertIn('structure_score',catalog[0])

    def test_type_checker_rejects_row_as_scalar_before_execution(self):
        plan=self.plan();plan['steps'][1]={'id':'s','op':'calculate','expr':{'add':[{'ref':'r'},{'value':1}]}}
        with self.assertRaisesRegex(PlanError,'is rows'):
            check_plan(plan,[self.region()],{},'Revenue')

    def test_type_checker_rejects_forward_dependency(self):
        plan=self.plan();plan['steps'][1]['input']='future'
        with self.assertRaisesRegex(PlanError,'forward'):
            check_plan(plan,[self.region()],{},'Revenue')

    def test_calculate_can_attach_scalar_input_as_existing_executor_allows(self):
        plan={'steps':[{'id':'a','op':'cell','table':'t1','row':3,'column':'B'},
                       {'id':'b','op':'calculate','input':'a','expr':{'mul':[{'ref':'a'},{'value':2}]}}],
              'output':{'step':'b'}}
        checked=check_plan(plan,[self.region()],{},'Revenue')
        self.assertEqual(checked['output_kind'],'scalar')
        self.assertEqual(execute(plan,[self.region()])['answer'],'4')

    def test_partial_scope_is_a_warning_not_a_false_gate(self):
        plan=self.plan(4)
        audit=check_plan(plan,[self.region()],{},'Sum all rows in triệu đồng.')
        codes={w['code'] for w in audit['scope']['warnings']}
        self.assertEqual(codes,{'possibly_incomplete_scope','currency_conversion_required'})
        self.assertEqual(audit['scope']['semantic_completeness'],'unconfirmed')
        self.assertEqual(execute(plan,[self.region()])['answer'],'5')

    def test_count_boolean_gets_specific_warning_without_guessing_fix(self):
        plan=self.plan();plan['steps'][1].update(metric='count',expr={'gt':[{'col':'B'},{'value':2}]})
        audit=check_plan(plan,[self.region()],{},'How many are above 2?')
        self.assertIn('count_boolean_expression',[w['code'] for w in audit['scope']['warnings']])

    def test_trace_records_input_output_cardinality(self):
        plan=self.plan();preflight=check_plan(plan,[self.region()],{},'Revenue')
        audit=execution_audit(plan,execute(plan,[self.region()]),preflight)
        self.assertEqual(audit['steps'][1]['input_rows'],3)
        self.assertEqual(audit['steps'][1]['scalar'],'10')

    def test_review_normalization_preserves_meaning_and_logs_verbosity(self):
        record={};issues=['Precise evidence '+str(i)+'x'*400 for i in range(7)]
        result=normalize_review({'verdict':'revise','issues':issues},record)
        self.assertEqual(result['verdict'],'revise')
        self.assertEqual(len(result['issues']),5)
        self.assertEqual(record['review_normalizations'][0]['original_issue_count'],7)
        self.assertIsNone(normalize_review({'verdict':'revise','issues':[]},record))
        malformed={'verdict':'perhaps','issues':[]}
        self.assertEqual(normalize_review(malformed,record),malformed)
        uncertain={'verdict':'accept','issues':[],'uncertainty':'Cannot verify the source'}
        self.assertEqual(normalize_review(uncertain,record),uncertain)

    def test_metamorphic_row_reordering_and_table_noise_preserve_computation(self):
        r=self.region();changed=self.region()
        for destination,source in [(3,5),(4,3),(5,4)]:
            for col in [1,2]:changed.cells[(destination,col)]=r.cells[(source,col)]
        noise=self.region('t9','Noise','Unrelated measurements')
        before=execute(self.plan(),[r])['answer']
        after=execute(self.plan(),[noise,changed])['answer']
        self.assertEqual(before,after)
        self.assertEqual(r.cells[(3,2)],2)

    def test_pipeline_sends_audit_to_existing_review_without_extra_calls(self):
        plan=self.plan();requests=[]
        class Client:
            prompt_cap=.001;completion_cap=.001
            def complete(self,messages,ledger,purpose):
                requests.append((purpose,messages))
                return json.dumps({'verdict':'accept','issues':[]} if purpose=='review' else plan)
        record={}
        with patch('src.pipeline.load_regions',return_value=[self.region()]):
            result=answer_with_tools(Path('unused'),'What is total Revenue?',Client(),record,settings_for_mode({},'llm-v4'))
        self.assertEqual(result,'10')
        self.assertEqual(len(requests),2)
        review_payload=next(json.loads(m['content']) for m in requests[1][1] if m['role']=='user')
        self.assertIn('execution_audit',review_payload)
        self.assertIn('question_spec',record)
        self.assertTrue(record['plan_checks'])


if __name__=='__main__':unittest.main()
