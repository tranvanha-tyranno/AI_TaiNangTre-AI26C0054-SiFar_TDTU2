import json
import unittest
from unittest.mock import patch
from pathlib import Path
from src.variants import settings_for_mode,V3_BASELINE_VERSION
from src.pipeline import answer_with_tools
from src.workbook_index import Region


class BaselineTest(unittest.TestCase):
    def test_restarted_v3_uses_identical_v2_operational_settings(self):
        original={'max_api_calls':4,'max_plan_repairs':2,'preview_rows':45,'semantic_review':'risky'}
        v2=settings_for_mode(original,'llm-v2');v3=settings_for_mode(original,'llm-v3')
        self.assertEqual(v3.pop('v3_base_variant'),'llm-v2')
        self.assertEqual(v2,v3)
        self.assertEqual(original['max_api_calls'],4)

    def test_v2_and_restarted_v3_emit_the_same_requests_and_answer(self):
        region=Region('t1','Data',1,3,1,2,{(1,1):'Code',(1,2):'Charge',
            (2,1):'A',(2,2):7,(3,1):'B',(3,2):11},[],[],[1])
        plan={'steps':[{'id':'r','op':'read','table':'t1','start_row':2,'end_row':3},
                       {'id':'s','op':'aggregate','input':'r','metric':'sum','expr':{'col':'B'}}],
              'output':{'step':'s'},'answer_spec':{'answer_type':'number','answer_field':'Charge','operation':'sum'}}
        class Client:
            prompt_cap=.001;completion_cap=.001
            def __init__(self): self.calls=[]
            def complete(self,messages,ledger,purpose):
                self.calls.append((purpose,messages))
                return json.dumps({'verdict':'accept','issues':[]} if purpose=='review' else plan)
        answers=[];clients=[];records=[]
        with patch('src.pipeline.load_regions',return_value=[region]), \
             patch('src.lmmv3.lite.answer',side_effect=AssertionError('Lite is archived')), \
             patch('src.lmmv3.pipeline.answer',side_effect=AssertionError('Eight-phase pipeline is archived')):
            for mode in ('llm-v2','llm-v3'):
                client=Client();record={}
                answers.append(answer_with_tools(Path('unused.xlsx'),'What is the total Charge? Answer with only the number.',client,record,settings_for_mode({},mode)))
                clients.append(client);records.append(record)
        self.assertEqual(answers,['18','18'])
        self.assertEqual(clients[0].calls,clients[1].calls)
        self.assertEqual(records[1]['pipeline_version'],V3_BASELINE_VERSION)
        self.assertEqual(records[1]['baseline_variant'],'llm-v2')


if __name__=='__main__': unittest.main()
