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

from src.excel_parser import parse_and_serialize
from src.qa_engine import post_process
from src.llm_client import ask_llm, get_client
from src.deterministic_qa import answer_deterministic


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


def answer_one_file(xlsx_path: Path, question: str, max_chars: int = 14000) -> str:
    _, table_text = parse_and_serialize(xlsx_path)
    # cắt ngắn nếu cần (parse_and_serialize đã cắt 14000)
    if len(table_text) > max_chars:
        table_text = table_text[:max_chars]
    raw = ask_llm(question, table_text)
    return post_process(raw, question)


def main():
    # Keep progress logging usable on Windows consoles with a legacy codepage.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description="Excel QA pipeline — Chủ đề 2")
    ap.add_argument("--xlsx_dir", type=str, default=None, help="Thư mục chứa .xlsx")
    ap.add_argument("--queries", type=str, default=None, help="Đường dẫn queries.json")
    ap.add_argument("--output", type=str, default=None, help="Đường dẫn submission.csv")
    ap.add_argument("--config", type=str, default="config/config.yaml", help="File config yaml (optional)")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--no-llm", action="store_true", help="Chạy offline: chỉ dùng bộ giải quyết định lượng")
    ap.add_argument("--mode", choices=["hybrid", "llm", "offline"], default=None,
                    help="hybrid (mặc định), llm, hoặc offline")
    args = ap.parse_args()

    cfg = {}
    if args.config and Path(args.config).exists():
        cfg = load_config(Path(args.config))

    xlsx_dir = Path(args.xlsx_dir or cfg.get("xlsx_dir") or "./Public_data_1/xlsx_files")
    queries_path = Path(args.queries or cfg.get("queries") or "./Public_data_1/queries.json")
    output_path = Path(args.output or cfg.get("output") or "./submission.csv")
    concurrency = args.concurrency if args.concurrency != 4 else cfg.get("concurrency", 4)
    mode = args.mode or cfg.get("mode") or "hybrid"
    if args.no_llm:
        mode = "offline"

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
    print(f"[INFO] {len(queries)} queries | xlsx_dir={xlsx_dir} | output={output_path}")
    print(f"[INFO] mode={mode} | LLM model={os.getenv('MODEL_NAME') or 'qwen/qwen3-7-flash'} | concurrency={concurrency}")

    # Hybrid/offline can run without credentials when the deterministic resolver
    # covers the query.  Only fail early for explicit LLM mode.
    if mode == "llm" and get_client() is None:
        print("[ERROR] Chưa cấu hình OPENROUTER_API_KEY. Đặt biến môi trường rồi chạy lại:", file=sys.stderr)
        print("        export OPENROUTER_API_KEY=sk-or-...", file=sys.stderr)
        print("   hoặc tạo file .env với dòng OPENROUTER_API_KEY=...", file=sys.stderr)
        print("   Lấy key tại https://openrouter.ai/", file=sys.stderr)
        sys.exit(2)

    results: dict[str, str] = {}
    t0 = time.time()

    def task(q):
        xlsx_path = xlsx_dir / q["file_name"]
        if not xlsx_path.exists():
            return q["id"], ""
        try:
            ans = None
            if mode in {"hybrid", "offline"}:
                ans = answer_deterministic(xlsx_path, q["query"])
            if ans is None and mode != "offline":
                ans = answer_one_file(xlsx_path, q["query"])
            ans = ans or ""
            return q["id"], ans
        except Exception as e:
            print(f"[WARN] {q['id']} lỗi: {e}", file=sys.stderr)
            return q["id"], ""

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futs = {pool.submit(task, q): q for q in queries}
        for fut in as_completed(futs):
            qid, ans = fut.result()
            results[qid] = ans
            q = futs[fut]
            print(f"  OK {qid} -> {ans[:120]}")

    elapsed = time.time() - t0
    print(f"[INFO] Hoàn tất {len(results)}/{len(queries)} trong {elapsed:.1f}s ({elapsed/len(queries):.1f}s/câu)")

    # ghi submission.csv theo đúng thứ tự queries.json
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writerow(["id", "answer"])
        for q in queries:
            w.writerow([q["id"], results.get(q["id"], "")])

    print(f"[INFO] Đã ghi {output_path}")

    # cảnh báo giới hạn đề thi
    avg_cost_hint = elapsed  # placeholder
    if elapsed > 40 * 60:
        print(f"[WARN] Tổng thời gian {elapsed/60:.1f} phút vượt ngưỡng 40 phút/20 câu của đề!", file=sys.stderr)


if __name__ == "__main__":
    main()
