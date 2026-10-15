# SiFar — Hỏi đáp dữ liệu Excel

Nhận thư mục Excel và `queries.json`, xuất `submission.csv` với hai cột `id,answer`. Có hai cách sử dụng độc lập: **dashboard để xem/thử nghiệm**, hoặc **CLI để chạy pipeline trực tiếp**.

## 1. Cài đặt một lần

Mở terminal tại thư mục dự án. Python **3.11 trở lên**; các lệnh dưới đây dùng PowerShell trên Windows và không cần activate venv.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Nếu tạo venv bị lỗi ensurepip nhưng đã có `.venv/Scripts/python.exe`, cài bằng pip hệ thống:

```powershell
python -m pip --python .venv/Scripts/python.exe install -r requirements.txt
```

Có thể dùng `requirements-lock.txt` thay `requirements.txt` để tái tạo các phiên bản đã lưu. Khi chạy trên Linux/macOS, dùng `.venv/bin/python` thay `.venv/Scripts/python.exe`.

## 2. Cách A — chạy dashboard

**PowerShell:**

```powershell
.\.venv\Scripts\python.exe dashboard.py
```

**Git Bash:**

```bash
./.venv/Scripts/python.exe dashboard.py
```

Mở **http://127.0.0.1:8501**. Giữ terminal chạy; **Ctrl+C** để dừng. Nếu cổng đang được dùng:

```powershell
.\.venv\Scripts\python.exe dashboard.py --port 8502
```

Sau đó mở http://127.0.0.1:8502. Khi cập nhật mã: dừng server, chạy lại và nhấn **Ctrl+F5** trên trình duyệt.

Dashboard đọc log cục bộ; mở trang và xem kết quả không gọi LLM. Chọn bộ dữ liệu, bấm **Chạy mới**, chọn phạm vi để bắt đầu một lần chạy. Mọi dataset đều dùng LLM + Tools.

**Nạp bộ dữ liệu mới ngoài Public/Test:** đặt Excel trong `xlsx_files/`, câu hỏi trong `queries.json`, rồi khởi động:

```powershell
.\.venv\Scripts\python.exe dashboard.py --dataset-dir "D:\DuLieuMoi\BoA"
```

Chọn **Dữ liệu riêng / BoA** trong danh sách dataset. Có thể thêm nhiều bộ bằng cách lặp `--dataset-dir`. Không cần tên file hay sheet giống dữ liệu mẫu. `expected_submission.csv`/`sample_submission.csv` là tùy chọn, chỉ dùng đối chiếu kết quả; không có đáp án chuẩn thì dashboard không chấm đúng/sai. Dừng server và chạy lại lệnh trên để nạp thêm bộ.

Các phần trực quan:

- **Biểu đồ tròn và bản đồ câu trả lời:** màu theo trạng thái; có thể đổi sang thời gian/chi phí. Bấm ô để mở câu, di chuột để xem nhanh.
- **Thời gian–tài nguyên:** mỗi điểm là một câu; đổi trục chi phí/token, bấm điểm để xem chi tiết. Số liệu chưa xác nhận không bị vẽ thành $0.
- **Phân bố thời gian:** trung vị, P90, câu chậm nhất; bấm cột để lọc khoảng thời gian.
- **Lịch sử:** đường tiến bộ theo tỷ lệ khớp, thời gian hoặc chi phí. Mặc định chỉ so cùng câu hỏi, tham chiếu và chế độ; bỏ chọn để xem phạm vi khác. Không nối đường qua số liệu thiếu hoặc lượt chỉ lỗi API.
- **So sánh hai lần chạy:** bản đồ câu cải thiện/bị lỗi lại, đáp án trước–sau, lỗi API riêng.
- **Chi tiết câu:** sơ đồ công cụ, số dòng qua từng bước, các lần sửa kế hoạch, preview LLM, token/chi phí và ô căn cứ.
- **Excel:** bấm ô căn cứ hoặc nhập địa chỉ như `AI2501`; xem theo vùng 200 dòng × 30 cột, không giới hạn ở góc đầu sheet.

Có thể lọc/sắp xếp/phân trang, chọn nhiều câu để chạy lại, chạy lại câu sai/lỗi và tải CSV/báo cáo JSON. Thông báo HTTP 402 lấy từ log, không phải kiểm tra số dư tài khoản hiện tại.

## 3. Cách B — chạy CLI, không cần mở dashboard

### Chạy Public bằng LLM

Cấu hình API ở mục 4, rồi chạy:

```powershell
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir .\Public_data_1\xlsx_files --queries .\Public_data_1\queries.json --output .\outputs\cli-public\submission.csv --log-dir .\outputs\cli-public\logs
```

Kết quả nằm ở `outputs/cli-public/submission.csv`. Không cần chạy `dashboard.py` hay mở trình duyệt.

**Git Bash** dùng cùng tham số:

