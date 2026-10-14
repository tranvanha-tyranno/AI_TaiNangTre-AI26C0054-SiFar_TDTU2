"""
llm_client.py — Gọi Qwen3.7-Flash qua OpenRouter (tương thích OpenAI API).
- Đọc API key từ ENV: OPENROUTER_API_KEY (hoặc OPENAI_API_KEY fallback)
- Model mặc định: qwen/qwen3-7-flash (theo đề)
- Có thể override qua ENV MODEL_NAME / config.yaml
- Retry 1 lần nếu lỗi transient.
"""
from __future__ import annotations
import os
import time
from typing import Optional
import json
import urllib.request
from .usage import BudgetError

try:
    from dotenv import load_dotenv
    # Load the project-local .env when present; real environment variables win.
    load_dotenv()
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # sẽ báo lỗi thân thiện khi gọi


DEFAULT_MODEL = "qwen/qwen3-7-flash"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def get_client() -> Optional["OpenAI"]:
    if OpenAI is None:
        return None
    api_key = (os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None
    base_url = (os.getenv("OPENROUTER_BASE_URL") or os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL).strip()
    # OpenRouter yêu cầu 2 header này để tính ranking/analytics, thiếu vẫn chạy
    # nhưng có thì tránh bị chặn 401 trên một số key/org.
    extra_headers = {
        "HTTP-Referer": os.getenv("OPENROUTER_REFERER") or "https://github.com/tranvanha-tyranno/AI_TaiNangTre-AI26C0054-SiFar_TDTU2",
        "X-Title": os.getenv("OPENROUTER_TITLE") or "SiFar-TDTU2 Excel QA",
    }
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=60.0,
        max_retries=0,
        default_headers=extra_headers,
    )


def get_model() -> str:
    return os.getenv("MODEL_NAME") or os.getenv("QWEN_MODEL") or DEFAULT_MODEL


