# Excel QA — LLM + công cụ

Pipeline chính: **đọc Excel → retrieval vùng bảng → LLM tạo kế hoạch JSON → công cụ Python thực hiện → kiểm tra/sửa → CSV**.
LLM không trả lời số liệu trực tiếp. Không dùng đáp án mẫu trong bộ giải, không thực thi Python/SQL do LLM sinh.

## Cài đặt

Python 3.12, kiểm tra trên Windows. Trong Git Bash tại thư mục repo:

```bash
python -m venv .venv
python -m pip --python .venv/Scripts/python.exe install -r requirements.txt
```

Nếu ensurepip lỗi nhưng `.venv/Scripts/python.exe` đã được tạo, dòng cài đặt thứ hai vẫn dùng pip hệ thống để cài vào venv.
`requirements-lock.txt` lưu phiên bản đã cài của môi trường hiện tại, có thể dùng thay requirements.txt.

Copy `.env.example` thành `.env` rồi điền khóa OpenRouter. Biến môi trường được ưu tiên hơn `.env`, sau đó YAML. Không commit khóa.

```dotenv
OPENROUTER_API_KEY=<khóa riêng của bạn>
MODEL_NAME=qwen/qwen3.7-flash
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

**Mã model:** văn bản đề và cấu hình mặc định ghi `qwen/qwen3-7-flash`; danh sách OpenRouter thực tế có `qwen/qwen3.7-flash` (dấu chấm). `.env` dùng ID hợp lệ để phát triển. Cần BTC xác nhận mã chính thức khi chấm; hỗ trợ thay model qua ENV, không sửa mã nguồn.

## Chạy pipeline chính

```bash
./.venv/Scripts/python.exe main.py \
  --mode llm \
  --xlsx_dir Public_data_1/xlsx_files \
  --queries Public_data_1/queries.json \
  --output outputs/submission.csv \
  --log-dir outputs/logs
```

Đường dẫn đều thay được. `--config config/config.yaml` dùng cấu hình mặc định; `--concurrency 1` mặc định để giới hạn bộ nhớ.
`llm` và `hybrid` đều chạy pipeline mới (hybrid chỉ là tên CLI tương thích, không còn tự giải bằng quy tắc trước LLM).
`--mode offline` giữ bộ giải cũ chỉ để so sánh I/O; không phải pipeline LLM và có những quy tắc chưa đúng ý nghĩa câu hỏi. Không dùng kết quả offline 20/20 để khẳng định khả năng tổng quát.

## Công cụ LLM được phép dùng

Model gọi `execute_spreadsheet_plan` với schema JSON. Bộ thực thi kiểm tra tên công cụ, tham số, cột, phạm vi và kiểu dữ liệu:

| Công cụ | Công việc |
|---|---|
| read / cell | Đọc đầy đủ vùng dữ liệu / lấy ô gốc |
| filter / derive | Lọc dòng / tính cột mới (số học, ngày và tuổi) |
| sort / take / select | Sắp xếp, lấy thứ hạng và chọn cột |
| aggregate / group | Đếm, tổng, trung bình, min/max và nhóm |
| join / concat | Ghép theo khóa / nối các vùng |
| unpivot | Chuyển nhiều cột thành dòng để tính trung bình hoặc xếp hạng |
| calculate / collect | Tính từ kết quả công cụ / gom nhiều đáp án theo thứ tự |

Ví dụ tuổi tại nhập học: read → derive `Admission - Birth` theo ngày → sort tăng dần → take offset=1 → chọn họ. Không sắp xếp ngày nhập học thay tuổi.

Parser giữ ô gộp, tọa độ và định dạng phần trăm; không tự điền mọi ô trống. Vùng tách theo hàng/cột trống, cùng vùng toàn sheet cho câu hỏi qua nhiều khối. Tiêu đề nhiều tầng được giữ trong các hàng gốc và ngữ cảnh, thay vì xóa mất. Retrieval dựa từ khóa; header inference và bảng ứng viên là heuristic, chưa bảo đảm mọi file mới.
Preview có thể thiếu dòng để tiết kiệm token; `read` và các công cụ dùng toàn bộ vùng được chỉ định. Preview giữ nhãn dòng để chọn đúng section. Không cần vector database.

## Nhật ký, token và chi phí

- `questions.jsonl`: retrieval, các kế hoạch và lỗi sửa, từng bước công cụ, ô căn cứ, thời gian từng giai đoạn, mọi lượt API.
- `summary.json`: tổng token vào/ra, tổng token, phí thực tế API báo, ước tính bảng giá, số lượt chưa rõ phí, bộ nhớ đỉnh của tiến trình.
- Chi phí lấy từ `usage.cost`, hoặc endpoint generation khi thiếu. `estimated_cost_usd` tính theo bảng giá catalog và token, không coi là phí thực tế.
- Retry hoặc sửa JSON đều được cộng; SDK không retry ngầm. Nếu lượt lỗi không có usage, ghi token/phí chưa rõ và giữ phần ngân sách đã dự phòng, không coi là miễn phí.
- Nhật ký cũ không có số liệu không thể suy ngược chính xác; cần chạy lại.

Ngân sách trong YAML: ≤ $0.10/câu, ≤ 4 lượt gọi/câu gồm retry, ≤ 2 lần sửa kế hoạch, 115 giây/câu và 2400 giây/lần chạy. Trước mỗi lượt, tính dự phòng theo số byte prompt và output tối đa; OpenRouter giới hạn giá provider qua `max_price`. Phí thực tế được trừ khi có số liệu; không tiếp tục nếu vượt ngân sách. Giới hạn token và provider có thể khiến model đắt hơn không được gọi.
Giới hạn parser 200000 ô, ZIP Excel giải nén 40 MB, intermediate tool cells 500000, join output 10000 dòng. Đây là giới hạn bảo vệ tài nguyên, file lớn hơn sẽ báo lỗi; không phải bằng chứng mọi dữ liệu ẩn đều xử lý được.
`peak_memory_mb` là bộ nhớ đỉnh tiến trình Python trong lần chạy, không phải toàn hệ thống. Bộ nhớ của dashboard không thuộc phép đo CLI.

Kiểm tra hợp lệ về cấu trúc/thực thi và định dạng không chứng minh LLM chọn đúng ý nghĩa câu hỏi. `validated=true` không có nghĩa đã đúng chuẩn BTC.

## Dashboard

```bash
./.venv/Scripts/python.exe dashboard.py
```

Mở http://127.0.0.1:8501, giữ terminal chạy; Ctrl+C để dừng. Cổng bận: thêm `--port 8502`.
Dashboard có câu hỏi/đáp án, đối chiếu file mẫu, Excel gốc, sáu bước pipeline; chi tiết hiển thị kế hoạch JSON, công cụ, ô căn cứ, token và phí từng lượt.
Nút Chạy mới dùng dữ liệu công khai và lưu riêng `outputs/runs/`; LLM có phí khi bắt đầu chạy. Mức khớp được tính lại từ nhật ký, không đọc báo cáo đánh giá cũ. API key không hiển thị; server chỉ lắng nghe localhost.

## Kiểm tra và đánh giá

```bash
./.venv/Scripts/python.exe -m unittest discover -s tests -v
./.venv/Scripts/python.exe scripts/evaluate.py \
  --prediction outputs/submission.csv \
  --reference Public_data_1/sample_submission.csv
