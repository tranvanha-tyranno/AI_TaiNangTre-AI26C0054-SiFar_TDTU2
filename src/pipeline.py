"""Retrieve -> plan -> execute -> validate -> format, with bounded repair."""
import time
import re
from .workbook_index import load_regions, retrieve
from .planner import messages, parse_plan
from .tools.executor import execute, PlanError
from .usage import UsageLedger, BudgetError


def answer_with_tools(path, question, client, record, settings):
    ledger=UsageLedger(limit_usd=settings.get('max_cost_per_question',.10),max_calls=settings.get('max_api_calls',4),
        seconds=settings.get('question_timeout',115),prompt_cap=client.prompt_cap,completion_cap=client.completion_cap)
    record.update(stage='parse',pipeline_version='tools-v1',plans=[],timings={})
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
                query=question.lower()
                expected_count=None
                if re.search(r'two integers|men, women|as\s+[`\"\']?men,\s*women',query): expected_count=2
                elif 'three sector names' in query: expected_count=3
                elif 'answer with only' in query or 'answer with the' in query: expected_count=1
                if expected_count is not None and result['value_count']!=expected_count:
                    raise PlanError(f'Question requires {expected_count} final value(s), got {result["value_count"]}. For multiple scalar cells use collect, then output columns=[value].')
                if 'two decimal' in query or 'exactly two' in query:
                    if any(not re.fullmatch(r'-?\d+\.\d{2}',value) for value in result['values']):
                        raise PlanError('Question requires exactly two decimals for each numeric answer; set output.decimals=2')
                if 'integer' in query and any(not re.fullmatch(r'-?\d+',v) for v in result['values']):
                    raise PlanError('Question requires integers without commas or units')
                if any(term in query for term in ('sector names','industry name','category name','last name')):
                    if any(re.fullmatch(r'-?\d+(\.\d+)?',v) for v in result['values']):
                        raise PlanError('Question asks for NAME labels, not numeric scores. Sort by values but output the corresponding name column, using aliases for short labels in the question.')
                named_list=re.search(r'\brank\b[^:]*:\s*(.*?)\.\s*answer',question,re.I|re.S)
                if named_list:
                    labels=[re.sub(r'^and\s+','',label.strip(),flags=re.I) for label in named_list.group(1).split(',')]
                    if len(labels)>1 and any(value.casefold() not in {label.casefold() for label in labels} for value in result['values']):
                        raise PlanError(f'Use exactly the names explicitly listed in the question: {labels}. Add output.aliases to shorten longer spreadsheet labels, while preserving computed sort order.')
                for target in plan.get('output',{}).get('aliases',{}).values():
                    if not isinstance(target,str) or target.casefold() not in question.casefold():
                        raise PlanError('Alias targets must be labels explicitly present in the question')
                record['timings']['execute']=record['timings'].get('execute',0)+time.monotonic()-start
                if time.monotonic()>ledger.deadline: raise BudgetError("Question deadline exceeded during execution")
                record.update(stage='validated',plan=plan,tool_trace=result['trace'],evidence=result['evidence'],
                              evidence_count=result['evidence_count'],validated=True)
                return result['answer']
            except (PlanError,ValueError,TypeError,KeyError,AttributeError) as error:
                record['validation_errors']=record.get('validation_errors',[])+[str(error)[:500]]
                if attempt>=settings.get('max_plan_repairs',2):
                    raise PlanError(str(error)) from None
                correction={'plan':plan or raw[:8000],'error':str(error)[:500]}
        raise PlanError("No valid answer produced")
    finally:
        record['usage']=ledger.summary()
