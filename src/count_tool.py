"""Compile a bounded declarative count request to the existing grounded DSL."""
from copy import deepcopy
from openpyxl.utils import get_column_letter
from .tools.executor import PlanError, number

NUMERIC={'number_eq','number_ne','number_gt','number_ge','number_lt','number_le'}
TEXT={'text_eq','text_ne','text_contains'}
UNARY={'is_number','is_null','not_empty'}
OPS=NUMERIC|TEXT|UNARY|{'digits'}

GUIDANCE='''For a row count with flat conditions, prefer one count_rows request instead of constructing derive/join/aggregate steps:
{"action":"count_rows","table":"OBSERVED_TABLE_ID","start_row":3,"end_row":99,"combine":"all","missing":"exclude","conditions":[{"column":"OBSERVED_COLUMN","op":"number_gt","value":5}]}
Use actual table IDs, column letters and row bounds from workbook evidence, and values from the question. all=AND, any=OR. Numeric operators number_eq/ne/gt/ge/lt/le accept either a numeric value OR other_column. Text operators text_eq/ne/text_contains accept a string value; trim whitespace, preserve code leading zeros; text_eq/ne are case-sensitive, text_contains is case-insensitive. digits requires the requested integer digit count, not numeric bounds. is_number/is_null/not_empty take no value. missing=exclude makes an invalid numeric comparison False; missing=error reports it. Choose explicitly from the question/data; never silently treat missing as zero. digits checks actual decimal digits, not arbitrary text length. Conditions=[] counts all rows in the declared bounds, including any headers/totals you failed to exclude. The tool does not infer annual scope, groups or missing predicates. Inspect if uncertain. If nested logic or joins are required, use the existing standard plan instead. Return counts, not guessed answers.
'''
REVIEW_NOTE='count_rows was compiled deterministically into read/filter/count. digit_length returns the number of decimal digits for a digit string or integral numeric code, preserving textual leading zeros; otherwise 0. Review scope, column bindings and conditions against evidence; no automatic semantic completeness is claimed.'


def schema():
    from .planner import tool_schema
    base=deepcopy(tool_schema('plan'))
    condition={'type':'object','properties':{
        'column':{'type':'string'},'op':{'enum':sorted(OPS)},
        'value':{'type':['string','number','boolean','null']},'other_column':{'type':'string'}},
        'required':['column','op'],'additionalProperties':False}
    count={'type':'object','properties':{
        'action':{'enum':['count_rows']},'table':{'type':'string'},
        'start_row':{'type':'integer'},'end_row':{'type':'integer'},
        'combine':{'enum':['all','any']},'missing':{'enum':['error','exclude']},
        'conditions':{'type':'array','maxItems':12,'items':condition}},
        'required':['action','table','start_row','end_row','combine','missing','conditions'],
        'additionalProperties':False}
    base['anyOf'].insert(0,count)
    return base


def compile_count(request, regions):
    required={'action','table','start_row','end_row','combine','missing','conditions'}
    if not isinstance(request,dict) or set(request)!=required or request['action']!='count_rows':
        raise PlanError('count_rows requires exactly action/table/start_row/end_row/combine/missing/conditions.')
    region=next((r for r in regions if r.id==request['table']),None)
    if region is None:raise PlanError('count_rows unknown table; inspect a real table first.')
    start,end=request['start_row'],request['end_row']
    if type(start)!=int or type(end)!=int or not region.start_row<=start<=end<=region.end_row:
        raise PlanError('count_rows bounds must stay inside the observed table.')
    if (not isinstance(request['combine'],str) or request['combine'] not in {'all','any'}
            or not isinstance(request['missing'],str) or request['missing'] not in {'error','exclude'}):
        raise PlanError('count_rows requires explicit combine all/any and missing error/exclude.')
    conditions=request['conditions']
    if not isinstance(conditions,list) or len(conditions)>12:raise PlanError('count_rows allows 0..12 flat conditions.')
    if not conditions and request['combine']=='any':raise PlanError('count_rows with no conditions requires combine=all to count all declared rows.')
    columns={get_column_letter(c) for c in range(region.start_col,region.end_col+1)}|{'_row','_section','_sheet','_section_row'}
    predicates=[]
    for condition in conditions:
        if not isinstance(condition,dict) or not {'column','op'}<=set(condition) or set(condition)-{'column','op','value','other_column'}:
            raise PlanError('count_rows condition needs column/op and only value or other_column when applicable.')
        column,op=condition['column'],condition['op']
        if not isinstance(column,str) or column not in columns:raise PlanError(f'count_rows unknown column {column}; available={sorted(columns)}.')
        if not isinstance(op,str) or op not in OPS:raise PlanError('count_rows unsupported condition operator.')
        left={'col':column};extras=set(condition)-{'column','op'}
        if op in UNARY:
            if extras:raise PlanError(f'count_rows {op} takes no value or other_column.')
            predicate={'not':[{'is_null':[left]}]} if op=='not_empty' else {op:[left]}
        elif op=='digits':
            value=condition.get('value')
            if extras!={'value'} or type(value)!=int or not 1<=value<=30:
                raise PlanError('count_rows digits requires an integer value 1..30.')
            predicate={'eq':[{'digit_length':[left]},{'value':value}]}
        elif op in TEXT:
            if extras!={'value'} or not isinstance(condition['value'],str):raise PlanError('count_rows text condition requires a string value.')
            predicate={op.removeprefix('text_'):[{'trim':[left]},{'value':condition['value'].strip()}]}
        else:
            operands=[left]
            if extras=={'other_column'}:
                other=condition['other_column']
                if not isinstance(other,str) or other not in columns:raise PlanError('count_rows unknown comparison column.')
                right={'col':other};operands.append(right)
            elif extras=={'value'} and type(condition['value']) in {int,float}:
                number(condition['value'])  # Reject nonfinite/extreme constants without guessing.
                right={'value':condition['value']}
            else:raise PlanError('count_rows numeric condition needs one finite numeric value OR other_column.')
            predicate={op.removeprefix('number_'):[{'number':[left]},{'number':[right]}]}
            if request['missing']=='exclude':
                predicate={'and':[*({'is_number':[v]} for v in operands),predicate]}
        predicates.append(predicate)
    steps=[{'id':'count_source','op':'read','table':region.id,'start_row':start,'end_row':end}]
    source='count_source'
    if predicates:
        where=predicates[0] if len(predicates)==1 else {'and' if request['combine']=='all' else 'or':predicates}
        steps.append({'id':'count_filtered','op':'filter','input':source,'where':where});source='count_filtered'
    steps.append({'id':'count_result','op':'aggregate','input':source,'metric':'count'})
    return {'steps':steps,'output':{'step':'count_result'},
            'answer_spec':{'answer_type':'number','answer_field':'records','operation':'count','metric':'Rows satisfying declared conditions'}}
