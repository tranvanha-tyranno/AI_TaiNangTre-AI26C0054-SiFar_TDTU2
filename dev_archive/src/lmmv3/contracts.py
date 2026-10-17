"""Provider schemas and local validation, without a network dependency."""
import copy
import re
import math
from ..tools.executor import PlanError


def obj(properties, required=None):
    return {'type':'object','properties':properties,'required':list(properties) if required is None else required,
            'additionalProperties':False}


TEXT={'type':'string','minLength':1,'maxLength':600}
def array(item, maximum=20, minimum=0):
    return {'type':'array','items':item,'maxItems':maximum,'minItems':minimum}


SPEC=obj({
    'language':TEXT,
    'requirements':array(obj({'id':{'type':'string','minLength':1,'maxLength':80},
        'kind':{'type':'string','minLength':1,'maxLength':80},
        'description':TEXT,'quote':{'type':'string','maxLength':600}}),minimum=0),
    'operation':TEXT,
    'output_count':{'type':['integer','null'],'minimum':1,'maximum':1000},
    'fields':array(obj({'name':TEXT,'type':{'enum':['label','number','boolean','date','text']},
        'decimals':{'type':['integer','null'],'minimum':0,'maximum':10},'quote':{'type':'string','maxLength':600}}),maximum=10,minimum=1),
    'separator':{'type':'string','maxLength':10},
    'ambiguities':array(TEXT,maximum=5)})


def schema(purpose, spec=None, catalog=None):
    from ..planner import tool_schema
    if purpose=='v3_spec': return copy.deepcopy(SPEC)
    base=copy.deepcopy(tool_schema('plan'))
    for operation in ('parse_number','parse_date'):
        base['$defs']['expr']['properties'][operation]={'type':'array','minItems':2,'maxItems':2,
            'items':{'$ref':'#/$defs/expr'}}
    plan,inspection=base['anyOf']
    plan['required']=[key for key in plan['required'] if key!='answer_spec']
    # Explicit complex operations compile into the same audited executor.
    steps=plan['properties']['steps']['items']['anyOf']
    steps.append(obj({'id':TEXT,'op':{'enum':['weighted_mean']},'input':TEXT,
        'value':{'$ref':'#/$defs/expr'},'weight':{'$ref':'#/$defs/expr'}}))
    steps.append(obj({'id':TEXT,'op':{'enum':['percent_change']},
        'old':{'$ref':'#/$defs/expr'},'new':{'$ref':'#/$defs/expr'}}))
    for step in steps:
        if step['properties']['op']['enum'][0] in {'aggregate','group'}:
            step['properties']['metric']['enum'] += ['median']
    coverage=array(obj({'requirement':TEXT,'table':TEXT,
        'range':{'anyOf':[TEXT,array(TEXT,maximum=40,minimum=1)]},'rationale':TEXT}),maximum=40)
    ready=obj({'action':{'enum':['plan']},'coverage':coverage,'plan':plan})
    ready['required'].remove('coverage')
    ready['properties']['ambiguity_resolutions']=array(obj({
        'index':{'type':'integer','minimum':0},'requirement':TEXT,'explanation':TEXT}),maximum=5)
    # Existing inspections plus schema, exact cell context, and bounded profiling.
    requests=inspection['properties']['requests']['items']['anyOf']
    for operation,props in [
        ('table_schema',{'table':TEXT}),
        ('read_cell',{'table':TEXT,'cell':TEXT}),
        ('profile',{'table':TEXT,'column':TEXT})]:
        requests.append(obj({'op':{'enum':[operation]},**props}))
    inspection['properties']['missing_requirements']=array(TEXT)
    unavailable=obj({'action':{'enum':['unanswerable']},'reason':TEXT})
    if purpose=='v3_review': return tool_schema('review')
    revised=obj({'action':{'enum':['revise_spec']},'reason':TEXT,'spec':copy.deepcopy(SPEC)})
    if spec:
        ids=[r['id'] for r in spec['requirements']]
        # IDs are hints in metadata. Real table references in executable steps
        # remain strict; a metadata typo must not prevent Python computation.
        inspection['properties']['missing_requirements']['description']='Prefer these requirement IDs: '+', '.join(ids)
    if catalog:
        table_ids=[item['table_id'] for item in catalog]
        for request in requests:
            if 'table' in request['properties']: request['properties']['table']={'type':'string','enum':table_ids}
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
            'string':lambda:isinstance(value,str),'integer':lambda:type(value) is int or (type(value) is float and math.isfinite(value) and value.is_integer()),
            'number':lambda:type(value) in (int,float),'boolean':lambda:type(value) is bool,'null':lambda:value is None}
    if kinds and not any(checks[k]() for k in kinds):
        raise PlanError(f'{path}: expected {kinds}; received {type(value).__name__} {repr(value)[:160]}')
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


def check_spec(spec, question, warnings=None):
    validate(spec,SPEC)
    ids=[r['id'] for r in spec['requirements']]
    if len(ids)!=len(set(ids)): raise PlanError('Duplicate requirement IDs')
    for i,item in enumerate(spec['requirements']+spec['fields']):
        if not item['quote'] or item['quote'] not in question:
            message=f'Unverified question quote at item {i}: {item["quote"]!r}'
            if warnings is None: raise PlanError('Every requirement/field must quote the original question verbatim; '+message)
            warnings.append(message)
    if warnings is not None:
        for item in spec['requirements']:
            if item['kind'] not in {'metric','scope','period','condition','unit','output'}:
                warnings.append(f'Descriptive requirement kind {item["kind"]!r}; review meaning against original question')
    return spec