class PlannerClient:
    """One SDK request per recorded attempt, with price caps and usage."""
    def __init__(self, prompt_cap=1.0, completion_cap=4.0, max_tokens=2000):
        self.client=get_client()
        if self.client is None: raise RuntimeError("Configure OPENROUTER_API_KEY")
        self.model=get_model()
        self.prompt_cap=prompt_cap
        self.completion_cap=completion_cap
        self.max_tokens=max_tokens
        self.base=str(self.client.base_url).rstrip('/')
        with urllib.request.urlopen(self.base+'/models',timeout=15) as response:
            catalog=json.load(response)['data']
        entry=next((item for item in catalog if item['id']==self.model),None)
        if entry is None: raise BudgetError(f"Model ID not in OpenRouter catalog: {self.model}")
        prices=entry.get('pricing',{})
        self.prompt_rate=float(prices.get('prompt',0))
        self.completion_rate=float(prices.get('completion',0))
        self.request_rate=float(prices.get('request',0))
        if self.prompt_rate*1e6>prompt_cap or self.completion_rate*1e6>completion_cap:
            raise BudgetError("Model price exceeds configured provider price caps")
        if self.request_rate:
            raise BudgetError("Per-request priced models are not supported by the current cost guard")

    def complete(self, messages, ledger, purpose='plan'):
        from .planner import tool_schema
        schema=tool_schema()
        tools=[{'type':'function','function':{'name':'execute_spreadsheet_plan',
                'description':'Execute a validated spreadsheet plan using the supplied tables and fixed tools.',
                'parameters':schema}}]
        last=None
        for retry in range(2):
            call=ledger.reserve(messages+[{'role':'system','content':json.dumps(tools)}],self.max_tokens,self.request_rate)
            call.update(purpose=purpose,model=self.model)
            started=time.monotonic()
            try:
                response=self.client.chat.completions.create(model=self.model,messages=messages,
                    max_tokens=self.max_tokens,temperature=0,
                    tools=tools,tool_choice={'type':'function','function':{'name':'execute_spreadsheet_plan'}},
                    timeout=min(45,max(.1,ledger.deadline-time.monotonic())),
                    extra_body={'reasoning':{'enabled':False},
                                'provider':{'max_price':{'prompt':self.prompt_cap,'completion':self.completion_cap}}})
                payload=response.model_dump()
                usage=payload.get('usage') or {}
                cost=usage.get('cost')
                source='usage.cost' if cost is not None else 'unknown'
                if cost is None and payload.get('id'):
                    # Usage endpoint is read-only; no additional generation.
                    try:
                        request=urllib.request.Request(self.base+'/generation?id='+payload['id'],
                            headers={'Authorization':'Bearer '+self.client.api_key})
                        with urllib.request.urlopen(request,timeout=min(5,max(.1,ledger.deadline-time.monotonic()))) as resp:
                            generation=json.load(resp)['data']
                        cost=generation.get('total_cost')
                        if cost is not None: source='generation.total_cost'
                    except Exception:
                        pass
                for key in ('prompt_tokens','completion_tokens','total_tokens'):
                    call[key]=usage.get(key)
                call.update(id=payload.get('id'),finish_reason=response.choices[0].finish_reason,
                            reasoning_tokens=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens'),
                            actual_cost_usd=float(cost) if cost is not None else None,cost_source=source,
                            status='completed',elapsed_seconds=time.monotonic()-started)
                if usage.get('prompt_tokens') is not None and usage.get('completion_tokens') is not None:
                    call['estimated_cost_usd']=usage['prompt_tokens']*self.prompt_rate+usage['completion_tokens']*self.completion_rate
                if cost is not None:
                    call['budget_charge_usd']=float(cost)
                if sum(c['budget_charge_usd'] for c in ledger.calls)>ledger.limit_usd:
                    raise BudgetError("API reported cost exceeds question budget; no further calls allowed")
                message=response.choices[0].message
                if message.tool_calls:
                    if len(message.tool_calls)!=1 or message.tool_calls[0].function.name!='execute_spreadsheet_plan':
                        raise RuntimeError('Unexpected tool call returned')
                    content=message.tool_calls[0].function.arguments
                else:
                    content=message.content or ''
                if not content.strip(): raise RuntimeError("Model returned empty JSON plan")
                return content
            except BudgetError:
                raise
            except Exception as error:
                if call['status']=='started':
                    call.update(status='error',error_type=type(error).__name__,
                                http_status=getattr(error,'status_code',None),elapsed_seconds=time.monotonic()-started)
                last=error
                status=getattr(error,'status_code',None)
                if retry or status in {400,401,402,403,404,422}:
                    raise RuntimeError(f"Planner API failed: {type(error).__name__}; HTTP {status}") from None
        raise last


SYSTEM_PROMPT = """You are an expert at answering questions based on Excel spreadsheet data.
You will be given the spreadsheet serialized as markdown tables.
Rules:
- Read carefully: numbers are in thousands/billions as noted; respect merged headers.
- Compute exactly: use the numbers shown, do not hallucinate.
- Output ONLY the final answer, no explanation, no quotes, no extra text.
- Follow the answer format specified in the question exactly (e.g. "only the integer", "Yes or No", "two decimals").
"""


def ask_llm(question: str, table_text: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
    client = get_client()
    model = get_model()
    if client is None:
        raise RuntimeError(
            "No LLM API key found. Set OPENROUTER_API_KEY (or OPENAI_API_KEY) in env. "
            "Get a key at https://openrouter.ai/"
        )

    user_prompt = f"Spreadsheet data:\n\n{table_text}\n\nQuestion: {question}\nAnswer (only the final answer, no explanation):"

    last_err = None
    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                extra_body={"reasoning": {"enabled": False}},
            )
            text = resp.choices[0].message.content or ""
            if not text.strip():
                raise RuntimeError(f"LLM returned no answer (finish_reason={resp.choices[0].finish_reason})")
            return text.strip()
        except Exception as e:
            last_err = e
            if getattr(e, "status_code", None) in {400, 401, 403, 404, 422}:
                raise
            if attempt == 0:
                time.sleep(1.5)
                continue
            raise
    raise last_err  # type: ignore
