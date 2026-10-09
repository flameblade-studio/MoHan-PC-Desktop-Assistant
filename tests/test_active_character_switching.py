from __future__ import annotations

lazy import logging
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest
lazy from PySide6.QtGui import QColor, QImage
lazy from PySide6.QtWidgets import QApplication

lazy from application import service_container
lazy from application import wardrobe_service as wardrobe_module
lazy from application.wardrobe_appearance_service import WardrobeAppearanceService
lazy from application.wardrobe_service import BUILTIN_OUTFIT_ID, WardrobeService
lazy from domain.character_source import (
    active_character_source,
    character_voice_profile,
)
lazy from domain.constants import CHARACTER_ASSET_PATHS
lazy from domain.outfit_pack import resolve_active_selection
lazy from domain.outfit_pack_official import (
    BUILTIN_MAKEUP_PACK_ID,
    OFFICIAL_NATIVE_HAIR_ALIAS,
    OFFICIAL_NATIVE_HEADWEAR_ALIAS,
    OFFICIAL_OUTFIT_PACK_ID,
    builtin_makeup_pack_id,
    builtin_outfit_resolution,
    official_native_hair_alias,
    official_native_headwear_alias,
    official_outfit_ensemble_id,
    official_outfit_pack_id,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
EXPECTED_VOICE_VOLUME_PERCENT = 125


@pytest.fixture(autouse=True)
def _restore_default_character(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(service_container.ACTIVE_CHARACTER_ENV, raising=False)
    service_container.create_character_source("mohan")
    yield
    service_container.create_character_source("mohan")


def _app() -> object:
    return QApplication.instance() or QApplication([])


def test_composition_root_selects_default_explicit_and_rejects_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default = service_container.create_default_character_source()
    assert default.character_id == "mohan"

    monkeypatch.setenv(service_container.ACTIVE_CHARACTER_ENV, "lin-keyun")
    selected = service_container.create_default_character_source()
    assert selected.character_id == "lin-keyun"
    assert active_character_source() is selected

    with pytest.raises(RuntimeError, match="Unsupported active character"):
        service_container.create_character_source("unknown")
    assert active_character_source() is selected


def test_linkeyun_source_exposes_persona_dialogue_voice_and_appearance() -> None:
    source = service_container.create_character_source("lin-keyun")
    expected_identity = {
        "zh-TW": ("林可芸", "劍主"),
        "zh-CN": ("林可芸", "剑主"),
        "en": ("Lin Keyun", "Swordmaster"),
        "ja-JP": ("林可芸", "剣主"),
    }
    for language in LANGUAGES:
        name, title = expected_identity[language]
        assert source.persona.display_name(language) == name
        assert source.persona.default_user_title(language) == title
        prompt = source.persona.persona_prompt(language)
        assert prompt.strip()
        assert "墨寒" not in prompt and "MoHan" not in prompt
        line = source.persona.dialogue_line(
            language,
            "welcome.general",
        )
        assert "{user_title}" in line
        assert "{user_title}" not in line.format(user_title=title)

    voice = source.voice.voice_profile
    assert character_voice_profile() is voice
    assert set(voice.instructions) == set(LANGUAGES)
    assert voice.default_provider == "system-local"
    assert voice.default_rate == -1
    assert voice.default_volume_percent == EXPECTED_VOICE_VOLUME_PERCENT
    assert voice.default_tts_voice == "coral"

    appearance = source.appearance.appearance_defaults
    assert appearance.outfit_pack_id == "linkeyun.official.modern-office"
    assert appearance.outfit_ensemble_id == "modern-office"
    assert (appearance.native_hair.item_id, appearance.native_hair.variant_id) == (
        "long-hair",
        "dark-brown",
    )
    assert appearance.native_headwear is None
    assert official_outfit_pack_id() == appearance.outfit_pack_id
    assert official_outfit_ensemble_id() == appearance.outfit_ensemble_id
    assert builtin_makeup_pack_id() == appearance.makeup_pack_id
    assert official_native_hair_alias() == (
        appearance.outfit_pack_id,
        "long-hair",
        "dark-brown",
    )
    assert official_native_headwear_alias() is None


def test_missing_linkeyun_outfit_falls_back_to_bare_base_with_diagnostic(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service_container.create_character_source("lin-keyun")
    store = tmp_path / "outfits"
    official_root = ROOT / "assets" / "official-packs"
    service = WardrobeService(store, official_pack_root=official_root)

    with caplog.at_level(logging.WARNING, logger="mohan.character_appearance"):
        outfits = service.outfits("en")

    assert len(outfits) == 1
    assert outfits[0].outfit_id == BUILTIN_OUTFIT_ID
    assert outfits[0].built_in
    assert outfits[0].ensemble is None
    assert "Lin Keyun" in outfits[0].display_name
    assert "linkeyun.official.modern-office" in caplog.text
    assert "using the bare base" in caplog.text
    assert OFFICIAL_OUTFIT_PACK_ID not in {outfit.outfit_id for outfit in outfits}

    garment = resolve_active_selection(
        store,
        "garment",
        official_pack_root=official_root,
    )
    assert garment.status == "builtin"
    assert garment.effective_pack_id == "builtin"
    assert garment.effective_pack_id != OFFICIAL_OUTFIT_PACK_ID

    headwear = WardrobeAppearanceService(
        store,
        official_pack_root=official_root,
    ).options("headwear", "en")
    assert tuple(option.option_id for option in headwear) == ("none",)


def test_installed_linkeyun_official_ensemble_is_only_the_builtin_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_container.create_character_source("lin-keyun")
    names = {
        "zh-TW": "現代辦公",
        "zh-CN": "现代办公",
        "en": "Modern Office",
        "ja-JP": "モダンオフィス",
    }
    official = SimpleNamespace(
        pack_id=official_outfit_pack_id(),
        ensemble_id=official_outfit_ensemble_id(),
        pack_display_names=names,
        ensemble_display_names=names,
        selections=(
            SimpleNamespace(
                category="garment",
                item_id="office-suit",
                variant_id="navy",
            ),
            SimpleNamespace(
                category="headwear",
                item_id=None,
                variant_id=None,
            ),
        ),
        autonomous_profile=None,
    )
    custom = SimpleNamespace(
        pack_id="example.custom",
        ensemble_id="casual",
        pack_display_names=names,
        ensemble_display_names=names,
        selections=(),
        autonomous_profile=None,
    )
    monkeypatch.setattr(
        wardrobe_module,
        "list_installed_ensembles",
        lambda *_args, **_kwargs: (official, custom),
    )
    monkeypatch.setattr(
        wardrobe_module,
        "list_installed_selections",
        lambda *_args, **_kwargs: (),
    )
    monkeypatch.setattr(
        wardrobe_module,
        "list_stale_body_profile_packs",
        lambda *_args, **_kwargs: (),
    )

    outfits = WardrobeService(tmp_path / "outfits").outfits("en")
    assert [outfit.outfit_id for outfit in outfits] == [
        BUILTIN_OUTFIT_ID,
        "example.custom/casual",
    ]
    assert outfits[0].ensemble is official
    assert all(outfit.outfit_id != official.pack_id for outfit in outfits[1:])
    assert builtin_outfit_resolution(
        "headwear",
        ("builtin", "builtin", "builtin"),
        (official,),
    ) == ("builtin", ("builtin", "none", "none"))


def test_linkeyun_official_mask_loader_uses_the_active_pack_id(
    tmp_path: Path,
) -> None:
    _app()
    service_container.create_character_source("lin-keyun")
    mask = (
        tmp_path
        / CHARACTER_ASSET_PATHS["appearance_masks"]
        / official_outfit_pack_id()
        / "front.png"
    )
    mask.parent.mkdir(parents=True)
    image = QImage(4, 4, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    image.setPixelColor(1, 1, QColor(255, 255, 255, 255))
    assert image.save(str(mask), "PNG")

    overlay = ActiveOutfitOverlay(
        tmp_path / "outfits",
        tmp_path,
        official_pack_root=tmp_path / "official-packs",
    )
    region = overlay._official_replacement_region("front", (4, 4))
    assert region is not None and not region.isEmpty()


def test_switching_back_to_mohan_restores_compatibility_defaults() -> None:
    service_container.create_character_source("lin-keyun")
    source = service_container.create_character_source("mohan")
    assert source.character_id == "mohan"
    assert official_outfit_pack_id() == OFFICIAL_OUTFIT_PACK_ID
    assert builtin_makeup_pack_id() == BUILTIN_MAKEUP_PACK_ID
    assert official_native_hair_alias() == OFFICIAL_NATIVE_HAIR_ALIAS
    assert official_native_headwear_alias() == OFFICIAL_NATIVE_HEADWEAR_ALIAS
