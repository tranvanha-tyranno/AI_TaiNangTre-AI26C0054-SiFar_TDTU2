import copy
import unittest
from src.reliability import normalize, preview, format_numeric_components
from src.tools.executor import execute, PlanError
from src.variants import settings_for_mode, v3_version
from src.workbook_index import Region


class ReliabilityTest(unittest.TestCase):
    def region(self):
        return Region('t1','Example',1,5,1,2,
            {(1,1):'Group X',(2,1):'class',(2,2):'968',
             (3,1):'Group Y',(4,1):'class',(4,2):'1,307',(5,1):'other',(5,2):'10'},[],[],[])

    def comparison(self, a, b, op='gt'):
        r=self.region();r.cells[(2,2)]=a;r.cells[(4,2)]=b
        plan={'steps':[{'id':'a','op':'cell','table':'t1','row':2,'column':'B'},
                       {'id':'b','op':'cell','table':'t1','row':4,'column':'B'},
                       {'id':'c','op':'calculate','expr':{op:[{'ref':'a'},{'ref':'b'}]}}],
              'output':{'step':'c'}}
        return plan,r

    def test_clear_numeric_text_ordering_preserves_baseline(self):
        for a,b in [('968','1,307'),('9','12'),('-2','-10')]:
            p,r=self.comparison(a,b)
            self.assertEqual(execute(p,[r],reliability=True)['answer'],
                             'Yes' if float(a.replace(',',''))>float(b.replace(',','')) else 'No')
        p,r=self.comparison('968','1,307')
        self.assertEqual(execute(p,[r])['answer'],'Yes')
        self.assertEqual(execute(p,[r],reliability=True)['answer'],'No')
        self.assertEqual(execute(p,[r])['answer'],'Yes')

    def test_identifier_equality_is_not_numeric_coercion(self):
        p,r=self.comparison('001','1','eq')
        self.assertEqual(execute(p,[r],reliability=True)['answer'],'No')

    def test_boolean_comparison_does_not_use_numeric_cast(self):
        p,r=self.comparison(True,False,'ne')
        self.assertEqual(execute(p,[r],reliability=True)['answer'],'Yes')
        p,r=self.comparison(True,1,'eq')
        with self.assertRaisesRegex(PlanError,'Boolean comparison'):
            execute(p,[r],reliability=True)
        p,r=self.comparison(True,False,'gt')
        with self.assertRaises(PlanError):execute(p,[r],reliability=True)

    def test_boolean_count_requires_filter_and_preserves_normal_count(self):
        p={'steps':[{'id':'r','op':'read','table':'t1','start_row':2},
                    {'id':'c','op':'aggregate','input':'r','metric':'count',
                     'expr':{'eq':[{'col':'A'},{'value':'class'}]}}],
           'output':{'step':'c'}}
        self.assertEqual(execute(p,[self.region()])['answer'],'4')
        with self.assertRaisesRegex(PlanError,'including False'):
            execute(p,[self.region()],reliability=True)
        p['steps'][1:]=[{'id':'f','op':'filter','input':'r','where':p['steps'][1]['expr']},
                       {'id':'c','op':'aggregate','input':'f','metric':'count'}]
        self.assertEqual(execute(p,[self.region()],reliability=True)['answer'],'2')

    def test_lag_is_lifted_only_when_declaration_is_unambiguous(self):
        p={'steps':[{'id':'x','op':'derive','input':'r','column':'previous',
                    'expr':{'lag':{'source':'B','column':'previous','offset':2}}}]}
        before=copy.deepcopy(p);new,changes=normalize(p)
        self.assertEqual(p,before)
        self.assertEqual(new['steps'][0],{'id':'x','op':'lag','input':'r','column':'previous','source':'B','offset':2})
        self.assertTrue(changes)
        p['steps'][0]['expr']['lag']['column']='ambiguous'
        self.assertEqual(normalize(p),(p,[]))

    def test_preview_section_anchor_uses_actual_preceding_row(self):
        p=preview(self.region(),'class',5)
        rows={r['row']:r for r in p['rows']}
        self.assertEqual(rows[2]['section_row'],1)
        self.assertEqual(rows[4]['section_row'],3)
        self.assertNotIn('section_row',self.region().preview('class',5)['rows'][1])

    def test_variant_switch_is_explicit_and_isolated(self):
        self.assertEqual(v3_version(settings_for_mode({},'llm-v3')),'lmmv3-v2-dedup-v1')
        settings=settings_for_mode({'v3_reliability':True},'llm-v3')
        self.assertEqual(v3_version(settings),'lmmv3-v2-reliability-v2')
        self.assertNotIn('v3_reliability',settings_for_mode(settings,'llm-v2'))

    def test_integer_formatting_only_touches_declared_numeric_components(self):
        result={'values':['001,307','1,307','1,23']}
        contract={'kind':'tuple','integer':True,'numeric_positions':[1,2]}
        changes=format_numeric_components(result,contract)
        self.assertEqual(result['values'],['001,307','1307','1,23'])
        self.assertEqual(len(changes),1)
        result={'values':['1,307']}
        self.assertEqual(format_numeric_components(result,{'kind':'scalar','integer':True}),[])
        self.assertEqual(result['values'],['1,307'])


if __name__=='__main__':unittest.main()
