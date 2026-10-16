"""Run each remaining transfer suite once, using the unchanged dashboard runner.

Resume skips any dataset already attempted, including failed/partial runs.
References remain in evaluation metadata and are never supplied to the solver.
"""
import hashlib
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import dashboard


def fingerprint():
    digest = hashlib.sha256()
    for source in [ROOT/'main.py', ROOT/'config/config.yaml', *sorted((ROOT/'src').rglob('*.py'))]:
        digest.update(str(source.relative_to(ROOT)).encode())
        digest.update(source.read_bytes())
    return digest.hexdigest()


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true', help='Explicitly resume a user-stopped batch; permits replacement of its zero-record interrupted run only.')
    args = parser.parse_args()
    manifest_path = ROOT/'outputs/v3-evaluation-batch.json'
    if manifest_path.exists() and json.loads(manifest_path.read_text(encoding='utf-8')).get('status') == 'stopped_by_user' and not args.resume:
        raise SystemExit('Batch stopped by user after Test/18. Explicitly resume before running more datasets.')
    baseline = ROOT/'outputs/runs/20261016-142856-ebdfbc'
    expected = json.loads((baseline/'metadata.json').read_text(encoding='utf-8'))['code_fingerprint']
    if fingerprint() != expected:
        raise SystemExit('Solver/config differs from baseline; batch not started.')
    from dotenv import load_dotenv
    from src.llm_client import PlannerClient
    load_dotenv(ROOT/'.env', override=False)
    client = PlannerClient(prompt_cap=1, completion_cap=4, max_tokens=3000, seed=42)
    baseline_context = json.loads((baseline/'run_context.json').read_text(encoding='utf-8'))
    if client.model != baseline_context['model']:
        raise SystemExit('Configured model differs from baseline; batch not started.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {
        'version': 'lmmv3-v2-dedup-v1', 'code_fingerprint': expected, 'runs': []}
    manifest['status'] = 'running'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    for suite in sorted((ROOT/'Test').iterdir()):
        if not suite.is_dir() or not suite.name[:2].isdigit() or not 14 <= int(suite.name[:2]) <= 22:
            continue
        if fingerprint() != expected:
            raise SystemExit('Solver/config changed during batch; stopping before next dataset.')
        current_manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if current_manifest.get('status') in {'stop_requested', 'stopped_by_user'}:
            print('STOPPED_AT_DATASET_BOUNDARY', flush=True)
            return
        existing = []
        for folder in (ROOT/'outputs/runs').iterdir():
            f = folder/'metadata.json'
            if f.exists():
                meta = json.loads(f.read_text(encoding='utf-8'))
                if meta.get('dataset') == suite.name and meta.get('mode') == 'llm-v3':
                    own_run = any(x['run'] == folder.name for x in manifest['runs'])
                    question_file = folder/'questions.jsonl'
                    zero_records = not question_file.exists() or not question_file.read_text(encoding='utf-8').strip()
                    if args.resume and own_run and meta.get('stopped_by_user') and zero_records:
                        meta['evaluation_excluded_reason'] = 'Zero-record interrupted startup; user explicitly authorized resuming remaining datasets.'
                        f.write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
                        continue
                    if own_run and meta.get('returncode') == 2 and not (folder/'questions.jsonl').exists():
                        meta['evaluation_excluded_reason'] = 'Environment preflight failed before any question/API inference; retained for audit.'
                        f.write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
                        continue
                    existing.append(folder.name)
        if existing:
            print('SKIP_ALREADY_ATTEMPTED', suite.name, existing, flush=True)
            continue
        name = dashboard.start_run('llm-v3', None, suite.name)
        manifest['runs'].append({'dataset': suite.name, 'run': name})
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print('START', suite.name, name, flush=True)
        while dashboard.JOB['running']:
            time.sleep(1)
        directory = ROOT/'outputs/runs'/name
        rows = [json.loads(line) for line in (directory/'questions.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()] if (directory/'questions.jsonl').exists() else []
        meta = json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
        matched = sum(r.get('answer') == meta['reference'].get(str(r['id'])) for r in rows)
        print('DONE', suite.name, 'records', len(rows), 'matched', matched, 'exit', dashboard.JOB['returncode'], flush=True)
        if not rows:
            raise SystemExit('No question records; stop batch to inspect infrastructure before continuing.')
        import report_v3_evaluation
        report_v3_evaluation.main()
    manifest['status'] = 'completed'
    manifest['next_dataset'] = None
    manifest['note'] = 'Completed full evaluations through Test/22; preflight and interrupted zero-record logs retained and excluded.'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print('BATCH_FINISHED', flush=True)


if __name__ == '__main__':
    main()
