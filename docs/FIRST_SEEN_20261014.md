# Kiểm tra dữ liệu gặp lần đầu — 14/10/2026

## Kết luận

Pipeline LLM có đọc workbook mới, nhưng lượt kiểm tra đầu chỉ khớp **6/10 câu**. Điểm số cao khi chạy lại Public/Test đã dùng để sửa solver chưa chứng minh được chất lượng trên tập mới. Đây là bộ tổng hợp nhỏ, không đại diện cho tập ẩn của BTC.

Offline là bộ quy tắc chọn theo tên file `p4_t01`–`p4_t10`; không phải bộ giải tổng quát. Chế độ `llm`/`hybrid` không gọi resolver này và không đọc CSV đáp án chuẩn.

## Quy trình và bằng chứng

- Ghi SHA-256 của `main.py` và toàn bộ Python trong `src/` trước khi tạo dữ liệu. Không sửa solver sau khi tạo bộ mới; kiểm tra hash sau chạy vẫn khớp.
- Tạo ngẫu nhiên đúng một bộ: 2 workbook `dispatch_dcbbcfee.xlsx`, `energy_dcbbcfee.xlsx`, 10 câu tiếng Việt/Anh. Không chọn lại dữ liệu để lấy kết quả tốt hơn.
- Có sheet giới thiệu, bảng lệch sang C6/B4, bảng phụ cùng sheet, tiêu đề gộp hai tầng, nối sheet, tổng và tỷ lệ. Nội dung và tên file không lấy từ Public/Test.
- Đáp án tính độc lập bằng Python từ các ô trong XLSX đã xuất; CSV oracle nằm ngoài thư mục dữ liệu đưa cho solver.
- Run **20261014-210900-deaf27** chạy bằng LLM + Tools. Không có tham chiếu trong metadata khi gọi pipeline; chỉ gắn tham chiếu để dashboard chấm sau khi subprocess hoàn tất.
- Kiểm tra hash Excel/câu hỏi sau chạy: không đổi. Các lần sửa kế hoạch trong chính một câu vẫn tính vào lượt đầu; không chạy lại bộ này.

Dữ liệu và bằng chứng cục bộ: `outputs/first-seen-20261014/` gồm `dataset/`, `protocol.json`, `input_sha256.json`, `oracle.csv`, `oracle.py`, `first_pass_report.json`. Log gốc: `outputs/runs/20261014-210900-deaf27/`. Thư mục outputs được Git ignore.

## Kết quả lần đầu

| ID | Yêu cầu | Kết quả | Đáp án |
|---|---|---|---|
| u01 | Đếm đơn đã giao | 6 | 6 |
| u02 | Tổng phí đơn đã giao | 1987 | 1987 |
| u03 | Tổng kiện tại Trạm Sen | 114 | 114 |
| u04 | ID đơn đã giao có phí cao nhất | D-2 | D-2 |
| u05 | Nối Hub map để tổng kiện khu East | Lỗi PlanError | 246 |
| u06 | Tổng phí / tổng kiện đơn đã giao | Lỗi API 429 | 8.60 |
| u07 | Tên phòng có kWh February cao nhất | 461 — trả nhầm số | Phòng Biển |
| u08 | Tổng kWh January của bốn phòng | 1078 | 1078 |
| u09 | % thay đổi tổng kWh | Lỗi JSON kế hoạch, API 429 và dừng theo budget | 44.71 |
| u10 | Phí February của Phòng Mây | 5938 | 5938 |

Có **6 đúng, 1 đáp án sai, 3 câu lỗi**. u05 dùng table ID có trong catalog nhưng không thuộc các vùng được chọn, và lặp lại lỗi qua các lượt repair. u07 vượt qua kiểm tra số lượng đáp án dù xuất cột số thay vì nhãn. u09 còn lỗi JSON nên không quy toàn bộ thất bại cho API. Đây là các điểm cần xử lý tiếp trong retrieval/repair và kiểm tra ngữ nghĩa đáp án.

Tổng 17 lượt API; chi phí xác nhận $0.002973753, **4 lượt chưa có usage**, nên chưa biết tổng phí đầy đủ. Thời gian pipeline khoảng 52 giây; peak memory đo được khoảng 76.6 MB. Model thực nghiệm `qwen/qwen3.7-flash`.

## Nạp dữ liệu mới lên dashboard

Dashboard trước đây chỉ liệt kê Public và `Test/*`. Nay nhận thêm thư mục bất kỳ có `xlsx_files/` và `queries.json`:

```powershell
.\.venv\Scripts\python.exe dashboard.py --port 8506 --dataset-dir .\outputs\first-seen-20261014\dataset
```

Chọn **Dữ liệu riêng / dataset**, sau đó chọn run **14/10 21:09:00** để xem lần đầu. Không cần file đáp án mẫu để xử lý dữ liệu mới. Có thể lặp `--dataset-dir` để nạp nhiều bộ. Khi khởi động lại, giữ các tham số này để xem workbook và lịch sử của bộ ngoài Test.

Windows còn có thể phục vụ dashboard cũ khi nhiều server cùng chiếm cổng qua `SO_REUSEADDR`. Bản mới dùng `SO_EXCLUSIVEADDRUSE` để từ chối server thứ hai trên cùng cổng; khi cập nhật cần dừng server cũ và khởi động lại.
