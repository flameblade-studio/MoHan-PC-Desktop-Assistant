from __future__ import annotations

lazy import unittest

lazy import numpy as np

lazy from tools.audit_profile_nose_lip_contract import (
    CURVATURE_PENALTY_COEFFICIENT,
    LANDMARK_INDICES,
    audit_nose_lip_contract,
)


def authority_landmarks() -> np.ndarray:
    points = np.column_stack((np.arange(100, dtype=np.float64), np.arange(100, dtype=np.float64) * 0.2))
    points[4] = (10.0, 10.0)
    points[94] = (12.0, 11.2)
    points[0] = (12.4, 13.6)
    return points


class NoseLipContractTests(unittest.TestCase):
    def test_indices_and_two_percent_penalty_are_authoritative(self):
        self.assertEqual(LANDMARK_INDICES, (4, 94, 0))
        self.assertEqual(CURVATURE_PENALTY_COEFFICIENT, 0.02)
        report = audit_nose_lip_contract(authority_landmarks(), authority_landmarks())
        expected = report.metrics["alignment_rms_normalized"] + 0.02 * report.metrics["curvature_delta_radians"]
        self.assertAlmostEqual(report.metrics["contract_score"], expected, places=14)

    def test_random_proper_similarity_transforms_pass_deterministically(self):
        reference = authority_landmarks()
        rng = np.random.default_rng(2400)
        reports = []
        for _ in range(200):
            theta = rng.uniform(-np.pi, np.pi)
            rotation = np.array(((np.cos(theta), -np.sin(theta)), (np.sin(theta), np.cos(theta))))
            scale = rng.uniform(0.35, 3.0)
            shift = rng.uniform(-200.0, 200.0, size=2)
            candidate = reference @ rotation.T * scale + shift
            report = audit_nose_lip_contract(reference, candidate)
            self.assertTrue(report.passed, report)
            reports.append(report.to_dict())
        rng = np.random.default_rng(2400)
        replay = []
        for _ in range(200):
            theta = rng.uniform(-np.pi, np.pi)
            rotation = np.array(((np.cos(theta), -np.sin(theta)), (np.sin(theta), np.cos(theta))))
            candidate = reference @ rotation.T * rng.uniform(0.35, 3.0) + rng.uniform(-200.0, 200.0, size=2)
            replay.append(audit_nose_lip_contract(reference, candidate).to_dict())
        self.assertEqual(reports, replay)

    def test_curvature_kink_is_rejected(self):
        reference = authority_landmarks()
        candidate = reference.copy()
        candidate[94] += (2.2, -2.8)
        report = audit_nose_lip_contract(reference, candidate)
        self.assertFalse(report.passed)
        self.assertIn("nose_lip_curvature_discontinuity", report.issues)

    def test_reflection_is_rejected(self):
        reference = authority_landmarks()
        reflected = reference * (-1.0, 1.0)
        with self.assertRaisesRegex(ValueError, "reflection"):
            audit_nose_lip_contract(reference, reflected)

    def test_invalid_input_fails_closed(self):
        reference = authority_landmarks()
        invalid = (
            reference[:94],
            reference[:, :1],
            np.vstack((reference[:99], np.array([[np.nan, 0.0]]))),
            np.full_like(reference, np.inf),
            np.zeros_like(reference),
        )
        for candidate in invalid:
            with self.subTest(shape=candidate.shape):
                with self.assertRaises(ValueError):
                    audit_nose_lip_contract(reference, candidate)

    def test_50hz_linear_transition_is_finite_and_continuous(self):
        reference = authority_landmarks()
        target = reference.copy()
        target[[4, 94, 0]] += ((0.3, -0.1), (0.2, 0.05), (0.1, 0.1))
        frames = np.stack([reference + (target - reference) * (tick / 50.0) for tick in range(51)])
        self.assertTrue(np.isfinite(frames).all())
        steps = np.linalg.norm(np.diff(frames[:, [4, 94, 0]], axis=0), axis=2)
        self.assertLess(float(steps.max()), 0.02)
        self.assertTrue(all(audit_nose_lip_contract(reference, frame, max_normalized_rms=0.1).passed for frame in frames))


if __name__ == "__main__":
    unittest.main()
