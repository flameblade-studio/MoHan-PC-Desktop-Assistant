lazy from pathlib import Path
lazy import sys
lazy import tempfile
lazy import unittest
lazy import json


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
            action = json.loads((layer_dir.parent / "action-manifest.json").read_text(encoding="utf-8"))
            self.assertIs(action["authority"]["visual_approval_established_by_tool"], False)
            report = audit(ROOT, layer_dir)
            self.assertTrue(report["passed"], report["failures"])
            self.assertEqual(0, report["metrics"]["recompose_diff_pixels"])
            self.assertEqual(0, report["metrics"]["lip_green_cyan_pixels"])


def main() -> None:
    result = unittest.main(exit=False)
    if not result.result.wasSuccessful():
        raise SystemExit(1)
    print("YAW000_GOLDEN_TEMPLATE_OK")


if __name__ == "__main__":
    main()
