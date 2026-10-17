import copy
import unittest
from src.read_scope import profiles, validate_read_scope, validate_group_identity
from src.tools.executor import execute, PlanError
from src.workbook_index import Region
from src.planner import tool_schema


def count_plan(start, end):
    return {'steps':[{'id':'r','op':'read','table':'t1','start_row':start,'end_row':end},
                     {'id':'n','op':'aggregate','input':'r','metric':'count'}],
            'output':{'step':'n'}}


class ReadScopeTest(unittest.TestCase):
    def codes(self):
        cells={(1,1):'Industry',(1,2):'Registry code',(1,3):'Rate'}
        for row in range(2,83): cells.update({(row,1):f'Branch {row}',(row,2):str(140000+row),(row,3):row%13})
        return Region('t1','Renamed',1,82,1,3,cells,[],[],[1])

    def years(self):
        cells={(1,1):'Index series',(2,2):'Year',(2,3):'Metric'}
        for row in range(3,13): cells.update({(row,2):1990+row,(row,3):row*2})
        cells.update({(14,2):'2004 Q1',(14,3):9,(15,2):'Q2',(15,3):12})
        return Region('t1','AnotherSheet',1,15,1,3,cells,[],[],[1,2])

    def test_profile_retains_real_bounds_not_preview_size(self):
        p=profiles(self.codes())
        self.assertEqual(p['identifier_profiles'],[{'column':'B','digits':6,'start_row':2,'end_row':82,'observations':81}])
        self.assertEqual(p['year_axis_profiles'],[])

    def test_partial_digit_code_scan_rejected_without_changing_plan(self):
        plan=count_plan(2,30); before=copy.deepcopy(plan)
        with self.assertRaisesRegex(PlanError,'Incomplete read scope'):
            validate_read_scope('How many branches with a 6-digit code exceed a rate?',plan,[self.codes()])
        self.assertEqual(plan,before)
        validate_read_scope('How many branches with a 6-digit code exceed a rate?',count_plan(2,82),[self.codes()])

    def test_annual_block_detected_in_second_column_and_quarters_excluded(self):
        p=profiles(self.years())
        self.assertEqual(p['year_axis_profiles'][0]['end_row'],12)
        with self.assertRaisesRegex(PlanError,'omitted annual'):
            validate_read_scope('Using annual rows labelled with a year, in how many years was X higher?',count_plan(3,9),[self.years()])
        validate_read_scope('Using annual rows labelled with a year, in how many years was X higher?',count_plan(3,12),[self.years()])

    def test_explicit_time_or_row_scope_does_not_require_full_scan(self):
        validate_read_scope('Using annual rows, how many years from 1993 to 1995?',count_plan(3,5),[self.years()])
        validate_read_scope('How many 6-digit codes in rows 2 to 10?',count_plan(2,10),[self.codes()])

    def test_multiple_reads_cover_same_sheet_without_false_missing_rows(self):
        p=count_plan(2,40);p['steps']=[p['steps'][0],{'id':'r2','op':'read','table':'t1','start_row':41,'end_row':82},
            {'id':'all','op':'concat','inputs':['r','r2']},{'id':'n','op':'aggregate','input':'all','metric':'count'}]
        validate_read_scope('How many 6-digit codes?',p,[self.codes()])

    def test_record_explicit_input_preserves_selected_row_provenance(self):
        p={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':82},
                    {'id':'s','op':'sort','input':'r','by':[{'column':'C','descending':True}]},
                    {'id':'t','op':'take','input':'s','limit':1},
                    {'id':'out','op':'record','input':'t','fields':{'name':{'col':'A'},'code':{'col':'B'}}}],
           'output':{'step':'out','columns':['name','code']}}
        result=execute(p,[self.codes()])
        self.assertEqual(result['answer'],'Branch 12, 140012')
        self.assertEqual(result['value_sources'][0],['Renamed!A12'])
        del p['steps'][-1]['input']
        with self.assertRaisesRegex(PlanError,'Unknown column'): execute(p,[self.codes()])

    def test_record_input_is_explicit_in_provider_schema(self):
        schema=tool_schema();plan=schema['anyOf'][0]
        record=next(v for v in plan['properties']['steps']['items']['anyOf'] if v['properties']['op']['enum']==['record'])
        self.assertIn('input',record['properties']);self.assertNotIn('input',record['required'])

    def test_scalar_record_and_untrusted_literal_guards_preserved(self):
        p={'steps':[{'id':'v','op':'cell','table':'t1','row':2,'column':'C'},
                    {'id':'out','op':'record','fields':{'value':{'ref':'v'}}}],
           'output':{'step':'out','columns':['value']}}
        self.assertEqual(execute(p,[self.codes()])['answer'],'2')
        p['steps'][-1]['fields']={'name':{'value':'invented result'}}
        with self.assertRaisesRegex(PlanError,'depend on spreadsheet'): execute(p,[self.codes()])

    def test_group_identity_uses_observed_headings_not_reference_answers(self):
        r=Region('t1','Novel',1,4,1,2,{(1,1):'Alpha',(2,1):'Task',(2,2):2,
            (3,1):'Beta',(4,1):'Task',(4,2):4},[],[],[])
        q='Among Alpha and Beta which is highest? Answer with only the group name.'
        with self.assertRaisesRegex(PlanError,'group-name identity'):
            validate_group_identity(q,{'output':{}},{'values':['Task']},[r])
        validate_group_identity(q,{'output':{}},{'values':['Beta']},[r])
        # A question asking for the detail name should not trigger group validation.
        validate_group_identity('Which task?',{'output':{}},{'values':['Task']},[r])

    def test_review_length_normalization_preserves_revocation(self):
        from src.review_validation import bounded_review
        for verdict in ['revise','accept']:
            review,changes=bounded_review({'verdict':verdict,'issues':['Wrong identity. '+('evidence '*80)]})
            self.assertEqual(review['verdict'],verdict);self.assertEqual(len(review['issues'][0]),300)
            self.assertTrue(changes)
        self.assertEqual(bounded_review({'verdict':'accept','issues':[]} ),({'verdict':'accept','issues':[]},[]))
        self.assertIsNone(bounded_review({'verdict':'revise','issues':[None]})[0])

    def test_sole_record_projection_has_one_unambiguous_output(self):
        from src.reliability import normalize
        p={'steps':[{'id':'r','op':'record','fields':{'amount':{'ref':'a'}}}], 'output':{'step':'r'}}
        fixed,changes=normalize(p)
        self.assertEqual(fixed['output']['columns'],['amount']);self.assertNotIn('columns',p['output'])
        self.assertEqual(changes[-1]['kind'],'sole_record_output_column')
        p['steps'][0]['fields']['other']={'ref':'b'}
        self.assertNotIn('columns',normalize(p)[0]['output'])

    def test_record_literal_can_only_be_an_observed_sheet_name(self):
        p={'steps':[{'id':'v','op':'cell','table':'t1','row':2,'column':'C'},
                    {'id':'out','op':'record','fields':{'sheet':{'value':'Renamed'},'value':{'ref':'v'}}}],
           'output':{'step':'out','columns':['sheet','value']}}
        self.assertEqual(execute(p,[self.codes()])['answer'],'Renamed, 2')
        p['steps'][-1]['fields']['sheet']={'value':'invented-sheet'}
        with self.assertRaisesRegex(PlanError,'depend on spreadsheet'): execute(p,[self.codes()])


if __name__=='__main__': unittest.main()