```bash
./.venv/Scripts/python.exe main.py --mode llm --xlsx_dir ./Public_data_1/xlsx_files --queries ./Public_data_1/queries.json --output ./outputs/cli-public/submission.csv --log-dir ./outputs/cli-public/logs
```

### Chạy một bộ Test riêng

Ví dụ bộ 30 câu lọc/xếp hạng:

```powershell
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir .\Test\06_people_filters\xlsx_files --queries .\Test\06_people_filters\queries.json --output .\outputs\cli-people\submission.csv --log-dir .\outputs\cli-people\logs
```

Thay `06_people_filters` bằng bộ muốn thử. [Test/README.md](Test/README.md) liệt kê **12 bộ, 212 câu** cùng đáp án tham chiếu.

### Chạy pipeline

```powershell
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir .\Public_data_1\xlsx_files --queries .\Public_data_1\queries.json --output .\outputs\public\submission.csv --log-dir .\outputs\public\logs
```

Pipeline chỉ có một chế độ `llm`. Không có resolver theo tên file, chế độ offline hoặc chế độ hybrid. Public và dữ liệu mới đều đi qua cùng một luồng LLM + Tools.

### Dữ liệu mới và cấu hình YAML

Thay `--xlsx_dir`, `--queries`, `--output`, `--log-dir` bằng đường dẫn của bạn. Đường dẫn có khoảng trắng cần đặt trong dấu nháy. Mỗi câu phải có `id`, `file_name`, `query`; ID không trùng và file phải nằm trong thư mục Excel.

```powershell
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir "D:\DuLieuMoi\BoA\xlsx_files" --queries "D:\DuLieuMoi\BoA\queries.json" --output .\outputs\bo-a\submission.csv --log-dir .\outputs\bo-a\logs
```

Pipeline LLM đọc workbook đầu vào, lập kế hoạch tính và có thể yêu cầu đọc thêm sheet/vùng trước khi tính; không đọc CSV đáp án chuẩn. Mỗi kế hoạch phải khai báo `answer_spec` (loại đáp án, trường cần trả, phép tính). Với câu có nhãn, nối bảng, tỷ lệ hoặc đổi đơn vị, pipeline có thể bật vòng rà soát ngữ nghĩa (`semantic_review: risky`). Review là bước phụ; nếu model review trả sai định dạng, ứng viên đã qua kiểm tra xác định vẫn được giữ và log ghi `verdict: unavailable`. Việc chạy lại Public/Test đã biết là kiểm thử hồi quy, chưa chứng minh khả năng tổng quát trên tập ẩn. Bộ mới cần được đánh giá ở lần chạy đầu, trước khi chỉnh solver dựa vào lỗi của chính bộ đó.

[Báo cáo bộ mới lần đầu ngày 14/10](docs/FIRST_SEEN_20261014.md): 6/10 câu khớp, có cả lỗi solver và lỗi API; giữ nguyên kết quả lần đầu để tránh nhầm với điểm số sau khi sửa theo bộ này.

```powershell
.\.venv\Scripts\python.exe main.py --config .\config\config.yaml
```

Tham số CLI ghi đè đường dẫn/chế độ trong YAML. Dùng thư mục output/log khác cho mỗi lần muốn giữ kết quả; chạy lại cùng đường dẫn sẽ ghi đè. Dashboard tự đăng ký các lần chạy từ web; log CLI ở đường dẫn tùy chọn không tự trở thành một mục lịch sử dashboard.

## 4. Cấu hình LLM

Tạo `.env` nếu chưa có, rồi điền khóa riêng. Nếu đã có file, chỉnh file hiện tại:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

```dotenv
OPENROUTER_API_KEY=<khóa của bạn>
MODEL_NAME=qwen/qwen3-7-flash
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

ENV có sẵn được ưu tiên hơn `.env`; model/base URL trong YAML là mặc định khi ENV chưa đặt. Không commit API key.

Đề quy định `qwen/qwen3-7-flash`. Các thực nghiệm đã lưu dùng `qwen/qwen3.7-flash` (dấu chấm). Có thể đổi `MODEL_NAME` khi phát triển theo model ID được OpenRouter hỗ trợ; cần xác nhận model ID với BTC trước khi chấm. Không cần sửa mã nguồn để đổi model.

Nếu gặp HTTP 402, kiểm tra credit và hạn mức API key tại OpenRouter. Offline vẫn chạy được. CLI không tự nạp credit hay thay khóa.

## 5. Kết quả, log và đánh giá

| Tệp | Nội dung |
|---|---|
| `submission.csv` | Một dòng cho mỗi câu, chỉ đáp án cuối cùng |
| `questions.jsonl` | Trạng thái, retrieval, kế hoạch/sửa, trace, căn cứ, preview, yêu cầu dạng đáp án, token/phí |
| `summary.json` | Tổng thời gian, usage và bộ nhớ đỉnh của tiến trình CLI |
| `run_context.json` | Model, cấu hình an toàn, Git revision và hash mã nguồn/đầu vào |

Dashboard lưu riêng tại `outputs/runs/<mã-lần-chạy>/`, thêm `metadata.json` và `queries.json` để giữ bộ dữ liệu/câu hỏi/tham chiếu của lần chạy. CLI lưu các log ở `--log-dir` (mặc định `outputs/logs`).

Đánh giá CLI Public:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction .\outputs\cli-public\submission.csv --reference .\Public_data_1\sample_submission.csv --report .\outputs\cli-public\evaluation.json
```

