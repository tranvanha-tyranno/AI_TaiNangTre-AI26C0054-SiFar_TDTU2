# 14_trade_periods

Xuất nhập khẩu của 6 mặt hàng mới; fiscal/calendar/FYTD trùng năm, số âm và tăng trưởng.

Đúng 30 câu; seed `261016`. Toàn bộ bản ghi, kỳ báo cáo và số liệu được sinh mới. Dữ liệu chỉ là tình huống tổng hợp để kiểm thử, không phải thống kê thực tế.

Cấu trúc tham khảo: `Public_data_1/xlsx_files/p4_t02.xlsx`.

Nhóm câu hỏi: absolute_difference, fiscal_vs_ytd, growth, noncontiguous_sum, period_disambiguation, signed_balance, trade_balance.

Đầu vào mô hình chỉ gồm `xlsx_files/` và `queries.json`. `expected_submission.csv`, `answer_checks.json` và `provenance.json` dành riêng cho đánh giá; không đưa chúng vào prompt/retrieval. `sample_submission.csv` có đáp án rỗng để làm mẫu I/O. Đáp án được tính từ địa chỉ ô, sau đó kiểm lại trên chính XLSX đã export, độc lập với bộ giải.

```powershell
python main.py --mode llm --xlsx_dir Test/14_trade_periods/xlsx_files --queries Test/14_trade_periods/queries.json --output outputs/14_trade_periods.csv --log-dir outputs/14_trade_periods-logs
python scripts/evaluate.py --prediction outputs/14_trade_periods.csv --reference Test/14_trade_periods/expected_submission.csv --report outputs/14_trade_periods-evaluation.json
```

Chưa đo độ chính xác LLM trên bộ này. Dashboard tự phát hiện khi tải lại danh sách dataset.
