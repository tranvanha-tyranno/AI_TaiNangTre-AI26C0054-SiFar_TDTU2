from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CLITest(unittest.TestCase):
    def test_only_llm_mode_is_advertised(self):
        result = subprocess.run([sys.executable, str(ROOT / "main.py"), "--help"], cwd=ROOT,
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
        self.assertEqual(result.returncode, 0)
        help_text=(result.stdout or '')+(result.stderr or '')
        self.assertIn('--mode {llm,llm-v2}', help_text)
        self.assertNotIn('offline', help_text.lower())
        self.assertNotIn('hybrid', help_text.lower())

    def test_removed_modes_are_rejected_before_output(self):
        for mode in ('offline', 'hybrid'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
                result = subprocess.run([sys.executable, str(ROOT / "main.py"), "--mode", mode,
                    "--queries", str(ROOT / "Public_data_1/queries.json"), "--output", str(Path(temp) / "out.csv")],
                    cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((Path(temp) / "out.csv").exists())

    def test_llm_v2_is_accepted(self):
        result = subprocess.run([sys.executable, str(ROOT / "main.py"), "--help"], cwd=ROOT,
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
        self.assertIn('llm-v2', (result.stdout or '')+(result.stderr or ''))


if __name__ == "__main__":
    unittest.main()
