# 26_logistics_event_versions

32800 dòng lịch sử cho 8000 vận đơn: sửa phiên bản, thứ tự vật lý xáo trộn, trạng thái cuối, giao đúng hẹn, phân vị thời gian và ngày UTC.

`Danh mục kho`: 500 bản ghi / 501 dòng vật lý; `Vận đơn`: 8,000 bản ghi / 8,001 dòng vật lý; `Lịch sử sự kiện`: 32,800 bản ghi / 32,801 dòng vật lý.

30 câu: **15 Việt, 5 Anh, 4 Trung, 3 Pháp, 3 Hàn**. ID là số tự nhiên; câu hỏi cố ý xáo trộn. CSV chuẩn dùng UTF-8 và sắp ID theo giá trị số tăng dần. Một câu thiếu trường dữ liệu có đáp án chuỗi rỗng. Câu đó không tính là lỗi fixture; không tự đổi đáp án thành N/A.

Dữ liệu hư cấu được sinh mới theo seed, có khóa và quan hệ nghiệp vụ nhất quán. Dòng cuối, phần giữa và các sheet phụ đều có câu yêu cầu truy xuất; không thể giải đầy đủ bằng preview đầu bảng. Các câu quy định phạm vi, đơn vị, xử lý thiếu dữ liệu, phá hòa và định dạng khi cần.

Chỉ truyền `xlsx_files/` và `queries.json` vào solver. `answer_audit.json` chứa SQL/đáp án để kiểm chứng bên ngoài mô hình; `dataset_manifest.json` mô tả vùng dữ liệu cho bộ kiểm tra. Không đưa các file này hoặc `expected_submission.csv` vào prompt/retrieval. `sample_submission.csv` chỉ là mẫu rỗng.

```powershell
python main.py --mode llm --xlsx_dir Test/26_logistics_event_versions/xlsx_files --queries Test/26_logistics_event_versions/queries.json --output outputs/26_logistics_event_versions.csv --log-dir outputs/26_logistics_event_versions-logs
python scripts/evaluate.py --prediction outputs/26_logistics_event_versions.csv --reference Test/26_logistics_event_versions/expected_submission.csv --report outputs/26_logistics_event_versions-strict.json
```

Điểm trên là strict exact match, chưa tái tạo chuẩn hóa BTC. Chưa chạy LLM hoặc đo chi phí/thời gian của mô hình. Quy định tài nguyên bài thi là RAM ≤ 4 GB, disk ≤ 1 GB và ZIP ≤ 100 MB theo AGENTS.md; kích thước file nhỏ không chứng minh cả pipeline đạt các giới hạn đó.
