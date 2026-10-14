# 10_dates_boundaries

Ngày tháng kiểu Excel, năm nhuận, lọc khoảng đóng/mở, sinh nhật và độ dài dự án. Mốc thời gian cố định.

25 câu. Nhóm: age, comparison, date_diff, date_filter, date_lookup, ranking. Dữ liệu tổng hợp cố định, không có thông tin cá nhân thật.

Chọn bộ này trong Dashboard → Chạy mới → LLM + Tools. Đáp án mẫu được tính bằng Python từ ô nguồn; `answer_checks.json` lưu phép tính và địa chỉ ô để kiểm chứng, không được đưa vào đầu vào của bộ giải. Không có đáp án hay công thức kiểm thử trong Excel.

```powershell
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir Test/10_dates_boundaries/xlsx_files --queries Test/10_dates_boundaries/queries.json --output outputs/10_dates_boundaries.csv --log-dir outputs/10_dates_boundaries-logs
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction outputs/10_dates_boundaries.csv --reference Test/10_dates_boundaries/expected_submission.csv
```

Offline chỉ kiểm tra I/O; có thể trả chưa trả lời. Chạy online có phí theo số câu. Câu hỏi quy định thứ tự, cách xử lý thiếu dữ liệu và số chữ số thập phân khi cần.
