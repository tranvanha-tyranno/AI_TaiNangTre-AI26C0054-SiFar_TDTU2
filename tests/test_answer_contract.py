import json
from pathlib import Path
import unittest
from src.answer_contract import infer_answer_contract,validate_answer_contract
from src.tools.executor import execute,PlanError
from src.workbook_index import load_regions,retrieve,Region
from src.pipeline import answer_with_tools

ROOT=Path(__file__).resolve().parents[1]


class AnswerContractTest(unittest.TestCase):
    def test_bilingual_scalar_rank_top_k_and_decimals(self):
        examples=[
            ('Tổng điểm của Engineering là bao nhiêu? Chỉ trả số nguyên.',1,'sum',None,None),
            ('Sort by Score. What is the ID at position 3 (1-based)? Answer only the ID.',1,None,2,None),
            ('List the IDs of the top 3 people. Separate IDs with comma and one space.',3,None,0,None),
            ('List the 3 Order IDs with lowest Revenue.',3,None,0,None),
            ('What is the average Score? Answer to exactly 2 decimal places.',1,'mean',None,2),
            ('Return two integers as Men, Women.',2,None,None,None),
            ('What is the highest score among the ten youngest people? Answer only the integer.',1,None,None,None),
            ('Which ID has the highest total Score? Answer only the ID.',1,None,None,None),
            ('What is the number of workers in "Total, 16 years and over"? Answer only the integer.',1,None,None,None),
            ('List all IDs with Flag Rare, separated by comma and one space.',None,None,None,None)]
        for q,count,reduction,offset,decimals in examples:
            with self.subTest(q=q):
                c=infer_answer_contract(q)
                self.assertEqual((c['count'],c['reduction'],c['rank_offset'],c['decimals']),
                                 (count,reduction,offset,decimals))

    def test_all_four_observed_bad_plans_are_rejected(self):
        folder=ROOT/'outputs/runs/20261014-170251-4f423d'
        if not folder.exists(): self.skipTest('Local experimental log is not packaged')
        records=[json.loads(line) for line in (folder/'questions.jsonl').read_text(encoding='utf-8').splitlines()]
        for r in records:
            if r['id'] not in {'06_q011','06_q019','06_q021','06_q023'}: continue
            selected,_=retrieve(load_regions(ROOT/'Test/06_people_filters/xlsx_files/data.xlsx'),r['query'])
            with self.subTest(id=r['id']),self.assertRaises(PlanError):
                result=execute(r['plan'],selected)
                validate_answer_contract(infer_answer_contract(r['query']),r['plan'],result)

    def test_singular_sum_does_not_accept_one_unreduced_input_row(self):
        region=Region('t1','Scores',1,2,1,2,{(1,1):'Dept',(1,2):'Score',(2,1):'Engineering',(2,2):10},[],[],[1])
        plan={'steps':[{'id':'r','op':'read','table':'t1','start_row':2}], 'output':{'step':'r','columns':['B']}}
        result=execute(plan,[region])
        with self.assertRaisesRegex(PlanError,'unreduced rows'):
            validate_answer_contract(infer_answer_contract('Tổng Score là bao nhiêu? Chỉ trả số nguyên.'),plan,result)
        plan['steps'].append({'id':'sum','op':'aggregate','input':'r','metric':'sum','expr':{'col':'B'}})
        plan['output']={'step':'sum'}
        validate_answer_contract(infer_answer_contract('Tổng Score là bao nhiêu? Chỉ trả số nguyên.'),plan,execute(plan,[region]))

    def test_output_limit_is_rejected_instead_of_ignored(self):
        region=Region('t1','Scores',1,2,1,1,{(1,1):10,(2,1):20},[],[],[])
        plan={'steps':[{'id':'r','op':'read','table':'t1'}], 'output':{'step':'r','columns':['A'],'limit':1}}
        with self.assertRaisesRegex(PlanError,'take STEP'): execute(plan,[region])

    def test_exact_cardinality_preserves_comma_inside_one_name(self):
        region=Region('t1','Names',1,1,1,1,{(1,1):"O'Neil, Jr."},[],[],[])
        plan={'steps':[{'id':'name','op':'cell','table':'t1','row':1,'column':'A'}], 'output':{'step':'name'}}
        result=execute(plan,[region])
        validate_answer_contract(infer_answer_contract('Answer only the name.'),plan,result)
        self.assertEqual(result['answer'],"O'Neil, Jr.")

    def test_two_integers_and_two_decimals_are_distinct_constraints(self):
        pair=infer_answer_contract('Return two integers as Men, Women.')
        self.assertTrue(pair['integer'])
        self.assertEqual(pair['count'],2)
        scalar=infer_answer_contract('Answer with two decimal places.')
        self.assertFalse(scalar['integer'])
        self.assertEqual(scalar['decimals'],2)
        self.assertNotEqual(scalar['count'],2)

    def test_wrong_rank_is_rejected_even_if_cardinality_is_one(self):
        region=Region('t1','Scores',1,3,1,1,{(1,1):10,(2,1):20,(3,1):30},[],[],[])
        plan={'steps':[{'id':'r','op':'read','table':'t1'},
                       {'id':'s','op':'sort','input':'r','by':[{'column':'A','descending':True}]},
                       {'id':'top','op':'take','input':'s','offset':0,'limit':1}],
              'output':{'step':'top','columns':['A']}}
        contract=infer_answer_contract('What is the value at position 3? Answer only the integer.')
        with self.assertRaisesRegex(PlanError,'offset=2'): validate_answer_contract(contract,plan,execute(plan,[region]))

    def test_missing_sum_is_repaired_using_question_contract(self):
        question='Tổng Score của những người thuộc Department Engineering và Status Active là bao nhiêu? Chỉ trả số nguyên.'
        class Client:
            prompt_cap=1;completion_cap=4;calls=0
            def complete(self,messages,ledger,purpose):
                self.calls+=1
                payload=json.loads(messages[1]['content'])
                if payload['answer_contract']['reduction']!='sum': raise AssertionError('Missing contract')
                steps=[{'id':'r','op':'read','table':'t1','start_row':3,'end_row':42},
                       {'id':'f','op':'filter','input':'r','where':{'and':[
                           {'eq':[{'col':'C'},{'value':'Engineering'}]},
                           {'eq':[{'col':'I'},{'value':'Active'}]}]}}]
                output={'step':'f','columns':['F']}
                if self.calls>1:
                    steps.append({'id':'s','op':'aggregate','input':'f','metric':'sum','expr':{'col':'F'}})
                    output={'step':'s'}
                return json.dumps({'steps':steps,'output':output})
        client=Client();record={}
        result=answer_with_tools(ROOT/'Test/06_people_filters/xlsx_files/data.xlsx',question,client,record,{})
        self.assertEqual(result,'560')
        self.assertEqual(client.calls,2)
        self.assertIn('do not list input cells',record['validation_errors'][0])

    def test_total_row_can_be_used_directly_after_double_count_repair(self):
        question='Calculate the total number of unpaid family workers across all age groups in the agricultural sector. What is the final sum? Answer with only the integer.'
        class Client:
            prompt_cap=1;completion_cap=4;calls=0
            def complete(self,messages,ledger,purpose):
                self.calls+=1
                if self.calls==1:
                    return json.dumps({'steps':[
                        {'id':'r','op':'read','table':'t1','start_row':7,'end_row':16},
                        {'id':'sum','op':'aggregate','input':'r','metric':'sum','expr':{'col':'E'}}],
                        'output':{'step':'sum'}})
                error=json.loads(messages[-1]['content'])['validation_error']
                if '!E7' not in error: raise AssertionError('Missing source coordinate in repair feedback')
                return json.dumps({'steps':[{'id':'total','op':'cell','table':'t1','row':7,'column':'E'}],
                                   'output':{'step':'total'}})
        client=Client();record={}
        queries=json.loads((ROOT/'Public_data_1/queries.json').read_text(encoding='utf-8'))
        filename=next(q['file_name'] for q in queries if q['id']=='p4_q012')
        result=answer_with_tools(ROOT/'Public_data_1/xlsx_files'/filename,question,client,record,{})
        self.assertEqual(result,'35')
        self.assertEqual(client.calls,1)
        self.assertEqual(record['answer_contract']['reduction'],'sum')


if __name__=='__main__': unittest.main()
