# 22_multilingual_social

Câu hỏi Việt/Pháp/Hàn/Trung; chăm sóc, thu nhập, tòa án, lao động và sức khỏe với số liệu mới.

Đúng 30 câu; seed `261016`. Toàn bộ bản ghi, kỳ báo cáo và số liệu được sinh mới. Dữ liệu chỉ là tình huống tổng hợp để kiểm thử, không phải thống kê thực tế.

Cấu trúc tham khảo: `Public_data_2/xlsx_files/p2_t11.xlsx`, `Public_data_2/xlsx_files/p2_t12.xlsx`, `Public_data_2/xlsx_files/p2_t13.xlsx`, `Public_data_2/xlsx_files/p2_t14.xlsx`, `Public_data_2/xlsx_files/p2_t15.xlsx`.

Nhóm câu hỏi: fr_mean, fr_missing, fr_range, fr_rank, ko_max, ko_percent_change, ko_ratio, ko_total, vi_care, vi_exclude_any, vi_income_gap, vi_income_rank, vi_income_ratio, vi_income_total, vi_missing_vs_zero, zh_group_gap, zh_marital_gap.

Đầu vào mô hình chỉ gồm `xlsx_files/` và `queries.json`. `expected_submission.csv`, `answer_checks.json` và `provenance.json` dành riêng cho đánh giá; không đưa chúng vào prompt/retrieval. `sample_submission.csv` có đáp án rỗng để làm mẫu I/O. Đáp án được tính từ địa chỉ ô, sau đó kiểm lại trên chính XLSX đã export, độc lập với bộ giải.

```powershell
python main.py --mode llm --xlsx_dir Test/22_multilingual_social/xlsx_files --queries Test/22_multilingual_social/queries.json --output outputs/22_multilingual_social.csv --log-dir outputs/22_multilingual_social-logs
python scripts/evaluate.py --prediction outputs/22_multilingual_social.csv --reference Test/22_multilingual_social/expected_submission.csv --report outputs/22_multilingual_social-evaluation.json
```

Chưa đo độ chính xác LLM trên bộ này. Dashboard tự phát hiện khi tải lại danh sách dataset.
