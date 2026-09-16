"""Native identity guards reject generated or expanded visible pixels."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image
lazy import pytest

lazy from tools.art_pipeline import native_identity_guard as subject


def _source_array() -> np.ndarray:
    image = np.zeros((4, 5, 4), dtype=np.uint8)
    image[1:3, 1:4] = [31, 47, 73, 192]
    image[2, 2] = [91, 107, 131, 128]
    return image


def _native_source(tmp_path: Path) -> subject.NativeRgbaSource:
    path = tmp_path / "native.png"
    Image.fromarray(_source_array(), mode="RGBA").save(path, format="PNG")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return subject.load_native_rgba_source(path, digest.upper())


def _issue_codes(report: subject.NativeIdentityReport) -> set[subject.IdentityIssueCode]:
    return {issue.code for issue in report.issues}


def test_loader_binds_digest_and_returns_read_only_rgba8(tmp_path: Path) -> None:
    source = _native_source(tmp_path)

    assert source.rgba.shape == (4, 5, 4)
    assert source.rgba.dtype == np.uint8
    assert source.rgba.flags.writeable is False


def test_exact_body_hands_and_face_core_pass(tmp_path: Path) -> None:
    source = _native_source(tmp_path)
    overlays = subject.IdentityOverlays(
        body=source.rgba.copy(),
        hands={"left": source.rgba.copy(), "right": source.rgba.copy()},
        face_core=source.rgba.copy(),
    )

    report = subject.validate_native_identity(source, overlays)

    assert report.passed is True
    assert report.issues == ()
    assert {check.target for check in report.checks} == {
        "body", "hand:left", "hand:right", "face_core",
    }


def test_rgb_mismatch_and_alpha_inflation_are_reported(tmp_path: Path) -> None:
    source = _native_source(tmp_path)
    body = source.rgba.copy()
    body[1, 1, 0] += 1
    body[1, 1, subject.ALPHA_CHANNEL] = 255

    report = subject.validate_native_identity(
        source,
        subject.IdentityOverlays(body=body),
    )

    assert report.passed is False
    assert _issue_codes(report) == {
        subject.IdentityIssueCode.RGB_MISMATCH,
        subject.IdentityIssueCode.ALPHA_INFLATION,
    }
    assert report.checks[0].rgb_mismatch_pixels == 1
    assert report.checks[0].alpha_inflation_pixels == 1


def test_face_allowed_mask_exempts_only_selected_rgb_difference(tmp_path: Path) -> None:
    source = _native_source(tmp_path)
    face = source.rgba.copy()
    face[1, 1, :3] = [200, 201, 202]
    allowed = np.zeros((4, 5), dtype=np.uint8)
    allowed[1, 1] = 255

    report = subject.validate_native_identity(
        source,
        subject.IdentityOverlays(face_core=face, allowed_dynamic_mask=allowed),
    )

    assert report.passed is True
    assert report.checks[0].allowed_pixels == 1


def test_assertion_returns_jsonable_facts_and_raises_with_report(tmp_path: Path) -> None:
    source = _native_source(tmp_path)
    facts = subject.assert_native_identity(
        source,
        subject.IdentityOverlays(body=source.rgba.copy()),
    )

    assert json.loads(json.dumps(facts)) == facts
    assert facts["passed"] is True
    changed = source.rgba.copy()
    changed[1, 1, 0] += 1
    with pytest.raises(subject.NativeIdentityMismatchError) as raised:
        subject.assert_native_identity(source, subject.IdentityOverlays(body=changed))
    assert raised.value.report.to_jsonable()["problems"] == [
        "rgb-mismatch:body:1 visible RGB pixels differ outside the allowed mask",
    ]


@pytest.mark.parametrize(
    ("overlays", "expected"),
    [
        (subject.IdentityOverlays(body=np.zeros((4, 5, 4), dtype=np.uint8)),
         subject.IdentityIssueCode.EMPTY_OVERLAY_MASK),
        (subject.IdentityOverlays(body=np.zeros((3, 5, 4), dtype=np.uint8)),
         subject.IdentityIssueCode.SHAPE_MISMATCH),
        (subject.IdentityOverlays(body=np.zeros((4, 5, 4), dtype=np.int16)),
         subject.IdentityIssueCode.INVALID_OVERLAY_ARRAY),
        (subject.IdentityOverlays(face_core=_source_array(),
                                  allowed_dynamic_mask=np.zeros((4, 5), dtype=np.uint8)),
         subject.IdentityIssueCode.EMPTY_ALLOWED_MASK),
    ],
)
def test_empty_or_mismatched_masks_fail_closed(
    tmp_path: Path,
    overlays: subject.IdentityOverlays,
    expected: subject.IdentityIssueCode,
) -> None:
    report = subject.validate_native_identity(_native_source(tmp_path), overlays)

    assert report.passed is False
    assert expected in _issue_codes(report)


def test_missing_source_and_digest_mismatch_are_explicit(tmp_path: Path) -> None:
    missing = subject.validate_native_identity(None, subject.IdentityOverlays())
    assert missing.passed is False
    assert subject.IdentityIssueCode.MISSING_SOURCE in _issue_codes(missing)

    path = tmp_path / "native.png"
    Image.fromarray(_source_array(), mode="RGBA").save(path, format="PNG")
    with pytest.raises(subject.NativeIdentityGuardError, match="SHA-256 mismatch"):
        subject.load_native_rgba_source(path, "0" * subject.SHA256_HEX_LENGTH)
