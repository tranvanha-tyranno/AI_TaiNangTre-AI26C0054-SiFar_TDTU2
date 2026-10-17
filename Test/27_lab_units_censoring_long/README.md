# 27_lab_units_censoring_long

1500 phép kiểm nghiệm, 27 cột tới AA: đổi mg/L–µg/L, kiểm duyệt '<', ô thiếu, tiêu đề lặp, trung vị, phân vị, điều kiện đủ cả ba chất.

`Điểm quan trắc`: 300 bản ghi / 301 dòng vật lý; `Ngưỡng nội bộ`: 12 bản ghi / 13 dòng vật lý; `Résultats dài`: 1,500 bản ghi / 1,502 dòng vật lý.

30 câu: **15 Việt, 5 Anh, 4 Trung, 3 Pháp, 3 Hàn**. ID là số tự nhiên; câu hỏi cố ý xáo trộn. CSV chuẩn dùng UTF-8 và sắp ID theo giá trị số tăng dần. Một câu thiếu trường dữ liệu có đáp án chuỗi rỗng. Câu đó không tính là lỗi fixture; không tự đổi đáp án thành N/A.

Dữ liệu hư cấu được sinh mới theo seed, có khóa và quan hệ nghiệp vụ nhất quán. Dòng cuối, phần giữa và các sheet phụ đều có câu yêu cầu truy xuất; không thể giải đầy đủ bằng preview đầu bảng. Các câu quy định phạm vi, đơn vị, xử lý thiếu dữ liệu, phá hòa và định dạng khi cần.

Chỉ truyền `xlsx_files/` và `queries.json` vào solver. `answer_audit.json` chứa SQL/đáp án để kiểm chứng bên ngoài mô hình; `dataset_manifest.json` mô tả vùng dữ liệu cho bộ kiểm tra. Không đưa các file này hoặc `expected_submission.csv` vào prompt/retrieval. `sample_submission.csv` chỉ là mẫu rỗng.

```powershell
python main.py --mode llm --xlsx_dir Test/27_lab_units_censoring_long/xlsx_files --queries Test/27_lab_units_censoring_long/queries.json --output outputs/27_lab_units_censoring_long.csv --log-dir outputs/27_lab_units_censoring_long-logs
python scripts/evaluate.py --prediction outputs/27_lab_units_censoring_long.csv --reference Test/27_lab_units_censoring_long/expected_submission.csv --report outputs/27_lab_units_censoring_long-strict.json
```

Điểm trên là strict exact match, chưa tái tạo chuẩn hóa BTC. Chưa chạy LLM hoặc đo chi phí/thời gian của mô hình. Quy định tài nguyên bài thi là RAM ≤ 4 GB, disk ≤ 1 GB và ZIP ≤ 100 MB theo AGENTS.md; kích thước file nhỏ không chứng minh cả pipeline đạt các giới hạn đó.
