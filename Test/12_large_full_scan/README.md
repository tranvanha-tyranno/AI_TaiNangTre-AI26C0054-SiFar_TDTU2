# 12_large_full_scan

2.500 dòng trên sheet lớn; câu hỏi ở giữa/cuối dữ liệu, tổng toàn bảng, lọc hiếm và cột ở ngoài 30 cột xem trước của dashboard.

35 câu. Nhóm: empty_filter, full_scan_average, full_scan_count, full_scan_sum, late_range, long_lookup, ranking, rare_filter, wide_lookup, wide_sum. Dữ liệu tổng hợp cố định, không có thông tin cá nhân thật.

Chọn bộ này trong Dashboard → Chạy mới → LLM + Tools. Đáp án mẫu được tính bằng Python từ ô nguồn; `answer_checks.json` lưu phép tính và địa chỉ ô để kiểm chứng, không được đưa vào đầu vào của bộ giải. Không có đáp án hay công thức kiểm thử trong Excel.

```powershell
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir Test/12_large_full_scan/xlsx_files --queries Test/12_large_full_scan/queries.json --output outputs/12_large_full_scan.csv --log-dir outputs/12_large_full_scan-logs
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction outputs/12_large_full_scan.csv --reference Test/12_large_full_scan/expected_submission.csv
```

Offline chỉ kiểm tra I/O; có thể trả chưa trả lời. Chạy online có phí theo số câu. Câu hỏi quy định thứ tự, cách xử lý thiếu dữ liệu và số chữ số thập phân khi cần.
