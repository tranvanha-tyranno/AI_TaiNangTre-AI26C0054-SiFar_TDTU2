import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from src.pipeline import answer_with_tools
from src.variants import settings_for_mode
from src.reliability import normalize, validate_section_identity, review_request
from src.tools.executor import execute, PlanError
from src.workbook_index import Region


class OutputReliabilityTest(unittest.TestCase):
    def region(self):
        return Region('t1','Data',1,7,1,2,
            {(1,1):'Class',(1,2):'Rate',(2,1):'Team X',
             (3,1):'tier',(3,2):4,(4,1):'other',(4,2):2,
             (5,1):'Team Y',(6,1):'tier',(6,2):9,(7,1):'other',(7,2):3},[],[],[1])

    def plan(self):
        return {'steps':[{'id':'r','op':'read','table':'t1','start_row':3},
                        {'id':'f','op':'filter','input':'r','where':{'eq':[{'col':'A'},{'value':'tier'}]}},
                        {'id':'s','op':'sort','input':'f','by':[{'column':'B','descending':True}]},
                        {'id':'t','op':'take','input':'s','limit':1}],
                'output':{'step':'t','columns':['A']},'answer_spec':{'answer_type':'label','operation':'argmax','answer_field':'group'}}

    def test_wrong_repeated_category_is_detected_correct_section_is_allowed(self):
        p=self.plan();r=self.region();contract={'answer_type':'label','answer_field':'group'}
        with self.assertRaisesRegex(PlanError,'repeated under 2 different sections'):
            validate_section_identity(contract,p,execute(p,[r]),[r])
        p['output']['columns']=['_section']
        result=execute(p,[r]);validate_section_identity(contract,p,result,[r])
        self.assertEqual(result['answer'],'Team Y')

    def test_explicit_column_identity_and_single_section_not_rejected(self):
        contract={'answer_type':'label','answer_field':'group'}
        p=self.plan();r=self.region();r.cells[(1,1)]='Group'
        validate_section_identity(contract,p,execute(p,[r]),[r])
        r=self.region();p['steps'][0]['end_row']=4
        validate_section_identity(contract,p,execute(p,[r]),[r])

    def test_count_completion_needs_question_and_plan_agreement(self):
        p=self.plan();p['steps']=p['steps'][:2];p['output']={'step':'f','columns':[]}
        p['answer_spec']['operation']='count';before=copy.deepcopy(p)
        fixed,changes=normalize(p,{'reduction':'count'})
        self.assertEqual(execute(fixed,[self.region()])['answer'],'2')
        self.assertEqual(p,before)
        self.assertEqual(fixed['steps'][-1]['input'],'f')
        self.assertEqual(changes[-1]['kind'],'complete_declared_row_count')
        self.assertEqual(normalize(p,{'reduction':None}),(p,[]))
        p['answer_spec']['operation']='lookup'
        self.assertEqual(normalize(p,{'reduction':'count'}),(p,[]))

    def test_explicit_row_listing_is_not_converted_to_count(self):
        p=self.plan();p['steps']=p['steps'][:2]
        p['output']={'step':'f','columns':['A']};p['answer_spec']['operation']='count'
        self.assertEqual(normalize(p,{'reduction':'count'}),(p,[]))

    def test_count_id_collision_and_step_limit(self):
        p=self.plan();p['steps']=p['steps'][:2];p['steps'][0]['id']='final_count';p['steps'][1]['input']='final_count'
        p['output']={'step':'f'};p['answer_spec']['operation']='count'
        new,_=normalize(p,{'reduction':'count'})
        self.assertEqual(new['output']['step'],'final_count_1')
        self.assertEqual(execute(new,[self.region()])['answer'],'2')
        p['steps'] += [{'id':f'padding{i}','op':'cell','table':'t1','row':3,'column':'B'} for i in range(23)]
        self.assertEqual(normalize(p,{'reduction':'count'}),(p,[]))

    def test_review_receives_final_values_and_preserves_raw_source(self):
        raw=[{'role':'user','content':json.dumps({'candidate':'Data, 2345','row_samples':{'r':[{'amount':'2,345'}]}})}]
        before=copy.deepcopy(raw)
        result={'answer':'Data, 2345','values':['Data','2345'],
                'output_normalizations':[{'component':1,'before':'2,345','after':'2345'}]}
        messages=review_request(raw,result)
        payload=json.loads(messages[-1]['content'])
        self.assertEqual(payload['final_output']['values'],['Data','2345'])
        self.assertEqual(payload['row_samples']['r'][0]['amount'],'2,345')
        self.assertTrue(payload['final_output']['normalizations'])
        self.assertEqual(raw,before)

    def test_pipeline_repairs_section_identity_with_existing_retry(self):
        plan=self.plan();calls=[]
        class Client:
            prompt_cap=.001;completion_cap=.001
            def complete(self,messages,ledger,purpose):
                calls.append((purpose,messages))
                if purpose=='review':return json.dumps({'verdict':'accept','issues':[]})
                candidate=copy.deepcopy(plan)
                if purpose=='repair':candidate['output']['columns']=['_section']
                return json.dumps(candidate)
        record={}
        with patch('src.pipeline.load_regions',return_value=[self.region()]):
            answer=answer_with_tools(Path('unused'),"Which group has the highest rate in the 'tier' class? Answer with only the group name.",
                                     Client(),record,settings_for_mode({'v3_reliability':True},'llm-v3'))
        self.assertEqual(answer,'Team Y')
        self.assertEqual([p for p,_ in calls],['plan','repair','review'])
        self.assertIn('Output identity',record['validation_errors'][0])
        payload=json.loads(next(m['content'] for m in calls[-1][1] if m['role']=='user'))
        self.assertEqual(payload['final_output']['values'],['Team Y'])

    def test_pipeline_completes_count_without_extra_call(self):
        plan=self.plan();plan['steps']=plan['steps'][:2]
        plan['output']={'step':'f'}
        plan['answer_spec']={'answer_type':'number','answer_field':'records','operation':'count'}
        calls=[]
        class Client:
            prompt_cap=.001;completion_cap=.001
            def complete(self,messages,ledger,purpose):
                calls.append(purpose)
                return json.dumps({'verdict':'accept','issues':[]} if purpose=='review' else plan)
        record={}
        with patch('src.pipeline.load_regions',return_value=[self.region()]):
            answer=answer_with_tools(Path('unused'),"How many records are in the tier class? Answer with only the integer.",
                                     Client(),record,settings_for_mode({'v3_reliability':True},'llm-v3'))
        self.assertEqual(answer,'2')
        self.assertEqual(calls,['plan','review'])


if __name__=='__main__':unittest.main()
