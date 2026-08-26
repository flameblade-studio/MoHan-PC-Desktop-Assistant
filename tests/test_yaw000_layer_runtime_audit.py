from __future__ import annotations

lazy from tools.audit_yaw000_layer_runtime import EXPECTED_LAYERS, SCHEMA, audit


def test_yaw000_runtime_audit_is_deterministic_and_fail_closed() -> None:
    first = audit()
    second = audit()
    assert first == second
    assert first.schema == SCHEMA
    assert first.passed is (not first.issues)
    assert first.layer_count == EXPECTED_LAYERS
    assert set(first.metrics) == {
        "rest_mean_channel_error",
        "blink_changed_pixels",
        "gaze_changed_pixels",
        "speech_changed_pixels",
        "physics_changed_pixels",
    }


def test_dynamic_eye_controls_are_visible_after_authority_restoration() -> None:
    report = audit()
    assert report.passed is True
    assert report.metrics["blink_changed_pixels"] >= 12
    assert report.metrics["gaze_changed_pixels"] >= 12
