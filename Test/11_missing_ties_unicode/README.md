# 11_missing_ties_unicode

Ô trống khác số 0, số âm, trùng tên, đồng điểm, Unicode tiếng Việt, dấu phẩy/nháy và mã có số 0 đầu.

25 câu. Nhóm: distinct, duplicate_name, empty_filter, max, min, missing_average, missing_count, missing_sum, negative_count, nonblank_count, sum, text_lookup, ties, zero_count. Dữ liệu tổng hợp cố định, không có thông tin cá nhân thật.

Chọn bộ này trong Dashboard → Chạy mới → LLM + Tools. Đáp án mẫu được tính bằng Python từ ô nguồn; `answer_checks.json` lưu phép tính và địa chỉ ô để kiểm chứng, không được đưa vào đầu vào của bộ giải. Không có đáp án hay công thức kiểm thử trong Excel.

```powershell
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir Test/11_missing_ties_unicode/xlsx_files --queries Test/11_missing_ties_unicode/queries.json --output outputs/11_missing_ties_unicode.csv --log-dir outputs/11_missing_ties_unicode-logs
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction outputs/11_missing_ties_unicode.csv --reference Test/11_missing_ties_unicode/expected_submission.csv
```

Offline chỉ kiểm tra I/O; có thể trả chưa trả lời. Chạy online có phí theo số câu. Câu hỏi quy định thứ tự, cách xử lý thiếu dữ liệu và số chữ số thập phân khi cần.
