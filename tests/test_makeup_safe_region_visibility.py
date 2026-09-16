"""Focused tests for explicit native safe-region visibility declarations."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import sys
lazy from copy import deepcopy
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import pytest
lazy from PySide6.QtGui import QColor, QImage
lazy from PySide6.QtWidgets import QApplication
lazy from domain.outfit_pack import MAKEUP_CANVASES, REQUIRED_SILHOUETTES, OutfitPackError
lazy from domain.outfit_pack_makeup import (
    FOUNDATION_STATES,
    HALF_BODY_RIGS,
    MAKEUP_SLOTS,
    SAFE_REGION_SCHEMA_V2,
    load_makeup_safe_regions,
)

MASK_DIR = "assets/native-geometry"
EVIDENCE = "I06/nonvisible-stage/receipt.json#native-geometry"
VISIBLE = "visible"
EMPTY = "empty"


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _descriptor(path: str, digest: str, canvas: tuple[int, int]) -> dict[str, object]:
    return {
        "path": path,
        "sha256": digest,
        "width": canvas[0],
        "height": canvas[1],
        "anchor": [0, 0],
    }


def _write_sources(root: Path) -> dict[tuple[int, int], dict[str, dict[str, object]]]:
    source_root = root / MASK_DIR
    source_root.mkdir(parents=True, exist_ok=True)
    sources: dict[tuple[int, int], dict[str, dict[str, object]]] = {}
    for canvas in MAKEUP_CANVASES.values():
        visible_image = QImage(canvas[0], canvas[1], QImage.Format_RGBA8888)
        visible_image.fill(QColor(255, 255, 255, 255))
        empty_image = QImage(canvas[0], canvas[1], QImage.Format_RGBA8888)
        empty_image.fill(QColor(0, 0, 0, 0))
        visible_path = source_root / f"visible-{canvas[0]}x{canvas[1]}.png"
        empty_path = source_root / f"empty-{canvas[0]}x{canvas[1]}.png"
        assert visible_image.save(str(visible_path), "PNG")
        assert empty_image.save(str(empty_path), "PNG")
        sources[canvas] = {
            VISIBLE: _descriptor(
                f"{MASK_DIR}/{visible_path.name}",
                hashlib.sha256(visible_path.read_bytes()).hexdigest(),
                canvas,
            ),
            EMPTY: _descriptor(
                f"{MASK_DIR}/{empty_path.name}",
                hashlib.sha256(empty_path.read_bytes()).hexdigest(),
                canvas,
            ),
        }
    return sources


def _visibility(
    *,
    foundation_nonvisible: bool,
    aperture_nonvisible: bool,
) -> dict[str, dict[str, dict[str, object]]]:
    return {
        state: {
            "foundation_coverage": {
                "nonvisible": foundation_nonvisible,
                "evidence": EVIDENCE,
            },
            "eye_aperture": {
                "nonvisible": aperture_nonvisible,
                "evidence": EVIDENCE,
            },
        }
        for state in sorted(FOUNDATION_STATES)
    }


def _payload(
    root: Path,
    *,
    native_visibility: bool = True,
) -> tuple[dict[str, object], dict[tuple[int, int], dict[str, dict[str, object]]]]:
    sources = _write_sources(root)
    silhouettes: dict[str, dict[str, object]] = {}
    for silhouette in REQUIRED_SILHOUETTES:
        canvas_kind = "half-body" if silhouette in HALF_BODY_RIGS else "full-body"
        canvas = MAKEUP_CANVASES[canvas_kind]
        foundation_kind = EMPTY if silhouette == "yaw+105-pitch+00" else VISIBLE
        aperture_kind = EMPTY if silhouette == "front-exasperated" else VISIBLE
        foundation = {
            state: deepcopy(sources[canvas][foundation_kind])
            for state in FOUNDATION_STATES
        }
        apertures = {
            state: deepcopy(sources[canvas][aperture_kind])
            for state in FOUNDATION_STATES
        }
        if silhouette == "front-exasperated":
            aperture_visibility = True
        else:
            aperture_visibility = False
        entry: dict[str, object] = {
            "canvas": list(canvas),
            "rig": "assets/native-geometry/rig",
            "slots": {slot: [] for slot in MAKEUP_SLOTS},
            "foundation_masks": foundation,
            "eye_aperture_masks": apertures,
        }
        if native_visibility:
            entry["native_visibility"] = _visibility(
                foundation_nonvisible=foundation_kind == EMPTY,
                aperture_nonvisible=aperture_visibility,
            )
        silhouettes[silhouette] = entry
    return {"schema": SAFE_REGION_SCHEMA_V2, "silhouettes": silhouettes}, sources


def _write_document(root: Path, payload: dict[str, object]) -> Path:
    document = root / "assets" / "makeup-safe-regions.json"
    document.parent.mkdir(parents=True, exist_ok=True)
    document.write_text(json.dumps(payload), encoding="utf-8")
    return document


def test_real_loader_accepts_proven_zero_geometry(qapp: QApplication, tmp_path: Path) -> None:
    payload, sources = _payload(tmp_path)
    document = _write_document(tmp_path, payload)

    parsed = load_makeup_safe_regions(document)

    back_mask = parsed["yaw+105-pitch+00"].foundation_mask("rest")
    exasperated_aperture = parsed["front-exasperated"].eye_aperture_mask("rest")
    visible_mask = parsed["yaw+090-pitch+00"].foundation_mask("rest")
    assert back_mask is not None and not any(back_mask.alpha)
    assert exasperated_aperture is not None and not any(exasperated_aperture.alpha)
    assert visible_mask is not None and any(visible_mask.alpha)
    assert sources[(1024, 1536)][EMPTY]["sha256"] == back_mask.sha256


@pytest.mark.parametrize(
    ("mask_kind", "declared_nonvisible", "expected_message"),
    (
        ("foundation_masks", True, "marked nonvisible"),
        ("eye_aperture_masks", False, "requires visible content"),
    ),
)
def test_visibility_declaration_must_match_alpha(
    qapp: QApplication,
    tmp_path: Path,
    mask_kind: str,
    declared_nonvisible: bool,
    expected_message: str,
) -> None:
    payload, _sources = _payload(tmp_path)
    target_name = "front-crossed" if mask_kind == "foundation_masks" else "front-exasperated"
    target = payload["silhouettes"][target_name]
    assert isinstance(target, dict)
    state_map = target["native_visibility"]
    assert isinstance(state_map, dict)
    state_map["rest"]["foundation_coverage" if mask_kind == "foundation_masks" else "eye_aperture"][
        "nonvisible"
    ] = declared_nonvisible
    document = _write_document(tmp_path, payload)
    with pytest.raises(OutfitPackError, match=expected_message):
        load_makeup_safe_regions(document)


def test_absent_visibility_keeps_legacy_empty_mask_gate(
    qapp: QApplication,
    tmp_path: Path,
) -> None:
    payload, _sources = _payload(tmp_path, native_visibility=False)
    document = _write_document(tmp_path, payload)
    with pytest.raises(OutfitPackError, match="requires visible content"):
        load_makeup_safe_regions(document)
