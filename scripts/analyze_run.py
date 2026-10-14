"""Summarize a saved dashboard run and compare it with an earlier run.

References are evaluation-only and never sent to the planner.
"""
import argparse
from collections import Counter
import json
from pathlib import Path


def analyze(folder):
    folder=Path(folder)
    meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    summary=json.loads((folder/'summary.json').read_text(encoding='utf-8')) if (folder/'summary.json').exists() else {}
    references=meta.get('reference',{})
    queries=meta.get('catalog') or json.loads((folder/'queries.json').read_text(encoding='utf-8'))
    records={str(r['id']):r for line in (folder/'questions.jsonl').read_text(encoding='utf-8').splitlines()
             if line.strip() for r in [json.loads(line)]}
    rows=[]
    for q in queries:
        r=records.get(str(q['id']),{})
        expected=references.get(str(q['id']))
        api_statuses=sorted({call.get('http_status') for call in r.get('usage',{}).get('calls',[])
                             if isinstance(call.get('http_status'),int) and call.get('status')=='error'})
        api_failed=r.get('status')=='error' and bool(api_statuses)
        rows.append({'id':str(q['id']),'query':q['query'],'file_name':q['file_name'],
                     'status':r.get('status','pending'),'stage':r.get('stage'),
                     'answer':r.get('answer',''),'expected':expected,
                     'match':r.get('answer')==expected if expected is not None and r else None,
                     'validated':r.get('validated',False),
                     'validation_errors':r.get('validation_errors',[]),
                     'error_type':r.get('error_type'),
                     'api_statuses':api_statuses,'api_failed':api_failed,
                     'plan_attempts':len(r.get('plans',[])),'elapsed_seconds':r.get('elapsed_seconds')})
    compared=[r for r in rows if r['match'] is not None]
    return {'run':folder.name,'dataset':meta.get('dataset'),'mode':meta.get('mode'),
            'finished':meta.get('finished',False),'questions':len(rows),'compared':len(compared),
            'matched':sum(r['match'] is True for r in rows),
            'exact_match':sum(r['match'] is True for r in compared)/len(compared) if compared else None,
            'status_counts':dict(Counter(r['status'] for r in rows)),
            'repair_questions':sum(r['plan_attempts']>1 for r in rows),
            'api_failure_questions':sum(r['api_failed'] for r in rows),
            'elapsed_seconds':summary.get('elapsed_seconds'),'usage':summary.get('usage'),
            'mismatches':[r for r in rows if r['match'] is False],
            'uncompared':[r['id'] for r in rows if r['match'] is None], 'rows':rows}


def compare(previous,current):
    old={r['id']:r for r in previous['rows']}
    new={r['id']:r for r in current['rows']}
    # Only compare identical questions AND identical expected answers. A fixed
    # reference (e.g. the old smoke age answer) is not a solver improvement.
    common=[key for key in old.keys() & new.keys() if old[key]['query']==new[key]['query']
            and old[key]['expected']==new[key]['expected'] and old[key]['expected'] is not None]
    return {'previous_run':previous['run'],'comparable_questions':len(common),
            'improved':sorted(key for key in common if old[key]['match'] is False and new[key]['match'] is True),
            'regressed':sorted(key for key in common if old[key]['match'] is True and new[key]['match'] is False and not new[key].get('api_failed')),
            'still_wrong':sorted(key for key in common if old[key]['match'] is False and new[key]['match'] is False and not new[key].get('api_failed')),
            'api_failed':sorted(key for key in common if new[key].get('api_failed'))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True,type=Path)
    parser.add_argument('--previous',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report=analyze(args.run)
    if args.previous: report['comparison']=compare(analyze(args.previous),report)
    output=args.output or args.run/'analysis.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'rows','mismatches','usage'}},ensure_ascii=True,indent=2))
    print('Report:',output)


if __name__=='__main__': main()
