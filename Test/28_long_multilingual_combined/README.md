# 28_long_multilingual_combined

Dataset gộp từ 5 workbook Excel compact, gồm **150 câu hỏi** và **5 file XLSX**. Tổng số dòng vật lý của các worksheet khoảng **14.821**, dưới 20.000 dòng. Mỗi workbook giữ domain và cấu trúc riêng; `queries.json` dùng `file_name` tương ứng để solver chọn đúng file.

Các suite nguồn: 23_civic_service_long, 24_procurement_temporal_long, 25_energy_intervals_long, 26_logistics_event_versions, 27_lab_units_censoring_long. ID là số tự nhiên, đã sắp tăng dần trong `expected_submission.csv`; câu không có đáp án dùng chuỗi rỗng. Chỉ truyền `xlsx_files/` và `queries.json` vào solver. `expected_submission.csv` và `answer_audit.json` chỉ dùng đánh giá ngoài ngữ cảnh solver.

```powershell
python main.py --mode llm --xlsx_dir Test/28_long_multilingual_combined/xlsx_files --queries Test/28_long_multilingual_combined/queries.json --output outputs/28_long_multilingual_combined.csv --log-dir outputs/28_long_multilingual_combined-logs
python scripts/evaluate.py --prediction outputs/28_long_multilingual_combined.csv --reference Test/28_long_multilingual_combined/expected_submission.csv --report outputs/28_long_multilingual_combined-strict.json
```
