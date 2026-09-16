"""Contract tests for foundation-bearing reviewed pose motion assets."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication

from domain.outfit_pack_official import BUILTIN_MAKEUP_PACK_ID
from infrastructure import reviewed_pose_overlay as overlay_module
from infrastructure.reviewed_pose_motion import (
    APPROVED_SOURCE_SHA256,
    COSMETIC_SLOTS,
    COSMETIC_STATES,
    DIMENSION,
    FOUNDATION_COSMETIC_SLOTS,
    FOUNDATION_SCHEMA,
    SCHEMA,
    load_reviewed_pose_motion,
)
from infrastructure.reviewed_pose_overlay import ReviewedPoseOverlayMixin


REST_STATE = "rest"
CLOSED_STATE = "closed"
SPEECH_STATE = "speech"
SPEECH_CLOSED_STATE = "speech-closed"
ZERO_INTENSITY = 0.0
FULL_INTENSITY = 1.0
LIGHT_STRENGTH = 0.55
TRANSPARENT_ALPHA = 0

BODY_POINT = (1, 1)
FOUNDATION_POINT = (4, 4)
EYES_POINT = (8, 8)
OUTSIDE_POINT = (40, 40)
MOUTH_POINT = (80, 80)

BASE_COLOR = QColor("#18324a")
MOUTH_COLOR = QColor("#b33a5b")
PATCH_COLOR = QColor("#496579")
LEAK_COLOR = QColor("#f0d071")
FOUNDATION_COLORS = {
    REST_STATE: QColor("#b8a28b"),
    CLOSED_STATE: QColor("#c7ae95"),
    SPEECH_STATE: QColor("#d4bca0"),
}
EYE_COLORS = {
    REST_STATE: QColor("#d13b5d"),
    CLOSED_STATE: QColor("#e04c68"),
    SPEECH_STATE: QColor("#ec5b72"),
}
CHEEK_COLORS = {
    REST_STATE: QColor("#df6a78"),
    CLOSED_STATE: QColor("#e67883"),
    SPEECH_STATE: QColor("#ef8990"),
}
LIP_COLORS = {
    REST_STATE: QColor("#9d3155"),
    CLOSED_STATE: QColor("#ae3c5e"),
    SPEECH_STATE: QColor("#bd4967"),
}


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _png(points: dict[tuple[int, int], QColor], *, dimension: int = DIMENSION) -> bytes:
    image = QImage(dimension, dimension, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    for point, color in points.items():
        image.setPixelColor(*point, color)
    output = QByteArray()
    buffer = QBuffer(output)
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(output)


def _record(root: Path, relative: str, payload: bytes) -> dict[str, str]:
    path = root / Path(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"path": relative, "sha256": hashlib.sha256(payload).hexdigest()}


def _cosmetic_points(state: str, slot: str) -> dict[tuple[int, int], QColor]:
    points = {
        "foundation": {FOUNDATION_POINT: FOUNDATION_COLORS[state]},
        "eyes": {EYES_POINT: EYE_COLORS[state]},
        "cheeks": {(12, 12): CHEEK_COLORS[state]},
        "lips": {(16, 16): LIP_COLORS[state]},
    }
    if state == CLOSED_STATE and slot == "foundation":
        points[slot][OUTSIDE_POINT] = LEAK_COLOR
    return points[slot]


def _write_fixture(
    root: Path,
    *,
    schema: str,
    missing_foundation_state: str | None = None,
) -> tuple[dict, str]:
    _app()
    root.mkdir(parents=True, exist_ok=True)
    body = _record(root, "body.rgba.png", _png({BODY_POINT: BASE_COLOR}))
    closed = _record(
        root,
        "motion/closed.rgba.png",
        _png({FOUNDATION_POINT: PATCH_COLOR, EYES_POINT: PATCH_COLOR}),
    )
    speech = _record(root, "motion/speech.rgba.png", _png({}))
    expected_slots = (
        FOUNDATION_COSMETIC_SLOTS if schema == FOUNDATION_SCHEMA else COSMETIC_SLOTS
    )
    cosmetics: dict[str, dict[str, dict[str, str]]] = {}
    for state in COSMETIC_STATES:
        cosmetics[state] = {}
        for slot in expected_slots:
            if state == missing_foundation_state and slot == "foundation":
                continue
            relative = f"cosmetics/{state}/{slot}.rgba.png"
            cosmetics[state][slot] = _record(
                root,
                relative,
                _png(_cosmetic_points(state, slot)),
            )
    manifest = {
        "schema": schema,
        "source_sha256": APPROVED_SOURCE_SHA256,
        "native_body_sha256": body["sha256"],
        "native_body": body,
        "closed": closed,
        "speech": speech,
        "cosmetics": cosmetics,
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest, body["sha256"]


def _rewrite(root: Path, manifest: dict) -> None:
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )


def _pixel(pixmap: QPixmap, point: tuple[int, int]) -> QColor:
    return pixmap.toImage().pixelColor(*point)


def test_v1_keeps_the_three_slot_contract(tmp_path: Path) -> None:
    root = tmp_path / "v1"
    _, body_sha = _write_fixture(root, schema=SCHEMA)

    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)

    assert assets.cosmetic_slots == COSMETIC_SLOTS
    assert _pixel(assets.cosmetic(SPEECH_CLOSED_STATE, "eyes"), EYES_POINT) == EYE_COLORS[CLOSED_STATE]
    with pytest.raises(ValueError, match="Unsupported reviewed pose cosmetic selection"):
        assets.cosmetic(SPEECH_CLOSED_STATE, "foundation")


def test_v2_requires_and_exposes_four_slots_for_every_state(tmp_path: Path) -> None:
    root = tmp_path / "v2"
    _, body_sha = _write_fixture(root, schema=FOUNDATION_SCHEMA)

    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)

    assert assets.cosmetic_slots == FOUNDATION_COSMETIC_SLOTS
    for state in COSMETIC_STATES:
        for slot in FOUNDATION_COSMETIC_SLOTS:
            assert _pixel(assets.cosmetic(state, slot), BODY_POINT).alpha() == TRANSPARENT_ALPHA
    assert (
        _pixel(assets.cosmetic(SPEECH_CLOSED_STATE, "foundation"), FOUNDATION_POINT)
        == FOUNDATION_COLORS[SPEECH_STATE]
    )
    assert (
        _pixel(assets.cosmetic(SPEECH_CLOSED_STATE, "eyes"), EYES_POINT)
        == EYE_COLORS[CLOSED_STATE]
    )
    assert (
        _pixel(assets.cosmetic(SPEECH_CLOSED_STATE, "cheeks"), (12, 12))
        == CHEEK_COLORS[REST_STATE]
    )
    assert (
        _pixel(assets.cosmetic(SPEECH_CLOSED_STATE, "lips"), (16, 16))
        == LIP_COLORS[SPEECH_STATE]
    )


@pytest.mark.parametrize("state", COSMETIC_STATES)
def test_v2_rejects_a_missing_foundation_state(tmp_path: Path, state: str) -> None:
    root = tmp_path / f"missing-{state}"
    _, body_sha = _write_fixture(
        root,
        schema=FOUNDATION_SCHEMA,
        missing_foundation_state=state,
    )

    with pytest.raises(ValueError, match="Incomplete reviewed pose motion cosmetics"):
        load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)


def test_v2_rejects_an_unknown_cosmetic_slot(tmp_path: Path) -> None:
    root = tmp_path / "unknown-slot"
    manifest, body_sha = _write_fixture(root, schema=FOUNDATION_SCHEMA)
    manifest["cosmetics"][REST_STATE]["unknown"] = manifest["cosmetics"][REST_STATE]["eyes"]
    _rewrite(root, manifest)

    with pytest.raises(ValueError, match="Incomplete reviewed pose motion cosmetics"):
        load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)


@pytest.mark.parametrize("state", COSMETIC_STATES)
def test_v2_verifies_each_foundation_sha256(tmp_path: Path, state: str) -> None:
    root = tmp_path / f"tampered-{state}"
    manifest, body_sha = _write_fixture(root, schema=FOUNDATION_SCHEMA)
    relative = manifest["cosmetics"][state]["foundation"]["path"]
    (root / Path(*relative.split("/"))).write_bytes(b"tampered foundation")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)


class _StrengthProbe(ReviewedPoseOverlayMixin):
    def __init__(self, selection: SimpleNamespace) -> None:
        self._store = Path(".")
        self.selection = selection

    def _selected_variant(self, category: str, selection: object) -> None:
        del category, selection


ALL_SLOTS = frozenset(FOUNDATION_COSMETIC_SLOTS)
ALL_FULL = dict.fromkeys(FOUNDATION_COSMETIC_SLOTS, FULL_INTENSITY)
PER_SLOT = {"foundation": ZERO_INTENSITY, "eyes": 0.25, "cheeks": 0.5, "lips": 0.75}


@pytest.mark.parametrize(
    ("pack_id", "variant_id", "intensity", "multipliers", "expected"),
    (
        ("builtin", "none", FULL_INTENSITY, ALL_FULL, dict.fromkeys(ALL_SLOTS, ZERO_INTENSITY)),
        (
            BUILTIN_MAKEUP_PACK_ID,
            "classic",
            ZERO_INTENSITY,
            ALL_FULL,
            dict.fromkeys(ALL_SLOTS, ZERO_INTENSITY),
        ),
        (
            BUILTIN_MAKEUP_PACK_ID,
            "light",
            FULL_INTENSITY,
            ALL_FULL,
            dict.fromkeys(ALL_SLOTS, LIGHT_STRENGTH),
        ),
        (BUILTIN_MAKEUP_PACK_ID, "classic", FULL_INTENSITY, PER_SLOT, PER_SLOT),
    ),
    ids=("bare", "removed", "light-once", "per-slot"),
)
def test_native_foundation_strengths_cover_bare_removal_slot_and_light_semantics(
    monkeypatch: pytest.MonkeyPatch,
    pack_id: str,
    variant_id: str,
    intensity: float,
    multipliers: dict[str, float],
    expected: dict[str, float],
) -> None:
    selection = SimpleNamespace(
        effective_pack_id=pack_id,
        effective_item_id="face",
        effective_variant_id=variant_id,
    )
    probe = _StrengthProbe(selection)
    monkeypatch.setattr(overlay_module, "resolve_active_selection", lambda *_: selection)
    monkeypatch.setattr(overlay_module, "read_makeup_intensity", lambda *_: intensity)
    monkeypatch.setattr(
        overlay_module,
        "read_makeup_slot_intensities",
        lambda *_args, **_kwargs: multipliers,
    )

    strengths = probe._native_cosmetic_strengths(slots=ALL_SLOTS)

    assert strengths is not None
    for slot in FOUNDATION_COSMETIC_SLOTS:
        assert strengths[slot] == pytest.approx(expected[slot])


class _OrderedAssets:
    cosmetic_slots = FOUNDATION_COSMETIC_SLOTS

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._layers = {
            "foundation": _point_pixmap(FOUNDATION_POINT, QColor("#c59b72")),
            "eyes": _point_pixmap(FOUNDATION_POINT, QColor("#e13f65")),
            "cheeks": _point_pixmap((12, 12), QColor(0, 0, 0, TRANSPARENT_ALPHA)),
            "lips": _point_pixmap((16, 16), QColor(0, 0, 0, TRANSPARENT_ALPHA)),
        }

    def cosmetic(self, state: str, slot: str) -> QPixmap:
        self.calls.append(slot)
        assert state == REST_STATE
        return self._layers[slot]


def _point_pixmap(point: tuple[int, int], color: QColor, *, dimension: int = 32) -> QPixmap:
    return QPixmap.fromImage(_image({point: color}, dimension=dimension))


def _image(
    points: dict[tuple[int, int], QColor],
    *,
    dimension: int,
    fill: QColor | None = None,
) -> QImage:
    image = QImage(dimension, dimension, QImage.Format.Format_RGBA8888)
    image.fill(fill if fill is not None else QColor(0, 0, 0, TRANSPARENT_ALPHA))
    for point, color in points.items():
        image.setPixelColor(*point, color)
    return image


class _OrderProbe(ReviewedPoseOverlayMixin):
    def _native_cosmetic_strengths(self, *, slots: frozenset[str]) -> dict[str, float]:
        return dict.fromkeys(slots, FULL_INTENSITY)


def test_foundation_is_painted_before_eye_makeup() -> None:
    _app()
    assets = _OrderedAssets()
    frame = QPixmap.fromImage(_image({}, dimension=32, fill=QColor("#19212b")))

    result = _OrderProbe()._paint_native_cosmetics(frame, assets, REST_STATE)

    assert assets.calls == list(FOUNDATION_COSMETIC_SLOTS)
    assert _pixel(result, FOUNDATION_POINT) == QColor("#e13f65")


class _BlinkProbe(ReviewedPoseOverlayMixin):
    def __init__(self, assets: object) -> None:
        self.assets = assets

    def _native_motion(self, view_id: str) -> object:
        del view_id
        return self.assets

    def _native_cosmetic_strengths(self, *, slots: frozenset[str]) -> dict[str, float]:
        return dict.fromkeys(slots, FULL_INTENSITY)


def test_closed_native_blink_paints_foundation_and_preserves_outside_patch(
    tmp_path: Path,
) -> None:
    root = tmp_path / "blink-v2"
    _, body_sha = _write_fixture(root, schema=FOUNDATION_SCHEMA)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)
    base = QPixmap.fromImage(
        _image({MOUTH_POINT: MOUTH_COLOR}, dimension=DIMENSION, fill=BASE_COLOR)
    )

    result = _BlinkProbe(assets).render_native_blink(
        base,
        "cheek-rest",
        eye_state=CLOSED_STATE,
    )

    assert result is not None
    assert _pixel(result, FOUNDATION_POINT) == FOUNDATION_COLORS[CLOSED_STATE]
    assert _pixel(result, EYES_POINT) == EYE_COLORS[CLOSED_STATE]
    assert _pixel(result, OUTSIDE_POINT) == BASE_COLOR
    assert _pixel(result, MOUTH_POINT) == MOUTH_COLOR
