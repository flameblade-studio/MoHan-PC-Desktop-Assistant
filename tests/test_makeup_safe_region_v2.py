"""Truth-table coverage for the partial v2 makeup safe-region contract."""

from __future__ import annotations

lazy import hashlib
lazy import os
lazy import sys
lazy from copy import deepcopy
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

lazy import pytest
lazy from PySide6.QtCore import QPoint
lazy from PySide6.QtGui import QColor, QImage
lazy from PySide6.QtWidgets import QApplication
lazy from domain.outfit_pack import REQUIRED_SILHOUETTES, OutfitPackError
lazy from domain.outfit_pack_makeup import (
    FOUNDATION_STATES,
    SAFE_REGION_SCHEMA_V2,
    load_makeup_safe_regions,
    parse_makeup_safe_regions,
    verify_makeup_layers,
)
lazy from infrastructure.image_alpha_regions import visible_alpha_region
lazy from test_outfit_pack import _pack
lazy from test_outfit_pack_makeup import _entry, canvas_for, layer_png, makeup_manifest

STATES = ("rest", "half", "closed")
SLOTS = {
    "eyes": [[10, 10, 10, 10]],
    "cheeks": [[30, 10, 10, 10]],
    "lips": [[50, 10, 10, 10]],
}
MISSING = object()


def _descriptor(path: str, digest: str, canvas: tuple[int, int]) -> dict:
    return {
        "path": path,
        "sha256": digest,
        "width": canvas[0],
        "height": canvas[1],
        "anchor": [0, 0],
    }


def _write_masks(root: Path) -> dict[tuple[int, int], dict[str, dict]]:
    root = root / "assets"
    root.mkdir(parents=True, exist_ok=True)
    result = {}
    for canvas in {(1024, 1536), (1254, 1254)}:
        width, height = canvas
        open_image = QImage(width, height, QImage.Format_RGBA8888)
        open_image.fill(QColor(255, 255, 255, 255))
        closed_image = QImage(width, height, QImage.Format_RGBA8888)
        closed_image.fill(QColor(0, 0, 0, 0))
        open_path = root / f"mask-{width}x{height}-open.png"
        closed_path = root / f"mask-{width}x{height}-closed.png"
        assert open_image.save(str(open_path), "PNG")
        assert closed_image.save(str(closed_path), "PNG")
        open_digest = hashlib.sha256(open_path.read_bytes()).hexdigest()
        closed_digest = hashlib.sha256(closed_path.read_bytes()).hexdigest()
        result[canvas] = {
            "open": _descriptor(f"assets/{open_path.name}", open_digest, canvas),
            "closed": _descriptor(f"assets/{closed_path.name}", closed_digest, canvas),
        }
    return result


def _payload(
    root: Path,
    *,
    foundation_masks: dict | object = MISSING,
    eye_aperture_masks: dict | object = MISSING,
) -> dict:
    masks = _write_masks(root)
    silhouettes = {}
    for silhouette in REQUIRED_SILHOUETTES:
        canvas = canvas_for(silhouette)

        def remap(value: dict) -> dict:
            result = deepcopy(value)
            for state, descriptor in result.items():
                if descriptor.get("path") == "OPEN":
                    result[state] = deepcopy(masks[canvas]["open"])
                elif descriptor.get("path") == "CLOSED":
                    result[state] = deepcopy(masks[canvas]["closed"])
            return result
        entry = {
            "canvas": list(canvas),
            "rig": "assets/rig",
            "slots": deepcopy(SLOTS),
        }
        if foundation_masks is not MISSING:
            entry["foundation_masks"] = remap(deepcopy(foundation_masks))
        if eye_aperture_masks is not MISSING:
            entry["eye_aperture_masks"] = remap(deepcopy(eye_aperture_masks))
        silhouettes[silhouette] = entry
    return {"schema": SAFE_REGION_SCHEMA_V2, "silhouettes": silhouettes}


def _full_maps() -> tuple[dict[str, dict], dict[str, dict]]:
    foundation = {state: {"path": "OPEN"} for state in STATES}
    apertures = {
        "rest": {"path": "OPEN"},
        "half": {"path": "OPEN"},
        "closed": {"path": "CLOSED"},
    }
    return foundation, apertures


