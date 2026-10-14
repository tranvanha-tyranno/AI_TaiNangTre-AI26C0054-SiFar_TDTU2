# AGENTS.md — Chủ đề 2: Hỏi đáp trên bảng tính Excel

> Tài liệu mô tả đề thi dành cho agent/đội phát triển. Tổng hợp từ đề chính thức (3 trang).

---

## 1. Mục tiêu (Objective)

Xây dựng **giải pháp tự động trả lời câu hỏi bằng ngôn ngữ tự nhiên** dựa trên dữ liệu trong các tệp Excel.

Đặc thù dữ liệu Excel:
- Nhiều trang tính (sheets), nhiều bảng trên cùng một trang.
- Tiêu đề phân cấp, ô gộp (merged cells), cấu trúc không đồng nhất.

Yêu cầu: giải pháp phải **xác định đúng thông tin liên quan** và đưa ra **câu trả lời chính xác**.

---

## 2. Dữ liệu được cung cấp

BTC cung cấp bộ dữ liệu công khai để các đội phát triển và tự đánh giá, gồm:

| Thành phần | Nội dung |
|---|---|
| `xlsx_files/` | Thư mục chứa các tệp Excel (`.xlsx`) |
| `queries.json` | Danh sách câu hỏi với các trường `id`, `file_name` và `query` |
| `sample_submission.csv` | Tệp mẫu kết quả gồm hai cột `id` và `answer` |

Chi tiết:

- Trong `queries.json`: `id` là mã câu hỏi; `file_name` là tên tệp Excel tương ứng; `query` là nội dung câu hỏi.
- Hình minh họa dữ liệu trong tệp Excel: bảng có các cột như `Quang`, `Van`, `Bui`, ngày sinh, điểm số, v.v. (ô gộp / tiêu đề phân cấp).

### Ví dụ `queries.json`

```json
[
  {"id": 1, "file_name": "sample.xlsx", "query": "How many people have a score higher than 80?"},
  {"id": 2, "file_name": "sample.xlsx", "query": "What is the last name of the person with the highest score?"}
]
```

### Ví dụ `submission.csv` tương ứng

```csv
id,answer
1,11
2,Ngo
```

### Tập kiểm thử

- Bài dự thi được đánh giá trên **tập kiểm thử ẩn** do BTC xây dựng theo quy trình tương tự bộ dữ liệu công khai.
- Bộ dữ liệu công khai đợt 1: *Truy cập tại đây* (link do BTC cung cấp).

---

## 3. Yêu cầu đối với bài dự thi

1. **I/O:** Giải pháp nhận đầu vào là **thư mục chứa các tệp `.xlsx`** và **tệp `queries.json`**; kết quả phải được xuất ra **tệp `submission.csv`** đúng định dạng mẫu.
2. **Một dòng / một câu hỏi:** Mỗi `id` trong `queries.json` tương ứng với đúng một dòng kết quả. Trường `answer` **chỉ ghi đáp án cuối cùng**, không kèm giải thích.
3. **Nộp bài:** Mỗi đội nộp **một tệp `.zip`** gồm mã nguồn, các tệp cấu hình/phụ thuộc cần thiết và **tệp `README.md`** hướng dẫn cài đặt, cấu hình, chạy chương trình bằng dòng lệnh.
4. **Tính khả tái tạo:** Giải pháp phải có khả năng **chạy lại với dữ liệu đầu vào mới**, không phụ thuộc vào đường dẫn cố định của dữ liệu mẫu. Bài không chạy được hoặc không tạo ra tệp kết quả hợp lệ sẽ **không được chấm**.

---

## 4. Giới hạn thời gian và điều kiện thực thi

