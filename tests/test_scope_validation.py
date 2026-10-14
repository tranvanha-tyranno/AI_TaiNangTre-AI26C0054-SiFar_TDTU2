from pathlib import Path
import unittest
from src.workbook_index import Region, load_regions, retrieve
from src.tools.executor import execute, PlanError
from src.scope_validation import validate_aggregate_scope
from src.planner import tool_schema

ROOT=Path(__file__).resolve().parents[1]


def scalar_plan():
    return {'steps':[
        {'id':'a','op':'cell','table':'t1','row':9,'column':'B'},
        {'id':'b','op':'cell','table':'t1','row':11,'column':'B'},
        {'id':'difference','op':'calculate','expr':{'sub':[{'ref':'b'},{'ref':'a'}]}}],
        'output':{'step':'difference'}}


class ScopeValidationTest(unittest.TestCase):
    def test_rejects_observed_single_industry_plan_and_accepts_full_sum(self):
        question='How many more employed people were aged 20 to 24 than aged 16 to 19 across all industries?'
        selected,_=retrieve(load_regions(ROOT/'Public_data_1/xlsx_files/p4_t05.xlsx'),question)
        plan=scalar_plan()
        self.assertEqual(execute(plan,selected)['answer'],'28')
        with self.assertRaisesRegex(PlanError,'scope is incomplete'):
            validate_aggregate_scope(question,plan,selected)
        for step in plan['steps'][:2]:
            step['op']='sum_columns'
            del step['column']
            step['columns']=list('BCDEFGHIJKLM')
        validate_aggregate_scope(question,plan,selected)
        result=execute(plan,selected)
        self.assertEqual(result['answer'],'9017')
        self.assertEqual(result['evidence_count'],24)
        self.assertIn('cpsaat14!M11',result['evidence'])
        variants=tool_schema()['properties']['steps']['items']['anyOf']
        summed=next(v for v in variants if v['properties']['op']['enum']==['sum_columns'])
        self.assertEqual(set(summed['required']),{'id','op','table','row','columns'})
        self.assertNotIn('input',summed['properties'])

    def test_all_category_guard_generalizes_and_accepts_explicit_total(self):
        region=Region('t1','Other',1,3,1,5,
            {(1,1):'Metric',(1,2):'Food',(1,3):'Housing',(1,4):'Travel',(1,5):'Total',
             (2,1):'Current',(2,2):10,(2,3):20,(2,4):0,(2,5):30,
             (3,1):'Prior',(3,2):5,(3,3):7,(3,4):3,(3,5):15},[],[],[1])
        plan=scalar_plan()
        plan['steps'][0]['row']=2; plan['steps'][1]['row']=3
        detail_region=Region('t1','Other',1,3,1,4,
            {k:v for k,v in region.cells.items() if k[1]<5},[],[],[1])
        with self.assertRaises(PlanError): validate_aggregate_scope('Difference across all categories?',plan,[detail_region])
        for step in plan['steps'][:2]: step['column']='E'
        validate_aggregate_scope('Difference across all categories?',plan,[region])
        for step in plan['steps'][:2]: step['column']='B'
        validate_aggregate_scope('Difference for Food only?',plan,[region])

    def test_sum_columns_keeps_zero_negatives_and_rejects_duplicates_blanks(self):
        region=Region('t1','Data',1,1,1,4,{(1,1):10,(1,2):0,(1,3):-3},[],[],[])
        plan={'steps':[{'id':'s','op':'sum_columns','table':'t1','row':1,'columns':['A','B','C']}],
              'output':{'step':'s'}}
        self.assertEqual(execute(plan,[region])['answer'],'7')
        for columns in [['A','A'],['D'],['Z']]:
            plan['steps'][0]['columns']=columns
            with self.assertRaises(PlanError): execute(plan,[region])

    def test_preview_compacts_merges_without_changing_executor_values(self):
        regions=load_regions(ROOT/'Public_data_1/xlsx_files/p4_t05.xlsx')
        region=next(r for r in regions if r.whole_sheet)
        preview=region.preview('across all industries')
        rows={r['row']:r['cells'] for r in preview['rows']}
        self.assertEqual(set(rows[1]),{'A'})
        self.assertEqual(rows[4]['B'],'2023')
        self.assertNotIn('C',rows[4])
        self.assertEqual(region.cells[(4,3)],2023)
        self.assertEqual(set(rows[5]),set('BCDEFGHIJKLM'))


if __name__=='__main__': unittest.main()
