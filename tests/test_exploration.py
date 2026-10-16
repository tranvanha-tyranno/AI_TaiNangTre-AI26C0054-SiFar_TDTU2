import json
import unittest
from unittest.mock import patch
from pathlib import Path
from src.exploration import observe
from src.tools.executor import PlanError
from src.workbook_index import Region


def regions():
    return [Region('t1','Orders',1,4,1,3,
        {(1,1):'ID',(1,2):'Hub',(1,3):'Charge',(2,1):'A',(2,2):'East',(2,3):10,
         (3,1):'B',(3,2):'West',(3,3):20,(4,1):'C',(4,2):'East',(4,3):30},[],[],[1]),
        Region('t2','Map',1,3,1,2,
        {(1,1):'Hub',(1,2):'Region',(2,1):'East',(2,2):'North',(3,1):'West',(3,2):'South'},[],[],[1])]


class ExplorationTest(unittest.TestCase):
    def test_inspection_lists_and_reads_existing_regions(self):
        observations, acquired = observe([
            {'op':'list_sheets'}, {'op':'search_cells','text':'Region'},
            {'op':'read_range','table':'t2','range':'A1:B3'}], regions(), 'What is Region?')
        self.assertEqual(observations[0]['sheets'], ['Orders','Map'])
        self.assertEqual(observations[1]['match_count'], 1)
        self.assertEqual(observations[2]['preview']['range'], 'A1:B3')
        self.assertEqual([r.id for r in acquired], ['t2'])

    def test_inspection_bounds_and_budget_are_rejected(self):
        with self.assertRaisesRegex(PlanError, 'inside the selected table'):
            observe([{'op':'read_range','table':'t1','range':'A1:D3'}], regions(), 'Q')
        with self.assertRaisesRegex(PlanError, '1..3'):
            observe([{'op':'list_sheets'}]*4, regions(), 'Q')

    def test_plan_schema_has_inspection_and_answer_spec(self):
        from src.planner import tool_schema
        schema=tool_schema()
        self.assertEqual({branch['properties']['action']['enum'][0] for branch in schema['anyOf'] if 'action' in branch['properties']},{'inspect'})
        plan=next(branch for branch in schema['anyOf'] if 'steps' in branch['properties'])
        self.assertIn('answer_spec',plan['properties'])

    def test_pipeline_accepts_inspection_turn_before_plan(self):
        from src.pipeline import answer_with_tools
        class Client:
            prompt_cap=1; completion_cap=4; calls=0
            def complete(self, msgs, ledger, purpose):
                self.calls += 1
                if self.calls == 1:
                    return json.dumps({'action':'inspect','requests':[{'op':'inspect_table','table':'t2'}]})
                payload=json.loads(msgs[1]['content'])
                assert payload['inspection_results']
                return json.dumps({'steps':[
                    {'id':'r','op':'read','table':'t1','start_row':2,'end_row':4},
                    {'id':'s','op':'aggregate','input':'r','metric':'sum','expr':{'col':'C'}}],
                    'answer_spec':{'answer_type':'number','answer_field':'Charge','operation':'sum'},
                    'output':{'step':'s'}})
        client=Client(); record={}
        with patch('src.pipeline.load_regions', return_value=regions()), \
             patch('src.pipeline.retrieve', return_value=([regions()[0]], [{'table_id':'t1','selected':True}])):
            answer=answer_with_tools(Path('unused'),'What is the total Charge?',client,record,{'max_api_calls':3})
        self.assertEqual(answer,'60')
        self.assertEqual(client.calls,2)
        self.assertEqual(record['interactions'][0]['action'],'inspect')

    def test_label_contract_rejects_metric_column(self):
        from src.answer_contract import infer_answer_contract, validate_answer_field
        from src.tools.executor import execute
        region=Region('t1','Meter',1,3,1,2,
            {(1,1):'Lab',(1,2):'Energy kWh',(2,1):'North',(2,2):10,(3,1):'South',(3,2):20},[],[],[1])
        plan={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':3},
                       {'id':'s','op':'sort','input':'r','by':[{'column':'B','descending':True}]},
                       {'id':'t','op':'take','input':'s','limit':1}],
              'output':{'step':'t','columns':['B']}}
        result=execute(plan,[region])
        with self.assertRaisesRegex(Exception,'NAME/label'):
            validate_answer_field(infer_answer_contract('Which Lab has the highest Energy kWh? Answer the Lab name only.'),plan,result,[region])

    def test_malformed_review_does_not_discard_valid_candidate(self):
        from src.pipeline import answer_with_tools
        class Client:
            prompt_cap=1; completion_cap=4; calls=0
            def complete(self, msgs, ledger, purpose):
                self.calls += 1
                if purpose == 'review': return json.dumps({'verdict':'accept','unexpected':'ignored'})
                return json.dumps({'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':4},
                    {'id':'s','op':'aggregate','input':'r','metric':'sum','expr':{'col':'C'}}],
                    'answer_spec':{'answer_type':'number','answer_field':'Charge','operation':'sum'},
                    'output':{'step':'s'}})
        client=Client();record={}
        with patch('src.pipeline.load_regions', return_value=regions()), \
             patch('src.pipeline.retrieve', return_value=([regions()[0]], [{'table_id':'t1','selected':True}])):
            answer=answer_with_tools(Path('unused'),'What is the total Charge?',client,record,{'max_api_calls':2,'semantic_review':'all'})
        self.assertEqual(answer,'60')
        self.assertEqual(record['reviews'][0]['verdict'],'unavailable')

    def test_rejected_candidate_is_diagnostic_only(self):
        from src.pipeline import answer_with_tools
        class Client:
            prompt_cap=1; completion_cap=4; calls=0
            def complete(self, msgs, ledger, purpose):
                self.calls += 1
                return json.dumps({'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':4}],
                    'answer_spec':{'answer_type':'number','answer_field':'Score','operation':'sum'},
                    'output':{'step':'r','columns':['A']}})
        client=Client();record={}
        with patch('src.pipeline.load_regions', return_value=regions()), \
             patch('src.pipeline.retrieve', return_value=([regions()[0]], [{'table_id':'t1','selected':True}])), \
             self.assertRaises(PlanError):
            answer_with_tools(Path('unused'),'What is the total Score?',client,record,{'max_api_calls':3,'max_plan_repairs':1})
        self.assertTrue(record.get('last_candidate_answer'))
        self.assertTrue(record.get('candidate_rejected'))
        self.assertFalse(record.get('validated'))


if __name__ == '__main__': unittest.main()
