# Excel QA pipeline

Pipeline cho đề **Hỏi đáp trên bảng tính Excel**. Chương trình nhận một thư mục
`.xlsx` và `queries.json`, sau đó ghi `submission.csv` với đúng hai cột `id,answer`.

## Cài đặt

### Dashboard trực quan (chạy cục bộ)

Trong Git Bash, tại thư mục repo:

```bash
./.venv/Scripts/python.exe dashboard.py
```

Mở `http://127.0.0.1:8501`. Giữ terminal chạy; Ctrl+C để dừng.
Nếu cổng đang dùng, thêm `--port 8502` và mở địa chỉ tương ứng.

Dashboard đọc nhật ký hiện có; hiển thị câu hỏi, đáp án, mức khớp file mẫu,
thời gian và nhánh xử lý. Chọn câu để xem chi tiết; mục Dữ liệu Excel cho xem
sheet gốc với địa chỉ dòng/cột. Mục Luồng xử lý giải thích phần đã có và phần
RAG/planner/công cụ chưa triển khai.

Nút Chạy mới cho chọn LLM, offline hoặc hybrid và một câu/toàn bộ bộ công khai.
LLM dùng khóa trong .env và có thể phát sinh phí khi bấm Bắt đầu chạy.
Mỗi lần chạy lưu riêng ở `outputs/runs/`; đáp án cập nhật sau mỗi câu hoàn thành.
Dashboard tính lại mức khớp từ nhật ký của lần đang xem, không dùng báo cáo
evaluation.json cũ. Token và chi phí hiển thị chưa đo, không phải số 0.
Dashboard không hiển thị khóa API và chỉ lắng nghe trên localhost.

### Môi trường Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Chạy thử offline

Chế độ này dùng bộ giải quyết định lượng cho các dạng bảng đã nhận diện, không
cần API key và phù hợp để kiểm tra I/O:

```powershell
python main.py `
  --xlsx_dir .\Public_data_1\xlsx_files `
  --queries .\Public_data_1\queries.json `
  --output .\submission.csv `
  --mode offline
```

Đã chạy bản offline trên dữ liệu công khai: đủ 20 dòng và khớp 20/20
với `Public_data_1/sample_submission.csv`. Đây là so sánh với file mẫu,
chưa chứng minh độ chính xác trên tập ẩn hoặc xác minh độc lập đáp án chuẩn.

## Chạy hybrid với Qwen qua OpenRouter

Hybrid thử trả lời bằng bộ tính toán cục bộ trước. Câu chưa nhận diện sẽ được
gửi tới `qwen/qwen3-7-flash`; API key chỉ đọc từ biến môi trường:

```powershell
$env:OPENROUTER_API_KEY = "sk-or-..."
python main.py --config .\config\config.yaml
```

Có thể truyền đường dẫn khác bằng `--xlsx_dir`, `--queries`, `--output`. Dùng
`--mode llm` để buộc gọi LLM cho mọi câu, hoặc `--mode offline` để không gọi
API. Nếu dùng Linux/macOS, thay cú pháp đặt biến môi trường bằng
`export OPENROUTER_API_KEY=...`.

## Thiết kế

- `src/deterministic_qa.py`: đọc trực tiếp ma trận Excel, mở rộng ô gộp,
  nhận diện tiêu đề nhiều dòng và thực hiện lookup/tính toán số học.
- `src/excel_parser.py`: chuyển bảng thành Markdown để đưa vào prompt khi cần
  LLM.
- `src/llm_client.py`: OpenAI-compatible client cho OpenRouter, model mặc định
  `qwen/qwen3-7-flash`, có retry một lần.
- `main.py`: CLI, chạy song song, giữ nguyên thứ tự câu hỏi và ghi CSV UTF-8.

Không có API key nào được lưu trong mã nguồn. Khi mở rộng cho bảng mới, thêm
resolver vào `src/deterministic_qa.py`; các câu còn lại tự động rơi xuống LLM
trong chế độ hybrid.

## Môi trường đã thiết lập và lần chạy đầu

Không cần kích hoạt môi trường; có thể chạy trực tiếp:

```powershell
.\.venv\Scripts\python.exe main.py --mode offline --output outputs/submission.csv
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction outputs/submission.csv --reference Public_data_1/sample_submission.csv
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Nếu tạo venv báo lỗi ensurepip nhưng đã có `.venv/Scripts/python.exe`, dùng pip của Python hệ thống:

```powershell
python -m pip --python .venv/Scripts/python.exe install -r requirements.txt
```

`requirements-lock.txt` lưu phiên bản đã cài và kiểm tra trong lần chạy này;
có thể dùng file đó thay `requirements.txt` để tái tạo môi trường.

Copy `.env.example` thành `.env` và điền OPENROUTER_API_KEY để chạy online.
Chương trình đọc `.env`, giữ ưu tiên biến môi trường hiện có. `.env`, `.venv`
và `outputs/` được bỏ qua bởi Git.

Nhật ký ở `outputs/logs/questions.jsonl`: câu hỏi, nhánh xử lý, trạng thái và
thời gian từng câu. Tổng kết ở `outputs/logs/summary.json`; báo cáo so sánh ở
`outputs/evaluation.json`. Dùng `--log-dir` để đổi thư mục nhật ký.

Exit code 0 khi đủ đáp án; 2 cho đầu vào không hợp lệ hoặc thiếu API ở mode llm;
3 nếu có câu lỗi/chưa trả lời (CSV vẫn được xuất với đáp án trống).

## Phạm vi bản đầu

Cập nhật kiểm tra lại: khóa mới hợp lệ và OpenRouter có ID
`qwen/qwen3.7-flash` (dấu chấm). `.env` đã dùng ID này để thử phát triển.
Một câu online đã trả đáp án, nhưng khác file mẫu; kết nối thành công chưa
đồng nghĩa trả lời đúng. Cần BTC xác nhận ID chính thức khi chấm vì văn bản đề
ghi `qwen/qwen3-7-flash`.

Kiểm tra online ngày 14/10/2026: OpenRouter trả HTTP 400,
`qwen/qwen3-7-flash is not a valid model ID`. Giữ nguyên mã model theo đề;
cần xác nhận với BTC trước khi đánh giá online. Có thể đổi `MODEL_NAME`
cho phát triển nếu đã xác định model phù hợp, nhưng phải đáp ứng model khi chấm.

Nhánh LLM hiện trả lời trực tiếp từ văn bản Excel có thể bị cắt ngắn, chưa có
RAG cấp bảng + planner JSON + bộ công cụ tổng quát. Xem `docs/IMPLEMENTATION.md`.
Chức năng codegen cũ trong qa_engine không được dùng bởi CLI.

API timeout 45 giây/lượt, tối đa hai lần thử ở nhánh trực tiếp, đã tắt retry
tự động của SDK. Chưa đo đủ token, chi phí thực tế và bộ nhớ đỉnh; chưa xác minh
các giới hạn online. Các cấu hình max_chars/max_tokens/temperature trong YAML
hiện chưa được nối vào CLI, không nên dùng chúng để khẳng định kiểm soát ngân sách.

Thư mục bổ sung: `scripts/` cho đánh giá, `tests/` cho kiểm tra CLI,
`docs/` cho trạng thái triển khai, `outputs/` cho kết quả và nhật ký.
Giới hạn đề lưu ở `COMPETITION_CONSTRAINTS.md`. Không đưa `.venv`, `.env`,
dữ liệu công khai và `outputs` vào ZIP nộp bài.
