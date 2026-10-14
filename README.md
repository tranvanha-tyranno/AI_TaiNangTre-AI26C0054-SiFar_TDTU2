# Excel QA pipeline

Pipeline cho đề **Hỏi đáp trên bảng tính Excel** (Chủ đề 2). Chương trình nhận một thư mục `.xlsx` và `queries.json`, sau đó ghi `submission.csv` với đúng hai cột `id,answer`.

## Cài đặt

### Môi trường Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# tái tạo chính xác phiên bản đã kiểm:
# python -m pip --python .venv/Scripts/python.exe install -r requirements-lock.txt
```

Copy `.env.example` thành `.env` và điền `OPENROUTER_API_KEY` để chạy online. Chương trình đọc `.env`, giữ ưu tiên biến môi trường hiện có.

### Dashboard trực quan (chạy cục bộ)

```bash
./.venv/Scripts/python.exe dashboard.py
# đổi cổng: ./.venv/Scripts/python.exe dashboard.py --port 8502
```

Mở `http://127.0.0.1:8501` (giữ terminal chạy; Ctrl+C để dừng).

*   Đọc nhật ký hiện có; hiển thị câu hỏi, đáp án, mức khớp file mẫu, thời gian và nhánh xử lý. Chọn dataset ở dropdown **DATASET** (Public_data_1 hoặc từng suite trong `Test/`), chọn lần chạy ở **LẦN CHẠY ĐANG XEM**.
*   Tổng quan: câu hỏi & kết quả, bộ lọc, chi tiết từng câu (nhánh `deterministic` / `llm_direct`, thời gian, loại lỗi).
*   Dữ liệu Excel: xem sheet gốc với địa chỉ dòng/cột, vùng ô gộp — theo dataset đang chọn.
*   Luồng xử lý: 4 bước hiện có + kế hoạch RAG/planner chưa triển khai, kèm giới hạn đề (40 phút / 20 câu, $0.10/câu, 1 GB, 100 MB ZIP).
*   Nút **Chạy mới**: chọn **Dataset**, **Chế độ** (LLM / Offline / Hybrid) và **Phạm vi** (một câu / toàn bộ). Mỗi lần chạy lưu riêng ở `outputs/runs/` và gắn `dataset` trong `metadata.json`; trạng thái tự cập nhật.
*   **Bộ kiểm thử trong Test/**: thẻ 5 suite ở Tổng quan — bấm thẻ để chuyển dataset; xem README từng suite.

Dashboard chỉ lắng nghe trên `127.0.0.1`/`localhost`, kiểm tra `Host`/`Origin`/`X-Dashboard-Token`, không hiển thị khóa API. Token/chi phí chưa đo (hiển thị "Chưa đo").

## Chạy bằng dòng lệnh

### Offline (không cần API key)

```powershell
python main.py --xlsx_dir .\Public_data_1\xlsx_files --queries .\Public_data_1\queries.json --output .\submission.csv --mode offline
# hoặc dùng config mặc định:
python main.py --config .\config\config.yaml --mode offline
# trực tiếp không cần venv activate:
.\.venv\Scripts\python.exe main.py --mode offline --output outputs/submission.csv
```

### Hybrid / LLM qua OpenRouter (Qwen)

```powershell
$env:OPENROUTER_API_KEY = "sk-or-..."
python main.py --config .\config\config.yaml              # hybrid (mặc định)
python main.py --mode llm --xlsx_dir .\Public_data_1\xlsx_files --queries .\Public_data_1\queries.json --output outputs/submission.csv
# Linux/macOS: export OPENROUTER_API_KEY=...
```

Tuỳ chọn chung: `--xlsx_dir`, `--queries`, `--output`, `--log-dir`, `--concurrency 1..6`, `--mode hybrid|llm|offline`, `--no-llm`. Đọc `xlsx_files/` + `queries.json` từ tham số, không hard-code. `OPENROUTER_API_KEY` / `MODEL_NAME=qwen/qwen3-7-flash` / `OPENROUTER_BASE_URL` cấu hình qua ENV hoặc `.env` / `config.yaml`.

Đã chạy offline trên dữ liệu công khai: đủ 20 dòng, khớp 20/20 với `Public_data_1/sample_submission.csv` (so sánh với file mẫu, chưa chứng minh tập ẩn). `00:00.4s` cho 20 câu ở `--mode offline --concurrency 4`.

### Đánh giá

```powershell
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction outputs/submission.csv --reference Public_data_1/sample_submission.csv
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction Test/01_smoke_replica/submission.csv --reference Test/01_smoke_replica/expected_submission.csv
```

## Bộ kiểm thử trong `Test/`

Năm suite riêng, mỗi suite là một thư mục con của `Test/` với cấu trúc **dựa trên `Public_data_1`** (cùng dạng `xlsx_files/` + `queries.json` + `expected_submission.csv` + `README.md`), tạo bởi `scripts/gen_test_suites.py`:

| Suite | Mục đích | Dữ liệu | Câu hỏi |
|-------|----------|---------|---------|
| `01_smoke_replica` | Smoke nhanh, không cần LLM | `mini_people.xlsx` (merged `Name`/`Date of`, 5 dòng) + `mini_fiscal.xlsx` | 3 câu: second-youngest, top score, fiscal Yes/No |
| `02_merged_hierarchy` | Ô gộp & tiêu đề phân cấp | `hierarchy.xlsx` (Household, merged 2-3 dòng) + `industry_hours.xlsx` | 2 câu: tổng 2024, xếp hạng ngành |
| `03_multisheet_multitable` | Nhiều sheet & nhiều bảng | `multi.xlsx` (Summary + Details, 2 bảng trên 1 sheet) | 2 câu: chênh lệch Manufacturing/Construction, tổng Summary 2024 |
| `04_robustness` | Biên & bảo mật | `edge.xlsx` (dấu phẩy, nháy, khoảng trắng, ô rỗng) + `queries_duplicate.json` / `queries_bad_path.json` | 1 câu hợp lệ + 2 file kỳ vọng lỗi (ID trùng, traversal) |
| `05_truncation_perf` | Cắt ngắn & hiệu năng | `large.xlsx` (500 dòng) | 4 câu tra ID 1/100/250/500 |

Chạy từng suite:

```powershell
# smoke
.\.venv\Scripts\python.exe main.py --mode offline --xlsx_dir ./Test/01_smoke_replica/xlsx_files --queries ./Test/01_smoke_replica/queries.json --output ./Test/01_smoke_replica/submission.csv
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction ./Test/01_smoke_replica/submission.csv --reference ./Test/01_smoke_replica/expected_submission.csv

# hierarchy
.\.venv\Scripts\python.exe main.py --mode offline --xlsx_dir ./Test/02_merged_hierarchy/xlsx_files --queries ./Test/02_merged_hierarchy/queries.json --output ./Test/02_merged_hierarchy/submission.csv

# multisheet
.\.venv\Scripts\python.exe main.py --mode offline --xlsx_dir ./Test/03_multisheet_multitable/xlsx_files --queries ./Test/03_multisheet_multitable/queries.json --output ./Test/03_multisheet_multitable/submission.csv

# robustness — hợp lệ
.\.venv\Scripts\python.exe main.py --mode offline --xlsx_dir ./Test/04_robustness/xlsx_files --queries ./Test/04_robustness/queries.json --output ./Test/04_robustness/submission.csv
# kỳ vọng lỗi (exit 2, không ghi file)
.\.venv\Scripts\python.exe main.py --mode offline --xlsx_dir ./Test/04_robustness/xlsx_files --queries ./Test/04_robustness/queries_duplicate.json --output ./Test/04_robustness/out.csv; echo $LASTEXITCODE
.\.venv\Scripts\python.exe main.py --mode offline --xlsx_dir ./Test/04_robustness/xlsx_files --queries ./Test/04_robustness/queries_bad_path.json --output ./Test/04_robustness/out.csv; echo $LASTEXITCODE

# truncation/perf
.\.venv\Scripts\python.exe main.py --mode offline --xlsx_dir ./Test/05_truncation_perf/xlsx_files --queries ./Test/05_truncation_perf/queries.json --output ./Test/05_truncation_perf/submission.csv

# tái tạo toàn bộ Test/:
.\.venv\Scripts\python.exe scripts/gen_test_suites.py
```

Trên dashboard: chọn dataset ở dropdown, bấm **Chạy mới** (dataset được lưu vào `metadata.json` và dùng cho `/api/state?dataset=...` và `/api/workbook?dataset=...`).

### Chạy kiểm thử tự động

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# Kiểm thử của Test/ (CLI + dashboard theo dataset):
.\.venv\Scripts\python.exe -m unittest discover -s Test -v
# hoặc: .\.venv\Scripts\python.exe -m unittest tests.test_cli tests.test_dashboard Test.test_test_suites -v
```

## Thiết kế

*   `src/deterministic_qa.py`: đọc trực tiếp ma trận Excel, mở rộng ô gộp, nhận diện tiêu đề nhiều dòng, lookup/tính toán số học (p4_t01..p4_t10; tập ẩn rơi xuống LLM).
*   `src/excel_parser.py`: chuyển bảng thành Markdown để đưa vào prompt khi cần LLM (`_expand_merged`, `_header_depth`, `serialize_for_llm` cắt 60/40 khi > 14000 chars).
*   `src/llm_client.py`: OpenAI-compatible client cho OpenRouter, model mặc định `qwen/qwen3-7-flash`, header `HTTP-Referer`/`X-Title`, `reasoning.enabled=False`, retry 1 lần, timeout 60s.
*   `main.py`: CLI, chạy song song (`--concurrency`), giữ thứ tự câu hỏi, ghi CSV UTF-8, `questions.jsonl` + `summary.json`.
*   `dashboard.py`: `datasets()` quét `Public_data_1` + `Test/*/queries.json`; `build_state(dataset)` / `workbook(..., dataset)`; `start_run(..., dataset)` lưu dataset vào metadata và truyền `--xlsx_dir`/`--queries` tương ứng; API `/api/datasets`, `/api/state?dataset=`, `/api/workbook?dataset=`.
*   `Test/` + `scripts/gen_test_suites.py`: 5 suite như trên.

## Nhật ký & giới hạn

Nhật ký ở `outputs/logs/questions.jsonl` (từng câu: `stage`, `status`, `elapsed_seconds`) và `outputs/logs/summary.json`; báo cáo so sánh ở `outputs/evaluation.json`. Dùng `--log-dir` để đổi thư mục.

Exit code 0 khi đủ đáp án; 2 cho đầu vào không hợp lệ hoặc thiếu API ở `mode llm`; 3 nếu có câu lỗi/chưa trả lời (CSV vẫn xuất với đáp án trống).

Giới hạn đề (`COMPETITION_CONSTRAINTS.md`): model `qwen/qwen3-7-flash` qua OpenRouter, không hard-code key; ≤ $0.10/câu (gồm retry); ≤ 40 phút/20 câu (6 vCPU, 12 GB RAM); ≤ 1 GB bộ nhớ; ZIP ≤ 100 MB; Exact Match.

Thư mục: `scripts/` (evaluate, gen_test_suites), `tests/` (CLI, dashboard), `Test/` (5 suite), `docs/`, `outputs/`, `config/`. Không đưa `.venv`, `.env`, `outputs` vào ZIP.
