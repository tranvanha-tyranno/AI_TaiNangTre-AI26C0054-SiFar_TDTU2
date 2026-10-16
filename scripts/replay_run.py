"""Replay saved plans without an API. This measures tool/validator changes only.

Reference answers are compared AFTER execution; they never enter the solver.
Use a fresh CLI run to measure the current planner, retrieval and review.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.answer_contract import infer_answer_contract, validate_answer_contract, validate_answer_field
from src.semantic_validation import validate_semantics, validate_rank_labels
from src.scope_validation import validate_aggregate_scope
from src.tools.executor import execute
from src.workbook_index import load_regions
from src.plan_normalization import normalize_plan


def replay(run, xlsx_dir):
    run=Path(run); xlsx_dir=Path(xlsx_dir).resolve()
    meta=json.loads((run/'metadata.json').read_text(encoding='utf-8'))
    rows=[]
    for line in (run/'questions.jsonl').read_text(encoding='utf-8').splitlines():
        record=json.loads(line)
        path=(xlsx_dir/record['file_name']).resolve()
        if not path.is_relative_to(xlsx_dir): raise ValueError('Workbook path outside xlsx_dir')
        regions=load_regions(path); contract=infer_answer_contract(record['query'])
        attempts=record.get('plans',[]) or [{'plan':record.get('plan')}]
        if record.get('plan') and not any(a.get('plan')==record['plan'] for a in attempts):
            attempts=[*attempts,{'plan':record['plan']}]
        errors=[]; answer=None; chosen=None
        for index,attempt in enumerate(attempts,1):
            plan=attempt.get('plan')
            try:
                plan,normalizations=normalize_plan(plan,regions,contract)
                result=execute(plan,regions)
                validate_aggregate_scope(record['query'],plan,regions)
                validate_answer_contract(contract,plan,result,record['query'])
                validate_answer_field(contract,plan,result,regions)
                validate_semantics(record['query'],contract,plan,result,regions)
                validate_rank_labels(record['query'],result)
                answer=result['answer']; chosen=index; break
            except (ValueError,TypeError,KeyError,AttributeError) as error:
                errors.append({'attempt':index,'error':str(error)})
        expected=meta.get('reference',{}).get(str(record['id']))
        rows.append({'id':record['id'],'query':record['query'],
                     'original_answer':record.get('answer'),'replayed_answer':answer,
                     'expected':expected,'original_match':record.get('answer')==expected if expected is not None else None,
                     'replayed_match':answer==expected if expected is not None else None,
                     'accepted_attempt':chosen,'errors':errors})
    return {'run':run.name,'kind':'offline_plan_replay_not_fresh_model_evaluation',
            'questions':len(rows),'original_matched':sum(r['original_match'] is True for r in rows),
            'replayed_matched':sum(r['replayed_match'] is True for r in rows),
            'rejected':sum(r['replayed_answer'] is None for r in rows),'rows':rows}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',required=True,type=Path)
    ap.add_argument('--xlsx-dir',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args(); report=replay(args.run,args.xlsx_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=True))
