#!/usr/bin/env python3
"""
main.py — Pipeline Hỏi đáp trên bảng tính Excel (Chủ đề 2)

Usage:
  python main.py --openrouter-key <key>
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
    ap.add_argument("--config", type=str, default=str(Path(__file__).resolve().parent / "config/config.yaml"), help="File config yaml (optional)")
    ap.add_argument("--concurrency", type=int, default=None)
    ap.add_argument("--mode", choices=["llm-v3"], default="llm-v3",
                    help="Pipeline bài nộp: LLM + công cụ Excel + RAG")
    args = ap.parse_args()

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

    xlsx_dir = Path(args.xlsx_dir or cfg.get("xlsx_dir") or "./input/xlsx_files")
    queries_path = Path(args.queries or cfg.get("queries") or "./input/queries.json")
    output_path = Path(args.output or cfg.get("output") or "./output/submission.csv")
    concurrency = args.concurrency if args.concurrency is not None else cfg.get("concurrency", 1)
    mode = 'llm-v3'
    from src.variants import settings_for_mode
    cfg = settings_for_mode(cfg,mode)
    if not isinstance(concurrency, int) or concurrency < 1 or concurrency > 6:
        ap.error("concurrency phải nằm trong khoảng 1 đến 6")

    # env cho llm_client
    if cfg.get("model"):
        os.environ.setdefault("MODEL_NAME", cfg["model"])
    if cfg.get("base_url"):
        os.environ.setdefault("OPENROUTER_BASE_URL", cfg["base_url"])

    if not queries_path.exists():
        print(f"[ERROR] không tìm thấy {queries_path.resolve()}. Chuẩn dữ liệu: input/queries.json và input/xlsx_files/. Trong Docker, gắn thư mục input vào /input.", file=sys.stderr)
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
        if isinstance(q["id"],bool) or not isinstance(q["id"], (str, int)) or str(q["id"]) in seen:
            ap.error("ID không hợp lệ hoặc trùng lặp")
        seen.add(str(q["id"]))
        if not isinstance(q["file_name"], str) or not isinstance(q["query"], str):
            ap.error("file_name và query phải là chuỗi")
        candidate = (xlsx_dir / q["file_name"]).resolve()
        if not candidate.is_relative_to(xlsx_dir.resolve()) or not candidate.is_file() or candidate.suffix.lower() != ".xlsx":
            ap.error(f"File Excel không hợp lệ cho ID {q['id']}")
    print(f"[INFO] {len(queries)} queries | xlsx_dir={xlsx_dir} | output={output_path}")
    print(f"[INFO] mode={mode} | LLM model={os.getenv('MODEL_NAME') or 'qwen/qwen3.7-flash'} | concurrency={concurrency}")

    if get_client() is None:
        print("[ERROR] Chưa có API key. Truyền --openrouter-key trên terminal.", file=sys.stderr)
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
            return q["id"], ans, record['status']
        except Exception as e:
            print(f"[WARN] {q['id']} lỗi: {type(e).__name__}", file=sys.stderr)
            record.update(status="error", error_type=type(e).__name__, answer='', validated=False,
                          failure_reason=f'Processing failed: {type(e).__name__}',
                          elapsed_seconds=round(time.perf_counter() - started, 4))
            return q["id"], '', 'error'

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futs = {pool.submit(task, q): q for q in queries}
        for fut in as_completed(futs):
            qid, ans, status = fut.result()
            results[qid] = ans
            print(f"  {status.upper()} {qid}")

    elapsed = time.monotonic() - run_started
    print(f"[INFO] Hoàn tất {len(results)}/{len(queries)} trong {elapsed:.1f}s ({elapsed/len(queries):.1f}s/câu)")

    # Official numeric IDs are sorted by numeric value; public string IDs
    # retain their input order for backward compatibility.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writerow(["id", "answer"])
        for q in (sorted(queries,key=lambda q:int(q['id'])) if all(str(q['id']).isdigit() for q in queries) else queries):
            w.writerow([q["id"], results.get(q["id"], "")])

    print(f"[INFO] Đã ghi {output_path}")
    # cảnh báo giới hạn đề thi
    if elapsed > 40 * 60:
        print(f"[WARN] Tổng thời gian {elapsed/60:.1f} phút vượt ngưỡng 40 phút/20 câu của đề!", file=sys.stderr)
    if any(not answer for answer in results.values()):
        print("[WARN] Một số câu chưa có đáp án; CSV đã ghi đủ ID với answer rỗng.", file=sys.stderr)
    # A complete CSV with unanswered rows is a valid competition result.
    # Fatal input/setup/write failures still terminate with a nonzero code.
    return 0


if __name__ == "__main__":
    sys.exit(main())
