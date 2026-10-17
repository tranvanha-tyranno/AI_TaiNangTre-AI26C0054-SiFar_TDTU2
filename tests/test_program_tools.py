import json
from pathlib import Path
import unittest

from src.program_executor import execute_program, format_result, num, dt, percentile
from src.program_pipeline import answer_with_program, use_program, check_format, repair_header_reads, execute_with_header_repairs
from src.tools.executor import PlanError
from src.workbook_index import Region


def fixtures():
    rows = {(1,1):'Code', (1,2):'Amount', (1,3):'Time'}
    for i in range(2,603):
        rows.update({(i,1):f'X{i:04d}', (i,2):i, (i,3):'2031-04-01T00:15:00Z'})
    return [Region('t1','Observations',1,602,1,3,rows,[],[],[1]),
            Region('t2','Tariffs',1,3,1,4,
                {(1,1):'Code',(1,2):'Start',(1,3):'End',(1,4):'Rate',
                 (2,1):'X0602',(2,2):'2031-01-01',(2,3):'2031-04-01',(2,4):2,
                 (3,1):'X0602',(3,2):'2031-04-01',(3,3):'2031-07-01',(3,4):7},[],[],[1]),
            Region('t3','Lookup',1,2,1,2,{(1,1):'Code',(1,2):'Name',(2,1):'X0602',(2,2):'Orchid'},[],[],[1])]


