"""Canonicalize unambiguous DSL spelling differences before strict execution.

Never infer a source coordinate, metric, filter threshold or answer. The raw
plan and every normalization remain in the question log for auditing.
"""
from copy import deepcopy
import json
from openpyxl.utils import get_column_letter

UNARY={'abs','number','date','lower','trim','length','is_null','is_number','not'}
PREDICATES={'eq','ne','gt','ge','lt','le','contains','starts_with','is_null','is_number','not','and','or'}


def normalize_plan(plan, regions, contract=None, repair_split_literals=False):
    if not isinstance(plan,dict) or not isinstance(plan.get('steps'),list): return plan,[]
    cloned=deepcopy(plan); changes=[]; schemas={}; scalars=set(); output=[]
    if (contract or {}).get('decimals') is not None and isinstance(cloned.get('output'),dict) and cloned['output'].get('decimals') is None:
        cloned['output']['decimals']=contract['decimals']
        changes.append({'kind':'explicit_question_decimals','decimals':contract['decimals']})
    spec=cloned.get('answer_spec')
    if isinstance(spec,dict) and spec.get('answer_field') in (None,'') and isinstance(spec.get('metric'),str) and spec['metric'].strip():
        spec['answer_field']=spec['metric']
        changes.append({'kind':'answer_field_from_declared_metric'})
    index={r.id:r for r in regions}
    def expr(value, columns, step_id, depth=0):
        if depth>15: return value  # Executor owns the nesting limit.
        if not isinstance(value,dict):
            if value is None or isinstance(value,(str,int,float,bool)):
                changes.append({'step':step_id,'kind':'explicit_literal'})
                return {'value':value}
            return value
        # Qwen occasionally emits {"lt":[{"col":"I"}],"value":2000}
        # instead of {"lt":[{"col":"I"},{"value":2000}]}. Preserve the
        # operator and literal, changing only the unambiguous container shape.
        if repair_split_literals and len(value)==2 and 'value' in value and (value['value'] is None or isinstance(value['value'],(str,int,float,bool))):
            operators=[key for key in value if key in {'sub','div','eq','ne','gt','ge','lt','le','contains','starts_with'}]
            if len(operators)==1:
                op=operators[0]; raw=value[op]
                if isinstance(raw,list) and len(raw)==1 and op not in UNARY:
                    changes.append({'step':step_id,'kind':'operator_literal_moved_into_args','operator':op})
                    return {op: [expr(raw[0],columns,step_id,depth+1), {'value':value['value']}]}
        if repair_split_literals and len(value)>1 and all(key in {'and','or','eq','ne','gt','ge','lt','le','contains','starts_with','is_null','is_number','not'} for key in value):
            # A common provider shape for a conjunction is
            # {"contains": [...], "is_number": [...]}; turn it into the
            # declared boolean operator without changing any predicate.
            changes.append({'step':step_id,'kind':'split_boolean_operator_keys','operators':list(value)})
            return {'and':[expr({key:arg},columns,step_id,depth+1) for key,arg in value.items()]}
        if len(value)!=1: return value
        op,arg=next(iter(value.items()))
        if op=='ref':
            if isinstance(arg,str) and arg in columns and arg not in scalars:
                changes.append({'step':step_id,'kind':'row_column_reference','column':arg})
                return {'col':arg}
            return value
        if op in {'col','value'}: return value
        if op in UNARY and isinstance(arg,dict):
            arg=[arg];changes.append({'step':step_id,'kind':'unary_array','operator':op})
        if isinstance(arg,list):
            args=[expr(child,columns,step_id,depth+1) for child in arg]
            if op in {'and','or'} and len(args)==1:
                changes.append({'step':step_id,'kind':'single_boolean_condition'})
                return args[0]
            return {op:args}
        return value
    for step in cloned['steps']:
        if not isinstance(step,dict): output.append(step);continue
        ident=step.get('id');op=step.get('op');columns=schemas.get(step.get('input'),set())
        for key in ['expr','where']:
            if key in step:
                step[key]=expr(step[key],columns,ident)
        if repair_split_literals and op=='filter' and 'missing' in step:
            step.pop('missing');changes.append({'step':ident,'kind':'drop_filter_missing_field'})
        if op=='record' and isinstance(step.get('fields'),dict):
            step['fields']={key:expr(value,columns,ident) if not isinstance(value,str) else value
                            for key,value in step['fields'].items()}
        if (op=='derive' and step.get('input') in scalars and cloned.get('output',{}).get('step')==ident
                and '"col"' not in json.dumps(step.get('expr',{}))):
            step.pop('input');step.pop('column',None);step['op']='calculate';op='calculate'
            changes.append({'step':ident,'kind':'scalar_final_expression'})
        if op=='aggregate' and step.get('metric')=='sum' and isinstance(step.get('expr'),dict) and set(step['expr']) & PREDICATES:
            guard='count_if_'+str(ident)
            if not any(s.get('id')==guard for s in cloned['steps'] if isinstance(s,dict)) and len(cloned['steps'])<25:
                output.append({'id':guard,'op':'filter','input':step.get('input'),'where':step['expr']})
                step.update(input=guard,metric='count');step.pop('expr')
                changes.append({'step':ident,'kind':'boolean_sum_to_count'})
        if op=='read' and step.get('table') in index:
            r=index[step['table']]
            schemas[ident]={get_column_letter(c) for c in range(r.start_col,r.end_col+1)}|{'_row','_sheet','_section','_section_row'}
        elif op in {'derive','lag'}: schemas[ident]=columns|{step.get('column')}
        elif op in {'filter','sort','take','fill_down'}: schemas[ident]=columns
        elif op=='select': schemas[ident]=set(step.get('columns',[]))
        elif op=='unpivot': schemas[ident]=set(step.get('keep_columns',[]))|{'column','label','value','_row'}
        elif op=='record': schemas[ident]=set(step.get('fields',{}))
        elif op=='concat': schemas[ident]=set.intersection(*(schemas.get(s,set()) for s in step.get('inputs',[]))) if step.get('inputs') else set()
        elif op=='collect': schemas[ident]={'value'}
        elif op=='join': schemas[ident]={'left.'+c for c in schemas.get(step.get('left'),set())}|{'right.'+c for c in schemas.get(step.get('right'),set())}
        elif op=='group': schemas[ident]=set(step.get('by',[]))|{step.get('column','value')}
        elif op in {'cell','sum_columns','calculate','aggregate'}: scalars.add(ident)
        output.append(step)
    cloned['steps']=output
    return cloned,changes
