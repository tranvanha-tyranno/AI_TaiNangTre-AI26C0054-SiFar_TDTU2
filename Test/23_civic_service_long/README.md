# 23_civic_service_long

Khảo sát dịch vụ đô thị: header 3 cấp, Total đổi vị trí, mean across all và mean loại Total, tỷ lệ có trọng số, lưu trữ gây nhiễu.

`Khảo sát 2028`: 12,000 bản ghi / 12,003 dòng vật lý; `Cỡ mẫu`: 12,000 bản ghi / 12,001 dòng vật lý; `Lưu trữ 2027`: 2,400 bản ghi / 2,401 dòng vật lý.

30 câu: **15 Việt, 5 Anh, 4 Trung, 3 Pháp, 3 Hàn**. ID là số tự nhiên; câu hỏi cố ý xáo trộn. CSV chuẩn dùng UTF-8 và sắp ID theo giá trị số tăng dần. Một câu thiếu trường dữ liệu có đáp án chuỗi rỗng. Câu đó không tính là lỗi fixture; không tự đổi đáp án thành N/A.

Dữ liệu hư cấu được sinh mới theo seed, có khóa và quan hệ nghiệp vụ nhất quán. Dòng cuối, phần giữa và các sheet phụ đều có câu yêu cầu truy xuất; không thể giải đầy đủ bằng preview đầu bảng. Các câu quy định phạm vi, đơn vị, xử lý thiếu dữ liệu, phá hòa và định dạng khi cần.

Chỉ truyền `xlsx_files/` và `queries.json` vào solver. `answer_audit.json` chứa SQL/đáp án để kiểm chứng bên ngoài mô hình; `dataset_manifest.json` mô tả vùng dữ liệu cho bộ kiểm tra. Không đưa các file này hoặc `expected_submission.csv` vào prompt/retrieval. `sample_submission.csv` chỉ là mẫu rỗng.

```powershell
python main.py --mode llm --xlsx_dir Test/23_civic_service_long/xlsx_files --queries Test/23_civic_service_long/queries.json --output outputs/23_civic_service_long.csv --log-dir outputs/23_civic_service_long-logs
python scripts/evaluate.py --prediction outputs/23_civic_service_long.csv --reference Test/23_civic_service_long/expected_submission.csv --report outputs/23_civic_service_long-strict.json
```

Điểm trên là strict exact match, chưa tái tạo chuẩn hóa BTC. Chưa chạy LLM hoặc đo chi phí/thời gian của mô hình. Quy định tài nguyên bài thi là RAM ≤ 4 GB, disk ≤ 1 GB và ZIP ≤ 100 MB theo AGENTS.md; kích thước file nhỏ không chứng minh cả pipeline đạt các giới hạn đó.
