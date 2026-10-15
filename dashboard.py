"""Local dashboard. Run: python dashboard.py --port 8501."""
from __future__ import annotations
import argparse
import csv
import hashlib
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
import re
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse
from src.usage import summarize_usage
from src.dashboard_analysis import decorate, summarize, compare_states, safe_context, cohort

ROOT = Path(__file__).resolve().parent
PROJECT_VERSION = "2.0.0"
STATIC = ROOT / "dashboard" / "dist"
OUTPUTS = ROOT / "outputs"
TEST_ROOT = ROOT / "Test"
EXTRA_DATASET_DIRS = []
# dataset id -> {label, xlsx_dir, queries, reference}
DATASET_DEFAULT = "public"
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.Lock()
JOB = {"running": False, "run_id": None, "returncode": None, "messages": [], "started": None}
RUN_CARD_CACHE = {}


class DashboardServer(ThreadingHTTPServer):
    # SO_REUSEADDR on Windows permits competing servers on the same port.
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def read_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def datasets():
    """Danh mục dataset cho dashboard: public + từng thư mục trong Test/."""
    result = [{"id": DATASET_DEFAULT, "label": "Public_data_1 (mặc định)", "kind": "public",
               "xlsx_dir": str(ROOT / "Public_data_1" / "xlsx_files"),
               "queries": str(ROOT / "Public_data_1" / "queries.json"),
               "reference": str(ROOT / "Public_data_1" / "sample_submission.csv")}]
    if TEST_ROOT.exists():
        for p in sorted(TEST_ROOT.iterdir()):
            if p.is_dir() and (p / "queries.json").is_file() and (p / "xlsx_files").is_dir():
                ref = p / "expected_submission.csv"
                if not ref.exists():
                    ref = p / "sample_submission.csv"
                result.append({
                    "id": p.name,
                    "label": f"Test / {p.name}",
                    "kind": "test",
                    "xlsx_dir": str(p / "xlsx_files"),
                    "queries": str(p / "queries.json"),
                    "reference": str(ref),
                    "readme": str(p / "README.md") if (p / "README.md").exists() else None,
                })
    for p in EXTRA_DATASET_DIRS:
        ref = p / "expected_submission.csv"
        if not ref.is_file():
            ref = p / "sample_submission.csv"
        result.append({
            "id": "external-" + hashlib.sha256(str(p).casefold().encode()).hexdigest()[:16],
            "label": f"Dữ liệu riêng / {p.name}", "kind": "external",
            "xlsx_dir": str(p / "xlsx_files"), "queries": str(p / "queries.json"),
            "reference": str(ref),
        })
    for dataset in result:
        dataset["question_count"] = len(read_json(Path(dataset["queries"]), []))
    return result


def configure_extra_datasets(paths):
    """Register arbitrary dataset folders without copying them into Test/."""
    folders = []
    known = {(ROOT / "Public_data_1").resolve()}
    if TEST_ROOT.is_dir():
        known.update(p.resolve() for p in TEST_ROOT.iterdir() if p.is_dir())
    for raw in paths:
        folder = Path(raw).expanduser().resolve()
        if not (folder / "xlsx_files").is_dir() or not (folder / "queries.json").is_file():
            raise ValueError(f"Dataset cần xlsx_files/ và queries.json: {folder}")
        questions = read_json(folder / "queries.json")
        if not isinstance(questions, list) or not questions or any(
                not isinstance(q, dict) or not all(k in q for k in ("id", "file_name", "query"))
                for q in questions):
            raise ValueError(f"queries.json không hợp lệ: {folder}")
        if folder not in known:
            folders.append(folder)
            known.add(folder)
    EXTRA_DATASET_DIRS[:] = folders


