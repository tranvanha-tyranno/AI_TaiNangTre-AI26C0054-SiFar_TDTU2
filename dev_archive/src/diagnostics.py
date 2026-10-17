"""Post-run diagnostics only: never changes answers or calls an LLM."""
from decimal import Decimal, InvalidOperation
import hashlib
import re

PHASES={'parse':'Đọc Excel','rag':'RAG','llm':'LLM lập kế hoạch','tool':'TOOL',
        'format':'Định dạng','api':'API / tài nguyên','unknown':'Chưa xác định'}


def finding(phase, code, title, evidence, certainty='confirmed', recovered=False,
            detected_at=None, candidates=None):
    return {'phase':phase,'phase_label':PHASES[phase],'code':code,'title':title,
            'evidence':evidence,'certainty':certainty,'recovered':recovered,
            'detected_at':detected_at or phase,'root_cause':'unconfirmed',
            'candidate_phases':candidates or [],'relation':'observed_failure'}


def classify(message, detected, recovered=False):
    lower=message.lower()
    if any(token in lower for token in ('expecting ', 'json', 'plan requires','expression must','expects an array','unsupported fields','operator not allowed','tool not allowed','scalar reference','final step does not exist','duplicate step')):
        return finding('llm','invalid_plan','Kế hoạch / tham số không hợp lệ',message,recovered=recovered,detected_at=detected)
    if any(token in lower for token in ('question requires','question asks','use exactly the names','alias targets','output aliases','final answer is missing')):
        return finding('format','output_contract','Đầu ra không đúng yêu cầu',message,recovered=recovered,detected_at=detected,candidates=['llm','format'])
    if any(token in lower for token in ('budget','deadline','time limit','maximum api','api failed','cost limit')):
        return finding('api','resource_or_api','API hoặc giới hạn tài nguyên',message,recovered=recovered,detected_at=detected)
    if any(token in lower for token in ('non-numeric','expected a number','invalid date','division by zero','missing or null')):
        return finding('tool','data_type_or_arithmetic','Công cụ gặp dữ liệu không tính được',message,recovered=recovered,detected_at=detected,candidates=['parse','llm','tool'])
    if any(token in lower for token in ('unknown column','unknown selected','outside','unknown retrieved','unknown table','no numeric rows','empty','rank outside','label cell')):
        return finding('tool','selection_or_bounds','Vùng / cột / lựa chọn không hợp lệ',message,recovered=recovered,detected_at=detected,candidates=['parse','rag','llm'])
    phase={'parse':'parse','retrieve':'rag','plan':'llm','execute':'tool','validate_output':'format'}.get(detected,'unknown')
    return finding(phase,'unclassified_failure','Lỗi cần kiểm tra thêm',message,'suspected',recovered,detected)


def numeric_values(text):
    values=str(text).split(', ')
    if not all(re.fullmatch(r'-?\d+(?:\.\d+)?',v) for v in values): return None
    try: return tuple(Decimal(v) for v in values)
    except InvalidOperation: return None


def diagnose(row):
    issues=[]
    recovered=row.get('status')=='ok'
    events=row.get('validation_events') or [{'message':text,'detected_at':'execute'} for text in row.get('validation_errors',[])]
    for event in events:
        issue=classify(event['message'],event.get('detected_at','execute'),recovered)
        issue['attempt']=event.get('attempt')
        issues.append(issue)
    failure=row.get('failure_event')
    if failure and failure.get('message') not in [event['message'] for event in events]:
        issues.append(classify(failure['message'],failure.get('phase',row.get('stage')),False))
    if row.get('status')=='error' and not issues:
        phase={'parse':'parse','retrieve':'rag','plan':'llm','execute':'tool'}.get(row.get('stage'),'unknown')
        issues.append(finding(phase,'failure_without_details','Nhật ký thiếu chi tiết lỗi',row.get('error_type','Lỗi xử lý'),'suspected'))
    if row.get('status')=='unanswered':
        issues.append(finding('unknown','unanswered','Chưa có đáp án','Chương trình không tạo được đáp án.'))
    if row.get('match') is False and row.get('status')=='ok':
        answer,reference=row.get('answer',''),row.get('reference','')
        numeric_request=any(word in row.get('query','').lower() for word in ('integer','number','decimal'))
        if numeric_request and numeric_values(answer) is not None and numeric_values(answer)==numeric_values(reference):
            issues.append(finding('format','numeric_representation','Cùng giá trị số, khác cách trình bày',f'{answer} ≠ {reference}',candidates=['llm','format']))
        else:
            issues.append(finding('unknown','answer_mismatch','Khác tham chiếu, chưa xác định phase',f'Đáp án: {answer}; tham chiếu: {reference}',
                'unknown',candidates=['parse','rag','llm','tool','format']))
    # A corrected validation failure is not counted as a current prediction error.
    return {'issues':issues,'active_count':sum(not issue['recovered'] for issue in issues),
            'recovered_count':sum(issue['recovered'] for issue in issues),
            'root_cause_confirmed':False,
            'note':'Phase là nơi quan sát lỗi. Nguyên nhân gốc chưa xác nhận; lỗi dây chuyền không được coi là nhiều lỗi độc lập.'}


def summarize(rows):
    buckets={}
    for row in rows:
        seen=set()
        for issue in row['diagnostics']['issues']:
            key=(issue['phase'],issue['code'],issue['certainty'],issue['recovered'])
            if key in seen: continue
            seen.add(key)
            bucket=buckets.setdefault(key,{'phase':issue['phase'],'phase_label':issue['phase_label'],'code':issue['code'],
                'title':issue['title'],'certainty':issue['certainty'],'recovered':issue['recovered'],'questions':0,'datasets':set()})
            bucket['questions']+=1; bucket['datasets'].add(row.get('dataset','public'))
    return [{**bucket,'datasets':sorted(bucket['datasets'])} for bucket in buckets.values()]


def identity(row):
    payload='\0'.join(str(row.get(key,'')) for key in ('dataset','source_file','query'))
    return hashlib.sha256(payload.encode()).hexdigest()


def history(entries):
    grouped={}
    for entry in entries:
        row=entry['row']
        if row.get('status')=='pending': continue
        # Reference changes define different comparisons, not regressions.
        key=(identity(row),row.get('reference'))
        grouped.setdefault(key,[]).append(entry)
    result={}
    for (key,ref),items in grouped.items():
        items.sort(key=lambda item:item['timestamp'])
        previous=None
        for entry in items:
            row=entry['row']; current=row.get('match')
            if row.get('status') in {'error','unanswered'}: current=False
            transition='not_comparable'
            if current is not None:
                transition='first_observation' if previous is None else ('improved' if current and not previous else 'regressed' if previous and not current else 'still_matches' if current else 'still_failing')
                previous=current
            record={'run':entry['run'],'match':row.get('match'),'status':row['status'],'transition':transition,
                    'pipeline_version':entry.get('pipeline_version'),'model':entry.get('model'),
                    'code_fingerprint':entry.get('code_fingerprint'),
                    'reference_basis':entry.get('reference_basis','current'),
                    'issues':[{k:issue[k] for k in ('phase','code','certainty','recovered')} for issue in row['diagnostics']['issues']]}
            result.setdefault((key,ref),[]).append(record)
    return result
