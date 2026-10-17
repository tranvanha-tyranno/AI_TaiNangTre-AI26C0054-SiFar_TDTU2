# Hướng dẫn chạy và nộp bài Excel QA

Chương trình đọc các file Excel và câu hỏi, gọi OpenRouter, rồi tạo **`output/submission.csv`**.

Bạn thực hiện theo thứ tự: **chuẩn bị dữ liệu → build Docker → chạy → lấy CSV**. API key được điền trong lệnh chạy ở bước 3.

## 1. Chuẩn bị trước khi chạy

**Điều kiện bắt buộc:** phải có thư mục `input/` tại thư mục gốc của bài làm **trước khi build và chạy Docker**. Thư mục này phải chứa `input/queries.json` và thư mục `input/xlsx_files/` có các file Excel tương ứng. Nếu chưa có, hãy tạo đúng cấu trúc và chép dữ liệu vào đó trước khi chuyển sang bước 2.

Cài và mở **Docker Desktop**, chọn chế độ **Linux containers**, chờ Docker Engine sẵn sàng. Không cần cài Python trên máy để chạy bằng Docker.

Mở thư mục bài làm có `Dockerfile` bằng File Explorer. Gõ `powershell` vào thanh địa chỉ của File Explorer rồi nhấn Enter. Các lệnh bên dưới phải chạy trong cửa sổ PowerShell đó.

Kiểm tra cấu trúc thư mục:

```text
thu-muc-bai-lam/
├── Dockerfile
├── .dockerignore
├── README.md
├── requirements.txt
├── main.py
├── src/
├── config/
│   ├── config.yaml
│   └── error_memory.json
├── input/
│   ├── queries.json
│   └── xlsx_files/
│       ├── book1.xlsx
│       └── book2.xlsx
└── output/                 ← chương trình ghi submission.csv tại đây
```

**Dữ liệu cần đặt:**

- Câu hỏi: `input/queries.json`.
- Excel tương ứng: `input/xlsx_files/`.
- Mỗi `file_name` trong câu hỏi phải trùng tên một file Excel trong `xlsx_files/`.

Ví dụ nội dung `queries.json`:

```json
[
  {"id": 1, "file_name": "book1.xlsx", "query": "Câu hỏi dựa trên dữ liệu book1.xlsx"},
  {"id": 2, "file_name": "book2.xlsx", "query": "Câu hỏi dựa trên dữ liệu book2.xlsx"}
]
```

Nếu `input/` đã có dữ liệu thì có thể dùng ngay. Muốn đổi dataset, thay cả `queries.json` và các Excel trong `input/xlsx_files/` bằng bộ mới. Giữ nguyên tên `input/` và `output/`; không sửa đường dẫn trong lệnh chạy.

## 2. Build Docker

Copy và chạy lệnh này:

```powershell
docker build --platform linux/amd64 -t sifar-excel-qa:latest .
```

Chờ lệnh hoàn tất thành công rồi mới sang bước 3. Dấu chấm `.` cuối lệnh nghĩa là build từ thư mục bài làm đang mở.

Chạy lại bước build khi sửa code, config hoặc thư viện. Khi chỉ thay dữ liệu hay API key, chạy thẳng bước 3.

## 3. Chạy chương trình

**Trong khối lệnh dưới đây, chỉ thay `THAY_BANG_API_KEY` bằng chuỗi OpenRouter API key của bạn.** Giữ dấu ngoặc kép quanh key. Key là một chuỗi, không phải đường dẫn đến file; không điền key vào Dockerfile hay config.

Copy toàn bộ khối và chạy trong PowerShell:

```powershell
New-Item -ItemType Directory -Force .\output | Out-Null

docker run --rm --platform linux/amd64 --cpus 6 --memory 4g `
  --mount "type=bind,source=$($PWD.Path)/input,target=/input,readonly" `
  --mount "type=bind,source=$($PWD.Path)/output,target=/output" `
  sifar-excel-qa:latest `
  --xlsx-dir /input/xlsx_files `
  --queries /input/queries.json `
  --output /output/submission.csv `
  --openrouter-key "THAY_BANG_API_KEY" `
  --openrouter-model qwen/qwen3.7-flash `
  --openrouter-base-url https://openrouter.ai/api/v1
```

Dấu `` ` `` ở cuối dòng dùng để xuống dòng trong PowerShell. Không thêm dấu cách sau ký tự này. Lệnh chạy gọi OpenRouter thật và phát sinh phí API.

### Sáu tham số BTC truyền vào

Các tham số nằm **sau `sifar-excel-qa:latest`** trong lệnh trên:

