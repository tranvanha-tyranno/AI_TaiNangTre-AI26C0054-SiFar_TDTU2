import json
import unittest
from src.workbook_index import Region
from src.tools.executor import execute, PlanError
from src.llmv4_recovery import parse_response, normalize_dependencies


class RegressionTest(unittest.TestCase):
    def region(self,a,b):
        return Region('t1','Data',1,3,1,2,{(1,1):'Name',(1,2):'Amount',
            (2,1):'a',(2,2):a,(3,1):'b',(3,2):b},[],[],[1])

    def comparison(self,op='gt'):
        return {'steps':[{'id':'a','op':'cell','table':'t1','row':2,'column':'B'},
                         {'id':'b','op':'cell','table':'t1','row':3,'column':'B'},
                         {'id':'c','op':'calculate','expr':{op:[{'ref':'a'},{'ref':'b'}]}}],
                'output':{'step':'c'}}

    def test_numeric_text_orders_numerically_and_baseline_is_unchanged(self):
        plan=self.comparison();region=self.region('1,423','957')
        self.assertEqual(execute(plan,[region])['answer'],'No')
        self.assertEqual(execute(plan,[region],typed_comparisons=True)['answer'],'Yes')
        self.assertEqual(execute(plan,[region])['answer'],'No')  # context reset
        self.assertEqual(region.cells[(2,2)],'1,423')

    def test_boolean_eq_filter_works_without_treating_true_as_one(self):
        plan={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':3},
                       {'id':'d','op':'derive','input':'r','column':'selected','expr':{'gt':[{'col':'B'},{'value':5}]}},
                       {'id':'f','op':'filter','input':'d','where':{'eq':[{'col':'selected'},{'value':True}]}},
                       {'id':'n','op':'aggregate','input':'f','metric':'count'}],
              'output':{'step':'n'}}
        region=self.region(8,3)
        with self.assertRaises(PlanError):execute(plan,[region])
        self.assertEqual(execute(plan,[region],typed_comparisons=True)['answer'],'1')
        with self.assertRaisesRegex(PlanError,'Boolean comparisons'):
            execute(self.comparison('eq'),[self.region(True,1)],typed_comparisons=True)

    def test_identifier_and_text_equality_are_not_numeric_coercions(self):
        self.assertEqual(execute(self.comparison('eq'),[self.region('0012','12')],typed_comparisons=True)['answer'],'No')
        self.assertEqual(execute(self.comparison(),[self.region('Beta','Alpha')],typed_comparisons=True)['answer'],'Yes')

    def test_ambiguous_comma_requires_explicit_locale(self):
        with self.assertRaisesRegex(PlanError,'declare locale'):
            execute(self.comparison(),[self.region('1,3','2,4')],typed_comparisons=True)

    def test_transport_whitespace_does_not_rewrite_literal_strings(self):
        steps=[{'id':'r','op':'read','table':'t1'},
               {'id':'f','op':'filter','input':'r','where':{'eq':[{'col':'A'},{'value':'Line\\nCode'}]}}]
        raw=json.dumps({'steps':'\\n'+json.dumps(steps)+'\\t','output':{'step':'f','columns':['A']}})
        repairs=[];parsed=parse_response(raw,repairs)
        self.assertEqual(parsed['steps'],steps)
        self.assertEqual(repairs[0]['kind'],'encoded_steps_transport_whitespace')
        with self.assertRaises(ValueError):
            parse_response(json.dumps({'steps':'\\n[{"id":"a" "op":"read"}]\\n'}),[])

    def test_immediate_lag_dependency_is_rebound_with_source_provenance(self):
        plan={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':3},
                       {'id':'prev','op':'lag','input':'r','source':'B','column':'prev'},
                       {'id':'d','op':'derive','input':'r','column':'delta','expr':{'if':[
                           {'and':[{'is_number':[{'col':'B'}]},{'is_null':[{'ref':'prev'}]}]},
                           {'value':None},{'sub':[{'col':'B'},{'ref':'prev'}]}]}},
                       {'id':'f','op':'filter','input':'d','where':{'is_number':[{'col':'delta'}]}}],
              'output':{'step':'f','columns':['delta'],'decimals':[0,0]}}
        fixed,changes=normalize_dependencies(plan)
        self.assertEqual(fixed['steps'][2]['input'],'prev')
        self.assertEqual(plan['steps'][2]['input'],'r')
        self.assertEqual(fixed['output']['decimals'],0)
        result=execute(fixed,[self.region(4,9)],typed_comparisons=True)
        self.assertEqual(result['answer'],'5')
        self.assertIn('Data!B2',result['evidence'])
        self.assertIn('Data!B3',result['evidence'])
        self.assertEqual(len(changes),2)

    def test_ambiguous_lag_reference_and_mixed_decimals_are_not_guessed(self):
        plan={'steps':[{'id':'r','op':'read','table':'t1'},
                       {'id':'previous','op':'lag','input':'r','source':'B','column':'prior_amount'},
                       {'id':'d','op':'derive','input':'r','column':'delta','expr':{'sub':[{'ref':'previous'},{'col':'B'}]}}],
              'output':{'step':'d','columns':['delta'],'decimals':[0,2]}}
        fixed,changes=normalize_dependencies(plan)
        self.assertEqual(fixed,plan)
        self.assertEqual(changes,[])


if __name__=='__main__':unittest.main()
