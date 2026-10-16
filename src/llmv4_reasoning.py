"""Structure-aware retrieval and conservative plan diagnostics, v4 only.

No reference answers or model calls. Uncertain semantic findings are warnings,
not gates; only demonstrably invalid dependency/type declarations are rejected.
"""
import json
import re
from .tools.executor import PlanError
from .workbook_index import retrieve, words

ROW_OPS = {'read','filter','derive','sort','take','select','group','join','unpivot','fill_down','lag','concat','collect','record'}
SCALAR_OPS = {'cell','sum_columns','calculate','aggregate'}
COMPARISONS = {'eq','ne','gt','ge','lt','le','and','or','not','contains','starts_with','is_null','is_number'}


def unit_facts(text, source):
    patterns = [('currency','VND',1000000000,r'\btỷ đồng\b|\bbillion (?:vnd|dong)\b'),
                ('currency','VND',1000000,r'\btriệu đồng\b|\bmillion (?:vnd|dong)\b'),
                ('currency','VND',1000,r'\bnghìn đồng\b|\bthousand (?:vnd|dong)\b'),
                ('energy','kWh',1,r'\bkwh\b'),('power','kW',1,r'\bkw\b'),
                ('percentage','percent',1,r'%|\bpercent(?:age)?\b|phần trăm')]
    return [{'dimension':dim,'unit':unit,'scale':scale,'source':source,'text':text[:300]}
            for dim,unit,scale,pattern in patterns if re.search(pattern,text,re.I)]


def question_spec(question, contract):
    periods = list(dict.fromkeys(re.findall(r'\b(?:19|20)\d{2}(?:\s*[/–-]\s*(?:19|20)\d{2})?\b',question)))
    quoted = re.findall(r'[\"“]([^\"”]+)[\"”]|\x27([^\x27]+)\x27',question)
    return {'output':contract, 'period_mentions':periods[:12],
            'quoted_targets':[a or b for a,b in quoted][:12],
            'unit_mentions':unit_facts(question,'question'),
            'whole_scope_requested':bool(re.search(r'all (?:rows|records)|toàn bộ (?:các )?(?:dòng|bản ghi)|tất cả (?:các )?bản ghi',question,re.I)),
            'note':'Mentions are candidates, not resolved bindings. Filters and metric roles must be grounded in workbook cells.'}


def metadata(region):
    headers = region.column_headers()
    context = [{'text':line,'source':f'{region.sheet}:context'} for line in region.context]
    for row in region.header_rows[:8]:
        for col in range(region.start_col,region.end_col+1):
            value=region.cells.get((row,col))
            if isinstance(value,str):
                from openpyxl.utils import get_column_letter
                context.append({'text':value,'source':f'{region.sheet}!{get_column_letter(col)}{row}'})
    facts=[];seen=set()
    for item in context:
        for fact in unit_facts(item['text'],item['source']):
            key=(fact['dimension'],fact['unit'],fact['scale'],fact['source'])
            if key not in seen:facts.append(fact);seen.add(key)
    return {'columns':[{'column':col,'header_path':path} for col,path in headers.items()],
            'unit_candidates':facts[:40], 'section_candidates':region.section_labels()[:60],
            'table_range':region.bounds,'note':'Candidates retain source coordinates; conflicting units must be resolved before calculation.'}


def retrieve_structured(regions, question, top_k):
    _, catalog = retrieve(regions,question,len(regions))
    by_id={r.id:r for r in regions}
    targets=question_spec(question,{})['quoted_targets']
    for item in catalog:
        r=by_id[item['table_id']]
        structure=' '.join([r.sheet,*r.context,*[str(v) for (row,_),v in r.cells.items() if row in r.header_rows]])
        structure+=' '+' '.join(s['label'] for s in r.section_labels()[:60])
        overlap=len(words(question)&words(structure))
        phrase_hits=sum(bool(target.strip()) and target.casefold() in structure.casefold() for target in targets)
        item['baseline_score']=item['score']
        item['structure_score']=overlap*2+phrase_hits*6
        item['score']+=item['structure_score']
    catalog.sort(key=lambda c:(-c['score'],c['table_id']))
    selected={c['table_id'] for c in catalog[:top_k]}
    for item in catalog:item['selected']=item['table_id'] in selected
    return [by_id[c['table_id']] for c in catalog[:top_k]],catalog


def _refs(value):
    if isinstance(value,dict):
        if set(value)=={'ref'}:yield value['ref']
        for child in value.values():yield from _refs(child)
    elif isinstance(value,list):
        for child in value:yield from _refs(child)