class ProgramExecutorTest(unittest.TestCase):
    def test_complete_scan_and_effective_date_join(self):
        code = """rows=read('t1',2)
selected=[r for r in rows if r['A']=='X0602'][0]
moment=dt(selected['C'])
tariffs=read('t2',2)
active=[r for r in tariffs if r['A']==selected['A'] and dt(r['B'])<=moment<dt(r['C'])]
assert len(active)==1
result=num(selected['B'])*num(active[0]['D'])
"""
        execution=execute_program(code,fixtures())
        self.assertEqual(format_result(execution,2),'4214.00')
        self.assertEqual(execution['reads'][0]['end_row'],602)

    def test_group_counter_and_label_are_data_dependent(self):
        code="""rows=read('t1',2)
count=0
for r in rows:
    if num(r['B'])>600:
        count+=1
result=['matched' if count else 'none',count]
"""
        self.assertEqual(format_result(execute_program(code,fixtures())), 'matched, 2')

    def test_ignored_unpacking_names_and_decimal_rounding_are_safe(self):
        code="rows=read('t1',2); result=sum(num(r['B']) for _,r in enumerate(rows)).to_integral_value()"
        self.assertEqual(format_result(execute_program(code,fixtures())),'181502')

    def test_group_dictionary_mutation_retains_data_dependency(self):
        code="""rows=read('t1',2)
groups=defaultdict(list)
for r in rows:
    groups[r['A']].append(num(r['B']))
means={}
for key,values in groups.items():
    means[key]=sum(values)/len(values)
result=sorted(means,key=lambda k:(-means[k],k))[0]
"""
        self.assertEqual(format_result(execute_program(code,fixtures())),'X0602')

    def test_metadata_aliases_work_but_unknown_fields_fail_closed(self):
        self.assertEqual(format_result(execute_program("rows=read('t1'); result=sum(1 for r in rows if r.get('row')>600)",fixtures())),'2')
        with self.assertRaisesRegex(PlanError,'Unknown row field'):
            execute_program("rows=read('t1'); result=sum(r.get('unobserved',0) for r in rows)",fixtures())

    def test_record_reader_preserves_text_lookup_rows_and_reports_selections(self):
        regions=fixtures()
        regions[2].header_rows=[1,2]
        result=execute_program("rows=data('t3'); selected=[r for r in rows if r['A']=='X0602']; result=selected[0]['B']",regions)
        self.assertEqual(format_result(result),'Orchid')
        self.assertEqual(next(v for v in result['variables'] if v['name']=='selected')['count'],1)
        self.assertEqual(result['reads'][0]['data_rows'],1)

    def test_lookup_audit_exposes_different_key_representations(self):
        code="rows=data('t1'); lookup={dt(r['C']).date().isoformat():r['B'] for r in rows}; result=lookup.get(str(dt(rows[0]['C'])),0)"
        result=execute_program(code,fixtures())
        audit=result['lookup_audit'][0]
        self.assertEqual((audit['matched'],audit['missing']),(0,1))
        self.assertIn('00:15',audit['missing_key_samples'][0])
        self.assertEqual(audit['mapping_key_samples'],['2031-04-01'])

    def test_date_header_repair_only_changes_proven_unbounded_reads(self):
        regions=fixtures()
        code="rows=read('t2'); dates=[dt(r['B']) for r in rows]; result=len(dates)"
        try:execute_program(code,regions)
        except PlanError as error:fixed,changes=repair_header_reads(code,regions,error)
        self.assertEqual(changes,[{'kind':'exclude_proven_date_header','table':'t2'}])
        self.assertEqual(format_result(execute_program(fixed,regions)),'2')

    def test_multiple_proven_headers_are_repaired_before_another_api_call(self):
        plan={'code':"a=[dt(r['B']) for r in read('t2')]; b=[dt(r['C']) for r in read('t1')]; result=len(a)+len(b)",'decimals':None}
        fixed,execution,changes=execute_with_header_repairs(plan,fixtures())
        self.assertEqual(format_result(execution),'603')
        self.assertEqual(format_result(execution),'603')

    def test_unbounded_read_is_normalized_to_data_before_execution(self):
        plan={'code':"rows=read('t2'); result=len(rows)",'decimals':0}
        fixed,execution,changes=execute_with_header_repairs(plan,fixtures())
        self.assertEqual(format_result(execution),'2')
        self.assertIn('data(',fixed['code'])

    def test_literal_answer_cannot_be_grounded_by_unused_read(self):
        with self.assertRaisesRegex(PlanError,'disconnected'):
            execute_program("rows=read('t1'); result=999",fixtures())

    def test_prohibited_capabilities_and_unbounded_work(self):
        for code in ("import os\nresult=1", "result=open('x')", "result=read.__globals__",
                     "rows=read('t1'); result=[0]*1000000000",
                     "rows=read('t1'); result=list(range(1000000000))"):
            with self.subTest(code=code), self.assertRaises((PlanError,NameError)):
                execute_program(code,fixtures())
        with self.assertRaisesRegex(PlanError,'execution limit'):
            execute_program("rows=read('t1'); result=0\nwhile True:\n result+=1",fixtures(),seconds=.02)

    def test_mutation_never_updates_workbook_cells(self):
        regions=fixtures()
        self.assertEqual(format_result(execute_program("r=read('t1',2); r[0]['B']=41; result=r[0]['B']",regions)),'41')
        self.assertEqual(regions[0].cells[(2,2)],2)

    def test_numeric_and_time_parsing(self):
        self.assertEqual(num('1.234,50'),num('1,234.50'))
        self.assertIsNone(num('ND'))
        self.assertEqual(dt('2031-04-01T07:15:00+07:00'),dt('2031-04-01T00:15:00Z'))
        self.assertEqual(dt('2031-04-01T00:15:00Z').minute,15)

    def test_half_up_rounding_matches_final_formatter(self):
        for expr in ("round(num(rows[0]['B'])/16,2)",
                     "(num(rows[0]['B'])/16).quantize(Decimal('0.01'))"):
            # 2/16 = .125: exercise the exact halfway case with different data.
            self.assertEqual(format_result(execute_program("rows=read('t1',2); result="+expr,fixtures()),2),'0.13')

    def test_percentile_methods_are_distinct_and_must_be_explicit(self):
        self.assertEqual(percentile([3,6,12,20],75,'nearest_rank'),12)
        self.assertEqual(percentile([3,6,12,20],75,'linear'),14)
        with self.assertRaises(PlanError):percentile([3,6],75,'guess')
        value=execute_program("import statistics as st\nrows=data('t1'); result=st.median([num(r['B']) for r in rows])",fixtures())
        self.assertEqual(format_result(value),'302')

    def test_helper_import_declarations_do_not_open_import_capability(self):
        code="from decimal import Decimal as D\nrows=read('t1',2); result=sum(D(str(r['B'])) for r in rows)"
        self.assertEqual(format_result(execute_program(code,fixtures())),'181502')
        with self.assertRaises(PlanError):
            execute_program("from pathlib import Path\nresult=1",fixtures())

    def test_preformatted_list_is_valid_and_does_not_lose_rank_order(self):
        execution=execute_program("rows=read('t1',2); result=', '.join(r['A'] for r in rows[-3:])",fixtures())
        check_format('List three codes',{'kind':'list','count':3},execution,
                     format_result(execution),{'decimals':None})
        self.assertEqual(format_result(execution),'X0600, X0601, X0602')

    def test_scalar_winner_cannot_be_replaced_by_number_of_input_columns(self):
        execution=execute_program("rows=read('t1',2); result=[r['A'] for r in rows[-8:]]",fixtures())
        with self.assertRaisesRegex(PlanError,'requires 1 output fields'):
            check_format('Which entity has the highest eight-column mean?',
                         {'kind':'scalar','count':1},execution,format_result(execution),{'decimals':None})

    def test_date_keys_and_zero_padding_use_safe_methods(self):
        execution=execute_program("rows=read('t1',2); result=[dt(rows[0]['C']).strftime('%Y-%m-%d'),str(rows[0]['B']).zfill(4)]",fixtures())
        self.assertEqual(format_result(execution),'2031-04-01, 0002')

    def test_structural_dispatch_has_no_dataset_identity(self):
        self.assertTrue(use_program(fixtures()))
        self.assertFalse(use_program(fixtures()[:1]))

    def test_review_revision_is_never_promoted(self):
        class Client:
            prompt_cap=.001
            completion_cap=.001
            def __init__(self): self.calls=[]
            def complete(self,messages,ledger,purpose):
                self.calls.append((purpose,ledger))
                ledger.reserve(messages,50).update(status='completed',actual_cost_usd=0,budget_charge_usd=0)
                if purpose=='review':
                    return json.dumps({'verdict':'revise','issues':['Wrong filter for requested scope']})
                return json.dumps({'code':"rows=read('t1',2); result=len(rows)",'decimals':None})
        record={};client=Client()
        with self.assertRaises(PlanError):
            answer_with_program(fixtures(),'Count eligible records',client,record,{'max_plan_repairs':1,'max_api_calls':4})
        self.assertFalse(record['validated'])
        self.assertEqual([c[0] for c in client.calls],['plan','review','repair','review'])
        self.assertEqual(len({id(c[1]) for c in client.calls}),1)


if __name__=='__main__': unittest.main()
