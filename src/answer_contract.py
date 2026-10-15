"""Infer answer shape from question wording; never consult references."""
import re
import json
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
    elif not list_request and re.search(r'\b(?:absolute )?difference\b|chênh lệch|hiệu tuyệt đối',intent_q): contract['reduction']='difference'
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
    contract['answer_type']=None
    contract['answer_field']=None
    named=re.search(r'\banswer (?:with )?(?:the )?([\w -]{1,40}?) name(?: only)?\b',q)
    which=re.search(r'\bwhich ([\w -]{1,40}?) (?:has|had|have|is|was)\b',q)
    vietnamese=re.search(r'(?:tên (?:của )?)(phòng|trạm|sản phẩm|nhân viên|ngành|khu vực)',q)
    if named:
        field=re.sub(r'^(?:(?:only|the)\s+)+','',named.group(1).strip()).strip()
        contract.update(answer_type='label',answer_field=field)
    elif which and which.group(1).strip() not in {'year','month','day','date','value','number','percentage'}:
        contract.update(answer_type='label',answer_field=which.group(1).strip())
    elif vietnamese:
        contract.update(answer_type='label',answer_field=vietnamese.group(1))
    return contract


def validate_answer_field(contract, plan, result, regions):
    """Check a declared source field against actual returned cell provenance."""
    spec=plan.get('answer_spec',{})
    if not isinstance(spec,dict): raise PlanError('answer_spec must be an object')
    if spec and (spec.get('answer_type') not in {'label','number','boolean','date','text'} or
                 not isinstance(spec.get('answer_field'),str) or not isinstance(spec.get('operation'),str)):
        raise PlanError('answer_spec requires answer_type, answer_field and operation')
    kind=contract.get('answer_type') or spec.get('answer_type')
    field=contract.get('answer_field') or spec.get('answer_field')
    requested=re.sub(r'[^\w]+',' ',str(field or '').casefold()).strip().rstrip('s')
    if spec and contract.get('answer_type') and spec.get('answer_type') != contract['answer_type']:
        raise PlanError(f"answer_spec says {spec.get('answer_type')} but the question requires {contract['answer_type']}")
    if spec and contract.get('answer_field') and spec.get('answer_field'):
        expected=re.sub(r'[^\w]+',' ',contract['answer_field'].casefold()).strip().rstrip('s')
        declared=re.sub(r'[^\w]+',' ',spec['answer_field'].casefold()).strip()
        declared=re.sub(r'^name\s+','',declared).rstrip('s')
        if expected != declared and expected not in declared and declared not in expected:
            raise PlanError(f"answer_spec field {spec['answer_field']} does not match requested field {contract['answer_field']}")
    if kind!='label': return
    if requested in {'industry','sector','category'} and any(re.search(r'\b\d+\s+to\s+\d+\s+years?\b',value,re.I) for value in result['values']):
        raise PlanError('Question requests an industry/sector/category name, but the result is a row label such as an age group. Map the horizontal metric column to its header label.')
    if any(re.fullmatch(r'[A-Z]{1,3}',value) for value in result['values']):
        raise PlanError('Question requests a label, but output is an Excel column identifier. For horizontal tables, map unpivot columns to their header labels using label_table and label_row before sorting and output the label.')
    if any(re.fullmatch(r'-?\d+(?:\.\d+)?',value) for value in result['values']):
        # Numeric identifiers/years can legitimately be label fields.
        if not field or not re.search(r'\b(?:id|code|year|month|day)\b',field,re.I):
            raise PlanError('Question requests a NAME/label, not the numeric metric. Output the source label field.')
    if not field: return
    def norm(value): return re.sub(r'[^\w]+',' ',str(value).casefold()).strip()
    requested=norm(field)
    requested=requested[:-1] if requested.endswith('s') else requested
    matching=set()
    for region in regions:
        for col,headers in region.column_headers().items():
            if any(norm(h).rstrip('s')==requested for h in headers): matching.add((region.sheet,col))
    if requested in {'industry','sector','category'}:
        for source in result.get('value_sources',[]):
            for ref in source:
                sheet,coordinate=ref.rsplit('!',1); col=re.sub(r'\d+$','',coordinate)
                region=next((r for r in regions if r.sheet==sheet),None)
                if region and col==re.sub(r'\d+$','',getattr(region,'bounds','').split(':')[0]) and sum(bool(h.strip()) for values in region.column_headers().values() for h in values)>4:
                    raise PlanError('Question asks for an industry/sector/category name, but the output came from the row-label column. For a horizontal table, unpivot metric columns and output their header labels.')
    # Generic names such as sector/industry can describe a horizontal axis;
    # only enforce heading identity when it is actually present in this file.
    if not matching: return
    for sources in result.get('value_sources',[]):
        locations={(ref.rsplit('!',1)[0],re.sub(r'\d+$','',ref.rsplit('!',1)[1])) for ref in sources}
        if not locations & matching:
            raise PlanError(f'Answer field must be {field}; returned cells come from another column. '
                            'Sort by the metric but output the requested source label.')


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


def validate_answer_contract(contract,plan,result,question=''):
    count=contract['count']
    reduction=contract['reduction']
    lineage=ancestors(plan)
    if reduction=='mean':
        aggregates=[s for s in lineage if s.get('op')=='aggregate' and s.get('metric')=='mean']
        if aggregates:
            agg=aggregates[-1]
            source=next((s for s in lineage if s.get('id')==agg.get('input')),None)
            selects=[s for s in lineage if s.get('op')=='select' and s.get('id')==agg.get('input')]
            if source and source.get('op')=='select' and len(source.get('columns',[]))>1:
                raise PlanError('Mean across columns requires unpivot the selected row into values, then aggregate mean over value. Aggregating column B of one row returns only the first category.')
        if re.search(r'unemployment rate',question,re.I) and not any(s.get('op')=='unpivot' for s in lineage):
            raise PlanError('Average unemployment rate across categories requires filtering the requested unemployment-rate row, unpivoting its category columns, then aggregating mean over value.')
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
    if reduction=='difference' and not any(s.get('op')=='calculate' and any(op in json.dumps(s.get('expr',{})) for op in ('sub','abs')) for s in lineage):
        raise PlanError('Question asks for an absolute difference. Compute the two requested totals separately, then calculate abs(sub(total_a,total_b)); do not aggregate the two rows together.')
    if reduction and reduction!='difference' and final['op'] not in {'cell','sum_columns','calculate','aggregate'}:
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