def parse_dataset_ids(raw: str | None) -> list[str]:
    """Hỗ trợ chọn nhiều dataset: 'a,b,c' -> ['a','b','c']; rỗng -> [DEFAULT]."""
    if raw is not None and not isinstance(raw, str):
        raise ValueError("Dataset phải là chuỗi ID")
    if not raw or not raw.strip():
        return [DATASET_DEFAULT]
    parts = [p.strip() for p in str(raw).split(",") if p.strip()]
    # dedup giữ thứ tự
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out or [DATASET_DEFAULT]


def dataset_ids():
    return {d["id"] for d in datasets()}


def dataset_for(dataset_id: str | None):
    target = (dataset_id or DATASET_DEFAULT).strip() or DATASET_DEFAULT
    # nếu truyền dạng "a,b" thì lấy phần tử đầu cho các hàm đơn lẻ cũ
    target = target.split(",")[0].strip() or DATASET_DEFAULT
    for d in datasets():
        if d["id"] == target:
            return d
    raise ValueError("Dataset không tồn tại")


def datasets_for(raw: str | None):
    ids = parse_dataset_ids(raw)
    result = []
    for ident in ids:
        found = False
        for d in datasets():
            if d["id"] == ident:
                result.append(d)
                found = True
                break
        if not found:
            raise ValueError(f"Dataset không tồn tại: {ident}")
    return result


def queries(dataset_id: str | None = None):
    selected = datasets_for(dataset_id)
    merged = []
    for ds in selected:
        for q in read_json(Path(ds["queries"]), []):
            merged.append({**q, "dataset": ds["id"], "original_id": q["id"],
                           "source_file": q["file_name"],
                           "id": f"{ds['id']}::{q['id']}" if len(selected) > 1 else q["id"],
                           "file_name": f"{ds['id']}/{q['file_name']}" if len(selected) > 1 else q["file_name"]})
    return merged


def reference(dataset_id: str | None = None):
    dataset_id = ",".join(parse_dataset_ids(dataset_id))
    if "," in dataset_id:
        merged: dict[str, str] = {}
        for ds in datasets_for(dataset_id):
            try:
                with Path(ds["reference"]).open(encoding="utf-8-sig", newline="") as stream:
                    for r in csv.DictReader(stream):
                        merged[f"{ds['id']}::{r['id']}"] = r["answer"]
            except (OSError, KeyError, FileNotFoundError):
                continue
        return merged
    ds = dataset_for(dataset_id)
    try:
        with Path(ds["reference"]).open(encoding="utf-8-sig", newline="") as stream:
            return {r["id"]: r["answer"] for r in csv.DictReader(stream)}
    except (OSError, KeyError, FileNotFoundError):
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
    def started_at(pair):
        key,path=pair
        if re.fullmatch(r'\d{8}-\d{6}-[a-z0-9]+',key):
            try: return datetime.strptime(key[:15],'%Y%m%d-%H%M%S').replace(tzinfo=timezone(timedelta(hours=7))).timestamp()
            except ValueError: pass
        log=path/'questions.jsonl'
        return log.stat().st_mtime if log.exists() else path.stat().st_mtime
    # Saving an analysis/export later must not reorder an older experiment.
    return dict(sorted(found.items(), key=started_at, reverse=True))


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
    try:
        from dotenv import dotenv_values
        local = dotenv_values(ROOT / ".env")
    except ImportError:
        local = {}
    return {"app_version": PROJECT_VERSION,
            "model": os.environ.get("MODEL_NAME") or local.get("MODEL_NAME") or "qwen/qwen3-7-flash",
            "key_configured": bool(os.environ.get("OPENROUTER_API_KEY") or local.get("OPENROUTER_API_KEY")),
            "base_url": "https://openrouter.ai/api/v1"}


