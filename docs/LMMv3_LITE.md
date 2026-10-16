# LMMv3 Lite — bản thử nghiệm đã lưu

**Lịch sử:** CLI hiện đã chuyển về [baseline LLMv2](LMMv3_V2_BASELINE.md). Nội dung dưới mô tả bản Lite trước đó.

Phiên bản: `lmmv3-lite-v1`, nhánh `Bao_LMMv3`. Đây là hướng phát triển lại từng bước, không phải lời khẳng định chính xác hơn các bản trước.

## Luồng hiện tại

1. Python đọc workbook giữ tọa độ và ô gộp; tạo catalog + preview gọn, tránh gửi snapshot chồng nhau.
2. LLM trả một kế hoạch công cụ trực tiếp, gồm steps và output.
3. Python thực thi trên toàn phạm vi khai báo, kiểm tra công cụ/tham chiếu/kiểu dữ liệu/phép tính và giữ nguồn ô.
4. Định dạng theo kế hoạch, xuất CSV và log.

Mặc định tối đa **2 lượt API/câu**, gồm cả transport retry: thông thường một lượt; lượt thứ hai dùng để sửa một lỗi cụ thể HOẶC lập kế hoạch sau một yêu cầu inspect. Không có lượt đặc tả, coverage gate, auto-read evidence hay review riêng. Không yêu cầu answer_spec. Kế hoạch lỗi lặp không được tiếp tục vô hạn.

## Cấu hình và chạy

- `--mode llm-v3` hiện gọi `src/lmmv3/lite.py`. Dashboard chọn **LMMv3 Lite · 1–2 lượt gọi**.
- `lite_max_api_calls: 2`, có thể chủ động đặt 1 hoặc 3 (trần Lite là 3).
- `lite_context_chars: 16000`: giới hạn phần JSON user context, gồm cả feedback; system/tool schema nằm ngoài mức này và được ghi kích thước riêng. Đây là giới hạn ký tự, không phải token chính xác.
- Giữ nguyên model/key/base URL qua ENV và ngân sách phí/runtime. LLM/LLMv2 không đổi.

```powershell
.\.venv\Scripts\python.exe dashboard.py --port 8501
```

```powershell
.\.venv\Scripts\python.exe main.py --mode llm-v3 --xlsx_dir ./Public_data_2/xlsx_files --queries ./Public_data_2/queries.json --output ./outputs/lite/submission.csv --log-dir ./outputs/lite/logs
```

Các lệnh chạy model sẽ dùng API và tính phí; chưa chạy trong lần triển khai này.

## Giữ lại những gì

Tái sử dụng parser và executor đã có: read/cell/filter/derive/sort/take/select/aggregate/group/calculate/record/collect/concat/lag/unpivot, số Decimal, nguồn ô, giới hạn tài nguyên và usage ledger. Không chạy code do LLM sinh. Công cụ chỉ tính theo kế hoạch, không tự sửa tọa độ hay tìm đáp án theo ID/file.

Tool inspect vẫn có thể được LLM gọi nếu thiếu dữ liệu. Kết quả đọc có giới hạn, thay thế feedback thay vì cộng dồn toàn bộ lịch sử. Header có thể được gửi riêng vì nằm ngoài vùng dữ liệu; không gửi hai bản giá trị gốc/chuẩn hóa cho từng ô như trước. Mỗi lượt ghi context/system/schema chars để đánh giá đầu vào.

## Những gì tạm bỏ khỏi luồng mới

Không có AI đặc tả riêng, kiểm tra coverage từng requirement, reviewer mặc định, các cơ chế fallback nhiều tầng hay công cụ weighted_mean/percent_change chuyên biệt. Các phép toán phức tạp chỉ được biểu diễn qua công cụ cơ bản khi phù hợp. Mục tiêu hiện tại là baseline nhỏ, quan sát được, dễ sửa.

Mã tám phase trước vẫn ở `src/lmmv3/pipeline.py` và lịch sử commit `eaf7ddd`; xem `docs/LMMv3.md` để đọc lịch sử. CLI không tự quay lại bản đó. Các run cũ giữ nguyên pipeline_version và kết quả để so sánh.

## Đánh giá và bước nâng cấp

`verification_level=tool_execution_only` nghĩa là Python đã thực thi hợp lệ; **không xác nhận đã hiểu đúng câu hỏi hoặc đáp án đúng**. Nếu không tạo được kế hoạch trong trần gọi, xuất rỗng và ghi lý do; lỗi API thực sự vẫn báo riêng. Bộ nhớ/disk và độ chính xác trên dataset chưa được chứng nhận.

Kiểm tra mới dùng workbook tổng hợp và client giả lập: một lượt thành công, một lượt sửa, inspect rồi tính, kế hoạch lặp, chia 0, output ghép, mã 001, giới hạn context và tương thích CLI. Không gọi API hoặc chạy benchmark dataset trong lần xây lại.

Kế hoạch phát triển tiếp: đo baseline trên bộ chưa dùng chỉnh solver, phân loại lỗi; mỗi lần chỉ thêm một khả năng và đo cả điểm, thời gian/token và suy giảm trên dạng khác. Trước mắt chưa thêm lại review/đặc tả tự động. Không đặt mục tiêu khớp riêng Public_data_2.
