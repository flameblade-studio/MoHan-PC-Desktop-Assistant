"""Contract tests for v3 source-bound makeup variants."""

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
    COSMETIC_VARIANTS,
    DIMENSION,
    FOUNDATION_COSMETIC_SLOTS,
    FOUNDATION_SCHEMA,
    PATCH_STATES,
    SCHEMA,
    VARIANT_SCHEMA,
    load_reviewed_pose_motion,
)
from infrastructure.reviewed_pose_overlay import ReviewedPoseOverlayMixin


POINT = (19, 19)
STATE_INDEX = {state: index for index, state in enumerate(COSMETIC_STATES)}
SLOT_INDEX = {slot: index for index, slot in enumerate(FOUNDATION_COSMETIC_SLOTS)}
VARIANT_INDEX = {variant: index for index, variant in enumerate(COSMETIC_VARIANTS)}


@pytest.fixture(scope="module", autouse=True)
def _qt_application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _png(color: QColor, *, point: tuple[int, int] = POINT) -> bytes:
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
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


def _color(variant: str, state: str, slot: str) -> QColor:
    value = (
        VARIANT_INDEX[variant] * 100
        + STATE_INDEX[state] * 10
        + SLOT_INDEX[slot]
    )
    return QColor(10 + value, 20 + value, 30 + value, 255)


def _write_v3_fixture(root: Path) -> tuple[dict, str]:
    body = _record(root, "body.rgba.png", _png(QColor("#182838")))
    patches = {
        state: _record(
            root,
            f"motion/{state}.rgba.png",
            _png(QColor("red" if state == "closed" else "blue")),
        )
        for state in PATCH_STATES
    }
    cosmetics: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
    for variant in COSMETIC_VARIANTS:
        variant_states: dict[str, dict[str, dict[str, str]]] = {}
        for state in COSMETIC_STATES:
            variant_states[state] = {
                slot: _record(
                    root,
                    f"cosmetics/{variant}/{state}/{slot}.rgba.png",
                    _png(_color(variant, state, slot)),
                )
                for slot in FOUNDATION_COSMETIC_SLOTS
            }
        cosmetics[variant] = variant_states
    manifest = {
        "schema": VARIANT_SCHEMA,
        "source_sha256": APPROVED_SOURCE_SHA256,
        "native_body_sha256": body["sha256"],
        "native_body": body,
        **patches,
        "cosmetics": cosmetics,
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest, body["sha256"]


def _write_legacy_fixture(root: Path, schema: str) -> str:
    body = _record(root, "body.rgba.png", _png(QColor("#182838")))
    cosmetics: dict[str, dict[str, dict[str, str]]] = {}
    slots = (
        FOUNDATION_COSMETIC_SLOTS
        if schema == FOUNDATION_SCHEMA
        else COSMETIC_SLOTS
    )
    for state in COSMETIC_STATES:
        cosmetics[state] = {
            slot: _record(
                root,
                f"cosmetics/{state}/{slot}.rgba.png",
                _png(_color("classic", state, slot)),
            )
            for slot in slots
        }
    manifest = {
        "schema": schema,
        "source_sha256": APPROVED_SOURCE_SHA256,
        "native_body_sha256": body["sha256"],
        "native_body": body,
        "closed": _record(root, "motion/closed.rgba.png", _png(QColor("red"))),
        "speech": _record(root, "motion/speech.rgba.png", _png(QColor("blue"))),
        "cosmetics": cosmetics,
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return body["sha256"]


def _rewrite(root: Path, manifest: dict) -> None:
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _pixel(pixmap: QPixmap) -> QColor:
    return pixmap.toImage().pixelColor(*POINT)


def test_v3_selects_distinct_variant_layers_and_speech_closed_roles(
    tmp_path: Path,
) -> None:
    root = tmp_path / "v3"
    _, body_sha = _write_v3_fixture(root)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)

    assert tuple(assets.variants or {}) == COSMETIC_VARIANTS
    assert assets.cosmetic_slots == FOUNDATION_COSMETIC_SLOTS
    assert _pixel(assets.cosmetic("rest", "eyes", variant="light")) == _color(
        "light", "rest", "eyes"
    )
    assert _pixel(assets.cosmetic("rest", "eyes", variant="classic")) == _color(
        "classic", "rest", "eyes"
    )
    assert _pixel(assets.cosmetic("rest", "eyes", variant="light")) != _pixel(
        assets.cosmetic("rest", "eyes", variant="classic")
    )
    for slot, state in {
        "foundation": "speech",
        "eyes": "closed",
        "cheeks": "rest",
        "lips": "speech",
    }.items():
        assert _pixel(
            assets.cosmetic("speech-closed", slot, variant="light")
        ) == _color("light", state, slot)


@pytest.mark.parametrize("mutation", ("unknown", "missing-state", "missing-slot"))
def test_v3_rejects_unknown_or_incomplete_variant_shapes(
    tmp_path: Path, mutation: str,
) -> None:
    root = tmp_path / mutation
    manifest, body_sha = _write_v3_fixture(root)
    if mutation == "unknown":
        manifest["cosmetics"]["sepia"] = manifest["cosmetics"]["classic"]
    elif mutation == "missing-state":
        manifest["cosmetics"]["light"].pop("speech")
    else:
        manifest["cosmetics"]["classic"]["rest"].pop("foundation")
    _rewrite(root, manifest)

    with pytest.raises(ValueError, match="variant|cosmetics"):
        load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)


