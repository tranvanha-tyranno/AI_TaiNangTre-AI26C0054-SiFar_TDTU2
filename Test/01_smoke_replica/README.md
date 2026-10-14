# 01_smoke_replica — Smoke nhanh (3 cau)

Kiểm tra I/O, tiêu đề Name/Date of có ô gộp và so sánh fiscal Yes/No. Chạy LLM để đánh giá đáp án; offline có thể trả chưa trả lời.

`smoke_q001` có đáp án `Dang`: Mai trẻ nhất tại nhập học (gần 19 tuổi), Ha đứng thứ hai (20 tuổi), Linh gần 21 tuổi. Phải dùng chênh lệch Birth–Admission của từng người, không xếp theo ngày sinh đơn thuần.

```powershell
./.venv/Scripts/python.exe main.py --mode offline --xlsx_dir ./Test/01_smoke_replica/xlsx_files --queries ./Test/01_smoke_replica/queries.json --output ./Test/01_smoke_replica/submission.csv
./.venv/Scripts/python.exe scripts/evaluate.py --prediction ./Test/01_smoke_replica/submission.csv --reference ./Test/01_smoke_replica/expected_submission.csv
```

Dashboard: chon dataset `01_smoke_replica` o dropdown.
