"""Shared configuration: the restarted v3 baseline executes existing v2."""
V3_BASELINE_VERSION='lmmv3-v2-baseline-v1'
V3_DEDUP_VERSION='lmmv3-v2-dedup-v1'


def v3_version(settings):
    if settings.get('v3_error_memory',False): return 'lmmv3-v2-error-memory-v3'
    if settings.get('v3_reliability',False): return 'lmmv3-v2-reliability-v1'
    return V3_DEDUP_VERSION if settings.get('v3_deduplicate_context',True) else V3_BASELINE_VERSION


def settings_for_mode(settings,mode):
    result=dict(settings)
    if mode!='llm-v3':
        result.pop('v3_reliability',None)
        result.pop('v3_error_memory',None)
        result.pop('v3_program_tools',None)
    if mode in {'llm-v2','llm-v3'}:
        result.update(pipeline_variant='llm-v2',max_api_calls=max(6,int(result.get('max_api_calls',4))),
                      max_plan_repairs=max(3,int(result.get('max_plan_repairs',2))),
                      max_inspection_rounds=max(3,int(result.get('max_inspection_rounds',2))),
                      semantic_review='all',retrieval_top_k=max(6,int(result.get('retrieval_top_k',4))),
                      preview_rows=max(60,int(result.get('preview_rows',45))))
        if mode=='llm-v3':
            result['v3_base_variant']='llm-v2'
            result['v3_deduplicate_context']=bool(result.get('v3_deduplicate_context',True))
            if result.get('v3_error_memory',False):
                result['max_api_calls']=max(8,int(result['max_api_calls']))
                result['max_plan_repairs']=max(4,int(result['max_plan_repairs']))
        else: result.pop('v3_base_variant',None)
    else:
        result['pipeline_variant']='llm';result.pop('v3_base_variant',None)
    return result
