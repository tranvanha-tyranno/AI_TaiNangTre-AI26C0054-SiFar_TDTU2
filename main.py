#!/usr/bin/env python3
"""
main.py — Pipeline Hỏi đáp trên bảng tính Excel (Chủ đề 2)

Usage:
  python main.py --xlsx_dir ./Public_data_1/xlsx_files --queries ./Public_data_1/queries.json --output ./submission.csv
  python main.py --config ./config/config.yaml   # đọc từ yaml

Yêu cầu đề thi:
  - Input: thư mục chứa .xlsx + file queries.json
  - Output: submission.csv (id,answer) đúng format mẫu
  - LLM: Qwen3.7-Flash qua OpenRouter (OPENROUTER_API_KEY env)
  - Chạy lại được với dữ liệu mới, không hard-code đường dẫn
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# cho phép chạy cả khi src là package hoặc script lẻ
sys.path.insert(0, str(Path(__file__).parent))

from src.llm_client import get_client, PlannerClient
from src.pipeline import answer_with_tools
from src.usage import UsageLedger, summarize_usage, peak_memory_mb


def load_config(path: Path) -> dict:
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except ImportError:
        print("[WARN] pyyaml chưa cài, bỏ qua --config", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"[WARN] không đọc được config {path}: {e}", file=sys.stderr)
        return {}


def main():
    run_started = time.monotonic()
    # Keep progress logging usable on Windows consoles with a legacy codepage.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description="Excel QA pipeline — Chủ đề 2")
    # Accept both the historical underscore spelling and the hyphenated
    # spelling used by the competition runner.
    ap.add_argument("--xlsx_dir", "--xlsx-dir", dest="xlsx_dir", type=str, default=None,
                    help="Thư mục chứa .xlsx")
    ap.add_argument("--queries", type=str, default=None, help="Đường dẫn queries.json")
    ap.add_argument("--output", type=str, default=None, help="Đường dẫn submission.csv")
    ap.add_argument("--openrouter-key", dest="openrouter_key", default=None,
                    help="OpenRouter API key supplied by the competition runner")
    ap.add_argument("--openrouter-model", dest="openrouter_model", default=None,
                    help="OpenRouter model ID supplied by the competition runner")
    ap.add_argument("--openrouter-base-url", dest="openrouter_base_url", default=None,
                    help="OpenRouter-compatible API base URL supplied by the runner")
    ap.add_argument("--log-dir", default="outputs/logs", help="Nhật ký từng câu")
    ap.add_argument("--config", type=str, default="config/config.yaml", help="File config yaml (optional)")
    ap.add_argument("--concurrency", type=int, default=None)
    ap.add_argument("--mode", choices=["llm", "llm-v2", "llm-v3"], default=None,
                    help="llm: baseline; llm-v2: deep; llm-v3: baseline từ LLMv2, chưa thêm cải tiến")
    args = ap.parse_args()
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent / ".env", override=False)
    except ImportError:
        pass

    # The official Docker contract passes provider settings as command-line
    # arguments. Translate them to the environment variables already used by
    # the local CLI so the rest of the pipeline has one configuration path.
    if args.openrouter_key is not None:
        os.environ["OPENROUTER_API_KEY"] = args.openrouter_key
    if args.openrouter_model is not None:
        os.environ["MODEL_NAME"] = args.openrouter_model
    if args.openrouter_base_url is not None:
        os.environ["OPENROUTER_BASE_URL"] = args.openrouter_base_url

    cfg = {}
    if args.config and Path(args.config).exists():
        cfg = load_config(Path(args.config))

    xlsx_dir = Path(args.xlsx_dir or cfg.get("xlsx_dir") or "./Public_data_1/xlsx_files")
    queries_path = Path(args.queries or cfg.get("queries") or "./Public_data_1/queries.json")
    output_path = Path(args.output or cfg.get("output") or "./submission.csv")
    concurrency = args.concurrency if args.concurrency is not None else cfg.get("concurrency", 1)
    mode = args.mode or cfg.get("mode") or "llm"
    from src.variants import settings_for_mode, v3_version
    cfg = settings_for_mode(cfg,mode)
    if not isinstance(concurrency, int) or concurrency < 1 or concurrency > 6:
        ap.error("concurrency phải nằm trong khoảng 1 đến 6")

    # env cho llm_client
    if cfg.get("model"):
        os.environ.setdefault("MODEL_NAME", cfg["model"])
    if cfg.get("base_url"):
        os.environ.setdefault("OPENROUTER_BASE_URL", cfg["base_url"])

    if not queries_path.exists():
        print(f"[ERROR] không tìm thấy {queries_path}", file=sys.stderr)
        sys.exit(1)
    if not xlsx_dir.exists():
        print(f"[ERROR] không tìm thấy {xlsx_dir}", file=sys.stderr)
        sys.exit(1)

    queries = json.loads(queries_path.read_text(encoding="utf-8"))
    if not isinstance(queries, list) or not queries:
        ap.error("queries.json phải là danh sách câu hỏi không rỗng")
    seen = set()
    for q in queries:
        if not isinstance(q, dict) or not all(k in q for k in ("id", "file_name", "query")):
            ap.error("Mỗi câu hỏi phải có id, file_name, query")
        if not isinstance(q["id"], (str, int)) or str(q["id"]) in seen:
            ap.error("ID không hợp lệ hoặc trùng lặp")
        seen.add(str(q["id"]))
        if not isinstance(q["file_name"], str) or not isinstance(q["query"], str):
            ap.error("file_name và query phải là chuỗi")
        candidate = (xlsx_dir / q["file_name"]).resolve()
        if not candidate.is_relative_to(xlsx_dir.resolve()) or not candidate.is_file() or candidate.suffix.lower() != ".xlsx":
            ap.error(f"File Excel không hợp lệ cho ID {q['id']}")
    print(f"[INFO] {len(queries)} queries | xlsx_dir={xlsx_dir} | output={output_path}")
    print(f"[INFO] mode={mode} | LLM model={os.getenv('MODEL_NAME') or 'qwen/qwen3-7-flash'} | concurrency={concurrency}")

    if get_client() is None:
        print("[ERROR] Chưa cấu hình OPENROUTER_API_KEY. Đặt biến môi trường rồi chạy lại:", file=sys.stderr)
        print("        export OPENROUTER_API_KEY=sk-or-...", file=sys.stderr)
        print("   hoặc tạo file .env với dòng OPENROUTER_API_KEY=...", file=sys.stderr)
        print("   Lấy key tại https://openrouter.ai/", file=sys.stderr)
        sys.exit(2)
    if not 0 < float(cfg.get('max_cost_per_question', .10)) <= .10:
        ap.error("max_cost_per_question phải > 0 và <= 0.10 USD")
    try:
        planner = PlannerClient(
            prompt_cap=cfg.get('max_prompt_price_per_million', 1.0),
            completion_cap=cfg.get('max_completion_price_per_million', 4.0),
            max_tokens=cfg.get('max_tokens_plan', 2000),seed=cfg.get('llm_seed',42))
    except Exception as error:
        print(f"[ERROR] Không khởi tạo được planner: {error}", file=sys.stderr)
        sys.exit(2)

    results: dict[str, str] = {}
    t0 = time.time()
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    from src.run_context import run_context
    context=run_context(Path(__file__).resolve().parent,queries_path,xlsx_dir,queries,cfg,mode,concurrency,
                        os.getenv('MODEL_NAME') or 'qwen/qwen3-7-flash')
    (log_dir / 'run_context.json').write_text(json.dumps(context,ensure_ascii=False,indent=2),encoding='utf-8')
    records = []
    progress_path = log_dir / "questions.jsonl"
    progress_path.write_text("", encoding="utf-8")

    def task(q):
        started = time.perf_counter()
        record = {"id": q["id"], "file_name": q["file_name"], "query": q["query"],
                  "stage": "parse", "status": "ok", "mode": mode}
        xlsx_path = xlsx_dir / q["file_name"]
        try:
            if time.monotonic()-run_started >= cfg.get('run_timeout',2400):
                raise RuntimeError('Run deadline exceeded; no more API calls')
            ans = None
            settings = dict(cfg)
            settings['question_timeout'] = min(cfg.get('question_timeout',115),
                max(.1,cfg.get('run_timeout',2400)-(time.monotonic()-run_started)))
            ans = answer_with_tools(xlsx_path, q['query'], planner, record, settings)
            if ans is None or ans == "":
                record["status"] = "unanswered"
            ans = ans or ""
            if record.get('finalized_with_warning') and ans:
                record['status']='finalized'
            record.update(answer=ans, elapsed_seconds=round(time.perf_counter() - started, 4))
            return q["id"], ans, record
        except Exception as e:
            print(f"[WARN] {q['id']} lỗi: {type(e).__name__}", file=sys.stderr)
            record.update(status="error", error_type=type(e).__name__, answer='', validated=False,
                          failure_reason=f'Processing failed: {type(e).__name__}',
                          elapsed_seconds=round(time.perf_counter() - started, 4))
            return q["id"], '', record

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futs = {pool.submit(task, q): q for q in queries}
        for fut in as_completed(futs):
            qid, ans, record = fut.result()
            records.append(record)
            with progress_path.open("a", encoding="utf-8") as stream:
                # Workbook previews and row samples may contain Excel dates.
                # Keep logs JSON-safe without changing the answer value.
                stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            results[qid] = ans
            q = futs[fut]
            print(f"  {record['status'].upper()} {qid} -> {ans[:120]}")

    elapsed = time.time() - t0
    print(f"[INFO] Hoàn tất {len(results)}/{len(queries)} trong {elapsed:.1f}s ({elapsed/len(queries):.1f}s/câu)")

    # ghi submission.csv theo đúng thứ tự queries.json
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writerow(["id", "answer"])
        for q in (sorted(queries,key=lambda q:int(q['id'])) if mode=='llm-v3' and all(str(q['id']).isdigit() for q in queries) else queries):
            w.writerow([q["id"], results.get(q["id"], "")])

    print(f"[INFO] Đã ghi {output_path}")
    order = {str(q['id']): i for i, q in enumerate(queries)}
    records.sort(key=lambda item: order[str(item['id'])])
    (log_dir / "questions.jsonl").write_text(
        "\n".join(json.dumps(record, ensure_ascii=False, default=str) for record in records) + "\n", encoding="utf-8")
    usage = summarize_usage(records)
    memory = peak_memory_mb()
    elapsed = time.monotonic() - run_started
    summary = {"questions": len(queries), "answered": sum(r['status'] in {'ok','finalized'} for r in records),
               "elapsed_seconds": elapsed, "mode": mode,
               "model": os.getenv('MODEL_NAME') or 'qwen/qwen3-7-flash',
               "cost_verified": usage['cost_complete'], "memory_verified": memory is not None and memory<=(4096 if mode=='llm-v3' else 1024),
               "peak_memory_mb": memory,
               "pipeline_version": v3_version(cfg) if mode=='llm-v3' else 'tools-v4',
               "memory_measurement_scope": "main_process_peak_only",
               "resource_compliance_verified": False,
               "disk_verified": False,
               "usage": usage}
    (log_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # cảnh báo giới hạn đề thi
    if elapsed > 40 * 60:
        print(f"[WARN] Tổng thời gian {elapsed/60:.1f} phút vượt ngưỡng 40 phút/20 câu của đề!", file=sys.stderr)
    if any(r['status'] not in {'ok','finalized'} for r in records):
        sys.exit(3)


if __name__ == "__main__":
    main()
