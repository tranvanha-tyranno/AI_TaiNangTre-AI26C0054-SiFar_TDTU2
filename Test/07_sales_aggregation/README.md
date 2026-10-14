# 07_sales_aggregation

96 giao dịch: tổng có điều kiện, nhóm, nhiều phép tính, giá trị âm của trả hàng và tỷ lệ có trọng số.

30 câu. Nhóm: comparison, filter_sum, group_sum, negative, percentage, period_sum, profit, range_filter, ranking, top_k, total, weighted_average. Dữ liệu tổng hợp cố định, không có thông tin cá nhân thật.

Chọn bộ này trong Dashboard → Chạy mới → LLM + Tools. Đáp án mẫu được tính bằng Python từ ô nguồn; `answer_checks.json` lưu phép tính và địa chỉ ô để kiểm chứng, không được đưa vào đầu vào của bộ giải. Không có đáp án hay công thức kiểm thử trong Excel.

```powershell
.\.venv\Scripts\python.exe main.py --mode llm --xlsx_dir Test/07_sales_aggregation/xlsx_files --queries Test/07_sales_aggregation/queries.json --output outputs/07_sales_aggregation.csv --log-dir outputs/07_sales_aggregation-logs
.\.venv\Scripts\python.exe scripts/evaluate.py --prediction outputs/07_sales_aggregation.csv --reference Test/07_sales_aggregation/expected_submission.csv
```

Offline chỉ kiểm tra I/O; có thể trả chưa trả lời. Chạy online có phí theo số câu. Câu hỏi quy định thứ tự, cách xử lý thiếu dữ liệu và số chữ số thập phân khi cần.
