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
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    if not api_key:
        return None
    base_url = os.getenv("OPENROUTER_BASE_URL") or os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL
    return OpenAI(api_key=api_key, base_url=base_url, timeout=45.0, max_retries=0)


def get_model() -> str:
    return os.getenv("MODEL_NAME") or os.getenv("QWEN_MODEL") or DEFAULT_MODEL


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
            )
            text = resp.choices[0].message.content or ""
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