def run_card(key,directory):
    signature=tuple((p.stat().st_mtime_ns,p.stat().st_size) if p.exists() else None
        for p in [directory/'metadata.json',directory/'questions.jsonl',directory/'summary.json',directory/'run_context.json'])
    cache_key=(str(directory),signature)
    if cache_key in RUN_CARD_CACHE: return {**RUN_CARD_CACHE[cache_key],'id':key}
    meta=read_json(directory/'metadata.json',{})
    total=read_json(directory/'summary.json',{})
    data=records(directory)
    dataset=meta.get('dataset') or DATASET_DEFAULT
    try: expected=meta.get('reference',reference(dataset))
    except ValueError: expected={}
    ids=meta.get('ids') or list(data)
    rows=[decorate({**data.get(str(ident),{}),'id':ident,'status':data.get(str(ident),{}).get('status','pending'),
          'match':data[str(ident)].get('answer','')==expected[str(ident)] if str(ident) in data and str(ident) in expected else None}) for ident in ids]
    analysis=summarize(rows)
    compared=sum(r['match'] is not None for r in rows)
    try: catalog=meta.get('catalog') or queries(dataset)
    except ValueError: catalog=[]
    included={str(ident) for ident in ids}
    cohort_rows=[{**q,'reference':expected.get(str(q['id']))} for q in catalog if str(q['id']) in included]
    card={'id':key,'mode':meta.get('mode') or total.get('mode','unknown'),
          'label':meta.get('label') or ('Nhật ký lần gần nhất' if key=='latest' else 'Thử một câu LLM'),
          'dataset':dataset,'questions':total.get('questions',len(ids)),'matched':analysis['outcomes'].get('match',0),
          'compared':compared,'completed':analysis['completed'],'api_errors':analysis['api_errors'],
          'repairs':analysis['repaired_questions'],'elapsed_seconds':meta.get('elapsed_seconds',total.get('elapsed_seconds',0)),
          'finished':meta.get('finished',bool(total)),
          'cohort':cohort(cohort_rows,dataset) if cohort_rows else None,
          'usage':total.get('usage') or summarize_usage(list(data.values())),
          'context':safe_context(read_json(directory/'run_context.json',{}))}
    if len(RUN_CARD_CACHE)>128: RUN_CARD_CACHE.pop(next(iter(RUN_CARD_CACHE)))
    RUN_CARD_CACHE[cache_key]=card
    return card


def build_state(selected=None, dataset_id: str | None = None, include_history=True):
    directories = run_dirs()
    if selected and selected not in directories:
        raise ValueError("Không tìm thấy lần chạy")
    if not selected:
        requested = set(parse_dataset_ids(dataset_id))
        matching = [key for key, folder in directories.items()
            if set(parse_dataset_ids(read_json(folder / "metadata.json", {}).get("dataset"))) == requested]
        selected = next(iter(matching), None)
    path = directories.get(selected)
    data = records(path) if path else {}
    meta = read_json(path / "metadata.json", {}) if path else {}
    summary = read_json(path / "summary.json", {}) if path else {}
    effective_dataset = ",".join(parse_dataset_ids(meta.get("dataset") if path else dataset_id))
    datasets_for(effective_dataset)
    all_queries = meta.get("catalog") or queries(effective_dataset)
    if meta.get("ids") is not None:
        included = {str(key) for key in meta["ids"]}
        all_queries = [q for q in all_queries if str(q["id"]) in included]
    elif selected == "smoke":
        all_queries = [q for q in all_queries if str(q["id"]) in data]
    expected = meta.get("reference", reference(effective_dataset))
    rows = []
    for q in all_queries:
        record = data.get(str(q["id"]), {})
        answer = record.get("answer", "")
        complete = bool(record)
        sample = expected.get(str(q["id"]))
        match = answer == sample if complete and sample is not None else None
        rows.append(decorate({**q, **record, "answer": answer, "reference": sample, "match": match,
                     "status": record.get("status", "pending")}))
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
    if include_history:
        choices=[run_card(key,directory) for key,directory in directories.items()]
    matched = sum(row["match"] is True for row in rows)
    compared = sum(row["match"] is not None for row in rows)
    measured_usage = summarize_usage([row for row in rows if row['status'] != 'pending'])
    return {"csrf": TOKEN, "config": safe_config(), "datasets": datasets(), "dataset": effective_dataset,
            "runs": choices, "selected": selected,
            "analysis":{**summarize(rows),'cohort':cohort(rows,effective_dataset)},"context":safe_context(read_json(path/'run_context.json',{}) if path else {}),
            "rows": rows, "job": job, "running": running,
            "summary": {**summary, "mode": meta.get("mode") or summary.get("mode", "unknown"),
                "questions": len(rows), "completed": sum(row["status"] != "pending" for row in rows),
                "answered": sum(row["status"] in {"ok","finalized"} and bool(row["answer"]) for row in rows),
                "matched": matched, "compared": compared, "elapsed_seconds": elapsed,
                "pipeline_version": summary.get('pipeline_version') or next((row.get('pipeline_version') for row in rows if row.get('pipeline_version')),None),
                "usage": measured_usage},
            "catalog": queries(effective_dataset), "files": sorted({q["file_name"] for q in all_queries})}


