import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import dashboard


class DashboardTest(unittest.TestCase):
    def test_matches_use_selected_logs(self):
        dashboard.OUTPUTS.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=dashboard.OUTPUTS) as temp:
            path = Path(temp)
            (path / "questions.jsonl").write_text(json.dumps({"id": "1", "answer": "wrong", "status": "ok"}) + '\n', encoding="utf-8")
            with patch.object(dashboard, "run_dirs", return_value={"test": path}), patch.object(dashboard, "queries", return_value=[{"id": "1", "query": "Q", "file_name": "a.xlsx"}]), patch.object(dashboard, "reference", return_value={"1": "right"}), patch.object(dashboard, "safe_config", return_value={}):
                state = dashboard.build_state("test")
            self.assertEqual(state["summary"]["matched"], 0)
            self.assertFalse(state["rows"][0]["match"])

    def test_partial_jsonl_and_invalid_run(self):
        dashboard.OUTPUTS.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=dashboard.OUTPUTS) as temp:
            path = Path(temp)
            (path / "questions.jsonl").write_text('{"id":"1","answer":"a"}\n{"id":', encoding="utf-8")
            self.assertEqual(list(dashboard.records(path)), ["1"])
            with patch.object(dashboard, "run_dirs", return_value={"test": path}):
                with self.assertRaises(ValueError):
                    dashboard.build_state("../../.env")

    def test_unknown_file_is_rejected(self):
        with self.assertRaises(ValueError):
            dashboard.workbook("../../.env")
