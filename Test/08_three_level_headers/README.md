# 08_three_level_headers

Tiêu đề 3 cấp Year / Quarter / Metric, hai chỉ tiêu lặp tên dưới từng quý và ghi chú cuối bảng không phải dữ liệu.

25 câu. Nhóm: comparison, difference, header_lookup, percentage_format, ranking, ratio, sum, units. Dữ liệu tổng hợp cố định, không có thông tin cá nhân thật.

Chọn bộ này trong Dashboard → Chạy mới → LLM + Tools. Đáp án mẫu được tính bằng Python từ ô nguồn; `answer_checks.json` lưu phép tính và địa chỉ ô để kiểm chứng, không được đưa vào đầu vào của bộ giải. Không có đáp án hay công thức kiểm thử trong Excel.

```powershell
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir Test/08_three_level_headers/xlsx_files --queries Test/08_three_level_headers/queries.json --output outputs/08_three_level_headers.csv --log-dir outputs/08_three_level_headers-logs
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction outputs/08_three_level_headers.csv --reference Test/08_three_level_headers/expected_submission.csv
```

Offline chỉ kiểm tra I/O; có thể trả chưa trả lời. Chạy online có phí theo số câu. Câu hỏi quy định thứ tự, cách xử lý thiếu dữ liệu và số chữ số thập phân khi cần.
