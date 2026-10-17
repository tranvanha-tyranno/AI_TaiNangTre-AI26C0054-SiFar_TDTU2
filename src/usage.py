"""Per-question usage ledger; unknown billings retain their reservation."""
from __future__ import annotations
import json
import math
import time


class BudgetError(RuntimeError):
    pass


class UsageLedger:
    def __init__(self, limit_usd=.10, max_calls=4, seconds=115,
                 prompt_cap=1.0, completion_cap=4.0):
        self.limit_usd=float(limit_usd)
        self.max_calls=max_calls
        self.deadline=time.monotonic()+seconds
        self.prompt_cap=prompt_cap
        self.completion_cap=completion_cap
        self.calls=[]

    def reserve(self, messages, max_tokens, request_cost=0):
        if time.monotonic() >= self.deadline: raise BudgetError("Question time budget exhausted")
        if len(self.calls)>=self.max_calls: raise BudgetError("Maximum API calls exhausted")
        # Conservative byte upper bound for prompt tokenization + protocol overhead.
        upper_tokens=len(json.dumps(messages,ensure_ascii=False).encode('utf-8'))+1024
        bound=upper_tokens*self.prompt_cap/1e6+max_tokens*self.completion_cap/1e6+request_cost
        used=sum(call.get('budget_charge_usd',0) for call in self.calls)
        if used+bound > self.limit_usd: raise BudgetError("Next call may exceed question cost limit")
        call={'attempt':len(self.calls)+1,'status':'started','reserved_usd':bound,
              'budget_charge_usd':bound,'prompt_tokens':None,'completion_tokens':None,
              'total_tokens':None,'actual_cost_usd':None,'estimated_cost_usd':None,
              'cost_source':'unknown'}
        self.calls.append(call)
        return call

    def summary(self):
        costs=[call['actual_cost_usd'] for call in self.calls]
        tokens=[call['total_tokens'] for call in self.calls]
        known_cost=sum(value for value in costs if value is not None)
        known_tokens=sum(value for value in tokens if value is not None)
        reasoning_known=all(c.get('reasoning_tokens') is not None for c in self.calls)
        ranking_known=reasoning_known and all(c.get('prompt_tokens') is not None for c in self.calls)
        return {'calls':self.calls,'api_calls':len(self.calls),
                'prompt_tokens':sum(c['prompt_tokens'] or 0 for c in self.calls),
                'completion_tokens':sum(c['completion_tokens'] or 0 for c in self.calls),
                'total_tokens':known_tokens,'tokens_complete':all(value is not None for value in tokens),
                'reasoning_tokens':sum(c.get('reasoning_tokens') or 0 for c in self.calls) if reasoning_known else None,
                'input_plus_reasoning_tokens':sum(c['prompt_tokens']+c['reasoning_tokens'] for c in self.calls) if ranking_known else None,
                'actual_cost_usd':known_cost,'cost_complete':all(value is not None for value in costs),
                'estimated_cost_usd':sum(c['estimated_cost_usd'] or 0 for c in self.calls),
                'unknown_cost_calls':sum(value is None for value in costs),
                'budget_charge_usd':sum(c['budget_charge_usd'] for c in self.calls),
                'limit_usd':self.limit_usd}
