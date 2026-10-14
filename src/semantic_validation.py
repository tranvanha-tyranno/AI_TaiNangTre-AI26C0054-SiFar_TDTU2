"""Check explicit units, category coverage and ranking labels without gold."""
from collections import Counter
from decimal import Decimal
import re
from openpyxl.utils.cell import coordinate_to_tuple
from .answer_contract import ancestors
from .tools.executor import PlanError, number


def requested_rank_labels(question):
    match=re.search(r'\brank\b[^:]*:\s*(.*?)\.\s*answer',question,re.I|re.S)
    if not match: return []
    labels=[re.sub(r'^and\s+','',s.strip(),flags=re.I) for s in match.group(1).split(',')]
    return labels if len(labels)>1 else []


def validate_rank_labels(question,result):
    labels=requested_rank_labels(question)
    if labels and Counter(label.casefold() for label in labels)!=Counter(v.casefold() for v in result['values']):
        raise PlanError(f'Ranking must return each requested row/category name exactly once: {labels}. '
                        'Return the original row label (preserve it with unpivot.keep_columns if needed), '
                        'not the repeated heading of the metric column. Use aliases only for names in the question.')


def has_scale(plan,factor):
    target=Decimal(str(factor))
    def literal(expr):
        if not isinstance(expr,dict) or set(expr)!={'value'}: return None
        try: return number(expr['value'])
        except PlanError: return None
    def walk(expr):
        if not isinstance(expr,dict): return False
        if 'mul' in expr and isinstance(expr['mul'],list):
            if any(literal(arg)==target for arg in expr['mul']): return True
        if 'div' in expr and isinstance(expr['div'],list) and len(expr['div'])==2:
            if literal(expr['div'][1])==Decimal(1)/target: return True
        return any(walk(child) for value in expr.values() if isinstance(value,list) for child in value)
    return any(walk(step.get('expr')) for step in ancestors(plan) if step['op'] in {'calculate','derive','aggregate','group'})


def validate_semantics(question,contract,plan,result,regions):
    problems=[]
    factor=contract.get('unit_scale')
    if factor and not has_scale(plan,factor):
        problems.append(f'Explicit unit conversion is missing: multiply the computed value by {factor} '
                        f'(or divide by {1/factor:g}); decimals only rounds, it does not change units.')
    scope=contract.get('category_scope')
    intent=re.split(r'\banswer\b|chỉ trả',question,flags=re.I)[0]
    if scope and contract.get('reduction')=='sum' and not re.search(r'\b(?:where|having|whose|with)\b',intent,re.I):
        noun=scope['noun']
        singular={'sectors':'sector','industries':'industry','categories':'category',
                  'regions':'region','departments':'department','products':'product'}[noun]
        sources=result.get('evidence_full',result.get('evidence',[]))
        numeric_by_sheet={}
        by_sheet={}
        for region in regions: by_sheet.setdefault(region.sheet,{}).update(region.cells)
        for ref in sources:
            sheet,coordinate=ref.rsplit('!',1)
            try:
                row,col=coordinate_to_tuple(coordinate)
                number(by_sheet.get(sheet,{}).get((row,col)))
            except (ValueError,PlanError): continue
            numeric_by_sheet.setdefault(sheet,set()).add(row)
        for region in regions:
            used=numeric_by_sheet.get(region.sheet,set())
            if not used: continue
            for dimension in region.row_dimensions():
                if not any(label.strip().casefold() in {singular,noun} for label in dimension['headers']): continue
                candidates=dimension['data_rows']
                if used & set(dimension['total_rows']): continue  # An explicit printed total is valid.
                if len(candidates)<2: continue
                labels={str(region.cells[(r,dimension['column_index'])]).strip() for r in candidates}
                required=scope.get('count')
                if required is not None and len(labels)!=required: continue  # Ambiguous region; do not assert coverage.
                consumed=used & set(candidates)
                if len(consumed)<len(candidates):
                    problems.append(f'Sum across {noun} needs all {len(candidates)} data ROWS in '
                        f'{region.sheet} ({candidates[0]}..{candidates[-1]}), but numeric result sources cover '
                        f'{len(consumed)}. Use read plus aggregate sum down the selected metric column; '
                        'sum_columns only sums across ONE row. Unused read steps do not compute a total.')
                    break
            if problems and any('data ROWS' in p for p in problems): break
    if problems: raise PlanError(' '.join(problems))
