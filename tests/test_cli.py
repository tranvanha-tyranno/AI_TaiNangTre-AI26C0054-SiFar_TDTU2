import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CLITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "outputs").mkdir(exist_ok=True)

    def test_public_offline_output_and_logs(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
            output = Path(temp) / "submission.csv"
            logs = Path(temp) / "logs"
            result = subprocess.run([sys.executable, str(ROOT / "main.py"), "--mode", "offline",
                "--xlsx_dir", str(ROOT / "Public_data_1/xlsx_files"),
                "--queries", str(ROOT / "Public_data_1/queries.json"),
                "--output", str(output), "--log-dir", str(logs)], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with output.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(reader.fieldnames, ["id", "answer"])
                actual = list(reader)
            queries = json.loads((ROOT / "Public_data_1/queries.json").read_text(encoding="utf-8"))
            self.assertEqual([r['id'] for r in actual], [str(q['id']) for q in queries])
            self.assertTrue(all(r['answer'] for r in actual))
            self.assertEqual(len((logs / "questions.jsonl").read_text(encoding="utf-8").splitlines()), len(queries))

    def test_duplicate_ids_rejected_before_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
            query = {"id": 1, "file_name": "p4_t01.xlsx", "query": "test"}
            path = Path(temp) / "queries.json"
            path.write_text(json.dumps([query, query]), encoding="utf-8")
            output = Path(temp) / "submission.csv"
            result = subprocess.run([sys.executable, str(ROOT / "main.py"), "--mode", "offline",
                "--queries", str(path), "--output", str(output)], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
