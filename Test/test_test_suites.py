import csv, json, subprocess, sys, unittest
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = ROOT / "Test"

# Lưu ý: bộ deterministic chỉ phủ stem p4_t01..p4_t10 nên các file Test/
# (mini_people.xlsx, hierarchy.xlsx, ...) ở mode offline sẽ là "unanswered".
# Test này vì vậy chỉ kiểm tra I/O + logs + từ chối input xấu,
# còn expected_submission.csv là reference cho mode hybrid/LLM trên dashboard.
SUITES = sorted(path.name for path in TEST_ROOT.iterdir()
                if path.is_dir() and (path / "queries.json").is_file())

def _read_csv(path: Path) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {r["id"]: r["answer"] for r in csv.DictReader(f)}


class TestSuitesOffline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not TEST_ROOT.exists():
            raise unittest.SkipTest("Test/ chưa tồn tại — chạy scripts/gen_test_suites.py")

    def test_each_suite_cli_writes_valid_csv_and_logs(self):
        for suite in SUITES:
            base = TEST_ROOT / suite
            if not (base / "queries.json").exists():
                self.fail(f"Thiếu {suite}/queries.json")
            queries = json.loads((base / "queries.json").read_text(encoding="utf-8"))
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as tmp:
                queries_path = base / "queries.json"
                # Fixture-oracle checks cover all 35 large-table answers. This
                # CLI smoke test exercises one full-column sum; the legacy
                # offline resolver otherwise reloads 2,500 x 35 cells per query.
                if suite == "12_large_full_scan":
                    queries = queries[-1:]
                    queries_path = Path(tmp) / "queries.json"
                    queries_path.write_text(json.dumps(queries), encoding="utf-8")
                out = Path(tmp) / "submission.csv"
                logs = Path(tmp) / "logs"
                result = subprocess.run(
                    [sys.executable, str(ROOT / "main.py"), "--mode", "offline",
                     "--xlsx_dir", str(base / "xlsx_files"),
                     "--queries", str(queries_path),
                     "--output", str(out), "--log-dir", str(logs)],
                    cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
                # offline có thể exit 0 (có đáp án) hoặc 3 (unanswered) — đều phải ghi CSV + logs
                self.assertIn(result.returncode, (0, 3), f"{suite} failed: {result.stderr[:800]}")
                self.assertTrue(out.exists(), f"{suite} phải ghi submission.csv")
                actual = _read_csv(out)
                self.assertEqual([str(k) for k in actual.keys()], [str(q["id"]) for q in queries],
                                 f"{suite} sai thứ tự/id")
                self.assertTrue((logs / "questions.jsonl").exists(), f"{suite} thiếu logs")

    def test_robustness_rejects_duplicate_and_traversal(self):
        base = TEST_ROOT / "04_robustness"
        for qfile in ["queries_duplicate.json", "queries_bad_path.json"]:
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as tmp:
                out = Path(tmp) / "out.csv"
                result = subprocess.run(
                    [sys.executable, str(ROOT / "main.py"), "--mode", "offline",
                     "--xlsx_dir", str(base / "xlsx_files"),
                     "--queries", str(base / qfile),
                     "--output", str(out)],
                    cwd=ROOT, capture_output=True)
                self.assertEqual(result.returncode, 2, f"{qfile} should be rejected with 2")
                self.assertFalse(out.exists(), f"{qfile} must not write output")