```

File mẫu chưa được xác minh độc lập là đáp án chuẩn. Chỉ báo cáo mức khớp với file mẫu, không coi là điểm trên tập ẩn.
Exit code: 0 khi tất cả câu có đáp án; 2 cho cấu hình/đầu vào lỗi; 3 khi có câu không trả lời được (vẫn xuất đủ dòng, đáp án lỗi để trống).

## Cấu trúc

```text
main.py                  CLI, điều phối và CSV
config/config.yaml       Giới hạn và cấu hình
src/workbook_index.py    Đọc Excel, vùng bảng và retrieval
src/planner.py           Hướng dẫn và schema gọi công cụ
src/llm_client.py        OpenRouter, theo dõi từng request
src/tools/executor.py    Bộ công cụ cố định, kiểm tra và provenance
src/pipeline.py          Plan/execute/repair và định dạng
src/usage.py             Token, phí, ngân sách và bộ nhớ
dashboard.py             Server dashboard cục bộ
dashboard/dist/          Giao diện
scripts/evaluate.py      So sánh CSV độc lập với bộ giải
tests/                   Kiểm tra công cụ, ngân sách, CLI và dashboard
docs/IMPLEMENTATION.md   Trạng thái triển khai
outputs/                 Kết quả sinh ra, không commit
```

`src/deterministic_qa.py`, `src/excel_parser.py`, `src/qa_engine.py` là mã cũ; pipeline chính không dùng chúng để trả lời. Giới hạn đề lưu tại COMPETITION_CONSTRAINTS.md. ZIP nộp ≤100 MB; bỏ `.venv`, `.env`, outputs và dữ liệu công khai khỏi gói nộp.

## Dataset và bộ kiểm thử mới

Dashboard tự quét `Public_data_1` và các thư mục trong `Test/` có `queries.json` cùng `xlsx_files/`.
Chọn một hoặc nhiều bộ trong **Dataset**, rồi bấm **Chạy mới**; có thể chạy một câu hoặc toàn bộ câu hỏi của các bộ đã chọn.
Kết quả vẫn hiển thị đáp án, đối chiếu, thời gian, token/chi phí và Excel gốc. Bộ Test dùng `expected_submission.csv` để đối chiếu (hoặc `sample_submission.csv` nếu có); bộ chưa chạy hiển thị câu hỏi đang chờ.
Mỗi lần chạy lưu riêng dataset, câu hỏi và đáp án tham chiếu trong metadata. Khi chạy nhiều bộ, CSV dùng ID `dataset::id` và file Excel được tách theo thư mục dataset để tránh trùng tên; chạy một bộ giữ nguyên ID gốc.
Sau khi cập nhật mã, dừng server bằng Ctrl+C rồi chạy lại `./.venv/Scripts/python.exe dashboard.py` và tải lại trang.

Test/ có 5 suite: 01_smoke_replica, 02_merged_hierarchy, 03_multisheet_multitable, 04_robustness, 05_truncation_perf. Mỗi suite có xlsx_files/, queries.json, expected_submission.csv và README. Tái tạo bằng scripts/gen_test_suites.py. Các suite là dữ liệu kiểm thử riêng, không phải tập ẩn của BTC.

```bash
./.venv/Scripts/python.exe main.py --mode llm --xlsx_dir Test/01_smoke_replica/xlsx_files --queries Test/01_smoke_replica/queries.json --output outputs/test_submission.csv
./.venv/Scripts/python.exe scripts/evaluate.py --prediction outputs/test_submission.csv --reference Test/01_smoke_replica/expected_submission.csv
```
