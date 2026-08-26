lazy import unittest
lazy from pathlib import Path

lazy from tools.build_full_body_golden_batch import build_manifest, expected_views


class FullBodyGoldenBatchTests(unittest.TestCase):
    def test_view_contract(self):
        views = expected_views()
        self.assertEqual(24, len(views))
        self.assertEqual("yaw-180-pitch+00", views[0])
        self.assertEqual("yaw+000-pitch+00", views[12])
        self.assertEqual("yaw+165-pitch+00", views[-1])

    def test_real_registry_is_fail_closed_partial(self):
        repo = Path(__file__).resolve().parents[1]
        registry = repo / "work/full-body-layer-golden-batch/authority-registry.json"
        if not registry.is_file():
            # The registry is a local work product (git-ignored).  A checkout
            # without it must still fail closed instead of inventing a state.
            with self.assertRaises(FileNotFoundError):
                build_manifest(repo, registry)
            self.skipTest("local golden-batch registry not present in this checkout")
        manifest = build_manifest(repo, registry)
        self.assertFalse(manifest["promotable"])
        self.assertEqual(1, manifest["summary"]["ready_views"])
        self.assertEqual(23, manifest["summary"]["blocked_views"])
        self.assertEqual(25, manifest["summary"]["ready_layers"])
        self.assertEqual(575, manifest["summary"]["blocked_layers"])
        yaw000 = next(v for v in manifest["views"] if v["view_id"] == "yaw+000-pitch+00")
        self.assertEqual("golden_ready", yaw000["status"])
        self.assertNotIn("shoe_bottom_clearance_invalid", " ".join(manifest["failures"]))


if __name__ == "__main__":
    unittest.main()
