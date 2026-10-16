"""Verify lossless context packing, not answer matching on a public dataset."""
from copy import deepcopy
import json
import unittest
from src.context_dedup import prepare,views
from src.variants import settings_for_mode,v3_version,V3_BASELINE_VERSION


def preview(table,sheet='Sheet',start=1,end=30):
    return {'table_id':table,'sheet':sheet,'range':f'A{start}:C{end}','merged_ranges':['A1:C1'],
        'columns':['A','B','C'],'header_rows':[1],
        'rows':[{'row':r,'cells':{c:f'{c}-{r}-long-label-value-unchanged' for c in ['A','B','C']}}
                for r in range(start,end+1)]}


def messages(previews,observations=None):
    return [{'role':'system','content':'Original planning instructions.'},
            {'role':'user','content':json.dumps({'question':'Original question','retrieved_tables':previews,
                                               'inspection_results':observations or []},ensure_ascii=False)}]


def expand(payload):
    result=deepcopy(payload);index={v['view_id']:v for v in views(result) if 'view_id' in v}
    for view in views(result):
        for ref in view.pop('row_refs',[]):
            for row_id in ref['rows']:
                source=next(r for r in index[ref['view_id']]['rows'] if r['row']==row_id)
                view['rows'].append({'row':row_id,'cells':{col:source['cells'][col] for col in ref['columns']}})
        if 'row_order' in view:
            order=view.pop('row_order');view['rows'].sort(key=lambda r:order.index(r['row']))
        for row in view['rows']:
            for owner,columns in row.pop('cells_from',{}).items():
                source=next(r for r in index[owner]['rows'] if r['row']==row['row'])
                for column in columns: row['cells'][column]=source['cells'][column]
        view.pop('view_id',None)
    return result


class ContextDedupTest(unittest.TestCase):
    def test_overlap_is_lossless_and_smaller_without_changing_metadata(self):
        original=messages([preview('whole'),preview('child',start=5,end=25)])
        snapshot=deepcopy(original);packed,stats=prepare(original)
        self.assertTrue(stats['applied']);self.assertEqual(stats['duplicate_cells_removed'],63)
        self.assertLess(stats['request_chars_after'],stats['request_chars_before'])
        self.assertEqual(expand(json.loads(packed[1]['content'])),json.loads(original[1]['content']))
        self.assertEqual(original,snapshot)

    def test_different_sheet_and_different_values_are_never_merged(self):
        second=preview('other','Other sheet');changed=preview('changed')
        changed['rows'][9]['cells']['B']='different value with the same coordinate'
        original=messages([preview('whole'),second,changed]);packed,stats=prepare(original)
        self.assertTrue(stats['applied']);self.assertEqual(stats['duplicate_cells_removed'],89)
        self.assertEqual(stats['conflicting_values_retained'],1)
        self.assertEqual(expand(json.loads(packed[1]['content'])),json.loads(original[1]['content']))

    def test_inspection_duplicate_reuses_existing_values_in_same_request(self):
        original=messages([preview('whole')],[{'op':'inspect_table','preview':preview('inspected')}])
        packed,stats=prepare(original)
        self.assertTrue(stats['applied'])
        self.assertEqual(expand(json.loads(packed[1]['content'])),json.loads(original[1]['content']))

    def test_unique_or_tiny_context_is_not_modified(self):
        for original in [messages([preview('whole')]),messages([preview('one',end=1),preview('two',end=1)])]:
            packed,stats=prepare(original)
            self.assertFalse(stats['applied']);self.assertEqual(packed,original)

    def test_references_are_unique_across_user_messages_and_do_not_leak_between_calls(self):
        original=messages([preview('whole'),preview('child')])
        original.append(deepcopy(original[1]))
        first,stats=prepare(original);second,_=prepare(original)
        self.assertEqual(first,second)
        ids=[]
        for message in first:
            if message['role']=='user':
                payload=json.loads(message['content']);ids.extend(v['view_id'] for v in views(payload))
                self.assertEqual(expand(payload),json.loads(original[first.index(message)]['content']))
        self.assertEqual(len(ids),len(set(ids)))

    def test_toggle_restores_v2_baseline_version(self):
        config=settings_for_mode({'v3_deduplicate_context':False},'llm-v3')
        self.assertEqual(config['pipeline_variant'],'llm-v2')
        self.assertEqual(v3_version(config),V3_BASELINE_VERSION)


if __name__=='__main__': unittest.main()
