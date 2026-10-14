import json, csv, tempfile, sys, unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import dashboard
import time
import openpyxl


def _write_expected(path: Path, rows: dict):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "answer"])
        for k, v in rows.items():
            w.writerow([k, v])


class DashboardDatasetTest(unittest.TestCase):
    def test_switching_dataset_does_not_reuse_public_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "questions.jsonl").write_text('{"id":"1","answer":"public","status":"ok"}\n', encoding="utf-8")
            with patch.object(dashboard, "run_dirs", return_value={"latest": path}):
                state = dashboard.build_state(dataset_id="01_smoke_replica")
            self.assertIsNone(state["selected"])
            self.assertEqual(state["dataset"], "01_smoke_replica")
            self.assertTrue(all(row["status"] == "pending" for row in state["rows"]))
            self.assertTrue(all(row["reference"] is not None for row in state["rows"]))

    def test_multi_run_separates_duplicate_ids_files_and_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, answer in [("a", "11"), ("b", "22")]:
                folder = root / "Test" / name
                (folder / "xlsx_files").mkdir(parents=True)
                book = openpyxl.Workbook()
                book.active["A1"] = answer
                book.save(folder / "xlsx_files" / "same.xlsx")
                book.close()
                (folder / "queries.json").write_text(json.dumps([
                    {"id": 1, "file_name": "same.xlsx", "query": "What is in A1?"}
                ]), encoding="utf-8")
                _write_expected(folder / "expected_submission.csv", {1: answer})
            with patch.object(dashboard, "TEST_ROOT", root / "Test"), patch.object(dashboard, "OUTPUTS", root / "outputs"):
                run = dashboard.start_run("offline", None, "a,b")
                deadline = time.monotonic() + 30
                while dashboard.JOB["running"] and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertFalse(dashboard.JOB["running"])
                folder = dashboard.OUTPUTS / "runs" / run
                self.assertIn(dashboard.JOB["returncode"], (0, 3))
                with (folder / "submission.csv").open(encoding="utf-8") as stream:
                    self.assertEqual([r["id"] for r in csv.DictReader(stream)], ["a::1", "b::1"])
                self.assertEqual(dashboard.workbook("a/same.xlsx", dataset_id="a,b")["rows"][0][0], "11")
                self.assertEqual(dashboard.workbook("b/same.xlsx", dataset_id="a,b")["rows"][0][0], "22")
                (folder / "questions.jsonl").write_text('\n'.join(json.dumps({"id": ident, "answer": answer, "status": "ok"})
                    for ident, answer in [("a::1", "11"), ("b::1", "22")]), encoding="utf-8")
                state = dashboard.build_state(run)
                self.assertEqual(state["summary"]["matched"], 2)
                self.assertEqual([r["reference"] for r in state["rows"]], ["11", "22"])
                self.assertEqual(dashboard.build_state(dataset_id="b,a")["selected"], run)

    def test_select_one_question_from_multiple_datasets(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(dashboard.threading, "Thread"):
            with patch.object(dashboard, "OUTPUTS", Path(tmp)), patch.dict(dashboard.JOB, running=False):
                dataset = "01_smoke_replica,02_merged_hierarchy"
                question = dashboard.queries(dataset)[-1]
                run = dashboard.start_run("offline", [question["id"]], dataset)
                state = dashboard.build_state(run)
                self.assertEqual([r["id"] for r in state["rows"]], [question["id"]])
                self.assertEqual(state["dataset"], dataset)

    def test_invalid_dataset_is_rejected(self):
        with self.assertRaises(ValueError):
            dashboard.build_state(dataset_id="../../.env")
        with self.assertRaises(ValueError):
            dashboard.start_run("offline", None, ["public"])

    def test_datasets_lists_public_and_test_suites(self):
        # Test/ đã có 5 suite sau gen_test_suites.py
        ds = dashboard.datasets()
        ids = {d["id"] for d in ds}
        self.assertIn("public", ids)
        for sid in ["01_smoke_replica", "02_merged_hierarchy", "03_multisheet_multitable", "04_robustness", "05_truncation_perf"]:
            self.assertIn(sid, ids)

    def test_build_state_uses_expected_per_dataset(self):
        dashboard.TEST_ROOT.joinpath("test_tmp_ds").mkdir(exist_ok=True)
        base = dashboard.TEST_ROOT / "test_tmp_ds"
        try:
            (base / "xlsx_files").mkdir(exist_ok=True)
            (base / "queries.json").write_text(json.dumps([{"id": "t_q001", "file_name": "a.xlsx", "query": "Q"}]), encoding="utf-8")
            _write_expected(base / "expected_submission.csv", {"t_q001": "42"})
            with tempfile.TemporaryDirectory(dir=dashboard.OUTPUTS) as tmp:
                path = Path(tmp)
                (path / "questions.jsonl").write_text(json.dumps({"id": "t_q001", "answer": "42", "status": "ok"}) + "\n", encoding="utf-8")
                (path / "metadata.json").write_text(json.dumps({"mode": "offline", "dataset": "test_tmp_ds", "ids": ["t_q001"]}), encoding="utf-8")
                with patch.object(dashboard, "run_dirs", return_value={"run1": path}):
                    state = dashboard.build_state("run1")
                self.assertEqual(state["dataset"], "test_tmp_ds")
                self.assertEqual(state["rows"][0]["reference"], "42")
                self.assertTrue(state["rows"][0]["match"])
        finally:
            import shutil
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
