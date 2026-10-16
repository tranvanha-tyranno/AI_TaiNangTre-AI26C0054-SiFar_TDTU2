# 19_safety_naics

1.100 ngành mới, NAICS 3/6 chữ số, ô thiếu và bị ẩn, tỷ lệ tổng đã báo cáo, bảng quartile.

Đúng 30 câu; seed `261016`. Toàn bộ bản ghi, kỳ báo cáo và số liệu được sinh mới. Dữ liệu chỉ là tình huống tổng hợp để kiểm thử, không phải thống kê thực tế.

Cấu trúc tham khảo: `Public_data_2/xlsx_files/p2_t06.xlsx`, `Public_data_2/xlsx_files/p2_t07.xlsx`.

Nhóm câu hỏi: exact_boundary, full_scan_rank, ignore_suppressed, missing_count, missing_marker, quartile_lookup, quartile_rank, quartile_threshold, reported_not_components, six_digit_scope.

Đầu vào mô hình chỉ gồm `xlsx_files/` và `queries.json`. `expected_submission.csv`, `answer_checks.json` và `provenance.json` dành riêng cho đánh giá; không đưa chúng vào prompt/retrieval. `sample_submission.csv` có đáp án rỗng để làm mẫu I/O. Đáp án được tính từ địa chỉ ô, sau đó kiểm lại trên chính XLSX đã export, độc lập với bộ giải.

```powershell
python main.py --mode llm --xlsx_dir Test/19_safety_naics/xlsx_files --queries Test/19_safety_naics/queries.json --output outputs/19_safety_naics.csv --log-dir outputs/19_safety_naics-logs
python scripts/evaluate.py --prediction outputs/19_safety_naics.csv --reference Test/19_safety_naics/expected_submission.csv --report outputs/19_safety_naics-evaluation.json
```

Chưa đo độ chính xác LLM trên bộ này. Dashboard tự phát hiện khi tải lại danh sách dataset.
