import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import dashboard
from src.dashboard_analysis import decorate,summarize,compare_states,safe_context


def row(ident,answer,reference='42',dataset='public',**extra):
    return decorate({'id':ident,'query':'Question','file_name':'a.xlsx','dataset':dataset,
        'answer':answer,'reference':reference,'match':answer==reference,'status':'ok',**extra})


class DashboardAnalyticsTest(unittest.TestCase):
    def test_api_error_is_not_an_answer_mismatch_or_solver_regression(self):
        original=row('x','42')
        failed=row('x','',status='error',usage={'calls':[{'status':'error','http_status':402}]})
        current={'selected':'new','dataset':'public','rows':[failed]}
        before={'selected':'old','dataset':'public','rows':[original]}
        analysis=summarize(current['rows'])
        self.assertEqual(analysis['outcomes'],{'api_error':1})
        self.assertEqual(analysis['api_errors'],1)
        comparison=compare_states(before,current)
        self.assertEqual(comparison['counts'],{'api_error':1})

    def test_compare_matches_original_ids_across_single_and_multi_dataset(self):
        previous={'selected':'old','dataset':'public,example','rows':[row('example::1','bad',dataset='example',original_id=1)]}
        current={'selected':'new','dataset':'example','rows':[row(1,'42',dataset='example',original_id=1)]}
        comparison=compare_states(previous,current)
        self.assertEqual(comparison['counts'],{'improved':1})
        self.assertEqual(comparison['comparable'],1)

    def test_changed_reference_and_pending_rows_are_not_improvements(self):
        previous={'selected':'old','dataset':'public','rows':[row('a','bad'),row('b','bad')]}
        current={'selected':'new','dataset':'public','rows':[row('a','bad',reference='bad'),row('b','',status='pending',match=None)]}
        result=compare_states(previous,current)
        self.assertEqual(result['excluded_changed_reference_or_question'],1)
        self.assertEqual(result['counts'],{'pending':1})

    def test_repaired_plan_remains_green_but_issue_is_counted(self):
        question=row('x','42',plans=[{'attempt':1},{'attempt':2}],validation_errors=['Answer contract requires 1 final value, got 8.'])
        self.assertEqual(question['outcome'],'match')
        analysis=summarize([question])
        self.assertEqual(analysis['repaired_questions'],1)
        self.assertEqual(analysis['issues'],{'answer_shape':1})

    def test_context_export_has_only_safe_settings(self):
        context=safe_context({'git_revision':'a','source_sha256':{'main.py':'hash'},
            'api_key':'secret','settings':{'max_api_calls':4,'OPENROUTER_API_KEY':'secret'}})
        self.assertNotIn('secret',json.dumps(context))
        self.assertEqual(context['settings'],{'max_api_calls':4})

    def test_large_workbook_page_keeps_original_coordinates_and_tail(self):
        result=dashboard.workbook('data.xlsx','Big','12_large_full_scan',2401,31)
        self.assertEqual(result['columns'],['AE','AF','AG','AH','AI'])
        self.assertEqual(result['start_row'],2401)
        self.assertEqual(result['end_row'],2501)
        self.assertEqual(result['rows'][-1][-1],'32507')
        self.assertLessEqual(len(result['rows']),200)
        for r,c in [(0,1),(1,0),(999999,1),(1,999999)]:
            with self.assertRaises(ValueError): dashboard.workbook('data.xlsx','Big','12_large_full_scan',r,c)

    def test_history_cache_invalidates_after_record_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'metadata.json').write_text(json.dumps({'ids':['x'],'reference':{'x':'42'},'dataset':'public'}),encoding='utf-8')
            log=p/'questions.jsonl'
            log.write_text(json.dumps({'id':'x','answer':'bad','status':'ok'}),encoding='utf-8')
            before=dashboard.run_card('test',p)
            log.write_text(json.dumps({'id':'x','answer':'42','status':'ok','elapsed_seconds':3}),encoding='utf-8')
            after=dashboard.run_card('test',p)
            self.assertEqual(before['matched'],0)
            self.assertEqual(after['matched'],1)

    def test_history_order_uses_run_time_not_recent_report_write(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            newer=base/'runs/20261014-170000-abc'
            older=base/'runs/20261014-160000-def'
            for folder in [newer,older]:
                folder.mkdir(parents=True)
                (folder/'metadata.json').write_text('{}',encoding='utf-8')
            os.utime(older,(2000000000,2000000000))
            with patch.object(dashboard,'OUTPUTS',base):
                self.assertEqual(list(dashboard.run_dirs()),[newer.name,older.name])

    def test_report_endpoint_omits_csrf_and_credentials(self):
        state={'selected':'run','dataset':'public','rows':[],'summary':{},'analysis':{},'context':{},'csrf':'token','config':{'api_key':'secret'}}
        server=dashboard.ThreadingHTTPServer(('127.0.0.1',0),dashboard.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with patch.object(dashboard,'build_state',return_value=state):
                result=json.load(urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/report?run=run'))
            self.assertNotIn('csrf',result)
            self.assertNotIn('secret',json.dumps(result))
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)


if __name__=='__main__': unittest.main()
