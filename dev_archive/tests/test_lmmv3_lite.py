"""Baseline tests with unseen synthetic values; no live API or reference answers."""
import json
import tempfile
import unittest
from pathlib import Path
import openpyxl
from src.lmmv3.lite import answer,context,bounded_payload,provider_schema,VERSION
from src.workbook_index import load_regions


class Client:
    prompt_cap=.001;completion_cap=.001
    def __init__(self,replies): self.replies=list(replies);self.purposes=[];self.payloads=[]
    def complete(self,messages,ledger,purpose):
        self.purposes.append(purpose);self.payloads.append(json.loads(messages[1]['content']))
        call=ledger.reserve(messages,300)
        call.update(prompt_tokens=10,completion_tokens=10,total_tokens=20,actual_cost_usd=0,
                    budget_charge_usd=0,estimated_cost_usd=0,status='completed')
        assert self.replies, 'Unexpected extra model call'
        reply=self.replies.pop(0)
        return json.dumps(reply) if isinstance(reply,dict) else reply


def plan(column='B'):
    return {'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':4},
                     {'id':'sum','op':'aggregate','input':'r','metric':'sum','expr':{'col':column}}],
            'output':{'step':'sum','decimals':2}}


class LiteTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'new.xlsx'
        book=openpyxl.Workbook();sheet=book.active;sheet.title='Ventes'
        sheet.append(['Code','Montant']);sheet.append(['001',17]);sheet.append(['002',23]);sheet.append(['003',41])
        book.save(self.path);book.close()

    def test_one_call_computes_without_specification_or_review(self):
        record={};client=Client([plan()])
        self.assertEqual(answer(self.path,'Quel est le total ? Deux décimales.',client,record,{}),'81.00')
        self.assertEqual(client.purposes,['v3_lite_plan'])
        self.assertEqual(record['verification_level'],'tool_execution_only')
        self.assertEqual(record['pipeline_version'],VERSION)
        self.assertIn('Ventes!B4',record['evidence'])
        self.assertNotIn('question_spec',record)

    def test_one_concrete_repair_reuses_data_without_history_growth(self):
        client=Client([plan('MISSING'),plan()]);record={}
        self.assertEqual(answer(self.path,'Total?',client,record,{}),'81.00')
        self.assertEqual(len(client.purposes),2)
        self.assertIn('error',client.payloads[1]['feedback'])
        self.assertNotIn('observations',client.payloads[1])
        self.assertEqual(len(record['validation_events']),1)

    def test_repeated_bad_plan_stops_within_two_calls(self):
        client=Client([plan('MISSING'),plan('MISSING')]);record={}
        self.assertEqual(answer(self.path,'Total?',client,record,{}),'')
        self.assertEqual(len(client.purposes),2);self.assertEqual(record['status'],'unanswered')
        self.assertNotIn('failure_event',record)

    def test_optional_inspection_has_one_followup_not_an_extra_review(self):
        client=Client([{'action':'inspect','requests':[{'op':'read_range','table':'t1','range':'A1:B4'}]},plan()]);record={}
        self.assertEqual(answer(self.path,'Total?',client,record,{}),'81.00')
        self.assertEqual(len(client.purposes),2)
        self.assertTrue(client.payloads[1]['feedback']['inspection'])

    def test_compound_output_uses_plan_format_and_preserves_identifier(self):
        request={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':2}],
                 'output':{'step':'r','columns':['A','B'],'separator':', ','decimals':0}}
        self.assertEqual(answer(self.path,'Return code, amount',Client([request]),{},{}),'001, 17')

    def test_context_excludes_duplicate_coordinate_snapshots(self):
        book=openpyxl.load_workbook(self.path);sheet=book.active;sheet['A7']='Notes';book.save(self.path);book.close()
        data=context(load_regions(self.path),'Total?',limit=16000)
        self.assertEqual(len(data['tables']),1)
        self.assertNotIn('original_cells',json.dumps(data))
        self.assertLessEqual(len(json.dumps(data,ensure_ascii=False)),16000)

    def test_payload_cap_includes_repair_and_does_not_truncate_question(self):
        question='Quel total ?';data=context(load_regions(self.path),question)
        payload=bounded_payload(question,data,{'error':'bad','previous_plan':'x'*15000},16000)
        self.assertLessEqual(len(json.dumps(payload,ensure_ascii=False)),16000)
        self.assertEqual(payload['question'],question)

    def test_division_by_zero_never_becomes_an_answer(self):
        bad={'steps':[{'id':'v','op':'cell','table':'t1','row':2,'column':'B'},
                      {'id':'bad','op':'calculate','expr':{'div':[{'ref':'v'},{'value':0}]}}], 'output':{'step':'bad'}}
        record={};self.assertEqual(answer(self.path,'Ratio?',Client([bad,bad]),record,{}),'')
        self.assertFalse(record['validated'])

    def test_schema_is_small_and_previous_variants_keep_their_schema(self):
        from src.planner import tool_schema
        self.assertLess(len(json.dumps(provider_schema())),len(json.dumps(tool_schema('plan'))))
        self.assertIn('answer_spec',tool_schema('plan')['anyOf'][0]['properties'])


if __name__=='__main__': unittest.main()
