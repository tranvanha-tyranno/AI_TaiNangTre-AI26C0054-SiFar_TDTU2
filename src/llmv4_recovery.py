"""Bounded transport and dependency spelling repairs; no invented semantics."""
import copy
import json
from .planner import parse_plan


def _outside_whitespace(value):
    out=[];quoted=False;escaped=False;i=0;edits=0
    while i<len(value):
        char=value[i]
        if quoted:
            out.append(char)
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
        elif char=='"':quoted=True;out.append(char)
        elif value[i:i+2] in ('\\n','\\r','\\t'):
            out.append(' ');i+=1;edits+=1
        else:out.append(char)
        i+=1
    return ''.join(out),edits


def parse_response(content, repairs):
    try:return parse_plan(content,repairs)
    except (ValueError,TypeError):
        # Decode only transport whitespace outside JSON strings. Leave cell
        # labels, literals, operators, quotes and commas exactly as supplied.
        candidate=json.loads(content)
        if not isinstance(candidate,dict) or not isinstance(candidate.get('steps'),str):raise
        cleaned,edits=_outside_whitespace(candidate['steps'])
        if not edits:raise
        candidate['steps']=cleaned
        local=[]
        plan=parse_plan(json.dumps(candidate,ensure_ascii=False),local)
        repairs.extend([{'kind':'encoded_steps_transport_whitespace','edits':edits},*local])
        return plan


def normalize_dependencies(plan):
    result=copy.deepcopy(plan);changes=[]
    steps=result.get('steps')
    if not isinstance(steps,list):return result,changes
    for i,step in enumerate(steps):
        if i==0 or not isinstance(step,dict) or step.get('op')!='derive':continue
        previous=steps[i-1]
        if not isinstance(previous,dict) or previous.get('op')!='lag':continue
        if step.get('input')!=previous.get('input'):continue
        ident,column=previous.get('id'),previous.get('column')
        if not isinstance(column,str) or not isinstance(ident,str):continue
        needed=False
        def visit(expr):
            nonlocal needed
            if isinstance(expr,dict):
                if expr=={'col':column}:needed=True
                if ident==column and expr=={'ref':ident}:
                    needed=True
                    return {'col':column}
                return {key:visit(value) for key,value in expr.items()}
            if isinstance(expr,list):return [visit(value) for value in expr]
            return expr
        expression=visit(step.get('expr'))
        if needed:
            step['input']=ident;step['expr']=expression
            changes.append({'step':step.get('id'),'kind':'immediate_lag_row_dependency','input':ident,'column':column})
    output=result.get('output')
    if isinstance(output,dict):
        digits=output.get('decimals')
        if isinstance(digits,list) and digits and all(type(n) is int and n==digits[0] and 0<=n<=10 for n in digits):
            output['decimals']=digits[0]
            changes.append({'kind':'uniform_output_decimals','decimals':digits[0]})
    return result,changes
