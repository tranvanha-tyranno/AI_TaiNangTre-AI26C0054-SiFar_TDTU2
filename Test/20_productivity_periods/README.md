# 20_productivity_periods

20 năm xen 80 quý và bảng level riêng, chênh lệch liên năm, xếp hạng, phạm vi annual/quarter.

Đúng 30 câu; seed `261016`. Toàn bộ bản ghi, kỳ báo cáo và số liệu được sinh mới. Dữ liệu chỉ là tình huống tổng hợp để kiểm thử, không phải thống kê thực tế.

Cấu trúc tham khảo: `Public_data_2/xlsx_files/p2_t03.xlsx`, `Public_data_2/xlsx_files/p2_t08.xlsx`.

Nhóm câu hỏi: annual_comparison_count, annual_gap_rank, annual_max, annual_mean, annual_threshold, largest_drop, level_lookup, period_count, quarter_max, recent_mean, year_on_year.

Đầu vào mô hình chỉ gồm `xlsx_files/` và `queries.json`. `expected_submission.csv`, `answer_checks.json` và `provenance.json` dành riêng cho đánh giá; không đưa chúng vào prompt/retrieval. `sample_submission.csv` có đáp án rỗng để làm mẫu I/O. Đáp án được tính từ địa chỉ ô, sau đó kiểm lại trên chính XLSX đã export, độc lập với bộ giải.

```powershell
python main.py --mode llm --xlsx_dir Test/20_productivity_periods/xlsx_files --queries Test/20_productivity_periods/queries.json --output outputs/20_productivity_periods.csv --log-dir outputs/20_productivity_periods-logs
python scripts/evaluate.py --prediction outputs/20_productivity_periods.csv --reference Test/20_productivity_periods/expected_submission.csv --report outputs/20_productivity_periods-evaluation.json
```

Chưa đo độ chính xác LLM trên bộ này. Dashboard tự phát hiện khi tải lại danh sách dataset.