Đánh giá CLI People:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction .\outputs\cli-people\submission.csv --reference .\Test\06_people_filters\expected_submission.csv --report .\outputs\cli-people\evaluation.json
```

Phân tích/so sánh các **lần chạy dashboard** (thay hai mã bằng thư mục thực tế):

```powershell
.\.venv\Scripts\python.exe scripts/analyze_run.py --run "outputs/runs/MA_LAN_MOI" --previous "outputs/runs/MA_LAN_CU"
```

Báo cáo `analysis.json` phân biệt lỗi API với lỗi kế hoạch/đáp án và chỉ so các câu/tham chiếu không đổi. Khớp file tham chiếu chưa chứng minh điểm trên tập ẩn; `validated=true` cũng không bảo đảm LLM chọn đúng ý nghĩa câu hỏi.

Exit code: **0** khi đủ đáp án; **1** khi thiếu đường dẫn đầu vào; **2** khi cấu hình/đầu vào/API khởi tạo lỗi; **3** khi có câu lỗi/chưa trả lời (vẫn xuất CSV, đáp án đó để trống).

## 6. Nguyên lý và giới hạn

Luồng chính: **đọc Excel → tìm vùng bảng → LLM tạo kế hoạch JSON → công cụ Python tính → kiểm tra/sửa → CSV**. Bộ giải không đọc đáp án mẫu, không thực thi Python/SQL do LLM sinh. Giữ tọa độ, ô gộp, tiêu đề nhiều cấp và nhiều sheet; preview có thể thiếu dòng nhưng công cụ đọc toàn vùng được chỉ định.

Công cụ hỗ trợ lookup, cộng ngang, lọc, cột tính, đếm/tổng/trung bình/min/max, nhóm, ghép, xếp hạng và định dạng. Kiểm tra dạng đáp án yêu cầu đúng số giá trị, vị trí/top K, số thập phân và Yes/No; các kiểm tra phạm vi/Total vẫn là heuristic.

Preview còn giữ đường dẫn tiêu đề Year/Quarter/Metric và chiều nhãn dòng. Pipeline kiểm tra yêu cầu chuyển phần trăm/đơn vị, tổng bao phủ đủ dòng của các nhóm được yêu cầu và tên xếp hạng không lặp sai; xem [báo cáo 5 bộ Test](docs/TEST_REVIEW_20261014_1951.md) để biết phạm vi kiểm tra và giới hạn.

Mặc định YAML: $0.10/câu, tối đa 4 lượt API, 2 lượt sửa kế hoạch, 115 giây/câu, 2400 giây/lần chạy, concurrency 1. Tất cả retry được ghi usage; phí thiếu dữ liệu không được coi là $0. Giới hạn đề: 40 phút/20 câu, RAM ≤1 GB và ZIP ≤100 MB. Các giới hạn và phép đo của một lần thử không bảo đảm mọi tập mới đạt yêu cầu; xem [COMPETITION_CONSTRAINTS.md](COMPETITION_CONSTRAINTS.md).

Chi tiết triển khai và thực nghiệm ở [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md), [báo cáo Public](docs/EXPERIMENT_REVIEW_20261014.md) và [báo cáo dạng đáp án](docs/ANSWER_CONTRACT_REVIEW_20261014.md).

## 7. Kiểm tra phát triển

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node tests/chart_math.cjs
```

Kiểm tra thao tác DOM khi dashboard đang chạy; chỉ phát triển cần Node/jsdom, ứng dụng không cần chúng:

```powershell
npm install --prefix outputs/dashboard-ui-test --no-save --package-lock=false jsdom@26.1.0
$env:DASHBOARD_TEST_URL = "http://127.0.0.1:8501"
node tests/dashboard_dom.cjs
```

Bài kiểm tra DOM mock yêu cầu chạy mới; không gọi LLM. Kiểm tra dữ liệu Test ở [Test/README.md](Test/README.md).

Mã chính: `main.py`, `src/`, `config/`; giao diện: `dashboard.py`, `dashboard/dist/`; kiểm tra: `tests/`, `scripts/`. Khi đóng gói, kèm mã nguồn, phụ thuộc, cấu hình và README; loại `.venv`, `.env`, `outputs` và dữ liệu mẫu khỏi ZIP.
