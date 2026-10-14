# 01_smoke_replica — Smoke nhanh (3 cau)

Kiem tra I/O, merged header Name/Date of, va nhanh fiscal Yes/No ma khong can LLM.

```powershell
./.venv/Scripts/python.exe main.py --mode offline --xlsx_dir ./Test/01_smoke_replica/xlsx_files --queries ./Test/01_smoke_replica/queries.json --output ./Test/01_smoke_replica/submission.csv
./.venv/Scripts/python.exe scripts/evaluate.py --prediction ./Test/01_smoke_replica/submission.csv --reference ./Test/01_smoke_replica/expected_submission.csv
```

Dashboard: chon dataset `01_smoke_replica` o dropdown.
