"""Compile complex arithmetic into audited Decimal operations; validate first."""
from copy import deepcopy
import re
from ..tools.executor import PlanError, execute, format_value, number
from .contracts import schema, validate


def compile_plan(plan):
    cloned=deepcopy(plan);steps=[]
    existing={step['id'] for step in cloned['steps']}
    def unique(base):
        candidate=base[:24];index=0
        while candidate in existing:
            index+=1;candidate=base[:20]+'_'+str(index)
        existing.add(candidate);return candidate
    for step in cloned['steps']:
        if step['op']=='weighted_mean':
            product=unique('wm_product');numerator=unique('wm_numerator');denominator=unique('wm_denominator')
            steps.extend([
                {'id':product,'op':'derive','input':step['input'],'column':product,'expr':{'mul':[step['value'],step['weight']]}},
                {'id':numerator,'op':'aggregate','input':product,'metric':'sum','expr':{'col':product}},
                {'id':denominator,'op':'aggregate','input':step['input'],'metric':'sum','expr':step['weight']},
                {'id':step['id'],'op':'calculate','expr':{'div':[{'ref':numerator},{'ref':denominator}]}}])
        elif step['op']=='percent_change':
            steps.append({'id':step['id'],'op':'calculate','expr':{'mul':[{'div':[{'sub':[step['new'],step['old']]},step['old']]},{'value':100}]}})
        else: steps.append(step)
    if len(steps)>25: raise PlanError('Compiled plan exceeds 25 steps; simplify it')
    cloned['steps']=steps
    # Final formatting is owned by the multilingual specification, per field.
    cloned['output'].pop('decimals',None)
    return cloned


def preflight(plan,regions):
    """Structural/type/reference checks run before executing any tool."""
    rule=schema('v3_plan');validate(plan,rule['anyOf'][0]['properties']['plan'],rule)
    known={};tables={r.id:r for r in regions}
    row_ops={'read','concat','unpivot','filter','derive','sort','take','select','group','join','lag','fill_down','record'}
    def refs(expr):
        if isinstance(expr,dict):
            if 'ref' in expr and known.get(expr['ref'])!='scalar': raise PlanError(f'Invalid preceding scalar ref {expr["ref"]}')
            for item in expr.values(): refs(item)
        elif isinstance(expr,list):
            for item in expr: refs(item)
    for step in plan['steps']:
        ident=step['id'];op=step['op']
        if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{0,30}',ident) or ident in known: raise PlanError('Invalid/duplicate step id')
        for key in ('table','label_table'):
            if key in step and step[key] not in tables: raise PlanError(f'{ident}: unknown table {step[key]}')
        for key in ('input','left','right'):
            if key in step and known.get(step[key])!='rows': raise PlanError(f'{ident}: {key} must name preceding row result')
        for key in step.get('inputs',[]):
            if key not in known: raise PlanError(f'{ident}: unknown input {key}')
            if op=='concat' and known[key]!='rows': raise PlanError('concat requires row inputs')
        for key in ('expr','where','value','weight','old','new','fields'): refs(step.get(key))
        known[ident]='rows' if op in row_ops else 'scalar'
        if op=='collect': known[ident]='rows'
    output=plan['output']
    if output['step'] not in known: raise PlanError('Output references nonexistent step')
    if known[output['step']]=='rows' and not output.get('columns'): raise PlanError('Row output requires columns')


def run(plan,regions):
    preflight(plan,regions)
    compiled=compile_plan(plan)
    # Compiled steps use only the existing finite tool executor, never generated code.
    return execute(compiled,regions),compiled


def format_answer(result,spec):
    values=result['values'];fields=spec['fields']
    if spec['output_count'] is not None and len(values)!=spec['output_count']:
        raise PlanError(f'Output count: expected {spec["output_count"]}, got {len(values)}')
    if len(values)%len(fields): raise PlanError('Output values do not match ordered field layout')
    formatted=[]
    for i,value in enumerate(values):
        field=fields[i%len(fields)]
        if field['type']=='number':
            number(value)
            formatted.append(format_value(number(value),{'decimals':field['decimals']}))
        elif field['type']=='boolean':
            if value not in {'Yes','No'}: raise PlanError('Boolean output must be Yes or No')
            formatted.append(value)
        else: formatted.append(value)
    return spec['separator'].join(formatted)
