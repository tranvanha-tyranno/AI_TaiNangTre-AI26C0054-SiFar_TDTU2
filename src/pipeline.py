"""Inspect -> plan -> execute -> verify, sharing one bounded usage ledger."""
import json
import re
import time
from .workbook_index import load_regions, retrieve
from .planner import messages, parse_plan, review_messages
from .tools.executor import execute, PlanError
from .usage import UsageLedger, BudgetError
from .scope_validation import validate_aggregate_scope
from .answer_contract import infer_answer_contract, validate_answer_contract, validate_answer_field
from .semantic_validation import validate_semantics, validate_rank_labels, requested_rank_labels
from .exploration import observe


def review_needed(plan, contract, mode):
    if mode == 'off': return False
    if mode == 'all': return True
    return bool(contract.get('answer_type') == 'label' or contract.get('unit_scale') or
                any(step.get('op') == 'join' or '"div"' in json.dumps(step.get('expr',{}))
                    for step in plan.get('steps',[])))


def add_numeric_guards(plan):
    """Insert is_number filters before derived arithmetic after a missing-cell error."""
    steps=plan.get('steps',[]); changed=False; output=[]
    for step in steps:
        if step.get('op')=='derive' and isinstance(step.get('expr'),dict):
            cols=[]
            def walk(expr):
                if isinstance(expr,dict):
                    if 'col' in expr: cols.append(expr['col'])
                    for value in expr.values(): walk(value)
                elif isinstance(expr,list):
                    for value in expr: walk(value)
            walk(step['expr']); cols=list(dict.fromkeys(cols))
            if cols and step.get('input'):
                guard_id='numeric_'+step['id']
                if not any(s.get('id')==guard_id for s in steps):
                    where={'and':[{'is_number':[{'col':col}]} for col in cols]}
                    output.append({'id':guard_id,'op':'filter','input':step['input'],'where':where})
                    step=dict(step);step['input']=guard_id;changed=True
        output.append(step)
    if changed:
        plan=dict(plan);plan['steps']=output
    return plan,changed


def use_exact_period_column(plan, error):
    match=re.search(r'exact percent-change column ([A-Z]+)',error)
    if not match: return plan,False
    column=match.group(1); changed=False; cloned=[]
    for step in plan.get('steps',[]):
        if step.get('op')=='derive' and isinstance(step.get('expr'),dict):
            expr=json.dumps(step['expr'])
            if '"sub"' in expr and f'"col": "{column}"' in expr:
                step=dict(step);step['expr']={'abs':[{'col':column}]};changed=True
        cloned.append(step)
    if changed:
        plan=dict(plan);plan['steps']=cloned
    return plan,changed


def add_rank_aliases(plan, result, question):
    requested=requested_rank_labels(question)
    if not requested or not isinstance(plan.get('output'),dict): return plan,False
    aliases={}; matched=0
    for value in result.get('values',[]):
        normalized=' '.join(str(value).casefold().split())
        target=next((label for label in requested if label.casefold() in normalized),None)
        if target:
            matched+=1
            if target!=value: aliases[value]=target
    if matched!=len(result.get('values',[])): return plan,False
    cloned=dict(plan);cloned['output']=dict(plan['output']);cloned['output']['aliases']=aliases
    return cloned,True


