"""Development UI compatibility; missing CLI measurements stay unknown."""


def summarize_usage(records):
    known = [r['usage'] for r in records if isinstance(r.get('usage'), dict)]
    complete = bool(records) and len(known) == len(records)
    result = {key: sum(u.get(key, 0) or 0 for u in known) for key in (
        'api_calls', 'prompt_tokens', 'completion_tokens', 'total_tokens',
        'actual_cost_usd', 'estimated_cost_usd', 'unknown_cost_calls')}
    result.update(
        cost_complete=complete and all(u.get('cost_complete', False) for u in known),
        tokens_complete=complete and all(u.get('tokens_complete', False) for u in known),
        input_plus_reasoning_tokens=(sum(u['input_plus_reasoning_tokens'] for u in known)
            if complete and all(u.get('input_plus_reasoning_tokens') is not None for u in known) else None))
    return result
