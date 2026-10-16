"""Provider schemas and local validation, without a network dependency."""
import copy
import re
from ..tools.executor import PlanError


def obj(properties, required=None):
    return {'type':'object','properties':properties,'required':list(properties) if required is None else required,
            'additionalProperties':False}


TEXT={'type':'string','minLength':1,'maxLength':600}
def array(item, maximum=20, minimum=0):
    return {'type':'array','items':item,'maxItems':maximum,'minItems':minimum}


SPEC=obj({
    'language':TEXT,
    'requirements':array(obj({'id':{'type':'string','pattern':'^[a-z][a-z0-9_]{0,30}$'},
        'kind':{'enum':['metric','scope','period','condition','unit','output']},
        'description':TEXT,'quote':TEXT}),minimum=1),
    'operation':TEXT,
    'output_count':{'type':['integer','null'],'minimum':1,'maximum':1000},
    'fields':array(obj({'name':TEXT,'type':{'enum':['label','number','boolean','date','text']},
        'decimals':{'type':['integer','null'],'minimum':0,'maximum':10},'quote':TEXT}),maximum=10,minimum=1),
    'separator':{'type':'string','maxLength':10},
    'ambiguities':array(TEXT,maximum=5)})


def schema(purpose):
    from ..planner import tool_schema
    if purpose=='v3_spec': return copy.deepcopy(SPEC)
    base=copy.deepcopy(tool_schema('plan'))
    for operation in ('parse_number','parse_date'):
        base['$defs']['expr']['properties'][operation]={'type':'array','minItems':2,'maxItems':2,
            'items':{'$ref':'#/$defs/expr'}}
    plan,inspection=base['anyOf']
    # Explicit complex operations compile into the same audited executor.
    steps=plan['properties']['steps']['items']['anyOf']
    steps.append(obj({'id':TEXT,'op':{'enum':['weighted_mean']},'input':TEXT,
        'value':{'$ref':'#/$defs/expr'},'weight':{'$ref':'#/$defs/expr'}}))
    steps.append(obj({'id':TEXT,'op':{'enum':['percent_change']},
        'old':{'$ref':'#/$defs/expr'},'new':{'$ref':'#/$defs/expr'}}))
    for step in steps:
        if step['properties']['op']['enum'][0] in {'aggregate','group'}:
            step['properties']['metric']['enum'] += ['median']
    coverage=array(obj({'requirement':TEXT,'table':TEXT,'range':TEXT,'rationale':TEXT}),maximum=40,minimum=1)
    ready=obj({'action':{'enum':['plan']},'coverage':coverage,'plan':plan})
    # Existing inspections plus schema, exact cell context, and bounded profiling.
    requests=inspection['properties']['requests']['items']['anyOf']
    for operation,props in [
        ('table_schema',{'table':TEXT}),
        ('read_cell',{'table':TEXT,'cell':TEXT}),
        ('profile',{'table':TEXT,'column':TEXT})]:
        requests.append(obj({'op':{'enum':[operation]},**props}))
    inspection['properties']['missing_requirements']=array(TEXT,minimum=1)
    inspection['required'].append('missing_requirements')
    unavailable=obj({'action':{'enum':['unanswerable']},'reason':TEXT})
    if purpose=='v3_review': return tool_schema('review')
    revised=obj({'action':{'enum':['revise_spec']},'reason':TEXT,'spec':copy.deepcopy(SPEC)})
    return {'$defs':base['$defs'],'anyOf':[ready,inspection,unavailable,revised]}


def validate(value, rule, root=None, path='$'):
    """Validate the finite JSON-schema subset used by our provider contracts."""
    root=root or rule
    if '$ref' in rule:
        target=root
        for part in rule['$ref'].split('/')[1:]: target=target[part]
        return validate(value,target,root,path)
    if 'anyOf' in rule:
        errors=[]
        for alternative in rule['anyOf']:
            try: validate(value,alternative,root,path);return
            except PlanError as error: errors.append(str(error))
        raise PlanError(f'{path}: does not match allowed schemas: '+ ' | '.join(errors)[:1500])
    if 'enum' in rule and value not in rule['enum']: raise PlanError(f'{path}: expected {rule["enum"]}')
    kinds=rule.get('type',[]);kinds=[kinds] if isinstance(kinds,str) else kinds
    checks={'object':lambda:isinstance(value,dict),'array':lambda:isinstance(value,list),
            'string':lambda:isinstance(value,str),'integer':lambda:type(value) is int,
            'number':lambda:type(value) in (int,float),'boolean':lambda:type(value) is bool,'null':lambda:value is None}
    if kinds and not any(checks[k]() for k in kinds): raise PlanError(f'{path}: expected {kinds}')
    if isinstance(value,dict):
        missing=set(rule.get('required',[]))-value.keys()
        if missing: raise PlanError(f'{path}: missing {sorted(missing)}')
        props=rule.get('properties',{})
        for key,item in value.items():
            if key in props: validate(item,props[key],root,f'{path}.{key}')
            elif rule.get('additionalProperties') is False: raise PlanError(f'{path}: unsupported field {key}')
            elif isinstance(rule.get('additionalProperties'),dict): validate(item,rule['additionalProperties'],root,f'{path}.{key}')
        if len(value)<rule.get('minProperties',0) or len(value)>rule.get('maxProperties',100000): raise PlanError(f'{path}: invalid property count')
    if isinstance(value,list):
        if not rule.get('minItems',0)<=len(value)<=rule.get('maxItems',100000): raise PlanError(f'{path}: invalid array length')
        for i,item in enumerate(value): validate(item,rule.get('items',{}),root,f'{path}[{i}]')
    if isinstance(value,str):
        if not rule.get('minLength',0)<=len(value)<=rule.get('maxLength',1000000): raise PlanError(f'{path}: invalid string length')
        if 'pattern' in rule and not re.search(rule['pattern'],value): raise PlanError(f'{path}: invalid identifier')
    if type(value) in (int,float) and not rule.get('minimum',float('-inf'))<=value<=rule.get('maximum',float('inf')):
        raise PlanError(f'{path}: number outside bounds')


def check_spec(spec, question):
    validate(spec,SPEC)
    ids=[r['id'] for r in spec['requirements']]
    if len(ids)!=len(set(ids)): raise PlanError('Duplicate requirement IDs')
    for item in spec['requirements']+spec['fields']:
        if item['quote'] not in question: raise PlanError('Every requirement/field must quote the original question verbatim')
    return spec
