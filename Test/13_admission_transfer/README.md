# 13_admission_transfer

64 hồ sơ mới: tuổi thực theo ngày tại nhập học, tuổi tròn, ngày nhuận, lọc và top-k.

Đúng 30 câu; seed `261016`. Toàn bộ bản ghi, kỳ báo cáo và số liệu được sinh mới. Dữ liệu chỉ là tình huống tổng hợp để kiểm thử, không phải thống kê thực tế.

Cấu trúc tham khảo: `Public_data_1/xlsx_files/p4_t01.xlsx`.

Nhóm câu hỏi: age_rank, birthday_boundary, completed_age, conditional_average, conditional_rank, date_filter, distinct, empty_result, exact_age_days, multi_condition, rank_score, strict_boundary, top_k_age_score, top_three.

Đầu vào mô hình chỉ gồm `xlsx_files/` và `queries.json`. `expected_submission.csv`, `answer_checks.json` và `provenance.json` dành riêng cho đánh giá; không đưa chúng vào prompt/retrieval. `sample_submission.csv` có đáp án rỗng để làm mẫu I/O. Đáp án được tính từ địa chỉ ô, sau đó kiểm lại trên chính XLSX đã export, độc lập với bộ giải.

```powershell
python main.py --mode llm --xlsx_dir Test/13_admission_transfer/xlsx_files --queries Test/13_admission_transfer/queries.json --output outputs/13_admission_transfer.csv --log-dir outputs/13_admission_transfer-logs
python scripts/evaluate.py --prediction outputs/13_admission_transfer.csv --reference Test/13_admission_transfer/expected_submission.csv --report outputs/13_admission_transfer-evaluation.json
```

Chưa đo độ chính xác LLM trên bộ này. Dashboard tự phát hiện khi tải lại danh sách dataset.
