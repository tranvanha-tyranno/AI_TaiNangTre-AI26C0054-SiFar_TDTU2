import unittest
from src.diagnostics import diagnose, summarize, identity, history


class DiagnosticsTest(unittest.TestCase):
    def test_mismatch_does_not_invent_model_or_retrieval_error(self):
        result=diagnose({'status':'ok','match':False,'answer':'wrong','reference':'right'})
        self.assertEqual([i['phase'] for i in result['issues']],['unknown'])
        self.assertFalse(result['root_cause_confirmed'])

    def test_multiple_observed_errors_and_recovery(self):
        row={'dataset':'a','status':'ok','match':False,'answer':'x','reference':'y',
             'validation_errors':['Plan requires 1..25 steps','Question requires exactly two decimals']}
        row['diagnostics']=diagnose(row)
        self.assertEqual(row['diagnostics']['recovered_count'],2)
        self.assertEqual(row['diagnostics']['active_count'],1)
        self.assertEqual({b['phase'] for b in summarize([row])},{'llm','format','unknown'})

    def test_executor_type_failure_does_not_prove_tool_bug(self):
        issue=diagnose({'status':'error','validation_errors':['Expected a number, got NoneType']})['issues'][0]
        self.assertEqual(issue['phase'],'tool')
        self.assertEqual(issue['root_cause'],'unconfirmed')
        self.assertIn('llm',issue['candidate_phases'])

    def test_numeric_equivalence_requires_numeric_question(self):
        row={'status':'ok','match':False,'answer':'3.1','reference':'3.10','query':'Answer with only the number'}
        self.assertEqual(diagnose(row)['issues'][0]['code'],'numeric_representation')
        row['query']='What is the identifier?'
        self.assertEqual(diagnose(row)['issues'][0]['phase'],'unknown')

    def test_history_isolates_datasets_and_reference_changes(self):
        entries=[]
        for run,ds,ref,match in [('r1','a','yes',False),('r2','b','yes',True),('r3','a','yes',True),('r4','a','no',False)]:
            row={'dataset':ds,'source_file':'same.xlsx','query':'same question','reference':ref,'status':'ok','match':match,'diagnostics':{'issues':[]}}
            entries.append({'run':run,'row':row,'timestamp':len(entries)})
        result=history(entries)
        seq=result[(identity(entries[0]['row']),'yes')]
        self.assertEqual([e['transition'] for e in seq],['first_observation','improved'])
        changed=result[(identity(entries[3]['row']),'no')]
        self.assertEqual(changed[0]['transition'],'first_observation')

    def test_duplicate_events_not_counted_as_multiple_questions(self):
        row={'status':'error','validation_errors':['Plan requires 1..25 steps']*3}
        row['diagnostics']=diagnose(row)
        self.assertEqual(summarize([row])[0]['questions'],1)
