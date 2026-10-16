import json
from pathlib import Path
import unittest
from unittest.mock import patch
from src.answer_contract import infer_answer_contract
from src.llmv4 import infer_contract, validate_contract, regions_v4, VERSION
from src.pipeline import answer_with_tools
from src.tools.executor import execute, PlanError
from src.variants import settings_for_mode
from src.workbook_index import Region


class Client:
    prompt_cap = .001
    completion_cap = .001

    def __init__(self, plan):
        self.plan = plan
        self.calls = []

    def complete(self, messages, ledger, purpose):
        self.calls.append((purpose,messages))
        return json.dumps({'verdict':'accept','issues':[]}) if purpose=='review' else self.plan


class V4Test(unittest.TestCase):
    def test_year_is_not_sum_of_filter_metric(self):
        question = 'Xác định năm mà tổng số hồ sơ dưới 100. Chỉ trả lời năm.'
        self.assertEqual(infer_answer_contract(question)['reduction'],'sum')
        c = infer_contract(question)
        self.assertIsNone(c['reduction'])
        self.assertEqual(c['answer_field'],'year')
        self.assertIsNone(infer_contract('Nhóm nào có tỷ lệ trung bình cao nhất? Chỉ trả lời tên nhóm.')['reduction'])

    def test_tuple_takes_precedence_and_formats_only_numeric_fields(self):
        q = 'Nhóm nào có tổng lớn nhất? Trả lời dạng `nhóm, giá trị`, đúng một chữ số thập phân.'
        c = infer_contract(q)
        self.assertEqual((c['kind'],c['count'],c['numeric_positions']),('tuple',2,[1]))
        plan = {'steps':[{'id':'a','op':'cell'}],'output':{'step':'a'}}
        good = {'value_count':2,'values':['Site 07','2.0'],'answer':'Site 07, 2.0'}
        validate_contract(c,plan,good,q)
        with self.assertRaises(PlanError):
            validate_contract(c,plan,{**good,'values':['Site 07','2']},q)
        with self.assertRaises(PlanError):
            validate_contract(c,plan,{**good,'value_count':1},q)

    def test_boolean_output_languages(self):
        for pair in ['Có/Không','Oui ou Non','是或否','はいまたはいいえ','네/아니요','Yes or No']:
            with self.subTest(pair=pair):
                self.assertTrue(infer_contract('Answer: '+pair)['yes_no'])
        self.assertFalse(infer_contract('Có bao nhiêu hồ sơ còn thiếu? Chỉ trả lời số nguyên.')['yes_no'])

    def region(self):
        cells={(1,1):'Power (megawatts)',(1,2):'Power (megawatts)',(1,3):'Power (megawatts)',
               (2,1):'Sensor',(2,2):'Power',(2,3):'Hours',
               (3,1):'North',(3,2):'North',(3,3):'North',(4,1):'x',(4,2):4,(4,3):3,
               (5,1):'South',(5,2):'South',(5,3):'South',(6,1):'y',(6,2):8,(6,3):2}
        return Region('t1','Measurements',1,6,1,3,cells,[],['A1:C1','A3:C3','A5:C5'],[1,2,3])

    def test_merged_groups_preserve_anchor_and_baseline(self):
        original=self.region();new=regions_v4([original])[0]
        self.assertEqual([s['label'] for s in new.section_labels()],['North','South'])
        self.assertEqual(original.header_rows,[1,2,3])
        self.assertEqual(original.section_labels(),[])
        plan={'steps':[{'id':'r','op':'read','table':'t1','start_row':6,'end_row':6}],
              'output':{'step':'r','columns':['_section']}}
        result=execute(plan,[new])
        self.assertEqual(result['answer'],'South')
        self.assertIn('Measurements!A5',result['evidence'])
        self.assertIn('megawatts',json.dumps(new.preview('power')['document_context']))
        self.assertEqual(new.cells,original.cells)

    def test_year_question_executes_and_boolean_localizes_without_extra_calls(self):
        region=Region('t1','Data',1,3,1,2,{(1,1):'Year',(1,2):'Cases',(2,1):2030,(2,2):5,(3,1):2031,(3,2):8},[],[],[1])
        cases=[('Xác định năm mà tổng số là 5. Chỉ trả lời năm.',
                {'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':2}],
                 'output':{'step':'r','columns':['A']},'answer_spec':{'answer_type':'number','answer_field':'Năm','operation':'lookup'}},'2030'),
               ('Ô B2 nhỏ hơn B3? Chỉ trả lời Có hoặc Không.',
                {'steps':[{'id':'a','op':'cell','table':'t1','row':2,'column':'B'},
                          {'id':'b','op':'cell','table':'t1','row':3,'column':'B'},
                          {'id':'c','op':'calculate','expr':{'lt':[{'ref':'a'},{'ref':'b'}]}}],
                 'output':{'step':'c'},'answer_spec':{'answer_type':'boolean','answer_field':'boolean','operation':'other'}},'Có')]
        with patch('src.pipeline.load_regions',return_value=[region]):
            for question,plan,expected in cases:
                client=Client(json.dumps(plan));record={}
                answer=answer_with_tools(Path('unused.xlsx'),question,client,record,settings_for_mode({},'llm-v4'))
                self.assertEqual(answer,expected)
                self.assertEqual(record['pipeline_version'],VERSION)
                self.assertEqual(len(client.calls),2)
                self.assertIn('output contract',client.calls[0][1][0]['content'])

    def test_repeated_invalid_response_stops_after_two_attempts(self):
        client=Client('{bad-json');record={}
        with patch('src.pipeline.load_regions',return_value=[self.region()]):
            with self.assertRaisesRegex(PlanError,'Identical'):
                answer_with_tools(Path('unused.xlsx'),'Inspect the chosen sensor.',client,record,settings_for_mode({},'llm-v4'))
        self.assertEqual(len(client.calls),2)
        self.assertIn('retry_stop_reason',record)
        self.assertEqual(len(record['validation_events']),2)

    def test_opt_in_settings_leave_v3_unchanged(self):
        source={'max_workbook_cells':200000}
        v4=settings_for_mode(source,'llm-v4')
        self.assertTrue(v4['v4_upgrade'])
        self.assertEqual(v4['max_workbook_cells'],200000)
        self.assertNotIn('v4_upgrade',settings_for_mode(v4,'llm-v3'))
        self.assertEqual(source,{'max_workbook_cells':200000})


if __name__=='__main__':unittest.main()
