import json
from pathlib import Path
import unittest
from src.answer_contract import infer_answer_contract
from src.semantic_validation import validate_semantics,validate_rank_labels
from src.tools.executor import execute,PlanError
from src.workbook_index import Region,load_regions,retrieve

ROOT=Path(__file__).resolve().parents[1]


def metrics():
    return Region('t1','Metrics',1,5,1,3,
        {(1,1):'Sector',(1,2):'Count',(1,3):'Rate',
         (2,1):'Alpha',(2,2):3,(2,3):.07,
         (3,1):'Beta',(3,2):7,(3,3):.09,
         (4,1):'Gamma',(4,2):-1,(4,3):0,
         (5,1):'Note: thousands, not data'},[],[],[1],formats={(2,3):'0%',(3,3):'0%',(4,3):'0%'})


class SemanticValidationTest(unittest.TestCase):
    def test_fraction_requires_explicit_conversion_and_keeps_two_decimals(self):
        question='Return Rate as percentage points (multiply stored fraction by 100). Answer exactly 2 decimal places.'
        contract=infer_answer_contract(question)
        plan={'steps':[{'id':'rate','op':'cell','table':'t1','row':2,'column':'C'}],
              'output':{'step':'rate','decimals':2}}
        self.assertEqual(execute(plan,[metrics()])['answer'],'0.07')
        with self.assertRaisesRegex(PlanError,'unit conversion'): validate_semantics(question,contract,plan,execute(plan,[metrics()]),[metrics()])
        plan['steps'].append({'id':'percent','op':'calculate','expr':{'mul':[{'ref':'rate'},{'value':100}]}})
        plan['output']['step']='percent'
        result=execute(plan,[metrics()])
        validate_semantics(question,contract,plan,result,[metrics()])
        self.assertEqual(result['answer'],'7.00')

    def test_unused_read_does_not_count_as_vertical_sum_coverage(self):
        question='What is the sum of Count across the 3 sectors? Answer only the integer.'
        plan={'steps':[{'id':'unused','op':'read','table':'t1','start_row':2,'end_row':4},
                       {'id':'one','op':'sum_columns','table':'t1','row':2,'columns':['B']}],
              'output':{'step':'one'}}
        with self.assertRaisesRegex(PlanError,'all 3 data ROWS'):
            validate_semantics(question,infer_answer_contract(question),plan,execute(plan,[metrics()]),[metrics()])
        plan['steps'][1]={'id':'one','op':'aggregate','input':'unused','metric':'sum','expr':{'col':'B'}}
        result=execute(plan,[metrics()])
        validate_semantics(question,infer_answer_contract(question),plan,result,[metrics()])
        self.assertEqual(result['answer'],'9')

    def test_unit_and_row_scope_errors_are_reported_together(self):
        question='Convert the total Count across all sectors from thousands into individual people. Answer only the integer.'
        plan={'steps':[{'id':'one','op':'cell','table':'t1','row':2,'column':'B'}],'output':{'step':'one'}}
        with self.assertRaises(PlanError) as caught:
            validate_semantics(question,infer_answer_contract(question),plan,execute(plan,[metrics()]),[metrics()])
        self.assertIn('1000',str(caught.exception));self.assertIn('all 3 data ROWS',str(caught.exception))
        plan={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':4},
                       {'id':'s','op':'aggregate','input':'r','metric':'sum','expr':{'col':'B'}},
                       {'id':'u','op':'calculate','expr':{'mul':[{'ref':'s'},{'value':1000}]}}],
              'output':{'step':'u'}}
        result=execute(plan,[metrics()]);validate_semantics(question,infer_answer_contract(question),plan,result,[metrics()])
        self.assertEqual(result['answer'],'9000')
        self.assertIsNone(infer_answer_contract('Answer only the integer in thousands.')['unit_scale'])

    def test_named_ranking_rejects_repeated_metric_heading(self):
        question="Rank the following sectors by employees in 'Beta': Alpha, Beta, and Gamma. Answer with three sector names."
        with self.assertRaisesRegex(PlanError,'exactly once'):
            validate_rank_labels(question,{'values':['Beta','Beta','Beta']})
        validate_rank_labels(question,{'values':['Beta','Gamma','Alpha']})

    def test_percent_and_quarter_paths_are_exposed_in_preview(self):
        regions=load_regions(ROOT/'Test/08_three_level_headers/xlsx_files/data.xlsx')
        preview=regions[0].preview('2024 Q1 rate')
        self.assertEqual(preview['column_hierarchy']['G'],['2024','Q1','Rate'])
        sector=next(d for d in preview['row_dimensions'] if d['column']=='A')
        self.assertEqual(sector['row_count'],8)
        self.assertEqual(sector['data_ranges'],[[4,11]])
        self.assertIn('G4',preview['percent_cells'])

    def test_scope_uses_full_evidence_beyond_ui_preview_limit(self):
        cells={(1,1):'Sector',(1,2):'Count'}
        cells.update({(r,1):f'Sector {r}' for r in range(2,152)})
        cells.update({(r,2):1 for r in range(2,152)})
        region=Region('t1','Rows',1,151,1,2,cells,[],[],[1])
        question='What is the sum of Count across all sectors? Answer only the integer.'
        plan={'steps':[{'id':'r','op':'read','table':'t1','start_row':2},
                       {'id':'s','op':'aggregate','input':'r','metric':'sum','expr':{'col':'B'}}],
              'output':{'step':'s'}}
        result=execute(plan,[region]);self.assertEqual(len(result['evidence']),100)
        self.assertEqual(len(result['evidence_full']),150)
        validate_semantics(question,infer_answer_contract(question),plan,result,[region])

    def test_observed_bad_plans_are_rejected(self):
        scenarios=[('20261014-194948-762d4c','08_three_level_headers'),('20261014-194340-f6fc28','02_merged_hierarchy')]
        for run,dataset in scenarios:
            path=ROOT/'outputs/runs'/run
            if not path.exists(): continue
            refs=json.loads((path/'metadata.json').read_text(encoding='utf-8'))['reference']
            for record in map(json.loads,(path/'questions.jsonl').read_text(encoding='utf-8').splitlines()):
                if record['answer']==refs[str(record['id'])]: continue
                regions,_=retrieve(load_regions(ROOT/'Test'/dataset/'xlsx_files'/record['file_name']),record['query'])
                result=execute(record['plan'],regions)
                with self.subTest(id=record['id']),self.assertRaises(PlanError):
                    validate_semantics(record['query'],infer_answer_contract(record['query']),record['plan'],result,regions)
                    validate_rank_labels(record['query'],result)


if __name__=='__main__': unittest.main()
