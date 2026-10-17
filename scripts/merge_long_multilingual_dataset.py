"""Combine the five compact long multilingual suites into one dataset."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

SUITES = [
    "23_civic_service_long",
    "24_procurement_temporal_long",
    "25_energy_intervals_long",
    "26_logistics_event_versions",
    "27_lab_units_censoring_long",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-root", type=Path, default=Path("Test"))
    parser.add_argument("--output", type=Path,
                        default=Path("Test/28_long_multilingual_combined"))
    args = parser.parse_args()

    out = args.output
    if out.exists():
        shutil.rmtree(out)
    xlsx_out = out / "xlsx_files"
    xlsx_out.mkdir(parents=True)

    queries, checks, expected, suite_manifests = [], [], [], []
    for suite in SUITES:
        source = args.test_root / suite
        workbook_name = f"{suite}.xlsx"
        shutil.copy2(source / "xlsx_files" / "data.xlsx", xlsx_out / workbook_name)

        suite_queries = json.loads((source / "queries.json").read_text(encoding="utf-8"))
        for query in suite_queries:
            query = dict(query)
            query["file_name"] = workbook_name
            queries.append(query)

        audit = json.loads((source / "answer_audit.json").read_text(encoding="utf-8"))
        for check in audit["checks"]:
            check = dict(check)
            check["source_suite"] = suite
            checks.append(check)

        with (source / "expected_submission.csv").open(encoding="utf-8", newline="") as f:
            expected.extend((int(row["id"]), row["answer"]) for row in csv.DictReader(f))
        manifest = json.loads((source / "dataset_manifest.json").read_text(encoding="utf-8"))
        suite_manifests.append({
            "name": suite,
            "workbook": workbook_name,
            "questions": len(suite_queries),
            "tables": manifest["tables"],
        })

    queries.sort(key=lambda q: int(q["id"]))
    checks.sort(key=lambda c: int(c["id"]))
    expected.sort(key=lambda row: row[0])
    (out / "queries.json").write_text(
        json.dumps(queries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (out / "expected_submission.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["id", "answer"])
        writer.writerows(expected)
    with (out / "sample_submission.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["id", "answer"])
        writer.writerows((question_id, "") for question_id, _ in expected)
    (out / "answer_audit.json").write_text(
        json.dumps({"schema_version": 1, "checks": checks}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest = {
        "suite": "28_long_multilingual_combined",
        "questions": len(queries),
        "workbook_count": len(SUITES),
        "row_budget": "14,821 physical worksheet rows across five workbooks",
        "suites": suite_manifests,
        "gold_order": "ascending numeric ID",
        "unknown_answer": "",
        "data_kind": "new fictional records; compact regeneration of suites 23-27",
    }
    (out / "dataset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    readme = f"""# 28_long_multilingual_combined

Dataset gộp từ 5 workbook Excel compact, gồm **{len(queries)} câu hỏi** và **{len(SUITES)} file XLSX**. Tổng số dòng vật lý của các worksheet khoảng **14.821**, dưới 20.000 dòng. Mỗi workbook giữ domain và cấu trúc riêng; `queries.json` dùng `file_name` tương ứng để solver chọn đúng file.

Các suite nguồn: {", ".join(SUITES)}. ID là số tự nhiên, đã sắp tăng dần trong `expected_submission.csv`; câu không có đáp án dùng chuỗi rỗng. Chỉ truyền `xlsx_files/` và `queries.json` vào solver. `expected_submission.csv` và `answer_audit.json` chỉ dùng đánh giá ngoài ngữ cảnh solver.

```powershell
python main.py --mode llm --xlsx_dir Test/28_long_multilingual_combined/xlsx_files --queries Test/28_long_multilingual_combined/queries.json --output outputs/28_long_multilingual_combined.csv --log-dir outputs/28_long_multilingual_combined-logs
python scripts/evaluate.py --prediction outputs/28_long_multilingual_combined.csv --reference Test/28_long_multilingual_combined/expected_submission.csv --report outputs/28_long_multilingual_combined-strict.json
```
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    print(f"Created {out}: {len(queries)} questions, {len(SUITES)} workbooks")


if __name__ == "__main__":
    main()
