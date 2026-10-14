"""Read-only summaries and comparisons for dashboard experiment logs."""
from collections import Counter
import hashlib
import json


def decorate(row):
    calls=(row.get('usage') or {}).get('calls',[])
    statuses=sorted({call['http_status'] for call in calls if isinstance(call.get('http_status'),int) and call.get('status')=='error'})
    api_failed=row.get('status')=='error' and bool(statuses)
    outcome='pending'
    if row.get('status')=='error': outcome='api_error' if api_failed else 'error'
    elif row.get('status')=='unanswered': outcome='unanswered'
    elif row.get('status')!='pending':
        outcome='match' if row.get('match') is True else 'mismatch' if row.get('match') is False else 'uncompared'
    errors=row.get('validation_errors',[])
    repairs=max(0,len(row.get('plans',[]))-1)
    return {**row,'outcome':outcome,'api_statuses':statuses,'api_failed':api_failed,
            'repairs':repairs,'had_validation_errors':bool(errors)}


def summarize(rows):
    counts=Counter(r['outcome'] for r in rows)
    phases=Counter()
    issues=Counter()
    for row in rows:
        for phase,value in (row.get('timings') or {}).items():
            if isinstance(value,(int,float)) and value>=0: phases[phase]+=value
        # Count affected questions once per error group, including repaired
        # plans; those groups do not imply the final answer is wrong.
        found=set()
        for error in row.get('validation_errors',[]):
            lowered=error.lower()
            category='invalid_plan'
            if 'total/subtotal' in lowered: category='double_count'
            elif 'scope is incomplete' in lowered: category='scope'
            elif any(word in lowered for word in ['final value','unreduced','ranking requires','yes or no','decimal']): category='answer_shape'
            elif any(word in lowered for word in ['no numeric','missing cell','none','null']): category='missing_data'
            found.add(category)
        if row['api_failed']: found.add('api')
        issues.update(found)
    completed=sum(r.get('status')!='pending' for r in rows)
    return {'outcomes':dict(counts),'phases':dict(phases),'issues':dict(issues),
            'repaired_questions':sum(r['repairs']>0 for r in rows),
            'repair_attempts':sum(r['repairs'] for r in rows),
            'api_errors':counts['api_error'],'completed':completed,
            'exact_match':counts['match']/sum(r.get('match') is not None for r in rows)
                if any(r.get('match') is not None for r in rows) else None,
            'slowest':sorted([{'id':str(r['id']),'seconds':r['elapsed_seconds'],'outcome':r['outcome']}
                              for r in rows if isinstance(r.get('elapsed_seconds'),(int,float))],
                             key=lambda r:-r['seconds'])[:8]}


def identity(row,default_dataset):
    dataset=row.get('dataset') or default_dataset
    ident=str(row.get('original_id',row['id']))
    if '::' in ident: dataset,ident=ident.split('::',1)
    return dataset,ident


def compare_states(before,after):
    old={identity(r,before['dataset']):r for r in before['rows']}
    new={identity(r,after['dataset']):r for r in after['rows']}
    rows=[];counts=Counter();excluded=0
    for key in sorted(old.keys() & new.keys()):
        previous,current=old[key],new[key]
        if (previous['query']!=current['query'] or previous.get('reference')!=current.get('reference')
                or current.get('reference') is None):
            excluded+=1;continue
        change='unchanged'
        if previous.get('status')=='pending' or current.get('status')=='pending': change='pending'
        elif current['api_failed']: change='api_error'
        elif previous['api_failed']: change='api_recovered'
        elif previous.get('match') is False and current.get('match') is True: change='improved'
        elif previous.get('match') is True and current.get('match') is False: change='regressed'
        elif current.get('match') is False: change='still_wrong'
        counts[change]+=1
        rows.append({'id':str(current['id']),'dataset':key[0],'query':current['query'],
                     'before':previous['answer'],'after':current['answer'],'reference':current['reference'],
                     'before_status':previous['outcome'],'after_status':current['outcome'],'change':change})
    return {'before':before['selected'],'after':after['selected'],'counts':dict(counts),
            'comparable':len(rows),'excluded_changed_reference_or_question':excluded,
            'only_before':len(old.keys()-new.keys()),'only_after':len(new.keys()-old.keys()),'rows':rows}


def safe_context(context):
    allowed_settings={'max_tokens_plan','max_cost_per_question','max_api_calls','max_plan_repairs',
        'question_timeout','run_timeout','max_prompt_price_per_million','max_completion_price_per_million',
        'max_workbook_cells','retrieval_top_k','preview_rows'}
    source=context.get('source_sha256',{})
    return {'git_revision':context.get('git_revision'),'model':context.get('model'),
            'source_fingerprint':hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()[:12] if source else None,
            'settings':{k:v for k,v in context.get('settings',{}).items() if k in allowed_settings}}
