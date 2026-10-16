import copy
import unittest
from src.llmv4 import infer_contract, validate_contract
from src.llmv4_reasoning import check_plan
from src.tools.executor import execute, PlanError
from src.workbook_index import Region


class LineageTests(unittest.TestCase):
    def region(self):
        return Region('t1','Measurements',1,6,1,3,
                      {(1,1):'Group one',(2,1):'a',(2,2):7,(2,3):2,
                       (3,1):'b',(3,2):3,(3,3):4,(4,1):'Group two',
                       (5,1):'c',(5,2):5,(5,3):8,(6,1):'d',(6,2):1,(6,3):2},[],[],[])

    def plan(self, metric='combined'):
        return {'steps':[{'id':'r','op':'read','table':'t1','start_row':2},
            {'id':'f','op':'filter','input':'r','where':{'is_number':[{'col':'B'}]}},
            {'id':'d','op':'derive','input':'f','column':metric,'expr':{'add':[{'col':'B'},{'col':'C'}]}},
            {'id':'s','op':'sort','input':'d','by':[{'column':metric,'descending':True}]},
            {'id':'t','op':'take','input':'s','limit':1}],
            'output':{'step':'t','columns':[metric]}}

    def test_schema_tracks_renamed_metrics(self):
        for metric in ['combined','result_X']:
            plan=self.plan(metric)
            audit=check_plan(plan,[self.region()],{},'')
            self.assertIn(metric,audit['column_schemas']['t'])
            self.assertEqual(execute(plan,[self.region()],typed_comparisons=True)['answer'],'13')

    def test_sibling_column_error_names_provider_without_reconnecting(self):
        plan=self.plan();plan['steps'][3]['input']='f';original=copy.deepcopy(plan)
        with self.assertRaisesRegex(PlanError,'earlier providers=.*combined.*d'):
            check_plan(plan,[self.region()],{},'')
        self.assertEqual(plan,original)

    def test_select_drops_columns_and_unpivot_replaces_schema(self):
        plan=self.plan();plan['steps'][2]={'id':'d','op':'select','input':'f','columns':['B']}
        with self.assertRaisesRegex(PlanError,'missing'):
            check_plan(plan,[self.region()],{},'')
        plan={'steps':[{'id':'r','op':'read','table':'t1'},
                       {'id':'u','op':'unpivot','input':'r','columns':['B','C'],'keep_columns':['A']}],
              'output':{'step':'u','columns':['value']}}
        self.assertEqual(check_plan(plan,[self.region()],{},'')['column_schemas']['u'],
                         ['A','_row','column','label','value'])

    def test_extremum_of_row_sum_is_valid_without_grand_total(self):
        plan=self.plan();q='What is the highest sum of the two measurements?'
        result=execute(plan,[self.region()],typed_comparisons=True)
        validate_contract(infer_contract(q),plan,result,q)
        q='What is the sum of the two measurements across all records?'
        with self.assertRaisesRegex(PlanError,'computed sum'):
            validate_contract(infer_contract(q),plan,result,q)

    def test_wrong_sort_metric_does_not_bypass_sum_validation(self):
        plan=self.plan();plan['steps'][3]['by'][0]['column']='B'
        q='What is the highest sum of the two measurements?'
        with self.assertRaisesRegex(PlanError,'computed sum'):
            validate_contract(infer_contract(q),plan,execute(plan,[self.region()]),q)

    def test_coverage_uses_all_rows_and_is_v4_only(self):
        plan=self.plan();result=execute(plan,[self.region()],typed_comparisons=True)
        event=result['trace'][1]
        self.assertEqual(event['row_count'],4)
        self.assertEqual(event['observed_coverage']['source_row_max'],6)
        self.assertEqual(event['observed_coverage']['section_count'],2)
        self.assertEqual(len(result['row_samples']['f']),3)
        self.assertNotIn('observed_coverage',execute(plan,[self.region()])['trace'][1])


if __name__=='__main__':unittest.main()
