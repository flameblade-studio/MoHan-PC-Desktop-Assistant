"""Tests for independent hairstyle and headwear selection."""

from __future__ import annotations

lazy import json
lazy import sys
lazy from pathlib import Path

lazy import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from application import wardrobe_appearance_service as service_module
lazy from application.wardrobe_appearance_service import (
    AppearanceOption,
    WardrobeAppearanceService,
)
lazy from domain import outfit_pack
lazy from domain.outfit_pack import InstalledSelection, OutfitPackError

LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
HAIRSTYLE = "hairstyle"
HEADWEAR = "headwear"


def _names(prefix: str) -> dict[str, str]:
    return {language: f"{prefix} {language}" for language in LANGUAGES}


def _selection(
    category: str,
    pack_id: str,
    item_id: str,
    variant_id: str,
) -> InstalledSelection:
    return InstalledSelection(
        category,
        pack_id,
        item_id,
        variant_id,
        _names("Pack"),
        _names("Item"),
        _names("Variant"),
    )


def _patch_catalog(
    monkeypatch,
    selections: tuple[InstalledSelection, ...],
) -> None:
    def by_category(_root: Path, category: str | None = None):
        if category is None:
            return selections
        return tuple(
            selection
            for selection in selections
            if selection.category == category
        )

    monkeypatch.setattr(
        service_module,
        "list_installed_selections",
        by_category,
    )
    monkeypatch.setattr(
        outfit_pack,
        "list_installed_selections",
        by_category,
    )


