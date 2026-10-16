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


def summarize_usage(records):
    entries=[r.get('usage') for r in records]
    known=[entry for entry in entries if entry is not None]
    ranking_complete=len(known)==len(records) and all(u.get('input_plus_reasoning_tokens') is not None for u in known)
    return {'api_calls':sum(u['api_calls'] for u in known),
            'input_plus_reasoning_tokens':sum(u['input_plus_reasoning_tokens'] for u in known) if ranking_complete else None,
            'prompt_tokens':sum(u['prompt_tokens'] for u in known),
            'completion_tokens':sum(u['completion_tokens'] for u in known),
            'total_tokens':sum(u['total_tokens'] for u in known),
            'actual_cost_usd':sum(u['actual_cost_usd'] for u in known),
            'estimated_cost_usd':sum(u['estimated_cost_usd'] for u in known),
            'unknown_cost_calls':sum(u['unknown_cost_calls'] for u in known),
            'cost_complete':len(known)==len(records) and all(u['cost_complete'] for u in known),
            'tokens_complete':len(known)==len(records) and all(u['tokens_complete'] for u in known)}


def peak_memory_mb():
    import os
    import sys
    try:
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in [
                    'PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
                    'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
            info=Counters(); info.cb=ctypes.sizeof(info)
            ctypes.windll.kernel32.GetCurrentProcess.restype=ctypes.c_void_p
            process=ctypes.windll.kernel32.GetCurrentProcess()
            function=ctypes.windll.psapi.GetProcessMemoryInfo
            function.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),wintypes.DWORD]
            if not function(process,ctypes.byref(info),info.cb): return None
            return info.PeakWorkingSetSize/(1024*1024)
        import resource
        raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return raw/(1024*1024) if sys.platform=='darwin' else raw/1024
    except Exception:
        return None
