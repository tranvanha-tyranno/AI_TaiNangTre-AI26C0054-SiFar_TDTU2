"""Analyze saved failures and activate reviewed procedural lessons, without API calls.

Reports can contain reference answers for evaluation. Memory exports contain only
allowlisted lesson IDs and support counts; raw questions/plans/answers stay out.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.answer_contract import infer_answer_contract
from src.error_lessons import LESSONS
from src.error_memory import load_memory, normalized


def failure_lessons(record, question):
    """Return evidence-based diagnoses and explicitly marked interpretation risks."""
    errors = record.get('validation_errors', [])
    text = normalized('\n'.join(str(e) for e in errors))
    result = {}

    def add(key, evidence, certainty='observed'):
        result[key] = {'lesson': key, 'certainty': certainty, 'evidence': evidence}

    for key, rule in LESSONS.items():
        if text and re.search(rule['error'], text, re.I):
            add(key, 'Saved validation/repair error matches this failure family.')
    plan = record.get('plan') or next((a.get('plan') for a in reversed(record.get('plans', []))
                                      if isinstance(a.get('plan'), dict)), {})
    steps = plan.get('steps', []) if isinstance(plan, dict) else []
    contract = infer_answer_contract(question)
    q = normalized(question)
    for step in steps:
        if step.get('op') == 'aggregate' and step.get('metric') == 'count' and 'expr' in step:
            # Count with expr can be valid non-null counting. Flag for inspection,
            # rather than assert a boolean failure without the intermediate data.
            add('conditional_count', 'Count has expr; inspect whether False values were counted.', 'hypothesis')
        if step.get('op') == 'lag':
            add('chronological_change', 'Plan uses lag; inspect annual filtering, ordering and first missing prior.', 'hypothesis')
    output = plan.get('output', {}) if isinstance(plan, dict) else {}
    if output.get('columns') and '_section' not in output['columns']:
        if re.search(LESSONS['section_identity']['question'], q):
            add('section_identity', 'Requested group identity may differ from the selected detail label.', 'hypothesis')
    for key in ('difference_direction', 'rowwise_extremum', 'numeric_text', 'tuple_grounding', 'hierarchical_mean', 'ratio_computation', 'complete_read_scope', 'sheet_identity', 'threshold_semantics', 'header_missing_filter', 'horizontal_series_axis', 'header_column_mapping', 'financial_text_numbers'):
        if re.search(LESSONS[key]['question'], q) or any(
                value in LESSONS[key].get('contract', ()) for value in
                (contract.get('kind'), contract.get('reduction')) if value):
            if key not in result:
                add(key, 'Question interpretation risk; verify against headers and execution evidence.', 'hypothesis')
    return list(result.values())


def analyze(run, reference=None):
    run = Path(run)
    log = run / 'questions.jsonl'
    if not log.exists(): log = run / 'logs' / 'questions.jsonl'
    if not log.exists(): raise ValueError(f'No questions.jsonl under {run}')
    meta_path = run / 'metadata.json'
    meta = json.loads(meta_path.read_text(encoding='utf-8')) if meta_path.exists() else {}
    refs = {str(k): v for k, v in meta.get('reference', {}).items()}
    if reference:
        with Path(reference).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['id', 'answer']: raise ValueError('Reference must have id,answer columns')
            rows = list(reader)
            if len({r['id'] for r in rows}) != len(rows): raise ValueError('Duplicate reference IDs')
            refs = {r['id']: r['answer'] for r in rows}
    catalog = {str(q['id']): q for q in meta.get('catalog', [])}
    # If a run appended a result twice, evaluate the final saved state once.
    records = {}
    for line in log.read_text(encoding='utf-8').splitlines():
        if line.strip():
            r = json.loads(line); records[str(r['id'])] = r
    rows = []; support = Counter(); matched = compared = 0
    for key, record in records.items():
        question = record.get('query') or catalog.get(key, {}).get('query', '')
        strict = record.get('answer', '') == refs[key] if key in refs else None
        compared += strict is not None; matched += strict is True
        failed = record.get('status') in {'error', 'unanswered'} or record.get('candidate_rejected', False)
        recovered = bool(record.get('validation_errors'))
        if strict is not False and not failed and not recovered: continue
        diagnoses = failure_lessons(record, question)
        api = record.get('usage', {}).get('calls', [])
        api_errors = [c.get('http_status') for c in api if c.get('status') == 'error']
        if api_errors:
            diagnoses.append({'lesson': None, 'certainty': 'observed',
                              'evidence': f'API errors {api_errors}; retrieval cannot fix provider availability.'})
        # Only fixed catalog IDs are exported. Never copy reviewer suggestions,
        # workbook strings, expected answers or question keywords into memory.
        support.update({d['lesson'] for d in diagnoses if d['lesson']})
        rows.append({'id': key, 'query': question, 'answer': record.get('answer', ''),
                     'expected': refs.get(key), 'strict_match': strict,
                     'kind': 'mismatch' if strict is False else 'failed' if failed else 'recovered_error',
                     'validation_errors': record.get('validation_errors', []),
                     'diagnoses': diagnoses})
    return {'run': str(run), 'metric': 'strict exact match', 'completed_records': len(records),
            'compared': compared, 'matched': matched,
            'strict_exact_match': matched / compared if compared else None,
            'uncompared': len(records) - compared, 'lesson_support': dict(support), 'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='append', required=True, type=Path)
    parser.add_argument('--reference', type=Path, help='Evaluation-only CSV for a single run')
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--memory-output', required=True, type=Path)
    parser.add_argument('--merge-memory', type=Path, help='Preserve previously activated lessons')
    args = parser.parse_args()
    if args.reference and len(args.run) != 1:
        parser.error('--reference requires exactly one --run')
    if args.report.resolve() == args.memory_output.resolve():
        parser.error('Report and memory output must be separate files')
    reports = [analyze(p, args.reference) for p in dict.fromkeys(args.run)]
    previous = Counter()
    if args.merge_memory:
        existing, _ = load_memory(args.merge_memory)
        previous.update({r['id']: r['support'] for r in existing['lessons']})
    support = Counter()
    for report in reports: support.update(report['lesson_support'])
    # max instead of summing old support makes re-importing the same corpus
    # idempotent when a previous snapshot is supplied.
    if args.merge_memory:
        support = Counter({k: max(support[k], previous[k]) for k in support.keys() | previous.keys()})
    memory = {'version': 1, 'lessons': [{'id': k, 'support': support[k]} for k in sorted(support)]}
    for path, data in ((args.report, {'evaluation_only': True, 'runs': reports}),
                       (args.memory_output, memory)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'runs': len(reports), 'activated_lessons': len(support),
                      'report': str(args.report), 'memory': str(args.memory_output)}))


if __name__ == '__main__': main()