| Tham số | Giá trị trong lệnh | Chức năng |
|---|---|---|
| `--xlsx-dir` | `/input/xlsx_files` | Đọc các workbook Excel. |
| `--queries` | `/input/queries.json` | Đọc danh sách câu hỏi. |
| `--output` | `/output/submission.csv` | Ghi CSV kết quả. |
| `--openrouter-key` | Key bạn điền | Xác thực OpenRouter. |
| `--openrouter-model` | `qwen/qwen3.7-flash` | Chọn model do BTC cung cấp. |
| `--openrouter-base-url` | `https://openrouter.ai/api/v1` | Địa chỉ API. |

**Đường dẫn trên máy và trong Docker tương ứng như sau:**

| Trên máy của bạn | Trong Docker |
|---|---|
| `input/xlsx_files/` | `/input/xlsx_files/` |
| `input/queries.json` | `/input/queries.json` |
| `output/submission.csv` | `/output/submission.csv` |

Hai dòng `--mount` tạo liên kết này. Vì vậy, dù dữ liệu lấy từ Public_data_1 hay Public_data_2, các tham số trong container vẫn là `/input/...` và `/output/...`. Không thay chúng bằng `/Public_data_1/...` hoặc `/Public_data_2/...`.

## 4. Lấy kết quả

Chờ chương trình xử lý xong toàn bộ câu hỏi và hiện thông báo **`Đã ghi /output/submission.csv`**. File CSV được ghi ở cuối lần chạy.

Sau đó chạy:

```powershell
$LASTEXITCODE
Get-Content .\output\submission.csv -Encoding UTF8
```

Bạn cũng có thể mở trực tiếp file **`output/submission.csv`** bằng File Explorer. Lần chạy sau sẽ ghi đè file này.

CSV dùng UTF-8, có đúng hai cột `id,answer`, đủ mỗi ID một lần; ID số được sắp tăng dần. Câu không trả lời được có answer rỗng. Mã thoát `0` nghĩa là đã tạo xong kết quả, không phải điểm chính xác của đáp án.

Chương trình chỉ tạo CSV. Không tạo thư mục log, file JSONL, summary hay debug; tiến trình được hiển thị trên terminal.

## 5. Các file cần ZIP để nộp

Chỉ chọn đúng các mục này khi bạn tự tạo ZIP:

```text
Dockerfile
.dockerignore
README.md
requirements.txt
main.py
config/
src/
```

- `Dockerfile` phải nằm ngay ở gốc ZIP, không nằm trong một thư mục cha.
- Giữ đủ `config/config.yaml` và `config/error_memory.json`.
- Không chọn `input/`, `output/`, `outputs/`, `Test/`, `tests/`, `dev_archive/`, `docs/`, `.venv/`, `.env`, `.git/`, `__pycache__/`, file `.pyc` hoặc script phát triển.
- Không đưa API key vào ZIP. Đặt tên ZIP theo tên đội; dung lượng không quá 100 MB.

Khi chấm, BTC tự gắn thư mục dữ liệu/kết quả và truyền sáu tham số cho image. Người chấm không cần sửa Dockerfile, điền config, tạo `.env` hoặc chạy script của đội. Image đã khai báo chương trình khởi động bằng `ENTRYPOINT`.

## 6. Nếu không chạy được

| Thông báo / hiện tượng | Cách xử lý |
|---|---|
| Không kết nối được Docker Engine | Mở Docker Desktop, chờ Engine sẵn sàng rồi chạy lại. |
| Không tìm thấy `Dockerfile` khi build | Mở PowerShell tại đúng thư mục bài làm có Dockerfile. |
| Chưa có thư mục `input/` | Tạo `input/` tại thư mục gốc, thêm `queries.json` và thư mục `xlsx_files/` có các file Excel, rồi mới build/chạy Docker. |
| Không tìm thấy `/input/queries.json` | Kiểm tra `input/queries.json` có tồn tại và giữ nguyên hai dòng mount ở bước 3. |
| Không tìm thấy file Excel | Kiểm tra `file_name` trong câu hỏi trùng tên file trong `input/xlsx_files/`, kể cả chữ hoa/thường trên Linux. |
| HTTP 401 hoặc 403 | Kiểm tra API key và quyền truy cập. |
| HTTP 402 | Kiểm tra số dư hoặc hạn mức tài khoản OpenRouter. |
| Chưa thấy CSV khi chương trình còn chạy | Chờ xử lý xong toàn bộ câu hỏi; CSV được ghi ở cuối lần chạy. |
| Kết quả không nằm trong `output/` | Dùng nguyên lệnh bước 3 tại thư mục bài làm; dòng mount output phải có `source=.../output,target=/output`. |
