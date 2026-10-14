from datetime import datetime
import unittest
from src.workbook_index import Region, load_regions, retrieve
from src.tools.executor import execute, PlanError
from src.usage import UsageLedger, BudgetError
from pathlib import Path


def table():
    cells={(1,1):'Name',(1,2):'Birth',(1,3):'Admission',(1,4):'Score'}
    for r,values in enumerate([
        ['Older',datetime(1990,1,1),datetime(2021,1,1),80],
        ['Youngest',datetime(2005,1,1),datetime(2023,1,1),90],
        ['Second',datetime(2002,1,1),datetime(2021,1,1),70],
    ],2):
        cells.update({(r,c):v for c,v in enumerate(values,1)})
    return Region('t1','People',1,4,1,4,cells,[],[],[1])


class ToolTest(unittest.TestCase):
    def test_second_youngest_uses_age_not_admission_chronology(self):
        plan={'steps':[
            {'id':'data','op':'read','table':'t1','start_row':2,'end_row':4},
            {'id':'ages','op':'derive','input':'data','column':'age','expr':{'date_diff_days':[{'col':'C'},{'col':'B'}]}},
            {'id':'sorted','op':'sort','input':'ages','by':[{'column':'age'}]},
            {'id':'rank','op':'take','input':'sorted','offset':1,'limit':1}],
            'output':{'step':'rank','columns':['A']}}
        answer=execute(plan,[table()])
        self.assertEqual(answer['answer'],'Second')
        self.assertIn('People!A4',answer['evidence'])
        self.assertIn('People!B3',answer['evidence'])

    def test_filter_and_sum_use_full_data_and_keep_zero(self):
        plan={'steps':[{'id':'data','op':'read','table':'t1','start_row':2,'end_row':4},
                       {'id':'f','op':'filter','input':'data','where':{'ge':[{'col':'D'},{'value':80}]}},
                       {'id':'total','op':'aggregate','input':'f','metric':'sum','expr':{'col':'D'}}],
              'output':{'step':'total','decimals':2}}
        self.assertEqual(execute(plan,[table()])['answer'],'170.00')

    def test_unknown_tools_and_invented_answers_rejected(self):
        for plan in [
            {'steps':[{'id':'x','op':'exec','code':'print(1)'}],'output':{'step':'x'}},
            {'steps':[{'id':'x','op':'calculate','expr':{'value':'Ngo'}}],'output':{'step':'x'}},
            {'steps':[{'id':'x','op':'read','table':'t1','start_row':0}],'output':{'step':'x','columns':['A']}},
        ]:
            with self.assertRaises(PlanError): execute(plan,[table()])

    def test_aggregate_does_not_silently_ignore_where(self):
        plan={'steps':[{'id':'r','op':'read','table':'t1','start_row':2},
            {'id':'a','op':'aggregate','input':'r','metric':'sum','expr':{'col':'D'},'where':{'value':True}}],
            'output':{'step':'a'}}
        with self.assertRaisesRegex(PlanError,'Unsupported fields'):
            execute(plan,[table()])

    def test_collect_scalars_and_decimal_formatting(self):
        plan={'steps':[{'id':'a','op':'cell','table':'t1','row':2,'column':'D'},
                       {'id':'b','op':'cell','table':'t1','row':3,'column':'D'},
                       {'id':'both','op':'collect','inputs':['a','b']}],
              'output':{'step':'both','columns':['value'],'decimals':2}}
        self.assertEqual(execute(plan,[table()])['answer'],'80.00, 90.00')

    def test_count_zero_still_has_evidence(self):
        plan={'steps':[{'id':'r','op':'read','table':'t1','start_row':2},
            {'id':'f','op':'filter','input':'r','where':{'gt':[{'col':'D'},{'value':100}]}},
            {'id':'n','op':'aggregate','input':'f','metric':'count'}],'output':{'step':'n'}}
        self.assertEqual(execute(plan,[table()])['answer'],'0')

    def test_group_and_join(self):
        plan={'steps':[{'id':'data','op':'read','table':'t1','start_row':2,'end_row':4},
                       {'id':'g','op':'group','input':'data','by':['A'],'metric':'sum','expr':{'col':'D'},'column':'score'},
                       {'id':'j','op':'join','left':'g','right':'data','left_on':'A','right_on':'A'},
                       {'id':'s','op':'sort','input':'j','by':[{'column':'left.score','descending':True}]},
                       {'id':'top','op':'take','input':'s','limit':1}],
              'output':{'step':'top','columns':['right.A']}}
        self.assertEqual(execute(plan,[table()])['answer'],'Youngest')

    def test_budget_unknown_calls_not_free(self):
        ledger=UsageLedger(limit_usd=.01,max_calls=2)
        ledger.reserve([{'role':'user','content':'hi'}],1000)
        with self.assertRaises(BudgetError): ledger.reserve([{'role':'user','content':'x'*9000}],1000)
        summary=ledger.summary()
        self.assertFalse(summary['cost_complete'])
        self.assertGreater(summary['budget_charge_usd'],0)

    def test_parser_preserves_public_coordinates(self):
        path=Path(__file__).resolve().parents[1]/'Public_data_1/xlsx_files/p4_t01.xlsx'
        regions=load_regions(path)
        selected,catalog=retrieve(regions,'second youngest at admission date')
        self.assertEqual(selected[0].cells[(13,4)],'Ngo')
        self.assertEqual(selected[0].cells[(2,6)],'Admission')
        self.assertTrue(catalog[0]['selected'])
