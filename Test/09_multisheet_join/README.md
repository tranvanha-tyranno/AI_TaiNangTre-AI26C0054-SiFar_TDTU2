# 09_multisheet_join

Ba sheet, hai bảng cùng sheet, tên cột lặp và hàng TOTAL dễ gây cộng đôi. Ghép Orders với Products theo Product ID.

30 câu. Nhóm: deduplicate_total, join_calculation, join_count, join_filter, join_lookup, join_sum, multi_step, ranking, reconcile, side_by_side, table_sum. Dữ liệu tổng hợp cố định, không có thông tin cá nhân thật.

Chọn bộ này trong Dashboard → Chạy mới → LLM + Tools. Đáp án mẫu được tính bằng Python từ ô nguồn; `answer_checks.json` lưu phép tính và địa chỉ ô để kiểm chứng, không được đưa vào đầu vào của bộ giải. Không có đáp án hay công thức kiểm thử trong Excel.

```powershell
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir Test/09_multisheet_join/xlsx_files --queries Test/09_multisheet_join/queries.json --output outputs/09_multisheet_join.csv --log-dir outputs/09_multisheet_join-logs
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction outputs/09_multisheet_join.csv --reference Test/09_multisheet_join/expected_submission.csv
```

Offline chỉ kiểm tra I/O; có thể trả chưa trả lời. Chạy online có phí theo số câu. Câu hỏi quy định thứ tự, cách xử lý thiếu dữ liệu và số chữ số thập phân khi cần.