def test_partial_v2_truth_table(tmp_path: Path) -> None:
    """Both maps opt in together; every malformed pair fails closed."""
    full_foundation, full_apertures = _full_maps()
    cases = {
        "both_empty_legacy": ({}, {}, True),
        "both_full": (full_foundation, full_apertures, True),
        "missing_foundation": (MISSING, full_apertures, False),
        "missing_aperture": (full_foundation, MISSING, False),
        "single_empty_foundation": ({}, full_apertures, False),
        "single_empty_aperture": (full_foundation, {}, False),
        "incomplete_foundation": ({"rest": {"path": "OPEN"}}, full_apertures, False),
        "incomplete_aperture": (full_foundation, {"rest": {"path": "OPEN"}}, False),
    }
    for name, (foundation, apertures, accepted) in cases.items():
        payload = _payload(tmp_path / name, foundation_masks=foundation, eye_aperture_masks=apertures)
        if accepted:
            parsed = parse_makeup_safe_regions(payload, asset_root=tmp_path / name)
            if foundation:
                assert set(parsed["front-crossed"].foundation_masks) == FOUNDATION_STATES
                assert parsed["front-crossed"].eye_aperture_mask("closed") is not None
            else:
                assert not parsed["front-crossed"].foundation_masks
                assert not parsed["front-crossed"].eye_aperture_masks
        else:
            with pytest.raises(OutfitPackError):
                parse_makeup_safe_regions(payload, asset_root=tmp_path / name)


@pytest.mark.parametrize("state", ("rest", "half"))
def test_open_eye_aperture_cannot_be_empty(tmp_path: Path, state: str) -> None:
    foundation, apertures = _full_maps()
    apertures[state] = {"path": "CLOSED"}
    payload = _payload(tmp_path, foundation_masks=foundation, eye_aperture_masks=apertures)
    with pytest.raises(OutfitPackError, match="requires visible content"):
        parse_makeup_safe_regions(payload, asset_root=tmp_path)


def test_alpha8_mask_produces_nonempty_visible_region() -> None:
    """A faint source pixel remains owned after conversion to a binary region."""
    _app = QApplication.instance() or QApplication([])
    image = QImage(9, 7, QImage.Format_ARGB32)
    image.fill(0)
    image.setPixelColor(3, 4, QColor(0, 0, 0, 127))
    region = visible_alpha_region(image)
    assert not region.isEmpty()
    assert region.boundingRect().getRect() == (3, 4, 1, 1)
    assert region.contains(QPoint(3, 4))
    assert not region.contains(QPoint(0, 0))


def test_foundation_marker_requires_matching_canonical_masks(tmp_path: Path) -> None:
    manifest, assets = makeup_manifest()
    variant = manifest["makeup"][0]["variants"][0]
    variant["foundation_silhouettes"] = ["front-crossed"]
    canvas = canvas_for("front-crossed")
    data = layer_png(canvas, (), QColor(245, 220, 215, 255))
    path = "assets/foundation-front-crossed.png"
    assets[path] = data
    variant["poses"]["front-crossed"].append({
        "slot": "foundation",
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "width": canvas[0],
        "height": canvas[1],
        "anchor": [0, 0],
        "z_order": 3,
    })
    # Complete the marker's required paired eye-state declarations so the
    # archive reaches the safe-region/variant crosscheck under test.
    variant["eye_states"] = {}
    for state in ("half", "closed"):
        poses = {}
        for silhouette in REQUIRED_SILHOUETTES:
            size = canvas_for(silhouette)
            eye_path = f"assets/{state}-{silhouette}-eyes.png"
            eye_data = layer_png(size)
            assets[eye_path] = eye_data
            entries = [_entry(eye_path, eye_data, "eyes", size)]
            if silhouette == "front-crossed":
                state_path = f"assets/{state}-foundation-front-crossed.png"
                assets[state_path] = data
                entries.append({
                    "slot": "foundation",
                    "path": state_path,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "width": size[0],
                    "height": size[1],
                    "anchor": [0, 0],
                    "z_order": 3,
                })
            poses[silhouette] = entries
        variant["eye_states"][state] = poses
    archive = _pack(tmp_path / "marker.mohan-outfit", manifest, assets)
    regions = load_makeup_safe_regions()
    with pytest.raises(OutfitPackError, match="canonical state masks"):
        verify_makeup_layers(archive, regions)


def main() -> int:
    result = pytest.main([__file__, "-q", *sys.argv[1:]])
    if result == 0:
        print("MAKEUP_SAFE_REGION_V2_OK")
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
