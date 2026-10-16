# 21_finance_multisheet

5 sheet tài chính mới: số chuỗi $/dấu phẩy/ngoặc âm, doanh thu bộ phận, fair value, cuối kỳ khác bình quân.

Đúng 30 câu; seed `261016`. Toàn bộ bản ghi, kỳ báo cáo và số liệu được sinh mới. Dữ liệu chỉ là tình huống tổng hợp để kiểm thử, không phải thống kê thực tế.

Cấu trúc tham khảo: `Public_data_2/xlsx_files/p2_t09.xlsx`, `Public_data_2/xlsx_files/p2_t10.xlsx`.

Nhóm câu hỏi: accounting_negative, avoid_total_double_count, boolean, cross_sheet_sum, cross_table_ratio, exact_text, fair_value_difference, fair_value_share, operating_margin, parentheses, revenue_growth, sheet_rank, year_end_vs_average.

Đầu vào mô hình chỉ gồm `xlsx_files/` và `queries.json`. `expected_submission.csv`, `answer_checks.json` và `provenance.json` dành riêng cho đánh giá; không đưa chúng vào prompt/retrieval. `sample_submission.csv` có đáp án rỗng để làm mẫu I/O. Đáp án được tính từ địa chỉ ô, sau đó kiểm lại trên chính XLSX đã export, độc lập với bộ giải.

```powershell
python main.py --mode llm --xlsx_dir Test/21_finance_multisheet/xlsx_files --queries Test/21_finance_multisheet/queries.json --output outputs/21_finance_multisheet.csv --log-dir outputs/21_finance_multisheet-logs
python scripts/evaluate.py --prediction outputs/21_finance_multisheet.csv --reference Test/21_finance_multisheet/expected_submission.csv --report outputs/21_finance_multisheet-evaluation.json
```

Chưa đo độ chính xác LLM trên bộ này. Dashboard tự phát hiện khi tải lại danh sách dataset.