| Hạng mục | Quy định |
|---|---|
| **Mô hình ngôn ngữ (LLM)** | Nếu dùng LLM để trả lời, phải hỗ trợ mô hình thống nhất khi chấm thi là **Qwen3.7-Flash** (`qwen/qwen3-7-flash`), truy cập qua **OpenRouter** (`https://openrouter.ai/qwen/qwen3-7-flash`). Phải cho phép **cấu hình thông tin truy cập API** (không hard-code khóa API vào mã nguồn). Quy định này không hạn chế việc dùng công cụ AI trong quá trình phát triển. |
| **Chi phí LLM** | Tổng chi phí LLM trên tập kiểm thử **không vượt quá 0.10 USD / câu hỏi** cho mỗi lần chấm, tính cả các lượt gọi lại (retry). Chi phí xác định theo mức sử dụng API do BTC ghi nhận. |
| **Thời gian thực thi** | Tối đa **40 phút cho 20 câu hỏi**, tính từ lúc bắt đầu chạy đến khi tạo xong `submission.csv`, bao gồm xử lý dữ liệu và gọi API. Máy chấm của BTC: **6 core vCPU, 12 GB RAM**. |
| **Dung lượng & bộ nhớ** | Tệp `.zip` nộp bài **≤ 100 MB**. Khi chạy trên tập kiểm thử, tổng không gian bộ nhớ sử dụng **≤ 1 GB**. |
| **Lưu ý** | Vi phạm một trong các giới hạn trên → **không được chấm điểm**. |

---

## 5. Chấm điểm và xếp hạng

BTC chạy các bài dự thi hợp lệ trên **tập kiểm thử ẩn**. Thứ tự xếp hạng theo các tiêu chí ưu tiên:

1. **Exact Match:** Số câu trả lời khớp chính xác với đáp án chuẩn — đội có nhiều câu đúng hơn xếp trước.
2. **Thời gian thực thi trung bình / câu hỏi:** Nếu hòa tiêu chí 1, đội có thời gian thấp hơn xếp trước.
3. **Số token LLM trung bình / câu hỏi:** Nếu hòa cả hai tiêu chí trên, đội dùng ít token hơn xếp trước.

---

## 6. Lịch trình

| Thời điểm | Hoạt động |
|---|---|
| **19h00 ngày 13/10** | BTC công bố bộ dữ liệu công khai lần 1; các đội bắt đầu phát triển giải pháp |
| **09h00 ngày 16/10** | BTC công bố bộ dữ liệu công khai lần 2 |
| **12h00 ngày 17/10** | Hạn cuối nộp tệp `.zip` chứa bài dự thi |
| **12h00–17h00 ngày 17/10** | BTC chấm các bài dự thi hợp lệ trên tập kiểm thử ẩn |
| **20h00 ngày 17/10** | Công bố bảng xếp hạng tạm thời |
| **08h00–17h00 ngày 18/10** | Vấn đáp xác minh giải pháp của các đội thi |
| **20h00 ngày 20/10** | Công bố bảng xếp hạng chính thức |

---

## 7. Vấn đáp và xác minh

- Phần vấn đáp nhằm xác minh mức độ **làm chủ giải pháp** của đội thi.
- Các đội phải giải thích được **nguyên lý hoạt động**, các **thành phần chính** và **chứng minh khả năng điều chỉnh mã nguồn** theo yêu cầu phù hợp với phạm vi đề thi.
- Đội không đáp ứng yêu cầu xác minh sẽ **bị loại khỏi bảng xếp hạng chính thức**.

---

## 8. Checklist cho agent khi triển khai

- [ ] Đọc `xlsx_files/` + `queries.json` từ **đường dẫn truyền qua tham số/ENV**, không hard-code.
- [ ] Xử lý merged cells, tiêu đề phân cấp, nhiều bảng/sheet trên cùng file.
- [ ] Sinh `submission.csv` với header `id,answer`, đủ số dòng, `answer` ngắn gọn (exact match).
- [ ] Hỗ trợ cấu hình LLM qua biến môi trường / file config: model `qwen/qwen3-7-flash` qua OpenRouter; không commit API key.
- [ ] Tối ưu chi phí ≤ $0.10/câu và thời gian ≤ 2 phút/câu trung bình; theo dõi số token.
- [ ] Đảm bảo chạy offline/online trong 6 vCPU / 12 GB RAM, peak memory ≤ 1 GB.
- [ ] Đóng gói `.zip` ≤ 100 MB kèm `README.md` hướng dẫn chạy bằng dòng lệnh.

---

*Nguồn: Đề thi Chủ đề 2 — Hỏi đáp trên bảng tính Excel (trang 1–3).*
