"""Retrieve -> plan -> execute -> validate -> format, with bounded repair."""
import time
import re
from .workbook_index import load_regions, retrieve
from .planner import messages, parse_plan
from .tools.executor import execute, PlanError
from .usage import UsageLedger, BudgetError
from .scope_validation import validate_aggregate_scope
from .answer_contract import infer_answer_contract, validate_answer_contract
from .semantic_validation import validate_semantics, validate_rank_labels


def answer_with_tools(path, question, client, record, settings):
    ledger=UsageLedger(limit_usd=settings.get('max_cost_per_question',.10),max_calls=settings.get('max_api_calls',4),
        seconds=settings.get('question_timeout',115),prompt_cap=client.prompt_cap,completion_cap=client.completion_cap)
    record.update(stage='parse',pipeline_version='tools-v1',plans=[],timings={})
    contract=infer_answer_contract(question)
    record['answer_contract']=contract
    try:
        start=time.monotonic()
        regions=load_regions(path,settings.get('max_workbook_cells',200000))
        record['timings']['parse']=time.monotonic()-start
        record['stage']='retrieve'
        start=time.monotonic()
        selected,catalog=retrieve(regions,question,settings.get('retrieval_top_k',4))
        record['retrieval']=catalog
        record['timings']['retrieve']=time.monotonic()-start
        if not selected: raise PlanError("Workbook has no usable regions")
        previews=[r.preview(question,settings.get('preview_rows',45)) for r in selected]
        record['previews']=previews
        correction=None
        for attempt in range(settings.get('max_plan_repairs',2)+1):
            record['stage']='plan'
            start=time.monotonic()
            raw=client.complete(messages(question,previews,catalog,correction),ledger,'plan' if attempt==0 else 'repair')
            record['timings']['plan']=record['timings'].get('plan',0)+time.monotonic()-start
            plan=None
            try:
                plan=parse_plan(raw)
                record['plans'].append({'attempt':attempt+1,'plan':plan})
                record['stage']='execute'
                start=time.monotonic()
                result=execute(plan,selected)
                record['stage']='validate_output'
                record['tool_trace']=result['trace']
                record['plans'][-1]['tool_trace']=result['trace']
                validate_aggregate_scope(question,plan,selected)
                query=question.lower()
                validate_answer_contract(contract,plan,result)
                validate_semantics(question,contract,plan,result,selected)
                if any(term in query for term in ('sector names','industry name','category name','last name')):
                    if any(re.fullmatch(r'-?\d+(\.\d+)?',v) for v in result['values']):
                        raise PlanError('Question asks for NAME labels, not numeric scores. Sort by values but output the corresponding name column, using aliases for short labels in the question.')
                validate_rank_labels(question,result)
                for target in plan.get('output',{}).get('aliases',{}).values():
                    if not isinstance(target,str) or target.casefold() not in question.casefold():
                        raise PlanError('Alias targets must be labels explicitly present in the question')
                record['timings']['execute']=record['timings'].get('execute',0)+time.monotonic()-start
                if time.monotonic()>ledger.deadline: raise BudgetError("Question deadline exceeded during execution")
                record.update(stage='validated',plan=plan,tool_trace=result['trace'],evidence=result['evidence'],
                              evidence_count=result['evidence_count'],validated=True)
                return result['answer']
            except (PlanError,ValueError,TypeError,KeyError,AttributeError) as error:
                if record['plans'] and record['plans'][-1]['attempt']==attempt+1:
                    record['plans'][-1]['validation_error']=str(error)[:500]
                record['validation_errors']=record.get('validation_errors',[])+[str(error)[:500]]
                record.setdefault('validation_events',[]).append({'attempt':attempt+1,
                    'detected_at':record['stage'],'error_type':type(error).__name__,'message':str(error)[:500]})
                if attempt>=settings.get('max_plan_repairs',2):
                    raise PlanError(str(error)) from None
                correction={'plan':plan or raw[:8000],'error':str(error)[:500]}
        raise PlanError("No valid answer produced")
    except Exception as error:
        record['failure_event']={'phase':record['stage'],'error_type':type(error).__name__,
            'message':str(error)[:500] if isinstance(error,(PlanError,BudgetError,ValueError)) else type(error).__name__}
        raise
    finally:
        record['usage']=ledger.summary()
