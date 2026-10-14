"""Local dashboard. Run: python dashboard.py --port 8501."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo
from src.usage import summarize_usage

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "dashboard" / "dist"
OUTPUTS = ROOT / "outputs"
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.Lock()
JOB = {"running": False, "run_id": None, "returncode": None, "messages": [], "started": None}


def read_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def queries():
    return read_json(ROOT / "Public_data_1" / "queries.json", [])


def reference():
    try:
        with (ROOT / "Public_data_1" / "sample_submission.csv").open(encoding="utf-8-sig", newline="") as stream:
            return {r["id"]: r["answer"] for r in csv.DictReader(stream)}
    except (OSError, KeyError):
        return {}


def run_dirs():
    found = {}
    for name, path in [("latest", OUTPUTS / "logs"), ("smoke", OUTPUTS / "llm_smoke_logs")]:
        if (path / "questions.jsonl").exists():
            found[name] = path
    base = OUTPUTS / "runs"
    if base.exists():
        for path in base.iterdir():
            if path.is_dir() and (path / "metadata.json").exists():
                found[path.name] = path
    return dict(sorted(found.items(), key=lambda pair: pair[1].stat().st_mtime, reverse=True))


def records(path):
    result = {}
    try:
        for line in (path / "questions.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
                result[str(record["id"])] = record
            except (ValueError, KeyError):
                continue  # Last line may still be being written.
    except OSError:
        pass
    return result


def safe_config():
    # Read only safe values, never return API credentials or raw .env content.
    from dotenv import dotenv_values
    local = dotenv_values(ROOT / ".env")
    return {"model": os.environ.get("MODEL_NAME") or local.get("MODEL_NAME") or "qwen/qwen3-7-flash",
            "key_configured": bool(os.environ.get("OPENROUTER_API_KEY") or local.get("OPENROUTER_API_KEY")),
            "base_url": "https://openrouter.ai/api/v1"}


def build_state(selected=None):
    directories = run_dirs()
    if selected and selected not in directories:
        raise ValueError("Không tìm thấy lần chạy")
    preferred = next((key for key,directory in directories.items()
                      if read_json(directory / 'summary.json',{}).get('pipeline_version') == 'tools-v1'),None)
    selected = selected or preferred or ("latest" if "latest" in directories else next(iter(directories), None))
    path = directories.get(selected)
    data = records(path) if path else {}
    meta = read_json(path / "metadata.json", {}) if path else {}
    summary = read_json(path / "summary.json", {}) if path else {}
    all_queries = queries()
    if meta.get("ids") is not None:
        included = {str(key) for key in meta["ids"]}
        all_queries = [q for q in all_queries if str(q["id"]) in included]
    elif selected == "smoke":
        all_queries = [q for q in all_queries if str(q["id"]) in data]
    expected = reference()
    rows = []
    for q in all_queries:
        record = data.get(str(q["id"]), {})
        answer = record.get("answer", "")
        complete = bool(record)
        sample = expected.get(str(q["id"]))
        match = answer == sample if complete and sample is not None else None
        rows.append({**q, **record, "answer": answer, "reference": sample, "match": match,
                     "status": record.get("status", "pending")})
    with LOCK:
        job = dict(JOB)
        job["messages"] = list(JOB["messages"][-20:])
    running = job["running"] and job["run_id"] == selected
    elapsed = summary.get("elapsed_seconds", 0)
    if running:
        elapsed = time.time() - job["started"]
    elif meta.get("finished"):
        elapsed = meta.get("elapsed_seconds", elapsed)
    choices = []
    for key, directory in directories.items():
        information = read_json(directory / "metadata.json", {})
        total = read_json(directory / "summary.json", {})
        choices.append({"id": key, "mode": information.get("mode") or total.get("mode", "unknown"),
                        "label": information.get("label") or ("Nhật ký lần gần nhất" if key == "latest" else "Thử một câu LLM")})
    matched = sum(row["match"] is True for row in rows)
    compared = sum(row["match"] is not None for row in rows)
    measured_usage = summarize_usage([row for row in rows if row['status'] != 'pending'])
    return {"csrf": TOKEN, "config": safe_config(), "runs": choices, "selected": selected,
            "rows": rows, "job": job, "running": running,
            "summary": {**summary, "mode": meta.get("mode") or summary.get("mode", "unknown"),
                "questions": len(rows), "completed": sum(row["status"] != "pending" for row in rows),
                "answered": sum(row["status"] == "ok" and bool(row["answer"]) for row in rows),
                "matched": matched, "compared": compared, "elapsed_seconds": elapsed,
                "pipeline_version": summary.get('pipeline_version') or next((row.get('pipeline_version') for row in rows if row.get('pipeline_version')),None),
                "usage": measured_usage},
            "catalog": queries(), "files": sorted({q["file_name"] for q in queries()})}


def start_run(mode, ids):
    if mode not in {"llm", "offline", "hybrid"}:
        raise ValueError("Chế độ không hợp lệ")
    all_queries = queries()
    if ids is not None:
        if not isinstance(ids, list) or not ids:
            raise ValueError("Chọn ít nhất một câu hỏi")
        wanted = {str(key) for key in ids}
        valid = {str(q["id"]) for q in all_queries}
        if not wanted <= valid:
            raise ValueError("ID câu hỏi không hợp lệ")
        all_queries = [q for q in all_queries if str(q["id"]) in wanted]
    with LOCK:
        if JOB["running"]:
            raise ValueError("Một lần chạy đang diễn ra; chờ hoàn thành")
        now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        name = now.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
        directory = OUTPUTS / "runs" / name
        directory.mkdir(parents=True)
        metadata = {"mode": mode, "ids": [q["id"] for q in all_queries],
                    "label": now.strftime("%d/%m %H:%M:%S"), "timezone": "Asia/Ho_Chi_Minh", "finished": False}
        (directory / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        (directory / "queries.json").write_text(json.dumps(all_queries, ensure_ascii=False), encoding="utf-8")
        JOB.update(running=True, run_id=name, returncode=None, messages=[], started=time.time())

    def worker():
        code = 1
        try:
            process = subprocess.Popen([sys.executable, "-u", str(ROOT / "main.py"),
                "--mode", mode, "--concurrency", "1",
                "--queries", str(directory / "queries.json"),
                "--xlsx_dir", str(ROOT / "Public_data_1" / "xlsx_files"),
                "--output", str(directory / "submission.csv"), "--log-dir", str(directory)],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            for line in process.stdout:
                # Keep UI messages free of credentials and provider account details.
                if "[WARN]" in line:
                    line = "Có câu gặp lỗi. Xem trạng thái và loại lỗi ở chi tiết câu hỏi."
                with LOCK:
                    JOB["messages"].append(line.strip())
                    JOB["messages"] = JOB["messages"][-100:]
            code = process.wait()
        except Exception:
            with LOCK:
                JOB["messages"].append("Không khởi động được chương trình xử lý.")
        finally:
            with LOCK:
                metadata.update(finished=True, returncode=code, elapsed_seconds=time.time() - JOB["started"])
                (directory / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
                JOB.update(running=False, returncode=code)
    threading.Thread(target=worker, daemon=True).start()
    return name


def workbook(filename, sheet=None):
    if filename not in {q["file_name"] for q in queries()}:
        raise ValueError("File không nằm trong bộ câu hỏi")
    import openpyxl
    from openpyxl.utils import get_column_letter
    path = (ROOT / "Public_data_1" / "xlsx_files" / filename).resolve()
    if not path.is_relative_to((ROOT / "Public_data_1" / "xlsx_files").resolve()):
        raise ValueError("Đường dẫn không hợp lệ")
    book = openpyxl.load_workbook(path, data_only=True)
    try:
        if sheet is not None and sheet not in book.sheetnames:
            raise ValueError("Sheet không tồn tại")
        ws = book[sheet or book.sheetnames[0]]
        rows = []
        for row in ws.iter_rows(max_row=min(ws.max_row, 200), max_col=min(ws.max_column, 30)):
            rows.append(["" if cell.value is None else str(cell.value) for cell in row])
        return {"filename": filename, "sheets": book.sheetnames, "sheet": ws.title,
                "rows": rows, "columns": [get_column_letter(c) for c in range(1, min(ws.max_column, 30) + 1)],
                "total_rows": ws.max_row, "total_columns": ws.max_column,
                "merged": [str(region) for region in ws.merged_cells.ranges]}
    finally:
        book.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, body, mime="application/json; charset=utf-8", status=200):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def allowed_host(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.allowed_host():
            self.send({"error": "Host không hợp lệ"}, status=403)
            return
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/state":
                self.send(build_state(params.get("run", [None])[0]))
            elif parsed.path == "/api/workbook":
                self.send(workbook(params.get("file", [""])[0], params.get("sheet", [None])[0]))
            elif parsed.path == "/api/download":
                state = build_state(params.get("run", [None])[0])
                buffer = io.StringIO(newline="")
                writer = csv.writer(buffer)
                writer.writerow(["id", "answer"])
                writer.writerows((row["id"], row["answer"]) for row in state["rows"])
                self.send(buffer.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8")
            elif parsed.path in {"/", "/app.js", "/style.css", "/details.css"}:
                name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/details.css": "details.css"}[parsed.path]
                mime = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css", "details.css": "text/css"}[name]
                self.send((STATIC / name).read_bytes(), mime + "; charset=utf-8")
            else:
                self.send({"error": "Không tìm thấy"}, status=404)
        except ValueError as error:
            self.send({"error": str(error)}, status=400)
        except Exception:
            self.send({"error": "Không đọc được dữ liệu. Kiểm tra file đầu vào."}, status=500)

    def do_POST(self):
        origin = self.headers.get("Origin")
        if not self.allowed_host() or self.headers.get("X-Dashboard-Token") != TOKEN or origin not in {
                f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
            self.send({"error": "Yêu cầu không hợp lệ"}, status=403)
            return
        if self.path != "/api/run":
            self.send({"error": "Không tìm thấy"}, status=404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length < 10000:
                raise ValueError("Dữ liệu yêu cầu không hợp lệ")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("Yêu cầu phải là đối tượng")
            self.send({"run_id": start_run(body.get("mode"), body.get("ids"))}, status=202)
        except (ValueError, TypeError) as error:
            self.send({"error": str(error)}, status=400)


def main():
    parser = argparse.ArgumentParser(description="Dashboard Excel QA cục bộ")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    OUTPUTS.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Dashboard: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