def _write_active(store: Path, state: dict[str, object]) -> bytes:
    active = store / "active.json"
    active.parent.mkdir(parents=True, exist_ok=True)
    active.write_text(
        json.dumps(state, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return active.read_bytes()


def test_options_have_stable_ids_and_four_language_names(
    monkeypatch,
    tmp_path: Path,
):
    hairstyle = _selection(
        HAIRSTYLE,
        "silk-pack",
        "long-hair",
        "ink",
    )
    headwear = _selection(
        HEADWEAR,
        "silver-pack",
        "hairpin",
        "moon",
    )
    _patch_catalog(monkeypatch, (hairstyle, headwear))
    service = WardrobeAppearanceService(tmp_path / "store")

    expected_none = {
        "zh-TW": '頭飾關閉',
        "zh-CN": '头饰关闭',
        "en": 'Headwear off',
        "ja-JP": '髪飾りオフ',
    }
    for language in LANGUAGES:
        assert service.options(HEADWEAR, language)[0] == AppearanceOption(
            "none",
            expected_none[language],
        )
        assert service.options(HAIRSTYLE, language)[0] == AppearanceOption(
            "silk-pack/long-hair/ink",
            f"Pack {language} · Item {language} · Variant {language}",
        )

    assert service.options(HEADWEAR, "ja-JP")[1] == AppearanceOption(
        "silver-pack/hairpin/moon",
        "Pack ja-JP · Item ja-JP · Variant ja-JP",
    )
    assert service.options(HAIRSTYLE, "unsupported")[0].display_name == (
        "Pack zh-TW · Item zh-TW · Variant zh-TW"
    )
    for alias, canonical in (("ja", "ja-JP"), ("en-US", "en"), ("zh-Hans", "zh-CN")):
        assert service.options(HAIRSTYLE, alias) == service.options(HAIRSTYLE, canonical)
        assert service.options(HEADWEAR, alias) == service.options(HEADWEAR, canonical)


def test_independent_apply_preserves_garment_and_makeup(
    monkeypatch,
    tmp_path: Path,
):
    hairstyle = _selection(
        HAIRSTYLE,
        "silk-pack",
        "long-hair",
        "ink",
    )
    old_hairstyle = _selection(
        HAIRSTYLE,
        "old-hair",
        "old",
        "black",
    )
    headwear = _selection(
        HEADWEAR,
        "silver-pack",
        "hairpin",
        "moon",
    )
    old_headwear = _selection(
        HEADWEAR,
        "old-hat",
        "old",
        "red",
    )
    _patch_catalog(
        monkeypatch,
        (hairstyle, old_hairstyle, headwear, old_headwear),
    )
    store = tmp_path / "store"
    original = {
        "garment": {
            "pack_id": "robe-pack",
            "item_id": "robe",
            "variant_id": "blue",
        },
        "makeup": {
            "pack_id": "mohan.makeup.builtin",
            "item_id": "mohan-signature",
            "variant_id": "classic",
        },
        "hairstyle": {
            "pack_id": "old-hair",
            "item_id": "old",
            "variant_id": "black",
        },
        "headwear": {
            "pack_id": "old-hat",
            "item_id": "old",
            "variant_id": "red",
        },
    }
    _write_active(store, original)
    service = WardrobeAppearanceService(store)

    service.apply(HAIRSTYLE, "silk-pack/long-hair/ink")
    after_hairstyle = json.loads(
        (store / "active.json").read_text(encoding="utf-8")
    )
    assert after_hairstyle["garment"] == original["garment"]
    assert after_hairstyle["makeup"] == original["makeup"]
    assert after_hairstyle["headwear"] == original["headwear"]
    assert after_hairstyle["hairstyle"] == {
        "pack_id": "silk-pack",
        "item_id": "long-hair",
        "variant_id": "ink",
    }
    assert service.active_id(HAIRSTYLE) == "silk-pack/long-hair/ink"

    service.apply(HEADWEAR, "silver-pack/hairpin/moon")
    after_headwear = json.loads(
        (store / "active.json").read_text(encoding="utf-8")
    )
    assert after_headwear["garment"] == original["garment"]
    assert after_headwear["makeup"] == original["makeup"]
    assert after_headwear["hairstyle"] == after_hairstyle["hairstyle"]
    assert after_headwear["headwear"] == {
        "pack_id": "silver-pack",
        "item_id": "hairpin",
        "variant_id": "moon",
    }
    assert service.active_id(HEADWEAR) == "silver-pack/hairpin/moon"


def test_none_headwear_clears_only_headwear(
    monkeypatch,
    tmp_path: Path,
):
    headwear = _selection(
        HEADWEAR,
        "silver-pack",
        "hairpin",
        "moon",
    )
    hairstyle = _selection(
        HAIRSTYLE,
        "silk-pack",
        "long-hair",
        "ink",
    )
    _patch_catalog(monkeypatch, (headwear, hairstyle))
    store = tmp_path / "store"
    original = {
        "garment": {
            "pack_id": "robe-pack",
            "item_id": "robe",
            "variant_id": "blue",
        },
        "makeup": {
            "pack_id": "mohan.makeup.builtin",
            "item_id": "mohan-signature",
            "variant_id": "classic",
        },
        "hairstyle": {
            "pack_id": "silk-pack",
            "item_id": "long-hair",
            "variant_id": "ink",
        },
        "headwear": {
            "pack_id": "silver-pack",
            "item_id": "hairpin",
            "variant_id": "moon",
        },
    }
    _write_active(store, original)
    service = WardrobeAppearanceService(store)

    service.apply(HEADWEAR, "none")

    current = json.loads(
        (store / "active.json").read_text(encoding="utf-8")
    )
    assert current["garment"] == original["garment"]
    assert current["makeup"] == original["makeup"]
    assert current["hairstyle"] == original["hairstyle"]
    assert current["headwear"] == {
        "pack_id": "builtin",
        "item_id": "none",
        "variant_id": "none",
    }
    assert service.active_id(HEADWEAR) == "none"


def test_invalid_options_never_write_active_state(
    monkeypatch,
    tmp_path: Path,
):
    hairstyle = _selection(
        HAIRSTYLE,
        "silk-pack",
        "long-hair",
        "ink",
    )
    _patch_catalog(monkeypatch, (hairstyle,))
    store = tmp_path / "store"
    before = _write_active(
        store,
        {
            "garment": {
                "pack_id": "robe-pack",
                "item_id": "robe",
                "variant_id": "blue",
            },
            "makeup": {
                "pack_id": "mohan.makeup.builtin",
                "item_id": "mohan-signature",
                "variant_id": "classic",
            },
            "hairstyle": {
                "pack_id": "old-hair",
                "item_id": "old",
                "variant_id": "black",
            },
        },
    )
    service = WardrobeAppearanceService(store)

    with pytest.raises(OutfitPackError, match="A hairstyle selection stays active"):
        service.apply(HAIRSTYLE, "none")
    assert (store / "active.json").read_bytes() == before

    with pytest.raises(OutfitPackError, match="not installed"):
        service.apply(HEADWEAR, "unknown/item/variant")
    assert (store / "active.json").read_bytes() == before

    with pytest.raises(OutfitPackError, match="Only hairstyle"):
        service.apply("garment", "anything")
    assert (store / "active.json").read_bytes() == before

    with pytest.raises(OutfitPackError, match="Only hairstyle"):
        service.options("garment")
    with pytest.raises(OutfitPackError, match="Only hairstyle"):
        service.active_id("garment")


def test_malformed_active_state_fails_closed(
    monkeypatch,
    tmp_path: Path,
):
    hairstyle = _selection(
        HAIRSTYLE,
        "silk-pack",
        "long-hair",
        "ink",
    )
    _patch_catalog(monkeypatch, (hairstyle,))
    store = tmp_path / "store"
    active = store / "active.json"
    active.parent.mkdir(parents=True, exist_ok=True)
    active.write_bytes(b"{not-json")
    before = active.read_bytes()
    service = WardrobeAppearanceService(store)

    with pytest.raises(OutfitPackError, match="Provide a supported saved appearance state"):
        service.apply(HAIRSTYLE, "silk-pack/long-hair/ink")
    assert active.read_bytes() == before

    with pytest.raises(OutfitPackError, match="Provide a supported saved appearance state"):
        service.active_id(HAIRSTYLE)
    assert active.read_bytes() == before


def main() -> int:
    return int(pytest.main([__file__, "-q", *sys.argv[1:]]))


if __name__ == "__main__":
    raise SystemExit(main())

