"""LEGACY_MAKEUP_SILHOUETTES: an optional, additive makeup-only silhouette set.

Proves (2026-09-29 schema addition, run as a plain script -- see the module
docstring in domain/outfit_pack.py for why): an existing pack/safe-region
document with no legacy key parses and verifies exactly as before; a pack
that DOES declare a legacy key parses and verifies; and a legacy-keyed layer
painting outside its (candidate) safe region is rejected exactly like a
required-silhouette one already is.
"""
from __future__ import annotations

lazy import hashlib
lazy import io
lazy import json
lazy import os
lazy import shutil
lazy import sys
lazy import zipfile
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import pytest
lazy from PIL import Image

lazy from domain.outfit_pack import LEGACY_MAKEUP_SILHOUETTES, inspect_outfit_pack
lazy from domain.outfit_pack_makeup import (
    SAFE_REGION_PATH,
    load_makeup_safe_regions,
    verify_makeup_layers,
)

OFFICIAL_PACK = ROOT / "assets/official-packs/mohan.makeup.builtin.mohan-outfit"


def test_legacy_makeup_silhouettes_are_exactly_two_optional_keys() -> None:
    assert set(LEGACY_MAKEUP_SILHOUETTES) == {"cheek-rest-legacy", "left-neutral-legacy"}


def test_existing_pack_without_a_legacy_key_is_unaffected() -> None:
    """The shipped pack declares no legacy silhouette; both real production
    validators must behave exactly as they did before this schema addition."""
    pack = inspect_outfit_pack(OFFICIAL_PACK)
    assert len(pack.items) >= 1
    verify_makeup_layers(OFFICIAL_PACK)  # real, shipped safe-region document


def _asset_root_with_candidate_safe_regions(tmp_path: Path, legacy_rects: dict) -> Path:
    """<root>/assets/makeup-safe-regions.json plus every foundation/eye-
    aperture mask the document's OTHER (required) silhouettes reference --
    load_makeup_safe_regions() resolves those paths relative to this root."""
    document = json.loads(SAFE_REGION_PATH.read_text(encoding="utf-8"))
    for legacy_key, source_key in (("cheek-rest-legacy", "cheek-rest"), ("left-neutral-legacy", "left-neutral")):
        entry = json.loads(json.dumps(document["silhouettes"][source_key]))
        entry["slots"] = legacy_rects[legacy_key]
        document["silhouettes"][legacy_key] = entry
    asset_root = tmp_path / "asset-root"
    assets_dir = asset_root / "assets"
    assets_dir.mkdir(parents=True)
    (assets_dir / "makeup-safe-regions.json").write_text(json.dumps(document), encoding="utf-8")
    for entry in document["silhouettes"].values():
        for field in ("foundation_masks", "eye_aperture_masks"):
            for descriptor in entry.get(field, {}).values():
                relative = Path(*descriptor["path"].split("/"))
                target = asset_root / relative
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / relative, target)
    return asset_root / "assets" / "makeup-safe-regions.json"


def _solid_layer(box: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> bytes:
    layer = Image.new("RGBA", (1254, 1254), (0, 0, 0, 0))
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            layer.putpixel((x, y), color)
    buffer = io.BytesIO()
    layer.save(buffer, "PNG")
    return buffer.getvalue()


def _pack_with_one_legacy_layer(
    tmp_path: Path, *, cheek_color: tuple[int, int, int, int], cheek_box: tuple[int, int, int, int] = (600, 600, 620, 620),
) -> Path:
    """A copy of the real shipped pack with one extra silhouette: 'classic'
    gets a full eyes/cheeks/lips declaration for the new "cheek-rest-legacy"
    silhouette (MAKEUP_SLOTS requires exactly those three); eyes and lips sit
    safely inside every candidate safe-region used by the tests below, only
    the cheeks box is varied to prove the escape/no-escape cases."""
    with zipfile.ZipFile(OFFICIAL_PACK) as src:
        manifest = json.loads(src.read("manifest.json"))
        classic = next(v for v in manifest["makeup"][0]["variants"] if v["id"] == "classic")
        payloads = {
            "cheeks": (_solid_layer(cheek_box, cheek_color), "assets/legacy-test-cheeks.png", 0),
            "eyes": (_solid_layer((420, 370, 440, 390), (10, 10, 10, 255)), "assets/legacy-test-eyes.png", 1),
            "lips": (_solid_layer((520, 570, 540, 590), (200, 60, 60, 255)), "assets/legacy-test-lips.png", 2),
        }
        classic.setdefault("poses", {})["cheek-rest-legacy"] = [
            {
                "anchor": [0, 0], "height": 1254, "width": 1254, "path": arcname,
                "sha256": hashlib.sha256(payload).hexdigest(), "slot": slot, "z_order": z,
            }
            for slot, (payload, arcname, z) in payloads.items()
        ]
        out_path = tmp_path / OFFICIAL_PACK.name
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in src.infolist():
                if item.filename == "manifest.json":
                    continue
                dst.writestr(item, src.read(item.filename))
            for payload, arcname, _z in payloads.values():
                dst.writestr(arcname, payload)
            dst.writestr("manifest.json", json.dumps(manifest))
    return out_path


def test_pack_with_a_legacy_key_parses_and_verifies(tmp_path: Path) -> None:
    legacy_rects = {
        "cheek-rest-legacy": {"cheeks": [[550, 550, 150, 150]], "eyes": [[400, 350, 300, 200]], "lips": [[500, 550, 200, 150]]},
        "left-neutral-legacy": {"cheeks": [[550, 550, 150, 150]], "eyes": [[400, 350, 300, 200]], "lips": [[500, 550, 200, 150]]},
    }
    safe_regions_path = _asset_root_with_candidate_safe_regions(tmp_path, legacy_rects)
    pack_path = _pack_with_one_legacy_layer(tmp_path, cheek_color=(255, 200, 200, 255))

    pack = inspect_outfit_pack(pack_path)
    assert len(pack.items) >= 1
    regions = load_makeup_safe_regions(safe_regions_path)
    verify_makeup_layers(pack_path, regions=regions)  # must not raise


def test_legacy_layer_escaping_its_safe_region_is_rejected(tmp_path: Path) -> None:
    legacy_rects = {
        "cheek-rest-legacy": {"cheeks": [[0, 0, 10, 10]], "eyes": [[400, 350, 300, 200]], "lips": [[500, 550, 200, 150]]},
        "left-neutral-legacy": {"cheeks": [[0, 0, 10, 10]], "eyes": [[400, 350, 300, 200]], "lips": [[500, 550, 200, 150]]},
    }
    safe_regions_path = _asset_root_with_candidate_safe_regions(tmp_path, legacy_rects)
    # The pack's cheeks pixels (600..620, 600..620) fall entirely outside the
    # tiny (0,0,10,10) rectangle declared above for this test.
    pack_path = _pack_with_one_legacy_layer(tmp_path, cheek_color=(255, 200, 200, 255))

    regions = load_makeup_safe_regions(safe_regions_path)
    with pytest.raises(Exception, match="cheeks safe region"):
        verify_makeup_layers(pack_path, regions=regions)
