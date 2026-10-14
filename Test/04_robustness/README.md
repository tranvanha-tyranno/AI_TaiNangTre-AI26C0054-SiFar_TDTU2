# 04_robustness — Bien & bao mat

- Dau phay, nhay don, khoang trang trong o/cau tra loi (CSV quoting)
- O rong / None
- Tu choi ID trung, duong dan traversal

```powershell
./.venv/Scripts/python.exe main.py --mode offline --xlsx_dir ./Test/04_robustness/xlsx_files --queries ./Test/04_robustness/queries.json --output ./Test/04_robustness/submission.csv
./.venv/Scripts/python.exe main.py --mode offline --xlsx_dir ./Test/04_robustness/xlsx_files --queries ./Test/04_robustness/queries_duplicate.json --output ./Test/04_robustness/out.csv; echo $LASTEXITCODE
```