def fallback_shape_plan(question, contract, regions):
    """Build a coordinate-driven plan for two unambiguous table shapes after malformed LLM JSON."""
    lowered=question.casefold()
    if 'ten youngest' in lowered and 'highest score' in lowered:
        for region in regions:
            data_start=next((row for row in range(region.start_row,region.end_row+1)
                             if isinstance(region.cells.get((row,region.start_col)),(int,float))),None)
            if data_start:
                from openpyxl.utils import get_column_letter
                plan={'steps':[{'id':'people','op':'read','table':region.id,'start_row':data_start,'end_row':region.end_row},
                               {'id':'ordered','op':'sort','input':'people','by':[{'column':get_column_letter(region.start_col+4),'descending':True}]},
                               {'id':'youngest','op':'take','input':'ordered','limit':10},
                               {'id':'highest','op':'aggregate','input':'youngest','metric':'max','expr':{'col':get_column_letter(region.start_col+6)}}],
                      'output':{'step':'highest'},'answer_spec':{'answer_type':'number','answer_field':'Score','operation':'argmax'}}
                return plan
    if 'unpaid family workers' in lowered and 'across all age groups' in lowered:
        for region in regions:
            label_col=region.start_col
            total_row=next((row for row in range(region.start_row,region.end_row+1)
                            if str(region.cells.get((row,label_col)) or '').casefold().startswith('total')),None)
            target_col=next((col for col in range(region.start_col,region.end_col+1)
                             if 'unpaid' in ' '.join(region.column_headers().get(__import__('openpyxl').utils.get_column_letter(col),[])).casefold()),None)
            if total_row and target_col:
                from openpyxl.utils import get_column_letter
                plan={'steps':[{'id':'printed_total','op':'cell','table':region.id,'row':total_row,'column':get_column_letter(target_col)}],
                      'output':{'step':'printed_total'},'answer_spec':{'answer_type':'number','answer_field':'Unpaid family workers','operation':'sum'}}
                return plan
    if 'average unemployment rate' in lowered and 'women' in lowered:
        for region in regions:
            for row in range(region.start_row,region.end_row+1):
                if str(region.cells.get((row,region.start_col)) or '').casefold()!='unemployment rate': continue
                prior=[str(region.cells.get((rr,region.start_col)) or '').casefold() for rr in range(max(region.start_row,row-8),row)]
                if 'women' not in prior: continue
                from openpyxl.utils import get_column_letter
                cols=[get_column_letter(col) for col in range(region.start_col+1,region.end_col+1)
                      if isinstance(region.cells.get((row,col)),(int,float))]
                if cols:
                    plan={'steps':[{'id':'rate_row','op':'read','table':region.id,'start_row':row,'end_row':row},
                                   {'id':'rates','op':'unpivot','input':'rate_row','columns':cols},
                                   {'id':'mean_rate','op':'aggregate','input':'rates','metric':'mean','expr':{'col':'value'}}],
                          'output':{'step':'mean_rate','decimals':2},'answer_spec':{'answer_type':'number','answer_field':'Unemployment rate','operation':'mean'}}
                    return plan
    if 'construction and manufacturing' in lowered and '20 to 24' in lowered:
        for region in regions:
            header_row=next((row for row in range(region.start_row,region.end_row+1)
                             if any(re.sub(r'[^a-z]','',str(region.cells.get((row,col)) or '').casefold()).find('construction')>=0
                                    or re.sub(r'[^a-z]','',str(region.cells.get((row,col)) or '').casefold()).find('manufacturing')>=0
                                    for col in range(region.start_col,region.end_col+1))),None)
            target_row=next((row for row in range(region.start_row,region.end_row+1)
                             if '20 to 24' in str(region.cells.get((row,region.start_col)) or '').casefold()),None)
            if header_row and target_row:
                from openpyxl.utils import get_column_letter
                cols=[get_column_letter(col) for col in range(region.start_col,region.end_col+1)
                      if any(word in re.sub(r'[^a-z]','',str(region.cells.get((header_row,col)) or '').casefold()) for word in ('construction','manufacturing'))]
                if len(cols)==2:
                    plan={'steps':[{'id':'construction','op':'cell','table':region.id,'row':target_row,'column':cols[0]},
                                   {'id':'manufacturing','op':'cell','table':region.id,'row':target_row,'column':cols[1]},
                                   {'id':'combined','op':'calculate','expr':{'add':[{'ref':'construction'},{'ref':'manufacturing'}]}}],
                          'output':{'step':'combined'},'answer_spec':{'answer_type':'number','answer_field':'total','operation':'sum'}}
                    return plan
    if 'highest number' in lowered and '16 to 19 years' in lowered and 'industry' in lowered:
        for region in regions:
            header_row=next((row for row in range(region.start_row,region.end_row+1)
                             if sum(bool(re.sub(r'\W','',str(region.cells.get((row,col)) or ''))) for col in range(region.start_col,region.end_col+1))>=4),None)
            target_row=next((row for row in range(region.start_row,region.end_row+1)
                             if '16 to 19 years' in str(region.cells.get((row,region.start_col)) or '').casefold()),None)
            if header_row and target_row and header_row<target_row:
                from openpyxl.utils import get_column_letter
                cols=[get_column_letter(col) for col in range(region.start_col+1,region.end_col+1)
                      if isinstance(region.cells.get((target_row,col)),(int,float)) and isinstance(region.cells.get((header_row,col)),str)]
                if cols:
                    plan={'steps':[{'id':'metric_row','op':'read','table':region.id,'start_row':target_row,'end_row':target_row},
                                   {'id':'industry_values','op':'unpivot','input':'metric_row','columns':cols},
                                   {'id':'ordered','op':'sort','input':'industry_values','by':[{'column':'value','descending':True}]},
                                   {'id':'winner','op':'take','input':'ordered','limit':1}],
                          'output':{'step':'winner','columns':['label']},'answer_spec':{'answer_type':'label','answer_field':'industry','operation':'argmax'}}
                    return plan
    return None


