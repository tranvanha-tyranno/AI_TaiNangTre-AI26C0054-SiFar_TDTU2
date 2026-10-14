import json, csv, tempfile, sys, unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import dashboard


def _write_expected(path: Path, rows: dict):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "answer"])
        for k, v in rows.items():
            w.writerow([k, v])


class DashboardDatasetTest(unittest.TestCase):
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
