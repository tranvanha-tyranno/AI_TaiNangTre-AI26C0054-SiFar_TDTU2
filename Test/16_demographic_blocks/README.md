# 16_demographic_blocks

Hai khối nam/nữ có nhãn lặp, 6 nhóm học vấn rời nhau; trung bình đơn khác tỷ lệ gộp.

Đúng 30 câu; seed `261016`. Toàn bộ bản ghi, kỳ báo cáo và số liệu được sinh mới. Dữ liệu chỉ là tình huống tổng hợp để kiểm thử, không phải thống kê thực tế.

Cấu trúc tham khảo: `Public_data_1/xlsx_files/p4_t04.xlsx`, `Public_data_2/xlsx_files/p2_t04.xlsx`, `Public_data_2/xlsx_files/p2_t05.xlsx`.

Nhóm câu hỏi: comparison, nonoverlap_total, participation_rate, population_gap, repeated_label_scope, unweighted_average, weighted_rate.

Đầu vào mô hình chỉ gồm `xlsx_files/` và `queries.json`. `expected_submission.csv`, `answer_checks.json` và `provenance.json` dành riêng cho đánh giá; không đưa chúng vào prompt/retrieval. `sample_submission.csv` có đáp án rỗng để làm mẫu I/O. Đáp án được tính từ địa chỉ ô, sau đó kiểm lại trên chính XLSX đã export, độc lập với bộ giải.

```powershell
python main.py --mode llm --xlsx_dir Test/16_demographic_blocks/xlsx_files --queries Test/16_demographic_blocks/queries.json --output outputs/16_demographic_blocks.csv --log-dir outputs/16_demographic_blocks-logs
python scripts/evaluate.py --prediction outputs/16_demographic_blocks.csv --reference Test/16_demographic_blocks/expected_submission.csv --report outputs/16_demographic_blocks-evaluation.json
```

Chưa đo độ chính xác LLM trên bộ này. Dashboard tự phát hiện khi tải lại danh sách dataset.
