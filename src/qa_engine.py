"""
qa_engine.py — Hybrid pipeline: LLM trực tiếp + fallback sinh code Python.

Luồng:
  1. parse_and_serialize(file) -> table_text
  2. ask_llm(question, table_text) -> answer_raw
  3. post_process(answer, question) -> chuẩn hoá theo format đề

Ngoài ra hỗ trợ mode code-gen: yêu cầu LLM viết code Python tính toán
trên `records` thay vì trả lời trực tiếp, rồi thực thi sandbox.
Dùng khi câu hỏi mang tính tính toán phức tạp.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict

from .excel_parser import parse_and_serialize
from .llm_client import ask_llm


def post_process(raw: str, question: str) -> str:
    """Chuẩn hoá đáp án cho Exact Match."""
    s = raw.strip()
    # loại bỏ prefix kiểu "Answer: "
    s = re.sub(r"^(answer|result)\s*:\s*", "", s, flags=re.I).strip()
    # loại bỏ dấu nháy bao quanh
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'", "`"):
        s = s[1:-1].strip()
    # giữ nguyên — đề yêu cầu format chính xác do LLM quyết định
    # chỉ strip whitespace thừa
    s = re.sub(r"\s+", " ", s).strip()
    return s


def answer_one(xlsx_path: str | Path, question: str, use_llm: bool = True) -> str:
    _, table_text = parse_and_serialize(xlsx_path)
    if not use_llm:
        # offline stub: trả về rỗng để test pipeline
        return ""
    raw = ask_llm(question, table_text)
    return post_process(raw, question)


# ---- code-gen fallback (tuỳ chọn) ----
CODE_SYSTEM = """You are a Python data analyst. You will be given spreadsheet data as a list of dicts `records` and `headers`.
Write a Python snippet that computes `answer` for the question. Only use `records`, `headers`, standard library.
End with `answer = ...` (string or int). Output ONLY the code block."""

def answer_with_codegen(xlsx_path: str | Path, question: str) -> str:
    """Thử sinh code rồi exec. Nếu fail thì fallback về ask_llm thường."""
    from .excel_parser import parse_excel
    from .llm_client import get_client, get_model, SYSTEM_PROMPT
    import os, time

    parsed = parse_excel(xlsx_path)
    # lấy sheet đầu
    sheet = next(iter(parsed.values()))
    headers = sheet["headers"]
    records = [dict(zip(headers, r)) for r in sheet["records"]]

    # build prompt cho code-gen
    preview = "\n".join(str(r) for r in records[:3])
    prompt = (
        f"headers = {headers}\n"
        f"Sample records (first 3):\n{preview}\n"
        f"Total records: {len(records)}\n"
        f"Question: {question}\n"
        "Write Python code that sets `answer`."
    )
    try:
        from openai import OpenAI
        client = get_client()
        if client is None:
            raise RuntimeError("no api key")
        model = get_model()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": CODE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.0,
        )
        code = resp.choices[0].message.content or ""
        # extract code block
        m = re.search(r"```python(.*?)```", code, re.S)
        if m:
            code = m.group(1)
        # exec sandbox (hạn chế builtins)
        local_vars: Dict = {"records": records, "headers": headers}
        exec(code, {"__builtins__": __builtins__}, local_vars)
        ans = local_vars.get("answer", "")
        return post_process(str(ans), question)
    except Exception:
        # fallback
        return answer_one(xlsx_path, question, use_llm=True)