def start_run(mode, ids, dataset_id: str | None = None):
    if mode not in {"llm", "llm-v2"}:
        raise ValueError("Chế độ không hợp lệ")
    ds_list = datasets_for(dataset_id)
    combined_id = ",".join(d["id"] for d in ds_list)
    is_multi = len(ds_list) > 1
    all_queries = queries(combined_id)
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
        now = datetime.now(timezone(timedelta(hours=7)))
        name = now.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
        directory = OUTPUTS / "runs" / name
        directory.mkdir(parents=True)
        # Keep the original basename; dataset folders separate duplicate names.
        if is_multi:
            merged = directory / "xlsx_files"
            for ds in ds_list:
                source_root = Path(ds["xlsx_dir"]).resolve()
                for q in all_queries:
                    if q["dataset"] != ds["id"]:
                        continue
                    source = (source_root / q["source_file"]).resolve()
                    target = (merged / q["file_name"]).resolve()
                    if not source.is_relative_to(source_root) or not target.is_relative_to(merged.resolve()):
                        raise ValueError("Đường dẫn Excel không hợp lệ")
                    if not source.is_file() or source.suffix.lower() != ".xlsx":
                        raise ValueError("Không tìm thấy file Excel")
                    if not target.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, target)
            xlsx_dir_for_run = str(merged)
        else:
            xlsx_dir_for_run = ds_list[0]["xlsx_dir"]
        metadata = {"mode": mode, "dataset": combined_id, "ids": [q["id"] for q in all_queries],
                    "catalog": all_queries, "reference": reference(combined_id),
                    "label": now.strftime("%d/%m %H:%M:%S"), "timezone": "Asia/Ho_Chi_Minh", "finished": False}
        (directory / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        (directory / "queries.json").write_text(json.dumps(all_queries, ensure_ascii=False), encoding="utf-8")
        JOB.update(running=True, run_id=name, returncode=None, messages=[], started=time.time())

    def worker():
        code = 1
        try:
            process = subprocess.Popen([sys.executable, "-u", str(ROOT / "main.py"),
                "--mode", mode, "--concurrency", "1",
                "--queries", str(directory / "queries.json"),
                "--xlsx_dir", xlsx_dir_for_run,
                "--output", str(directory / "submission.csv"), "--log-dir", str(directory)],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            with process.stdout:
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


def workbook(filename, sheet=None, dataset_id: str | None = None, start_row=1, start_col=1):
    if not isinstance(start_row,int) or not isinstance(start_col,int) or min(start_row,start_col)<1:
        raise ValueError('Dòng và cột bắt đầu phải là số nguyên dương')
    query = next((q for q in queries(dataset_id) if q["file_name"] == filename), None)
    if query is None:
        raise ValueError("File không nằm trong bộ câu hỏi")
    import openpyxl
    from openpyxl.utils import get_column_letter
    ds = dataset_for(query["dataset"])
    root = Path(ds["xlsx_dir"]).resolve()
    path = (root / query["source_file"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Đường dẫn không hợp lệ")
    book = openpyxl.load_workbook(path, data_only=True)
    try:
        if sheet is not None and sheet not in book.sheetnames:
            raise ValueError("Sheet không tồn tại")
        ws = book[sheet or book.sheetnames[0]]
        if start_row>ws.max_row or start_col>ws.max_column: raise ValueError('Vị trí nằm ngoài sheet')
        end_row=min(ws.max_row,start_row+199);end_col=min(ws.max_column,start_col+29)
        rows = []
        for row in ws.iter_rows(min_row=start_row,max_row=end_row,min_col=start_col,max_col=end_col):
            rows.append(["" if cell.value is None else str(cell.value) for cell in row])
        return {"filename": filename, "sheets": book.sheetnames, "sheet": ws.title,
                "rows": rows, "columns": [get_column_letter(c) for c in range(start_col,end_col+1)],
                "start_row":start_row,"end_row":end_row,"start_col":start_col,"end_col":end_col,
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
                self.send(build_state(params.get("run", [None])[0], params.get("dataset", [None])[0]))
            elif parsed.path == "/api/workbook":
                self.send(workbook(params.get("file", [""])[0], params.get("sheet", [None])[0], params.get("dataset", [None])[0],
                                   int(params.get('row',['1'])[0]),int(params.get('col',['1'])[0])))
            elif parsed.path == '/api/compare':
                before=params.get('before',[''])[0];after=params.get('after',[''])[0]
                if not before or not after: raise ValueError('Chọn hai lần chạy để so sánh')
                self.send(compare_states(build_state(before,include_history=False),build_state(after,include_history=False)))
            elif parsed.path == '/api/report':
                state=build_state(params.get('run',[None])[0],params.get('dataset',[None])[0],include_history=False)
                self.send({key:state[key] for key in ['selected','dataset','rows','summary','analysis','context']})
            elif parsed.path == "/api/download":
                state = build_state(params.get("run", [None])[0], params.get("dataset", [None])[0])
                buffer = io.StringIO(newline="")
                writer = csv.writer(buffer)
                writer.writerow(["id", "answer"])
                writer.writerows((row["id"], row["answer"]) for row in state["rows"])
                self.send(buffer.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8")
            elif parsed.path == "/api/catalog":
                self.send({"catalog": queries(params.get("dataset", [None])[0])})
            elif parsed.path == "/api/datasets":
                self.send({"datasets": datasets(), "default": DATASET_DEFAULT})
            elif parsed.path in {"/", "/app.js", "/style.css", "/details.css", "/workspace.css",'/visuals.css','/chart-math.js'}:
                name = 'index.html' if parsed.path=='/' else parsed.path[1:]
                mime = 'text/html' if name.endswith('.html') else 'text/javascript' if name.endswith('.js') else 'text/css'
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
            self.send({"run_id": start_run(body.get("mode"), body.get("ids"), body.get("dataset"))}, status=202)
        except (ValueError, TypeError) as error:
            self.send({"error": str(error)}, status=400)


def main():
    for stream in (sys.stdout,sys.stderr):
        try: stream.reconfigure(encoding='utf-8',errors='replace')
        except AttributeError: pass
    parser = argparse.ArgumentParser(description="Dashboard Excel QA cục bộ")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--dataset-dir", action="append", default=[], metavar="PATH",
                        help="Thêm thư mục có xlsx_files/ và queries.json; có thể lặp nhiều lần")
    args = parser.parse_args()
    try:
        configure_extra_datasets(args.dataset_dir)
    except ValueError as error:
        parser.error(str(error))
    OUTPUTS.mkdir(exist_ok=True)
    try:
        server = DashboardServer(("127.0.0.1", args.port), Handler)
    except OSError:
        parser.error(f"Không mở được cổng {args.port}. Dừng dashboard cũ hoặc chọn --port khác.")
    print(f"Dashboard: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
