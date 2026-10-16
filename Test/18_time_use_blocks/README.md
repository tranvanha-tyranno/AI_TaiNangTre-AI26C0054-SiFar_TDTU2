# 18_time_use_blocks

3 nhóm tuổi trẻ, mẹ/cha và tình trạng việc làm; giờ khác tỷ lệ tham gia, so sánh nhiều khối.

Đúng 30 câu; seed `261016`. Toàn bộ bản ghi, kỳ báo cáo và số liệu được sinh mới. Dữ liệu chỉ là tình huống tổng hợp để kiểm thử, không phải thống kê thực tế.

Cấu trúc tham khảo: `Public_data_2/xlsx_files/p2_t01.xlsx`.

Nhóm câu hỏi: activity_sum, cross_block_rank, group_hours_gap, mixed_output, percent_vs_hours, unit_conversion.

Đầu vào mô hình chỉ gồm `xlsx_files/` và `queries.json`. `expected_submission.csv`, `answer_checks.json` và `provenance.json` dành riêng cho đánh giá; không đưa chúng vào prompt/retrieval. `sample_submission.csv` có đáp án rỗng để làm mẫu I/O. Đáp án được tính từ địa chỉ ô, sau đó kiểm lại trên chính XLSX đã export, độc lập với bộ giải.

```powershell
python main.py --mode llm --xlsx_dir Test/18_time_use_blocks/xlsx_files --queries Test/18_time_use_blocks/queries.json --output outputs/18_time_use_blocks.csv --log-dir outputs/18_time_use_blocks-logs
python scripts/evaluate.py --prediction outputs/18_time_use_blocks.csv --reference Test/18_time_use_blocks/expected_submission.csv --report outputs/18_time_use_blocks-evaluation.json
```

Chưa đo độ chính xác LLM trên bộ này. Dashboard tự phát hiện khi tải lại danh sách dataset.
