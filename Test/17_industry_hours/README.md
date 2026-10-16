# 17_industry_hours

Hai sheet ngành/nghề mới, tuổi, giờ làm, đơn vị nghìn, dòng TOTAL và phép tính chéo sheet.

Đúng 30 câu; seed `261016`. Toàn bộ bản ghi, kỳ báo cáo và số liệu được sinh mới. Dữ liệu chỉ là tình huống tổng hợp để kiểm thử, không phải thống kê thực tế.

Cấu trúc tham khảo: `Public_data_1/xlsx_files/p4_t05.xlsx`, `Public_data_1/xlsx_files/p4_t06.xlsx`, `Public_data_1/xlsx_files/p4_t07.xlsx`, `Public_data_1/xlsx_files/p4_t08.xlsx`, `Public_data_1/xlsx_files/p4_t09.xlsx`, `Public_data_1/xlsx_files/p4_t10.xlsx`.

Nhóm câu hỏi: age_difference, comparison, cross_sheet_ratio, exclude_total_rank, hours_share, no_double_count, occupation_sum, pair_output, sector_order, two_industries.

Đầu vào mô hình chỉ gồm `xlsx_files/` và `queries.json`. `expected_submission.csv`, `answer_checks.json` và `provenance.json` dành riêng cho đánh giá; không đưa chúng vào prompt/retrieval. `sample_submission.csv` có đáp án rỗng để làm mẫu I/O. Đáp án được tính từ địa chỉ ô, sau đó kiểm lại trên chính XLSX đã export, độc lập với bộ giải.

```powershell
python main.py --mode llm --xlsx_dir Test/17_industry_hours/xlsx_files --queries Test/17_industry_hours/queries.json --output outputs/17_industry_hours.csv --log-dir outputs/17_industry_hours-logs
python scripts/evaluate.py --prediction outputs/17_industry_hours.csv --reference Test/17_industry_hours/expected_submission.csv --report outputs/17_industry_hours-evaluation.json
```

Chưa đo độ chính xác LLM trên bộ này. Dashboard tự phát hiện khi tải lại danh sách dataset.
