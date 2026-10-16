"""Resolve an explicit comparison direction against observed row identities."""
import re
import unicodedata
from openpyxl.utils import column_index_from_string
from .tools.executor import number, PlanError


def norm(value):
    return re.sub(r'[^\w]', '', unicodedata.normalize('NFKC', str(value)).casefold())


def relation(question):
    q=unicodedata.normalize('NFKC',question).casefold()
    if re.search(r'\bsigned\b|\bnet change\b|new\s*[-−]\s*old|带符号|有符号|正负|có dấu|thay đổi ròng',q):
        return None
    patterns=[
        (r'(?:^|[,;])(?P<subject>[^,;?]+?)比(?P<reference>[^,;?]+?)(?P<direction>低|高)(?:了)?多少(?:个)?百分点', {'低':'lower','高':'higher'}),
        (r'how (?:much|many (?:percentage )?points?) (?P<direction>lower|higher) (?:is|was|are|were) (?P<subject>.+?) than (?P<reference>[^?;.]+)', {}),
        (r'(?:^|[,;])(?P<subject>[^,;?]+?) (?P<direction>thấp hơn|cao hơn) (?P<reference>[^,;?]+?) bao nhiêu(?: điểm phần trăm)?', {'thấp hơn':'lower','cao hơn':'higher'}),
    ]
    for pattern,mapping in patterns:
        match=re.search(pattern,q)
        if match:
            return {'subject':match['subject'],'reference':match['reference'],
                    'direction':mapping.get(match['direction'],match['direction'])}
    return None


def normalize_difference(plan, question, regions):
    """Mutate a copied plan only when both operands have unique source bindings.

    Lower means reference-subject; higher means subject-reference. A genuine
    negative directional difference remains negative. No blanket abs operation.
    """
    comparison=relation(question)
    if not comparison:return []
    steps={s.get('id'):s for s in plan.get('steps',[]) if isinstance(s,dict)}
    final=steps.get(plan.get('output',{}).get('step'),{})
    if final.get('op')!='calculate' or plan.get('answer_spec',{}).get('operation')!='difference':return []
    expr=final.get('expr')
    if not isinstance(expr,dict) or set(expr)!={'sub'}:return []
    operands=expr['sub']
    if not isinstance(operands,list) or len(operands)!=2:return []
    cells=[];tables={r.id:r for r in regions}
    for operand in operands:
        if not isinstance(operand,dict) or set(operand)!={'ref'}:return []
        if not isinstance(operand['ref'],str):return []
        source=steps.get(operand['ref'],{})
        if source.get('op')!='cell':return []
        region=tables.get(source.get('table'))
        row,column=source.get('row'),source.get('column')
        if region is None or not isinstance(row,int) or not isinstance(column,str):return []
        try:
            col=column_index_from_string(column)
            number(region.cells.get((row,col)))
        except (ValueError,TypeError,PlanError):return []
        if not region.start_row<=row<=region.end_row or not region.start_col<=col<=region.end_col:return []
        labels=[]
        for c in range(region.start_col,region.end_col+1):
            value=region.cells.get((row,c))
            if not isinstance(value,str) or not value.strip():continue
            try:number(value)
            except PlanError:labels.append(value)
        cells.append({'operand':operand,'labels':labels,'sheet':region.sheet,'column':column,
                      'source':f'{region.sheet}!{column}{row}'})
    # Same metric/period column; otherwise row labels alone cannot establish roles.
    if (cells[0]['sheet'],cells[0]['column'])!=(cells[1]['sheet'],cells[1]['column']):return []
    bindings={}
    for role in ('subject','reference'):
        fragment=norm(comparison[role])
        scores=[max((len(norm(label)) for label in cell['labels'] if norm(label) and norm(label) in fragment),default=0) for cell in cells]
        best=max(scores)
        if best==0 or scores.count(best)!=1:return []
        bindings[role]=scores.index(best)
    if bindings['subject']==bindings['reference']:return []
    first='reference' if comparison['direction']=='lower' else 'subject'
    second='subject' if first=='reference' else 'reference'
    order=[bindings[first],bindings[second]]
    if order==[0,1]:return []
    expr['sub']=[cells[i]['operand'] for i in order]
    return [{'kind':'grounded_comparison_direction','step':final['id'],
             'direction':comparison['direction'],'subject_source':cells[bindings['subject']]['source'],
             'reference_source':cells[bindings['reference']]['source'],
             'formula':f'{first}-{second}'}]
