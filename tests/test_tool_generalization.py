"""Regression cases from run failure classes, with independent names/values."""
from decimal import Decimal
import unittest

from src.answer_contract import infer_answer_contract, validate_answer_contract, validate_answer_field
from src.pipeline import add_numeric_guards
from src.planner import tool_schema, parse_plan, repair_containers
import json
from src.plan_normalization import normalize_plan
from src.scope_validation import validate_aggregate_scope
from src.tools.executor import PlanError, execute, expression, number
from src.workbook_index import Region


def region(cells, end=5, width=3):
    return Region('t1', 'Unseen sheet', 1, end, 1, width, cells, [], [], [1])


class ToolGeneralizationTest(unittest.TestCase):
    def test_currency_and_missing_data_remain_distinct(self):
        for text, expected in [('$2,004',2004),('($1,234.50)',-1234.5),('\u00a3 18',18),
                               ('1\u202f234',1234),('\u221212.5',-12.5),('0%',0)]:
            self.assertEqual(number(text), Decimal(str(expected)))
        for text in ['(-8-)', '..', '-', 'See note 42', True, None, 'NaN', '1,23']:
            with self.subTest(text=text), self.assertRaises(PlanError): number(text)

    def test_tuple_keeps_label_and_formats_only_numeric_component(self):
        q='Which size class has the highest gap? Answer as `size class, gap`, with the gap using exactly one decimal place.'
        r=region({(2,1):'17 - 63',(2,2):Decimal('7.25')})
        p={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':2}],
           'output':{'step':'r','columns':['A','B'],'decimals':1},
           'answer_spec':{'answer_type':'label','answer_field':'size class','operation':'argmax'}}
        result=execute(p,[r]); c=infer_answer_contract(q)
        validate_answer_contract(c,p,result,q);validate_answer_field(c,p,result,[r])
        self.assertEqual(result['answer'],'17 - 63, 7.3')
        p['output']['columns']=['B']
        with self.assertRaisesRegex(PlanError,'2 final'): validate_answer_contract(c,p,execute(p,[r]),q)

    def test_metric_words_do_not_force_wrong_reductions(self):
        for q in ['For which group are average hours highest? Answer only the group name.',
                  'Identify the year when the total labor force was below 70. Answer with only the year.']:
            self.assertIsNone(infer_answer_contract(q)['reduction'])
        self.assertEqual(infer_answer_contract('Using annual rows, in how many years was A higher than B? Answer only the integer.')['reduction'],'count')

    def test_percent_decrease_contract_multilingual(self):
        q='2001년 대비 2002년에 총 사건 수는 몇 퍼센트 감소했습니까? 소수점 둘째 자리까지 숫자만 답하십시오.'
        c=infer_answer_contract(q)
        self.assertEqual(c['decimals'],2);self.assertEqual(c['reduction'],'percent_change')
        r=region({(2,1):250,(3,1):200})
        p={'steps':[{'id':'old','op':'cell','table':'t1','row':2,'column':'A'},
                    {'id':'new','op':'cell','table':'t1','row':3,'column':'A'}],
           'output':{'step':'new','decimals':2}}
        with self.assertRaisesRegex(PlanError,'Percent change'): validate_answer_contract(c,p,execute(p,[r]),q)
        p['steps'].append({'id':'change','op':'calculate','expr':{'mul':[{'div':[{'sub':[{'ref':'old'},{'ref':'new'}]},{'ref':'old'}]},{'value':100}]}})
        p['output']['step']='change'
        result=execute(p,[r]);validate_answer_contract(c,p,result,q)
        self.assertEqual(result['answer'],'20.00')

    def test_lag_ranking_changes_when_unseen_values_change(self):
        # Both winner and amount must respond to input, including shuffled years.
        for values, expected in [([90,140,110],'2042, 30'),([90,140,50],'2042, 90')]:
            cells={(1,1):'Year',(1,2):'Workers'}
            for row,year,value in [(2,2042,values[2]),(3,2040,values[0]),(4,2041,values[1])]:
                cells[row,1]=year;cells[row,2]=value
            p={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':4},
                {'id':'s','op':'sort','input':'r','by':[{'column':'A'}]},
                {'id':'l','op':'lag','input':'s','source':'B','column':'previous'},
                {'id':'valid','op':'filter','input':'l','where':{'is_number':[{'col':'previous'}]}},
                {'id':'d','op':'derive','input':'valid','column':'decrease','expr':{'sub':[{'col':'previous'},{'col':'B'}]}},
                {'id':'rank','op':'sort','input':'d','by':[{'column':'decrease','descending':True}]},
                {'id':'top','op':'take','input':'rank','limit':1}],
                'output':{'step':'top','columns':['A','decrease']}}
            result=execute(p,[region(cells)])
            self.assertEqual(result['answer'],expected)
            self.assertIn('Unseen sheet!B4',result['evidence'])

    def test_section_label_retains_original_cell_provenance(self):
        cells={(1,1):'Activity',(1,2):'Hours',(2,1):'Unseen group',(3,1):'  Task ',(3,2):0,
               (4,1):'Other group',(5,1):'  Task ',(5,2):6}
        p={'steps':[{'id':'r','op':'read','table':'t1','start_row':2},
            {'id':'labels','op':'derive','input':'r','column':'section',
             'expr':{'if':[{'is_null':[{'col':'B'}]},{'col':'A'},{'value':None}]}},
            {'id':'filled','op':'fill_down','input':'labels','columns':['section']},
            {'id':'tasks','op':'filter','input':'filled','where':{'eq':[{'trim':[{'col':'A'}]},{'value':'Task'}]}},
            {'id':'s','op':'sort','input':'tasks','by':[{'column':'B','descending':True}]},
            {'id':'t','op':'take','input':'s','limit':1}],
            'output':{'step':'t','columns':['section']}}
        result=execute(p,[region(cells)])
        self.assertEqual(result['answer'],'Other group');self.assertIn('Unseen sheet!A4',result['value_sources'][0])

    def test_record_pairs_scalar_labels_and_values(self):
        r=region({(2,1):'New label',(3,2):'$3,100'})
        p={'steps':[{'id':'label','op':'cell','table':'t1','row':2,'column':'A'},
                    {'id':'metric','op':'cell','table':'t1','row':3,'column':'B'},
                    {'id':'pair','op':'record','fields':{'group':'label','amount':'metric'}}],
           'output':{'step':'pair','columns':['group','amount'],'decimals':0}}
        result=execute(p,[r]);self.assertEqual(result['answer'],'New label, 3100')
        q='Answer as `group, amount`, with the amount as an integer.'
        validate_answer_contract(infer_answer_contract(q),p,result,q)
        self.assertEqual(len(result['evidence']),2)

    def test_single_row_aggregate_cannot_bypass_all_category_scope(self):
        r=region({(1,1):'Age',(1,2):'Farming',(1,3):'Mining',(1,4):'Trade',
                  (2,1):'Older',(2,2):4,(2,3):8,(2,4):10},end=2,width=4)
        p={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':2},
                    {'id':'s','op':'aggregate','input':'r','metric':'sum','expr':{'col':'B'}}],
           'output':{'step':'s'}}
        with self.assertRaisesRegex(PlanError,'incomplete'): validate_aggregate_scope('Across all industries, how many workers?',p,[r])

    def test_lazy_if_and_code_length(self):
        self.assertEqual(expression({'if':[{'value':False},{'div':[{'value':1},{'value':0}]},{'value':9}]},{},{}).value,9)
        self.assertTrue(expression({'eq':[{'length':[{'value':' 001234 '}]},{'value':6}]},{},{}).value)

    def test_guard_for_one_column_has_valid_arity(self):
        p={'steps':[{'id':'d','op':'derive','input':'r','column':'n','expr':{'abs':[{'col':'B'}]}}]}
        guarded,changed=add_numeric_guards(p)
        self.assertTrue(changed);self.assertIn('is_number',guarded['steps'][0]['where'])

    def test_schema_exposes_every_new_tool(self):
        plan=next(b for b in tool_schema()['anyOf'] if 'steps' in b['properties'])
        operations={v['properties']['op']['enum'][0] for v in plan['properties']['steps']['items']['anyOf']}
        self.assertTrue({'lag','fill_down','record'}<=operations)

    def test_normalization_is_logged_and_keeps_raw_plan(self):
        r=region({(2,1):'  Alpha ',(2,2):3,(3,1):'Beta',(3,2):2})
        p={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':3},
            {'id':'f','op':'filter','input':'r','where':{'eq':[{'trim':{'ref':'A'}},'Alpha']}},
            {'id':'n','op':'aggregate','input':'f','metric':'count'}],'output':{'step':'n'}}
        canonical,changes=normalize_plan(p,[r])
        self.assertEqual(execute(canonical,[r])['answer'],'1')
        self.assertEqual({c['kind'] for c in changes},{'row_column_reference','unary_array','explicit_literal'})
        self.assertEqual(p['steps'][1]['where']['eq'][0],{'trim':{'ref':'A'}})

    def test_read_section_context_survives_narrow_read_bounds(self):
        r=region({(1,1):'Activity',(1,2):'Value',(2,1):'Far group',
                  (3,1):'Task',(3,2):7,(4,1):'Other group',(5,1):'Task',(5,2):2})
        p={'steps':[{'id':'r','op':'read','table':'t1','start_row':3,'end_row':3}],
           'output':{'step':'r','columns':['_section']}}
        result=execute(p,[r]);self.assertEqual(result['answer'],'Far group')
        self.assertEqual(result['value_sources'][0],['Unseen sheet!A2'])
        self.assertEqual(r.preview('Task')['section_labels'][0]['row'],2)

    def test_record_cannot_turn_invented_literal_into_answer(self):
        r=region({(2,1):'Real label'})
        for value in ['Invented label',42]:
            p={'steps':[{'id':'r','op':'record','fields':{'answer':{'value':value}}}],
               'output':{'step':'r','columns':['answer']}}
            with self.assertRaisesRegex(PlanError,'depend on spreadsheet'):execute(p,[r])

    def test_normalization_never_guesses_missing_scalar_or_column(self):
        r=region({(2,2):3})
        p={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':2},
            {'id':'d','op':'derive','input':'r','column':'x','expr':{'ref':'imagined'}}],
            'output':{'step':'d','columns':['x']}}
        canonical,changes=normalize_plan(p,[r]);self.assertFalse(changes)
        with self.assertRaisesRegex(PlanError,'Scalar reference'):execute(canonical,[r])

    def test_boolean_sum_normalizes_to_explicit_filtered_count(self):
        r=region({(2,2):3,(3,2):8})
        p={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':3},
            {'id':'n','op':'aggregate','input':'r','metric':'sum','expr':{'gt':[{'col':'B'},{'value':5}]}}],
            'output':{'step':'n'}}
        canonical,changes=normalize_plan(p,[r])
        self.assertEqual(execute(canonical,[r])['answer'],'1')
        self.assertEqual(changes[-1]['kind'],'boolean_sum_to_count')

    def test_scalar_formatting_preserves_requested_precision(self):
        r=region({(2,2):'8,700',(3,2):'6,090'})
        p={'steps':[{'id':'v','op':'cell','table':'t1','row':2,'column':'B'},
            {'id':'formatted','op':'derive','input':'v','column':'result','expr':{'number':[{'ref':'v'}]}}],
            'output':{'step':'formatted','columns':['result']}}
        canonical,changes=normalize_plan(p,[r],{'decimals':2})
        self.assertEqual(execute(canonical,[r])['answer'],'8700.00')
        self.assertIn('scalar_final_expression',{c['kind'] for c in changes})
        self.assertEqual(expression({'round':[{'value':1.235},{'value':2}]},{},{}).value,Decimal('1.24'))

    def test_encoded_json_closers_repair_preserves_computation(self):
        encoded='[{"id":"v","op":"cell","table":"t1","row":2,"column":"B"}, {"id":"a","op":"calculate","expr":{"mul":[{"ref":"v"},100]}]'
        raw=json.dumps({'steps':encoded,'output':{'step':'a'}})
        changes=[];p=parse_plan(raw,changes)
        p,_=normalize_plan(p,[region({(2,2):7})])
        self.assertEqual(execute(p,[region({(2,2):7})])['answer'],'700')
        self.assertEqual(changes[0]['edits'],1)
        self.assertEqual(repair_containers('{"label":"braces } ] stay intact"}')[1],0)
        for malformed in ['[{"id":"unfinished"', '[{"id":', '{}'+('}'*8)]:
            with self.assertRaises(ValueError):repair_containers(malformed)


if __name__=='__main__': unittest.main()
