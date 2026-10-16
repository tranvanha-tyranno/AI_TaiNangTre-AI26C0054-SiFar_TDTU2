"""Shared configuration: the restarted v3 baseline executes existing v2."""
V3_BASELINE_VERSION='lmmv3-v2-baseline-v1'


def settings_for_mode(settings,mode):
    result=dict(settings)
    if mode in {'llm-v2','llm-v3'}:
        result.update(pipeline_variant='llm-v2',max_api_calls=max(6,int(result.get('max_api_calls',4))),
                      max_plan_repairs=max(3,int(result.get('max_plan_repairs',2))),
                      max_inspection_rounds=max(3,int(result.get('max_inspection_rounds',2))),
                      semantic_review='all',retrieval_top_k=max(6,int(result.get('retrieval_top_k',4))),
                      preview_rows=max(60,int(result.get('preview_rows',45))))
        if mode=='llm-v3': result['v3_base_variant']='llm-v2'
        else: result.pop('v3_base_variant',None)
    else:
        result['pipeline_variant']='llm';result.pop('v3_base_variant',None)
    return result
