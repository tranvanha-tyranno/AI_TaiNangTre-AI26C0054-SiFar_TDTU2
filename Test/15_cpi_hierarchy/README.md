# 15_cpi_hierarchy

CPI mới với mức thụt cấp 0–3, con trực tiếp khác cháu, điều chỉnh mùa vụ khác chưa điều chỉnh.

Đúng 30 câu; seed `261016`. Toàn bộ bản ghi, kỳ báo cáo và số liệu được sinh mới. Dữ liệu chỉ là tình huống tổng hợp để kiểm thử, không phải thống kê thực tế.

Cấu trúc tham khảo: `Public_data_1/xlsx_files/p4_t03.xlsx`, `Public_data_2/xlsx_files/p2_t02.xlsx`.

Nhóm câu hỏi: adjusted_disambiguation, comparison, direct_children, filter, hierarchy_average, hierarchy_scope, index_difference, percent_points, ranking, weight_gap.

Đầu vào mô hình chỉ gồm `xlsx_files/` và `queries.json`. `expected_submission.csv`, `answer_checks.json` và `provenance.json` dành riêng cho đánh giá; không đưa chúng vào prompt/retrieval. `sample_submission.csv` có đáp án rỗng để làm mẫu I/O. Đáp án được tính từ địa chỉ ô, sau đó kiểm lại trên chính XLSX đã export, độc lập với bộ giải.

```powershell
python main.py --mode llm --xlsx_dir Test/15_cpi_hierarchy/xlsx_files --queries Test/15_cpi_hierarchy/queries.json --output outputs/15_cpi_hierarchy.csv --log-dir outputs/15_cpi_hierarchy-logs
python scripts/evaluate.py --prediction outputs/15_cpi_hierarchy.csv --reference Test/15_cpi_hierarchy/expected_submission.csv --report outputs/15_cpi_hierarchy-evaluation.json
```

Chưa đo độ chính xác LLM trên bộ này. Dashboard tự phát hiện khi tải lại danh sách dataset.
