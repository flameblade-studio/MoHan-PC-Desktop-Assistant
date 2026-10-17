"""Contract tests for the MoHan official-look scattered body layers."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy from PIL import Image

lazy from infrastructure.bundled_character_source import LegacyMohanCharacterSource


ROOT = Path(__file__).resolve().parents[1]
BODY_ROOT = ROOT / "assets/characters/mohan/body"
EXPECTED_LAYER_VIEW_COUNT = 203
EXPECTED_LAYER_PNG_COUNT = 186


def _document(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_mohan_body_layers_use_the_lin_keyun_scattered_contract() -> None:
    manifest = _document(BODY_ROOT / "manifest.json")
    source = _document(ROOT / "assets/characters/mohan/pack-source.json")
    layer_views = manifest["layer_views"]
    assert source["body_pack"] == manifest["body_pack"]
    assert source["layer_views"] == layer_views
    assert len(layer_views) == EXPECTED_LAYER_VIEW_COUNT
    cheek_views = (
        "cheek", "cheek-rest", "cheek-happy", "cheek-caught", "cheek-worried",
        "cheek-glance", "cheek-reminder", "happy", "caught", "worried",
        "glance", "reminder",
    )
    assert set(cheek_views) <= set(layer_views)
    assert {
        json.dumps(layer_views[view], sort_keys=True)
        for view in cheek_views
    } == {json.dumps(layer_views["cheek-rest"], sort_keys=True)}

    pngs = sorted(BODY_ROOT.glob("views/*/*.png"))
    assert len(pngs) == EXPECTED_LAYER_PNG_COUNT
    assert {path.name for path in pngs} == {
        "base-hide-mask.png", "body-fix.png", "garment.png",
        "hair-back.png", "hair-front.png", "ornament.png",
    }
    with Image.open(pngs[0]) as image:
        assert image.mode == "RGBA"
        assert image.size in {(1024, 1536), (1254, 1254)}


def test_bundled_source_reads_a_manifest_bound_scattered_layer() -> None:
    source = LegacyMohanCharacterSource(ROOT, body_pack_roots=())
    plan = next(iter(source.character_layer_views.values()))
    record = plan.layers[0]
    payload = source.load_character_layer(record)
    assert hashlib.sha256(payload).hexdigest() == record.sha256


def test_bundled_source_falls_back_to_current_look_when_body_pack_missing() -> None:
    source = LegacyMohanCharacterSource(ROOT, body_pack_roots=())
    assert source.resolved_body_pack is None
    assert source.body_pack_fallback_active
    assert source.body_pack_download_required
    assert source.body_pack_resolution_error is not None
    assert source.body_pack_resolution_error.code == "body_pack_missing"


def test_mohan_builtin_default_remains_the_official_blue_white_ensemble() -> None:
    defaults = _document(ROOT / "assets/characters/mohan/appearance/defaults.json")
    outfit = defaults["outfit"]
    assert outfit == {
        "pack_id": "mohan.official.blue-white-hanfu",
        "ensemble_id": "blue-white-hanfu",
        "native_hair": {"item_id": "loose-hair", "variant_id": "ink-black"},
        "native_headwear": {"item_id": "silver-hairpiece", "variant_id": "silver"},
    }
