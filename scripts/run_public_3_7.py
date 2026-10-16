"""One full first-pass evaluation per supplied dataset, with frozen solver settings."""
import csv
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import dashboard
from run_v3_evaluation_batch import fingerprint
from report_v3_evaluation import outcome

OUT = ROOT/'outputs/v3-public-3-7'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def report(manifest):
    results, questions = [], []
    for item in manifest['runs']:
        folder = ROOT/'outputs/runs'/item['run']
        meta = read(folder/'metadata.json')
        if not meta.get('finished') or not (folder/'summary.json').exists():
            continue
        summary = read(folder/'summary.json')
        records = {str(r['id']): r for line in (folder/'questions.jsonl').read_text(encoding='utf-8').splitlines() if line.strip() for r in [json.loads(line)]}
        counts = {}
        for q in meta['catalog']:
            r = records.get(str(q['id']), {})
            category = outcome(r, meta['reference'].get(str(q['id'])))
            counts[category] = counts.get(category, 0) + 1
            questions.append({'dataset':item['dataset'], 'run':item['run'], 'id':str(q['id']),
                'outcome':category, 'query':q['query'], 'answer':r.get('answer',''),
                'reference':meta['reference'].get(str(q['id'])), 'stage':r.get('stage'),
                'events':r.get('validation_events',[]), 'reviews':r.get('reviews',[]),
                'seconds':r.get('elapsed_seconds'), 'usage':r.get('usage',{}),
                'final_plan':r.get('plan') or (r.get('plans',[])[-1].get('plan') if r.get('plans') else None)})
        results.append({'dataset':item['dataset'], 'run':item['run'], 'counts':counts, 'summary':summary})
    (OUT/'report.json').write_text(json.dumps({'runs':results,'questions':questions},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# LMMv3 — Public_data_3–7', '', 'Một lần chạy đầy đủ mỗi bộ, strict exact match. Không dùng tham chiếu trong solver; không đổi cấu hình. Tên Public_data là tên thư mục người dùng cung cấp, không khẳng định đây là dữ liệu chính thức của BTC.', '',
           '| Dataset | Khớp | Khác | Lỗi xử lý | API | Chưa trả lời | Giây | USD đã biết |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in results:
        c=r['counts'];s=r['summary'];u=s['usage']
        lines.append(f"| {r['dataset']} | {c.get('Khớp',0)}/{s['questions']} | {c.get('Đáp án khác',0)} | {c.get('Lỗi xử lý',0)} | {c.get('Lỗi API',0)} | {c.get('Chưa trả lời',0)} | {s['elapsed_seconds']:.1f} | {u['actual_cost_usd']:.6f} |")
    lines += ['', '## Các câu chưa khớp', '']
    for q in questions:
        if q['outcome']=='Khớp':continue
        lines += [f"### {q['dataset']} / {q['id']} — {q['outcome']}", '', q['query'], '', f"Đáp án: `{q['answer']}`; tham chiếu: `{q['reference']}`.", '']
        for e in q['events']:lines.append(f"- {e.get('detected_at')}: {e['message']}")
        if not q['events']:lines.append('- Chưa xác định nguyên nhân từ thông báo lỗi; cần đối chiếu kế hoạch và workbook.')
        lines.append('')
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    with (OUT/'questions.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        keys=['dataset','run','id','outcome','query','answer','reference','stage','seconds']
        writer=csv.DictWriter(stream,fieldnames=keys,extrasaction='ignore');writer.writeheader();writer.writerows(questions)
    print('RESULTS',[(r['dataset'],r['counts']) for r in results],flush=True)


def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    OUT.mkdir(exist_ok=True)
    manifest_path=OUT/'batch.json'
    manifest=read(manifest_path) if manifest_path.exists() else {'status':'running','runs':[]}
    if manifest.get('status')=='stopped_by_user':raise SystemExit('User stopped batch; explicit resume required.')
    baseline=ROOT/'outputs/runs/20261016-142856-ebdfbc'
    expected=read(baseline/'metadata.json')['code_fingerprint']
    if fingerprint()!=expected:raise SystemExit('Solver/config differs from baseline; not running.')
    from dotenv import load_dotenv
    from src.llm_client import PlannerClient
    load_dotenv(ROOT/'.env',override=False)
    client=PlannerClient(prompt_cap=1,completion_cap=4,max_tokens=3000,seed=42)
    if client.model!=read(baseline/'run_context.json')['model']:raise SystemExit('Model differs from baseline.')
    eligibility=read(ROOT/'outputs/v3-evaluation/eligibility_public_3_7.json')
    paths=[Path(x['path']) for x in eligibility if all(f['eligible'] for f in x['files'])]
    dashboard.configure_extra_datasets(paths)
    for path in paths:
        if fingerprint()!=expected:raise SystemExit('Solver changed; stopped before next dataset.')
        if manifest_path.exists() and read(manifest_path).get('status') in {'stop_requested','stopped_by_user'}:return
        ds=next(d for d in dashboard.datasets() if Path(d['queries']).parent.resolve()==path.resolve())
        previous=[]
        for folder in (ROOT/'outputs/runs').iterdir():
            f=folder/'metadata.json'
            if f.exists() and read(f).get('dataset')==ds['id']:previous.append(folder.name)
        if previous:
            print('SKIP_ALREADY_ATTEMPTED',path.name,previous,flush=True);continue
        name=dashboard.start_run('llm-v3',None,ds['id'])
        manifest['runs'].append({'dataset':path.name,'path':str(path),'run':name})
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        print('START',path.name,name,flush=True)
        while dashboard.JOB['running']:time.sleep(1)
        report(manifest)
        folder=ROOT/'outputs/runs'/name
        if not (folder/'questions.jsonl').exists():raise SystemExit('No question records; stop to inspect startup failure.')
    manifest['status']='completed'
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    report(manifest)
    print('BATCH_FINISHED',flush=True)


if __name__=='__main__':main()
