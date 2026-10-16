"""Evaluation-only aggregation: never imports the planner or calls an API."""
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.diagnostics import classify

VERSION = 'lmmv3-v2-dedup-v1'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def outcome(record, expected):
    if not record:
        return 'Chưa trả lời'
    if record.get('status') == 'error':
        failure = record.get('failure_event') or {}
        message = str(failure.get('message', ''))
        # A transient API incident followed by a different failure is not an API final failure.
        if record.get('stage') == 'api' or failure.get('phase') == 'api' or 'Planner API failed:' in message or record.get('error_type') in ('APIError', 'APIConnectionError', 'AuthenticationError', 'RateLimitError'):
            return 'Lỗi API'
        return 'Lỗi xử lý'
    if record.get('status') == 'unanswered' or record.get('answer', '') == '':
        return 'Chưa trả lời'
    return 'Khớp' if record.get('answer') == expected else 'Đáp án khác'


def main():
    output = ROOT/'outputs/v3-evaluation'
    output.mkdir(exist_ok=True)
    selected = {}
    excluded = []
    for folder in sorted((ROOT/'outputs/runs').iterdir()):
        if not (folder/'metadata.json').exists():
            continue
        meta = load(folder/'metadata.json')
        dataset = meta.get('dataset', '')
        eligible = dataset == 'public_data_2' or (dataset[:2].isdigit() and 13 <= int(dataset[:2]) <= 22)
        if not eligible or meta.get('mode') != 'llm-v3':
            continue
        summary = load(folder/'summary.json') if (folder/'summary.json').exists() else {}
        if summary.get('pipeline_version') != VERSION:
            excluded.append({'run': folder.name, 'reason': 'different version or no summary'})
            continue
        catalog = meta.get('catalog', [])
        if not meta.get('finished') or len(catalog) != 30:
            excluded.append({'run': folder.name, 'reason': 'partial or unfinished'})
            continue
        if dataset in selected:
            excluded.append({'run': folder.name, 'reason': 'later run; first full attempt retained'})
            continue
        selected[dataset] = (folder, meta, summary)
    results, details, findings = [], [], []
    for dataset, (folder, meta, summary) in sorted(selected.items()):
        check_path = ROOT/'Test'/dataset/'answer_checks.json'
        categories = {str(x['id']): x.get('category', 'unspecified') for x in load(check_path)} if check_path.exists() else {}
        records = {str(r['id']): r for line in (folder/'questions.jsonl').read_text(encoding='utf-8').splitlines() if line.strip() for r in [json.loads(line)]}
        local = []
        for q in meta['catalog']:
            r = records.get(str(q['id']), {})
            expected = meta['reference'].get(str(q['id']))
            category = outcome(r, expected)
            calls = r.get('usage', {}).get('calls', [])
            events = r.get('validation_events', [])
            seen = set()
            observed = []
            for e in events:
                issue = classify(e['message'], e.get('detected_at', r.get('stage')))
                key = (issue['phase'], issue['code'])
                observed.append({'phase_observed': e.get('detected_at'), 'code': issue['code'], 'message': e['message'], 'attempt': e.get('attempt')})
                if key not in seen:
                    findings.append({'dataset': dataset, 'id': str(q['id']), 'phase': issue['phase'], 'code': issue['code'], 'title': issue['title'], 'outcome': category, 'evidence': e['message'], 'certainty': 'observed symptom; root cause unconfirmed'})
                    seen.add(key)
            row = {'dataset': dataset, 'run': folder.name, 'id': str(q['id']), 'outcome': category,
                   'question_category': categories.get(str(q['id']), 'public / unspecified'),
                   'answer': r.get('answer', ''), 'reference': expected, 'query': q['query'],
                   'stage': r.get('stage'), 'status': r.get('status', 'pending'),
                   'seconds': r.get('elapsed_seconds', 0), 'api_calls': len(calls),
                   'total_tokens': r.get('usage', {}).get('total_tokens', 0),
                   'known_cost_usd': r.get('usage', {}).get('actual_cost_usd', 0),
                   'plan_records': len(r.get('plans', [])), 'validation_events': len(events),
                   'repeated_validation_messages': len(events) - len({e['message'] for e in events}),
                   'api_error_calls': sum(c.get('status') == 'error' for c in calls),
                   'review_unavailable': sum(v.get('verdict') == 'unavailable' for v in r.get('reviews', []))}
            last_attempt = r.get('plans', [])[-1] if r.get('plans') else {}
            details.append({**row, 'events': observed, 'reviews': r.get('reviews', []), 'final_plan': r.get('plan') or last_attempt.get('plan'), 'failure_event': r.get('failure_event')})
            local.append(row)
        counts = Counter(r['outcome'] for r in local)
        purpose_usage = defaultdict(lambda: {'calls': 0, 'tokens': 0, 'known_cost_usd': 0})
        for record in records.values():
            for call in record.get('usage', {}).get('calls', []):
                bucket = purpose_usage[call.get('purpose', 'unknown')]
                bucket['calls'] += 1
                bucket['tokens'] += call.get('total_tokens') or 0
                bucket['known_cost_usd'] += call.get('actual_cost_usd') or 0
        results.append({'dataset': dataset, 'run': folder.name, 'questions': len(local), 'counts': dict(counts),
                        'purpose_usage': dict(purpose_usage),
                        'matched_first_plan_no_validation_error': sum(r['outcome'] == 'Khớp' and r['plan_records'] == 1 and not r['validation_events'] for r in local),
                        'matched_after_validation_error': sum(r['outcome'] == 'Khớp' and r['validation_events'] > 0 for r in local),
                        'elapsed_seconds': summary.get('elapsed_seconds'), 'usage': summary.get('usage'),
                        'code_fingerprint': meta.get('code_fingerprint'), 'model': summary.get('model')})
    buckets = defaultdict(lambda: {'questions': set(), 'datasets': set(), 'outcomes': Counter()})
    for f in findings:
        b = buckets[(f['phase'], f['code'], f['title'])]
        b['questions'].add((f['dataset'], f['id']))
        b['datasets'].add(f['dataset'])
        b['outcomes'][f['outcome']] += 1
    phases = [{'phase': k[0], 'code': k[1], 'title': k[2], 'questions': len(v['questions']), 'datasets': sorted(v['datasets']), 'outcomes': dict(v['outcomes'])} for k, v in buckets.items()]
    phases.sort(key=lambda v: (-len(v['datasets']), -v['questions']))
    category_counts = defaultdict(Counter)
    observed_stages = defaultdict(set)
    for row in details:
        category_counts[row['question_category']][row['outcome']] += 1
        for event in row['events']:
            observed_stages[event['phase_observed']].add((row['dataset'], row['id']))
    payload = {'version': VERSION, 'comparison': 'strict exact match, not official BTC normalization', 'runs': results, 'observed_error_groups': phases, 'observed_stages': {str(k):len(v) for k,v in observed_stages.items()}, 'question_categories': {k:dict(v) for k,v in category_counts.items()}, 'questions': details, 'excluded': excluded}
    (output/'report.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    for name, data in [('questions.csv', [{k:v for k,v in row.items() if k not in ('events','reviews','final_plan','failure_event')} for row in details]), ('findings.csv', findings)]:
        if data:
            with (output/name).open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    lines = ['# Đánh giá LMMv3 — một lượt đầy đủ mỗi dataset', '',
             'Strict exact match; giữ lần chạy đầy đủ đầu tiên, không chọn điểm tốt nhất. Đáp án tham chiếu chỉ dùng sau chạy. Phân loại phase là nơi quan sát dấu hiệu, chưa chứng minh nguyên nhân gốc. Một câu có thể thuộc nhiều nhóm lỗi.', '',
             '| Dataset | Khớp | Khác | Xử lý | API | Chưa trả lời | Giây | API calls | Token | USD đã biết |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in results:
        c = r['counts'];u = r['usage'] or {}
        lines.append(f"| {r['dataset']} | {c.get('Khớp',0)}/{r['questions']} | {c.get('Đáp án khác',0)} | {c.get('Lỗi xử lý',0)} | {c.get('Lỗi API',0)} | {c.get('Chưa trả lời',0)} | {r['elapsed_seconds']:.1f} | {u.get('api_calls',0)} | {u.get('total_tokens',0)} | {u.get('actual_cost_usd',0):.6f} |")
    total = Counter(row['outcome'] for row in details)
    lines += ['', f'Tổng: {len(details)} câu; {dict(total)}.',
              f"Chi phí có đủ usage ở {sum(bool((r['usage'] or {}).get('cost_complete')) for r in results)}/{len(results)} run. Các số USD trong bảng là tổng đã biết, không thay usage thiếu bằng giá ước lượng.",
              f"Có {sum(row['api_error_calls'] for row in details)} lượt gọi API lỗi (bao gồm lượt phục hồi); {sum(row['review_unavailable'] for row in details)} review không dùng được; {sum(row['repeated_validation_messages'] for row in details)} thông báo validation lặp lại trong cùng câu.",
              '', '## Nhóm dấu hiệu lỗi (mỗi câu chỉ đếm một lần trong một nhóm)', '', '| Phase quan sát | Dấu hiệu | Số câu | Số dataset | Kết quả cuối |', '|---|---|---:|---:|---|']
    for p in phases:
        lines.append(f"| {p['phase']} | {p['title']} | {p['questions']} | {len(p['datasets'])} | {p['outcomes']} |")
    lines += ['', '## Điểm làm tốt', '']
    for r in results:
        lines.append(f"- {r['dataset']}: {r['matched_first_plan_no_validation_error']} câu khớp với một kế hoạch và không có validation error; {r['matched_after_validation_error']} câu khớp sau lỗi được ghi nhận.")
    lines += ['', '## Kết quả theo dạng câu hỏi (nhãn fixture, chỉ dùng sau chạy)', '', '| Dạng câu hỏi | Khớp | Tổng | Kết quả |', '|---|---:|---:|---|']
    for category, counts in sorted(category_counts.items()):
        lines.append(f"| {category} | {counts.get('Khớp',0)} | {sum(counts.values())} | {dict(counts)} |")
    lines += ['', '## Từng câu chưa khớp', '']
    for row in details:
        if row['outcome'] != 'Khớp':
            lines += [f"### {row['dataset']} / {row['id']} — {row['outcome']}", '', row['query'], '', f"Đáp án: `{row['answer']}`; tham chiếu: `{row['reference']}`. Phase cuối: `{row['stage']}`.", '']
            for event in row['events']:
                lines.append(f"- Lượt {event['attempt']} / {event['phase_observed']}: {event['message']}")
            if not row['events']:
                lines.append('- Chưa có lỗi được ghi nhận để kết luận nguyên nhân; cần đối chiếu final_plan và workbook trong report.json.')
            lines.append('')
    lines += ['## Giới hạn đánh giá', '', 'Một lượt không đo độ biến thiên. Các suite tổng hợp tham khảo cấu trúc public, không chứng minh đạt tập ẩn. Lỗi API phục hồi được ghi riêng trong questions.csv; lỗi API cuối chỉ gán khi log xác định phase/loại API, các trường hợp không đủ chứng cứ vẫn giữ lỗi xử lý. RAM trong summary chỉ đo tiến trình chính; chưa chứng nhận tài nguyên toàn hệ thống. Chi phí thiếu usage cần báo thiếu, không thay bằng ước lượng như số đo thực.']
    (output/'report.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'runs': len(results), 'questions': len(details), 'outcomes': dict(total), 'report': str(output/'report.md')}, ensure_ascii=True))


if __name__ == '__main__':
    main()
