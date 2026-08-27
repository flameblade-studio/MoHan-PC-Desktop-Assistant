lazy from pathlib import Path
lazy import sys
lazy import tempfile
lazy import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

lazy from audit_yaw000_golden_template import audit
lazy from build_yaw000_golden_template import build


class Yaw000GoldenTemplateTests(unittest.TestCase):
    def test_build_and_fail_closed_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            layer_dir = Path(tmp) / "golden" / "layers"
            manifest = build(ROOT, layer_dir)
            self.assertEqual(25, len(manifest["records"]))
            report = audit(ROOT, layer_dir)
            self.assertTrue(report["passed"], report["failures"])
            self.assertEqual(0, report["metrics"]["recompose_diff_pixels"])
            self.assertEqual(0, report["metrics"]["lip_green_cyan_pixels"])


if __name__ == "__main__":
    unittest.main()
