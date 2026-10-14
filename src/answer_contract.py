"""Infer answer shape from question wording; never consult references."""
import re
import unicodedata
from .tools.executor import PlanError

COUNTS={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,
        'một':1,'hai':2,'ba':3,'bốn':4,'năm':5}


def count_value(text):
    return int(text) if text.isdigit() else COUNTS.get(text)


def infer_answer_contract(question):
    q=re.sub(r'\s+',' ',unicodedata.normalize('NFKC',question).lower()).strip()
    # A quoted row/header name such as "Total, 16 years and over" is a
    # lookup target, not an instruction to sum its detail rows again.
    intent_q=re.sub(r'"[^"]*"|`[^`]*`','',q)
    contract={'kind':'unknown','count':None,'reduction':None,'rank_offset':None,'decimals':None,
              'yes_no':bool(re.search(r'\byes\s*(?:or|/)\s*no\b',q))}
    list_request=bool(re.search(r'\b(?:list|rank)\b|liệt kê|xếp hạng|(?:separated|separate).*comma',q))
    multiple=re.search(r'\b(\d+|two|three|four|five) (?:(?:order|product|person) )?(?:integers|sector names|industry names|ids|codes|values|names)\b',q)
    top=re.search(r'\btop\s+(\d+|one|two|three|four|five|ten)\b',q)
    position=re.search(r'\b(?:at|in) position\s+(\d+)\b|vị trí (\d+)\b',q)
    if position:
        contract.update(kind='scalar',count=1,rank_offset=int(position.group(1) or position.group(2))-1)
    elif multiple:
        contract.update(kind='list',count=count_value(multiple.group(1)))
        if re.search(r'\b(?:top|lowest|highest)\b',q): contract['rank_offset']=0
    elif top and list_request:
        contract.update(kind='list',count=count_value(top.group(1)),rank_offset=0)
    elif re.search(r'two integers|men,\s*women',q):
        contract.update(kind='list',count=2)
    elif list_request:
        contract['kind']='list'
    elif re.search(r'\banswer (?:with )?(?:only|the|exactly|to)\b|chỉ (?:trả|ghi|đưa ra)|\b(?:what is|how many|who was|who is|which\b.*(?:has|is))\b',q):
        contract.update(kind='scalar',count=1)
    if contract['yes_no']: contract.update(kind='scalar',count=1)
    label_request=bool(re.search(r'^which\b|what is the (?:id|name|code|sector|industry|category)\b',q))
    if not list_request and not label_request and re.search(r'\baverage\b|trung bình',intent_q): contract['reduction']='mean'
    elif not list_request and not label_request and re.search(r'\b(?:sum|total)\b|\btổng\b',intent_q): contract['reduction']='sum'
    elif re.search(r'^how many(?! more)|^có bao nhiêu|^bao nhiêu',q): contract['reduction']='count'
    if contract['reduction'] and contract['kind']=='unknown': contract.update(kind='scalar',count=1)
    decimals=re.search(r'(?:exactly|to|with)\s+(\d+|two|three|four) decimal places|(?:two|exactly two) decimals|hai (?:chữ số|số) thập phân',q)
    if decimals:
        contract['decimals']=count_value(decimals.group(1)) if decimals.group(1) else 2
    # Integer ID/code questions must preserve identifiers, including leading 0.
    contract['integer']=bool(re.search(r'\bintegers?\b|số nguyên',q))
    contract['unit_scale']=None
    if re.search(r'\bmultiply\b[^)]{0,80}\b(?:by\s+)?100\b',q): contract['unit_scale']=100
    elif re.search(r'from thousands (?:into|to) (?:individual |actual )?(?:people|persons|units)',q): contract['unit_scale']=1000
    elif re.search(r'from millions (?:into|to) (?:individual |actual )?(?:people|persons|units)',q): contract['unit_scale']=1000000
    category=re.search(r'\b(?:across|over|among)\s+(?:all|the\s+(\d+)|(\d+))\s+(sectors|industries|categories|regions|departments|products)\b',intent_q)
    contract['category_scope']=({'noun':category.group(3),'count':int(category.group(1) or category.group(2)) if category.group(1) or category.group(2) else None} if category else None)
    return contract


def ancestors(plan):
    steps={s['id']:s for s in plan['steps']}; visited={}
    def walk(ident):
        if ident in visited or ident not in steps: return
        step=steps[ident];visited[ident]=step
        for key in ('input','left','right'):
            if key in step: walk(step[key])
        for source in step.get('inputs',[]): walk(source)
        def expr_refs(value):
            if isinstance(value,dict):
                if 'ref' in value: walk(value['ref'])
                for child in value.values(): expr_refs(child)
            elif isinstance(value,list):
                for child in value: expr_refs(child)
        expr_refs(step.get('expr'));expr_refs(step.get('where'))
    walk(plan['output']['step'])
    return list(visited.values())


def validate_answer_contract(contract,plan,result):
    count=contract['count']
    reduction=contract['reduction']
    lineage=ancestors(plan)
    if count is not None and result['value_count']!=count:
        if reduction:
            hint=f'Compute aggregate metric={reduction} after filtering, and return the scalar; do not list input cells.'
        elif contract['rank_offset'] is not None:
            hint=f'After sort, use take offset={contract["rank_offset"]}, limit={count}, then output only the requested column.'
        else:
            hint='Return only the requested field(s). For a highest/lowest label, sort, take limit=1, output the label.'
        raise PlanError(f'Answer contract requires {count} final value(s), got {result["value_count"]}. {hint}')
    # Enforce the requested rank against the actual dependency chain. A top-3
    # result must not be an arbitrary slice elsewhere in an unused branch.
    if contract['rank_offset'] is not None and any(s['op']=='sort' for s in lineage):
        takes=[s for s in lineage if s['op']=='take']
        if not any(s.get('offset',0)==contract['rank_offset'] and s.get('limit',1)==count for s in takes):
            raise PlanError(f'Ranking requires take offset={contract["rank_offset"]}, limit={count} on the sorted output.')
    final=next(s for s in lineage if s['id']==plan['output']['step'])
    if reduction and final['op'] not in {'cell','sum_columns','calculate','aggregate'}:
        if not any(s['op'] in {'aggregate','group'} and s.get('metric')==reduction for s in lineage):
            raise PlanError(f'Question requires a computed {reduction}, but the output is unreduced rows. '
                            f'Use aggregate metric={reduction} on the intended data, or an explicit total cell.')
    if contract['yes_no'] and result['answer'] not in {'Yes','No'}:
        raise PlanError('Question requires Yes or No. Use a boolean comparison on computed scalar refs, not a numeric cell.')
    if contract['decimals'] is not None:
        digits=contract['decimals']
        pattern=rf'-?\d+\.\d{{{digits}}}' if digits else r'-?\d+'
        if any(not re.fullmatch(pattern,v) for v in result['values']):
            raise PlanError(f'Question requires exactly {digits} decimal places; set output.decimals={digits}.')
    if contract['integer'] and any(not re.fullmatch(r'-?\d+',v) for v in result['values']):
        raise PlanError('Question requires integers without commas or units.')
