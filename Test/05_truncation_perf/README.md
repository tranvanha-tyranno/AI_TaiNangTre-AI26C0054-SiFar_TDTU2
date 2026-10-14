# 05_truncation_perf — Cat ngan & hieu nang

500 dong de kiem tra serialize_for_llm(max_chars=14000) cat 60/40 va dashboard hien 200x30.

```powershell
./.venv/Scripts/python.exe main.py --mode offline --xlsx_dir ./Test/05_truncation_perf/xlsx_files --queries ./Test/05_truncation_perf/queries.json --output ./Test/05_truncation_perf/submission.csv
```