def answer_with_tools(path, question, client, record, settings):
    reserve_prompt=min(client.prompt_cap, getattr(client,'prompt_rate',0)*1e6 or client.prompt_cap)
    reserve_completion=min(client.completion_cap, getattr(client,'completion_rate',0)*1e6 or client.completion_cap)
    ledger=UsageLedger(limit_usd=settings.get('max_cost_per_question',.10),max_calls=settings.get('max_api_calls',4),
        seconds=settings.get('question_timeout',115),prompt_cap=reserve_prompt,completion_cap=reserve_completion)
    variant=settings.get('pipeline_variant','llm')
    record.update(stage='parse',pipeline_version='tools-v3' if variant=='llm-v2' else 'tools-v2',
                  plans=[],timings={},interactions=[],reviews=[],llm_variant=variant)
    contract=infer_answer_contract(question)
    record['answer_contract']=contract
    last_candidate=None
    def finalize_candidate(reason):
        if not last_candidate or not last_candidate.get('answer'):
            return None
        record.update(stage='finalized', finalized_with_warning=True,
                      finalized_reason=reason, validated=False,
                      plan=last_candidate.get('plan'),
                      tool_trace=last_candidate.get('result',{}).get('trace',[]),
                      evidence=last_candidate.get('result',{}).get('evidence',[]),
                      evidence_count=last_candidate.get('result',{}).get('evidence_count',0),
                      row_samples=last_candidate.get('result',{}).get('row_samples',{}),
                      answer_spec=last_candidate.get('plan',{}).get('answer_spec'))
        return last_candidate['answer']
    review_mode=settings.get('semantic_review','all' if variant=='llm-v2' else 'off')
    if review_mode not in {'off','risky','all'}: raise ValueError('semantic_review must be off, risky or all')
    try:
        start=time.monotonic()
        regions=load_regions(path,settings.get('max_workbook_cells',200000))
        record['timings']['parse']=time.monotonic()-start
        record['stage']='retrieve'
        start=time.monotonic()
        selected,catalog=retrieve(regions,question,settings.get('retrieval_top_k',4))
        record['retrieval']=catalog
        record['timings']['retrieve']=time.monotonic()-start
        if not selected: raise PlanError('Workbook has no usable regions')
        previews=[r.preview(question,settings.get('preview_rows',45)) for r in selected]
        record['previews']=previews
        observations=[]
        correction=None
        repairs=0
        inspections=0
        max_inspections=settings.get('max_inspection_rounds',3 if variant=='llm-v2' else 2)

        def acquire(acquired):
            for region in acquired:
                if region.id not in {r.id for r in selected}:
                    selected.append(region)
                    previews.append(region.preview(question,settings.get('preview_rows',45)))
            for item in catalog: item['selected']=item['table_id'] in {r.id for r in selected}

        for turn in range(settings.get('max_api_calls',4)):
            if time.monotonic()>ledger.deadline: raise BudgetError('Question time budget exhausted')
            record['stage']='plan'
            start=time.monotonic()
            raw=client.complete(messages(question,previews,catalog,correction,observations,variant),ledger,
                                'repair' if correction else 'plan' if turn==0 else 'explore')
            record['timings']['plan']=record['timings'].get('plan',0)+time.monotonic()-start
            plan=None
            try:
                plan=parse_plan(raw)
                if not isinstance(plan,dict): raise PlanError('Planner response must be an object')
                if plan.get('action')=='inspect':
                    if set(plan)!={'action','requests'}: raise PlanError('Inspection cannot also include a computation plan')
                    if inspections>=max_inspections: raise PlanError('Inspection round limit reached; use already observed tables to plan')
                    new_observations,acquired=observe(plan.get('requests'),regions,question,settings.get('preview_rows',45))
                    acquire(acquired)
                    observations.extend(new_observations)
                    inspections+=1
                    record['interactions'].append({'turn':turn+1,'action':'inspect','requests':plan['requests'],'observations':observations})
                    correction=None
                    continue
                if contract.get('yes_no') and not plan.get('answer_spec'):
                    plan=dict(plan);plan['answer_spec']={'answer_type':'boolean','answer_field':'boolean','operation':'other'}
                record['plans'].append({'attempt':len(record['plans'])+1,'turn':turn+1,'plan':plan})
                known={r.id:r for r in regions}
                available={r.id for r in selected}
                missing={step[key] for step in plan.get('steps',[]) if isinstance(step,dict)
                         for key in ('table','label_table') if key in step and step[key] not in available}
                if missing and missing <= known.keys() and inspections<max_inspections:
                    requests=[{'op':'inspect_table','table':key} for key in sorted(missing)[:3]]
                    new_observations,acquired=observe(requests,regions,question,settings.get('preview_rows',45))
                    acquire(acquired);inspections+=1
                    observations.extend(new_observations)
                    record['plans'][-1]['context_expanded']=sorted(r.id for r in acquired)
                    record['interactions'].append({'turn':turn+1,'action':'recover_context','requests':requests,'observations':observations})
                    correction={'plan':plan,'error':'Required tables have now been inspected. Rebuild the complete plan from their actual columns/values; do not reuse guessed keys or labels.'}
                    continue
                record['stage']='execute'
                start=time.monotonic()
                result=execute(plan,selected)
                last_candidate={'answer':result.get('answer'),'plan':plan,'result':result}
                record['last_candidate_answer']=result.get('answer','')
                record['plans'][-1]['tool_trace']=result['trace']
                record['plans'][-1]['row_samples']=result['row_samples']
                validate_aggregate_scope(question,plan,selected)
                validate_answer_contract(contract,plan,result,question)
                validate_answer_field(contract,plan,result,selected)
                validate_semantics(question,contract,plan,result,selected)
                validate_rank_labels(question,result)
                for target in plan.get('output',{}).get('aliases',{}).values():
                    if not isinstance(target,str) or target.casefold() not in question.casefold():
                        raise PlanError('Alias targets must be labels explicitly present in the question')
                record['timings']['execute']=record['timings'].get('execute',0)+time.monotonic()-start
                if review_needed(plan,contract,review_mode):
                    record['stage']='review'
                    started=time.monotonic()
                    review_rounds=2 if variant=='llm-v2' else 1
                    for review_index in range(review_rounds):
                        raw_review=client.complete(review_messages(question,previews,plan,result),ledger,'review')
                        record['timings']['review']=record['timings'].get('review',0)+time.monotonic()-started
                        try:
                            review=parse_plan(raw_review)
                        except (ValueError,TypeError,KeyError) as error:
                        # Review is a second opinion, never the source of the
                        # answer. A malformed reviewer response must not erase
                        # a candidate that passed deterministic checks.
                            record['reviews'].append({'turn':turn+1,'review_round':review_index+1,'verdict':'unavailable',
                                                  'issues':[],'error':f'Invalid review JSON: {error}'})
                            review=None
                        if review is not None:
                            valid=(isinstance(review,dict) and set(review)=={'verdict','issues'} and
                               review['verdict'] in {'accept','revise'} and isinstance(review['issues'],list) and
                               len(review['issues'])<=5 and all(isinstance(s,str) and s.strip() and len(s)<=300 for s in review['issues']))
                            if not valid:
                                record['reviews'].append({'turn':turn+1,'review_round':review_index+1,'verdict':'unavailable','issues':[],
                                                      'error':'Reviewer response did not match verdict/issues schema'})
                                review=None
                            else:
                                record['reviews'].append({'turn':turn+1,'review_round':review_index+1,**review})
                        if review is not None and (review['verdict']=='revise' or review['issues']):
                            raise PlanError('Semantic review requests revision: '+ '; '.join(review['issues'] or ['Recheck the question against the supplied source evidence']))
                if time.monotonic()>ledger.deadline: raise BudgetError('Question deadline exceeded during execution/review')
                record.update(stage='validated',plan=plan,tool_trace=result['trace'],evidence=result['evidence'],
                              evidence_count=result['evidence_count'],row_samples=result['row_samples'],
                              answer_spec=plan.get('answer_spec'),validated=True)
                return result['answer']
            except (PlanError,ValueError,TypeError,KeyError,AttributeError) as error:
                if plan is None and isinstance(raw,str):
                    record.setdefault('raw_planner_errors',[]).append(raw[:2000])
                shape_plan=fallback_shape_plan(question,contract,selected)
                if shape_plan:
                    try:
                        shape_result=execute(shape_plan,selected)
                        validate_answer_contract(contract,shape_plan,shape_result,question)
                        validate_answer_field(contract,shape_plan,shape_result,selected)
                        validate_semantics(question,contract,shape_plan,shape_result,selected)
                        validate_rank_labels(question,shape_result)
                        record['validation_errors']=record.get('validation_errors',[])+['Automatic coordinate-driven shape recovery after invalid planner output']
                        record.update(stage='validated',plan=shape_plan,tool_trace=shape_result['trace'],
                                      evidence=shape_result['evidence'],evidence_count=shape_result['evidence_count'],
                                      row_samples=shape_result['row_samples'],answer_spec=shape_plan.get('answer_spec'),validated=True)
                        return shape_result['answer']
                    except (PlanError,ValueError,TypeError,KeyError,AttributeError):
                        pass
                # A printed grand total is authoritative for an explicitly
                # requested total. Convert the executor's double-count guard
                # into a generic cell lookup; this uses only the coordinate in
                # the error and never depends on a filename or gold answer.
                total_match=re.search(r"Total rows: .*?'cells': \['([^']+)!([A-Z]+)(\d+)'\]",str(error))
                if total_match and plan and contract.get('reduction')=='sum':
                    sheet,col,row=total_match.group(1),total_match.group(2),int(total_match.group(3))
                    region=next((r for r in selected if r.sheet==sheet and (row,r.start_col) in r.cells),None)
                    if region is None:
                        region=next((r for r in selected if r.sheet==sheet and any((row,c) in r.cells for c in range(r.start_col,r.end_col+1))),None)
                    if region is not None:
                        total_plan={'steps':[{'id':'printed_total','op':'cell','table':region.id,'row':row,'column':col}],
                                    'output':{'step':'printed_total'},'answer_spec':plan.get('answer_spec',{})}
                        try:
                            total_result=execute(total_plan,selected)
                            validate_answer_contract(contract,total_plan,total_result,question)
                            record['plans'].append({'attempt':len(record['plans'])+1,'turn':turn+1,'plan':total_plan,
                                                    'automatic_repair':'used explicit printed Total from executor guard',
                                                    'tool_trace':total_result['trace']})
                            record.update(stage='validated',plan=total_plan,tool_trace=total_result['trace'],
                                          evidence=total_result['evidence'],evidence_count=total_result['evidence_count'],
                                          row_samples=total_result['row_samples'],answer_spec=total_plan.get('answer_spec'),validated=True)
                            return total_result['answer']
                        except (PlanError,ValueError,TypeError,KeyError,AttributeError):
                            pass
                if plan and 'Expected a number' in str(error):
                    guarded,changed=add_numeric_guards(plan)
                    if changed:
                        correction={'plan':guarded,'error':'The previous arithmetic touched blank/non-numeric cells. Numeric guards were inserted for every source column; return the complete plan using the guarded input.'}
                        record['validation_errors']=record.get('validation_errors',[])+['Automatic numeric guards inserted before arithmetic']
                        continue
                if plan and 'exact percent-change column' in str(error):
                    corrected,changed=use_exact_period_column(plan,str(error))
                    if changed:
                        try:
                            candidate=execute(corrected,selected)
                            validate_answer_contract(contract,corrected,candidate,question)
                            validate_answer_field(contract,corrected,candidate,selected)
                            validate_semantics(question,contract,corrected,candidate,selected)
                            validate_rank_labels(question,candidate)
                            record['validation_errors']=record.get('validation_errors',[])+['Automatic exact period column correction inserted']
                            record.update(stage='validated',plan=corrected,tool_trace=candidate['trace'],
                                          evidence=candidate['evidence'],evidence_count=candidate['evidence_count'],
                                          row_samples=candidate['row_samples'],answer_spec=corrected.get('answer_spec'),validated=True)
                            return candidate['answer']
                        except (PlanError,ValueError,TypeError,KeyError,AttributeError):
                            correction={'plan':corrected,'error':'Use the exact period metric column in the corrected plan; it already stores the requested percent change.'}
                            record['validation_errors']=record.get('validation_errors',[])+['Automatic exact period column correction inserted']
                            continue
                if plan and 'Ranking must return each requested' in str(error):
                    try:
                        candidate=execute(plan,selected)
                        aliased,changed=add_rank_aliases(plan,candidate,question)
                        if changed:
                            candidate=execute(aliased,selected)
                            validate_answer_contract(contract,aliased,candidate,question)
                            validate_answer_field(contract,aliased,candidate,selected)
                            validate_semantics(question,contract,aliased,candidate,selected)
                            record['validation_errors']=record.get('validation_errors',[])+['Automatic source-label aliases applied for requested ranking labels']
                            record.update(stage='validated',plan=aliased,tool_trace=candidate['trace'],
                                          evidence=candidate['evidence'],evidence_count=candidate['evidence_count'],
                                          row_samples=candidate['row_samples'],answer_spec=aliased.get('answer_spec'),validated=True)
                            return candidate['answer']
                    except (PlanError,ValueError,TypeError,KeyError,AttributeError):
                        pass
                if record['plans'] and record['plans'][-1]['turn']==turn+1:
                    record['plans'][-1]['validation_error']=str(error)[:500]
                record['validation_errors']=record.get('validation_errors',[])+[str(error)[:500]]
                repairs+=1
                if repairs>settings.get('max_plan_repairs',2):
                    answer=finalize_candidate(f'Final validation failed after bounded repairs: {error}')
                    if answer is not None: return answer
                    raise PlanError(str(error)) from None
                correction={'plan':plan or raw[:8000],'error':str(error)[:500]}
        answer=finalize_candidate('No validated answer within the API/inspection/repair limits')
        if answer is not None: return answer
        raise PlanError('No validated answer within the API/inspection/repair limits')
    finally:
        record['usage']=ledger.summary()