def test_v3_rejects_unknown_variant_and_asset_digest_drift(tmp_path: Path) -> None:
    root = tmp_path / "tampered"
    manifest, body_sha = _write_v3_fixture(root)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)
    with pytest.raises(ValueError, match="variant"):
        assets.cosmetic("rest", "eyes", variant="sepia")

    manifest["cosmetics"]["light"]["rest"]["eyes"]["sha256"] = "0" * 64
    _rewrite(root, manifest)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)


@pytest.mark.parametrize("schema", (SCHEMA, FOUNDATION_SCHEMA))
def test_v1_and_v2_keep_single_map_compatible_with_optional_variant(
    tmp_path: Path, schema: str,
) -> None:
    root = tmp_path / schema.rsplit(".", maxsplit=1)[-1]
    body_sha = _write_legacy_fixture(root, schema)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)

    assert assets.variants is None
    assert _pixel(assets.cosmetic("rest", "eyes")) == _pixel(
        assets.cosmetic("rest", "eyes", variant="light")
    )


class _StrengthProbe(ReviewedPoseOverlayMixin):
    def __init__(self, selection: SimpleNamespace) -> None:
        self._store = Path(".")
        self.selection = selection

    def _selected_variant(self, category: str, selection: object) -> None:
        del category, selection


def test_explicit_v3_variant_strength_does_not_apply_legacy_light_factor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = SimpleNamespace(
        effective_pack_id=BUILTIN_MAKEUP_PACK_ID,
        effective_item_id="face",
        effective_variant_id="light",
    )
    monkeypatch.setattr(
        overlay_module, "resolve_active_selection", lambda *_: selection
    )
    monkeypatch.setattr(overlay_module, "read_makeup_intensity", lambda *_: 1.0)
    monkeypatch.setattr(
        overlay_module,
        "read_makeup_slot_intensities",
        lambda *_args, **_kwargs: dict.fromkeys(FOUNDATION_COSMETIC_SLOTS, 1.0),
    )
    probe = _StrengthProbe(selection)

    explicit = probe._native_cosmetic_strengths(
        slots=frozenset(FOUNDATION_COSMETIC_SLOTS), variant="light"
    )
    legacy = probe._native_cosmetic_strengths(
        slots=frozenset(FOUNDATION_COSMETIC_SLOTS)
    )
    assert explicit == dict.fromkeys(FOUNDATION_COSMETIC_SLOTS, 1.0)
    assert legacy == dict.fromkeys(FOUNDATION_COSMETIC_SLOTS, 0.55)