def normalize_response(response):
    """Repair equivalent container spelling only, preserving computation semantics."""
    cloned=copy.deepcopy(response);changes=[]
    if not isinstance(cloned,dict): return cloned,changes
    if 'steps' in cloned and 'output' in cloned and 'plan' not in cloned:
        nested={k:cloned.pop(k) for k in ('steps','output','answer_spec') if k in cloned}
        cloned.update(action='plan',plan=nested);changes.append('wrap_direct_plan')
    if cloned.get('action')=='inspect':
        cloned.setdefault('missing_requirements',[])
        if isinstance(cloned['missing_requirements'],str): cloned['missing_requirements']=[cloned['missing_requirements']]
    if not isinstance(cloned.get('plan'),dict): return cloned,changes
    cloned.setdefault('coverage',[])
    if cloned['coverage'] is None: cloned['coverage']=[];changes.append('empty_coverage')
    if isinstance(cloned['coverage'],dict): cloned['coverage']=[cloned['coverage']];changes.append('single_coverage_item')
    plan=cloned['plan']
    # answer_spec duplicates the separate specification, not executable logic.
    if 'answer_spec' in plan:
        metadata=plan.pop('answer_spec')
        changes.append({'kind':'advisory_answer_spec','value':metadata})
    for item in cloned['coverage'] if isinstance(cloned['coverage'],list) else []:
        if isinstance(item,dict):
            if 'ranges' in item and 'range' not in item:
                item['range']=item.pop('ranges');changes.append('ranges_alias')
            item.setdefault('requirement','unspecified');item.setdefault('rationale','Planner evidence citation')
    if isinstance(cloned['coverage'],list):
        retained=[]
        for item in cloned['coverage']:
            if isinstance(item,dict) and isinstance(item.get('table'),str) and isinstance(item.get('range'),(str,list)):
                retained.append(item)
            else: changes.append({'kind':'discard_metadata','field':'coverage','value':item})
        cloned['coverage']=retained
    if 'ambiguity_resolutions' in plan:
        if 'ambiguity_resolutions' in cloned and cloned['ambiguity_resolutions']!=plan['ambiguity_resolutions']:
            raise PlanError('Conflicting top-level and nested ambiguity_resolutions')
        cloned['ambiguity_resolutions']=plan.pop('ambiguity_resolutions');changes.append('hoist_ambiguity_resolutions')
    unary={'abs','number','date','lower','trim','length','is_null','is_number','not'}
    def walk(value):
        if isinstance(value,dict):
            if len(value)==1:
                key=next(iter(value))
                if key in unary and isinstance(value[key],dict):
                    value[key]=[value[key]];changes.append('unary_array:'+key)
            for item in value.values(): walk(item)
        elif isinstance(value,list):
            for item in value: walk(item)
    # Restrict repair to expression-bearing fields, never literal dictionaries.
    for step in plan.get('steps',[]):
        if not isinstance(step,dict): continue
        for key in ('expr','where','value','weight','old','new'):
            if key in step: walk(step[key])
        if step.get('op')=='record' and isinstance(step.get('fields'),dict):
            for item in step['fields'].values(): walk(item)
    return cloned,changes


def normalize_spec(spec):
    """Canonicalize numeric/null spelling only; never infer counts or intent."""
    result=copy.deepcopy(spec);changes=[]
    if not isinstance(result,dict): return result,changes
    defaults={'language':'und','requirements':[],'operation':'unspecified','output_count':None,'separator':', ','ambiguities':[]}
    for key,value in defaults.items():
        if key not in result:
            result[key]=value;changes.append({'kind':'missing_metadata_default','path':key,'to':value})
    for field in result.get('fields',[]) if isinstance(result.get('fields'),list) else []:
        if isinstance(field,dict):
            for key,value in [('decimals',None),('quote',''),('name','value')]: field.setdefault(key,value)
    for requirement in result.get('requirements',[]) if isinstance(result.get('requirements'),list) else []:
        if isinstance(requirement,dict):
            requirement.setdefault('quote','');requirement.setdefault('description','Unspecified requirement');requirement.setdefault('kind','unspecified')
    targets=[(result,'output_count','$.output_count')]
    if isinstance(result.get('fields'),list):
        targets.extend((field,'decimals',f'$.fields[{i}].decimals') for i,field in enumerate(result['fields']) if isinstance(field,dict))
    for owner,key,path in targets:
        if key not in owner: continue
        old=owner[key];new=old
        if isinstance(old,str):
            raw=old.strip()
            if raw=='null': new=None
            elif re.fullmatch(r'[+-]?\d+(?:\.0+)?',raw): new=int(raw.split('.')[0])
        elif type(old) is float and math.isfinite(old) and old.is_integer(): new=int(old)
        if type(new) is not type(old):
            owner[key]=new;changes.append({'path':path,'from':old,'from_type':type(old).__name__,'to':new})
    return result,changes