def check_plan(plan, regions, contract, question):
    """Check known row/scalar dependencies before executing; no guessed coercions."""
    steps=plan.get('steps')
    if not isinstance(steps,list) or not 1<=len(steps)<=25:
        raise PlanError('Typed plan requires 1..25 steps.')
    tables={r.id:r for r in regions};kinds={};audit=[]
    for step in steps:
        if not isinstance(step,dict):raise PlanError('Typed plan step must be an object.')
        name,op=step.get('id'),step.get('op')
        if not isinstance(name,str) or name in kinds:raise PlanError('Typed plan requires unique string step IDs.')
        if op not in ROW_OPS|SCALAR_OPS:raise PlanError(f'Typed plan: unsupported operation {op}.')
        kind='rows' if op in ROW_OPS else 'scalar'
        for field in ('table','label_table'):
            if field in step and step[field] not in tables:raise PlanError(f'Typed plan: unknown table {step[field]}.')
        dependencies=[]
        for field in ('input','left','right'):
            if field in step:
                value=step[field]
                if not isinstance(value,str) or value not in kinds:raise PlanError(f'Typed plan {name}: missing/forward {field} dependency {value}.')
                if (field in {'left','right'} or op!='calculate') and kinds[value]!='rows':
                    raise PlanError(f'Typed plan {name}: {field} requires rows, got scalar {value}.')
                dependencies.append(value)
        for value in step.get('inputs',[]):
            if not isinstance(value,str) or value not in kinds:raise PlanError(f'Typed plan {name}: unknown input {value}.')
            expected='rows' if op=='concat' else 'scalar'
            if kinds[value]!=expected:raise PlanError(f'Typed plan {name}: {op} requires {expected} inputs, got {value}.')
            dependencies.append(value)
        expressions=[step.get('expr'),step.get('where')]
        if op=='record':
            fields=step.get('fields',{})
            if not isinstance(fields,dict):raise PlanError('Typed plan record requires a fields mapping.')
            expressions.extend({'ref':v} if isinstance(v,str) else v for v in fields.values())
        for value in _refs(expressions):
            if not isinstance(value,str) or value not in kinds:raise PlanError(f'Typed plan {name}: unknown scalar ref {value}.')
            if kinds[value]!='scalar':raise PlanError(f'Typed plan {name}: ref {value} is rows; use col on a row input.')
            dependencies.append(value)
        kinds[name]=kind
        audit.append({'id':name,'op':op,'output_kind':kind,'dependencies':sorted(set(dependencies))})
    output=plan.get('output') or {}
    if output.get('step') not in kinds:raise PlanError('Typed plan output must reference an existing step.')
    if kinds[output['step']]=='rows' and not output.get('columns'):
        raise PlanError('Typed plan row output requires explicit columns.')
    from .llmv4_schema import check_columns
    return {'steps':audit,'column_schemas':check_columns(plan,regions),
            'output_kind':kinds[output['step']], 'scope':scope_audit(plan,regions,contract,question)}


def scope_audit(plan, regions, contract, question):
    tables={r.id:r for r in regions};reads=[];warnings=[]
    for step in plan.get('steps',[]):
        if step.get('op')!='read' or step.get('table') not in tables:continue
        r=tables[step['table']];start=step.get('start_row',r.start_row);end=step.get('end_row',r.end_row)
        reads.append({'step':step['id'],'table':r.id,'sheet':r.sheet,'read_rows':[start,end],'available_rows':[r.start_row,r.end_row]})
        if question_spec(question,contract)['whole_scope_requested'] and isinstance(end,int) and end<r.end_row:
            warnings.append({'code':'possibly_incomplete_scope','step':step['id'],'message':f'Read ends at {end}, but {r.sheet} continues to {r.end_row}. Verify omitted rows versus the requested whole scope; headers/notes may justify exclusions.'})
    for step in plan.get('steps',[]):
        expr=step.get('expr') or {}
        if step.get('op')=='aggregate' and step.get('metric')=='count' and isinstance(expr,dict) and set(expr)&COMPARISONS:
            warnings.append({'code':'count_boolean_expression','step':step['id'],'message':'count counts non-null values, including False. If counting matching rows, filter by the predicate before count.'})
    target={x['scale'] for x in unit_facts(question,'question') if x['dimension']=='currency'}
    source=set()
    used={s.get('table') for s in plan.get('steps',[]) if s.get('table') in tables}
    for table in used:
        source.update(x['scale'] for x in metadata(tables[table])['unit_candidates'] if x['dimension']=='currency')
    if len(target)==1 and len(source)==1 and source!=target:
        warnings.append({'code':'currency_conversion_required','source_scale':next(iter(source)), 'target_scale':next(iter(target)),
                         'message':'Source and requested currency scales differ. Verify conversion in the actual calculation; this warning does not assert conversion is absent.'})
    return {'reads':reads,'warnings':warnings,'status':'needs_verification' if warnings else 'no_specific_warning',
            'semantic_completeness':'unconfirmed','note':'No warning is not proof of complete data or correct interpretation.'}


def execution_audit(plan,result,preflight):
    steps={s['id']:s for s in plan['steps']};trace={s['id']:s for s in result['trace']};rows=[]
    for ident,step in steps.items():
        event=trace.get(ident,{})
        input_id=step.get('input')
        rows.append({'id':ident,'op':step['op'],'input_rows':trace.get(input_id,{}).get('row_count'),
                     'output_rows':event.get('row_count'),'scalar':event.get('scalar'),
                     'observed_coverage':event.get('observed_coverage'),
                     'output_kind':'rows' if event.get('row_count') is not None else 'scalar'})
    return {'steps':rows,'scope':preflight['scope'],'output_value_count':result['value_count'],
            'evidence_count':result['evidence_count'],'note':'Execution evidence and warnings, not a correctness certificate.'}