class _VariantAssets:
    cosmetic_slots = FOUNDATION_COSMETIC_SLOTS
    variants = {"light": object(), "classic": object()}

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def cosmetic(self, state: str, slot: str, *, variant: str = "classic") -> QPixmap:
        self.calls.append((state, slot, variant))
        image = QImage(32, 32, QImage.Format.Format_RGBA8888)
        image.fill(Qt.GlobalColor.transparent)
        return QPixmap.fromImage(image)


class _PaintProbe(ReviewedPoseOverlayMixin):
    def __init__(self) -> None:
        self.seen_variants: list[str | None] = []

    def _native_cosmetic_strengths(
        self, *, slots: frozenset[str], variant: str | None = None
    ) -> dict[str, float]:
        self.seen_variants.append(variant)
        return dict.fromkeys(slots, 1.0)


def test_v3_painter_passes_the_selected_variant_to_every_slot() -> None:
    assets = _VariantAssets()
    frame = QPixmap(32, 32)
    frame.fill(QColor("black"))
    _PaintProbe()._paint_native_cosmetics(frame, assets, "rest", variant="light")

    assert assets.calls == [
        ("rest", slot, "light") for slot in FOUNDATION_COSMETIC_SLOTS
    ]


def test_v3_glamorous_has_independent_blink_and_speech_pigments(tmp_path: Path) -> None:
    root = tmp_path / "glamorous"
    _, body_sha = _write_v3_fixture(root)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)
    for slot, state in {"foundation": "speech", "eyes": "closed", "cheeks": "rest", "lips": "speech"}.items():
        selected = _pixel(assets.cosmetic("speech-closed", slot, variant="glamorous"))
        assert selected == _color("glamorous", state, slot)
        assert selected != _pixel(assets.cosmetic("speech-closed", slot, variant="classic"))


def test_existing_two_variant_v3_still_loads_and_rejects_undeclared_glamorous(tmp_path: Path) -> None:
    root = tmp_path / "existing-v3"
    manifest, body_sha = _write_v3_fixture(root)
    manifest["cosmetics"].pop("glamorous")
    _rewrite(root, manifest)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)
    assert set(assets.variants) == {"light", "classic"}
    with pytest.raises(ValueError, match="variant"):
        assets.cosmetic("rest", "eyes", variant="glamorous")


@pytest.mark.parametrize("schema", (SCHEMA, FOUNDATION_SCHEMA))
def test_legacy_material_cannot_silently_substitute_classic_for_glamorous(tmp_path: Path, schema: str) -> None:
    root = tmp_path / "legacy-glamorous"
    body_sha = _write_legacy_fixture(root, schema)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)
    with pytest.raises(ValueError, match="variant"):
        assets.cosmetic("rest", "eyes", variant="glamorous")


def test_glamorous_native_render_keeps_its_selection_through_speech(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "glamorous-render"
    _, body_sha = _write_v3_fixture(root)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)
    selection = SimpleNamespace(effective_pack_id=BUILTIN_MAKEUP_PACK_ID, effective_variant_id="glamorous")
    monkeypatch.setattr(overlay_module, "resolve_active_selection", lambda *_: selection)
    monkeypatch.setattr(overlay_module, "read_makeup_intensity", lambda *_: 1.0)
    monkeypatch.setattr(overlay_module, "read_makeup_slot_intensities", lambda *_, **kw: dict.fromkeys(kw["slots"], 1.0))

    class NativeProbe(_StrengthProbe):
        def _native_motion(self, view_id):
            return assets

        def native_neutral(self, view_id):
            return assets.native_body.pixmap()

        def apply_appearance(self, frame, view_id):
            return frame

    probe = NativeProbe(selection)
    for speaking, state in ((False, "rest"), (True, "speech")):
        rendered = probe.render_native_state("cheek-rest", speaking=speaking)
        assert _pixel(rendered) == _color("glamorous", state, "lips")
        assert rendered.toImage().pixelColor(0, 0).alpha() == 0
