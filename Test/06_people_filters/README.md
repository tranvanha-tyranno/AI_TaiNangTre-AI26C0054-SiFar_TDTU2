# 06_people_filters

40 người, tiêu đề tên/ngày/điểm có ô gộp. Lọc nhiều điều kiện, tuổi tròn tại ngày nhập học, xếp hạng và phá hòa.

30 câu. Nhóm: age, average, conditional_sum, count, empty_filter, lookup, multi_filter, percentage, ranking, top_k. Dữ liệu tổng hợp cố định, không có thông tin cá nhân thật.

Chọn bộ này trong Dashboard → Chạy mới → LLM + Tools. Đáp án mẫu được tính bằng Python từ ô nguồn; `answer_checks.json` lưu phép tính và địa chỉ ô để kiểm chứng, không được đưa vào đầu vào của bộ giải. Không có đáp án hay công thức kiểm thử trong Excel.

```powershell
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir Test/06_people_filters/xlsx_files --queries Test/06_people_filters/queries.json --output outputs/06_people_filters.csv --log-dir outputs/06_people_filters-logs
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction outputs/06_people_filters.csv --reference Test/06_people_filters/expected_submission.csv
```

Offline chỉ kiểm tra I/O; có thể trả chưa trả lời. Chạy online có phí theo số câu. Câu hỏi quy định thứ tự, cách xử lý thiếu dữ liệu và số chữ số thập phân khi cần.
