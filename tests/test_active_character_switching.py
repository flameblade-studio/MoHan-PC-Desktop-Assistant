from __future__ import annotations

lazy import logging
lazy import importlib
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest

lazy from application import service_container
lazy from application import wardrobe_service as wardrobe_module
lazy from application.character_runtime_bootstrap import ACTIVE_CHARACTER_ENV
lazy from application.wardrobe_appearance_service import WardrobeAppearanceService
lazy from application.wardrobe_service import BUILTIN_OUTFIT_ID, WardrobeService
lazy from domain.character_runtime import (
    CHARACTER_ASSET_PATHS,
    CHARACTER_EXPRESSION_ROLES,
    CHARACTER_LAYER_ROLES,
    CHARACTER_POSE_ROLES,
    character_rig_manifest,
)
lazy from domain.character_source import active_character_engine_profile, active_character_source
lazy from domain.outfit_pack import (
    installed_pack_path,
    list_installed_outfits,
    resolve_active_selection,
)
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
lazy from infrastructure.bundled_character_source import BundledCharacterSource
lazy from infrastructure.installed_character_packs import (
    DEVELOPMENT_CHARACTER_PACK_ARCHIVE_ENV,
    CharacterPackInstallError,
    install_character_pack,
    installed_character_pack_path,
)
lazy from tests.character_pack_fixtures import (
    FAKE_CANONICAL_NAME,
    FAKE_CHARACTER_ID,
    FAKE_OUTFIT_ENSEMBLE_ID,
    FAKE_OUTFIT_PACK_ID,
    build_fake_character_pack,
    rewrite_character_pack_manifest,
    tamper_character_pack_payload,
)
lazy from tools import build_character_pack as character_pack_builder

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR_ENV = "MOHAN_DATA_DIR"


@pytest.fixture(autouse=True)
def _restore_default_character(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(ACTIVE_CHARACTER_ENV, raising=False)
    monkeypatch.delenv(DEVELOPMENT_CHARACTER_PACK_ARCHIVE_ENV, raising=False)
    monkeypatch.delenv(DATA_DIR_ENV, raising=False)
    service_container.create_character_source("mohan")
    yield
    service_container.create_character_source("mohan")


def _install_fake_character(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path]:
    archive = build_fake_character_pack(tmp_path)
    data_root = tmp_path / "profile"
    result = install_character_pack(archive, data_root=data_root)
    assert result.character_id == FAKE_CHARACTER_ID
    monkeypatch.setenv(DATA_DIR_ENV, str(data_root))
    return archive, data_root


def test_product_bundle_exposes_only_mohan() -> None:
    default = service_container.create_default_character_source()
    assert default.character_id == "mohan"

    with pytest.raises(ValueError, match="contains only its default character"):
        BundledCharacterSource(ROOT, "lin-keyun")
    assert active_character_source() is default


def test_installs_and_selects_a_valid_standalone_character_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _archive, data_root = _install_fake_character(tmp_path, monkeypatch)
    monkeypatch.setenv(ACTIVE_CHARACTER_ENV, FAKE_CHARACTER_ID)

    selected = service_container.create_default_character_source()

    assert selected.character_id == FAKE_CHARACTER_ID
    assert selected.canonical_name == FAKE_CANONICAL_NAME
    assert selected.persona.persona_prompt("en").startswith("You are Test Sentinel")
    assert selected.appearance.appearance_defaults.outfit_pack_id == FAKE_OUTFIT_PACK_ID
    assert selected.appearance.appearance_defaults.outfit_ensemble_id == (
        FAKE_OUTFIT_ENSEMBLE_ID
    )
    assert selected.appearance.appearance_defaults.native_headwear is None
    assert selected.manifest.access == "owner_decision_pending"
    assert {license_.status for license_ in selected.manifest.licenses} == {
        "owner_decision_pending"
    }
    assert selected.asset_root == installed_character_pack_path(
        FAKE_CHARACTER_ID,
        data_root=data_root,
    ).resolve()
    profile = active_character_engine_profile()
    assert profile.assets is selected.assets
    assert profile.rig_manifest is selected.appearance.rig_manifest
    assert character_rig_manifest() is selected.appearance.rig_manifest
    assert CHARACTER_ASSET_PATHS["halfbody_root"] == "assets/test-sentinel/expressions"
    assert CHARACTER_POSE_ROLES["front_idle"] == "test-sentinel-front"
    assert CHARACTER_EXPRESSION_ROLES["gentle"] == "test-sentinel-gentle"
    assert CHARACTER_LAYER_ROLES["rear_hair"] == "test-sentinel-rear-hair"
    face_motion = importlib.import_module("domain.face_motion")
    assert "test-sentinel-gentle" in face_motion.HAPPY_EXPRESSIONS


def test_missing_installed_character_fails_closed_to_mohan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path / "profile"))

    with (
        caplog.at_level(logging.ERROR, logger="mohan.character_selection"),
        pytest.raises(RuntimeError, match="bundled default character remains active"),
    ):
        service_container.create_character_source("not-installed")

    assert active_character_source().character_id == "mohan"
    assert "source_not_found" in caplog.text


def test_tampered_download_is_not_installed(tmp_path: Path) -> None:
    archive = build_fake_character_pack(tmp_path)
    tampered = tamper_character_pack_payload(
        archive,
        tmp_path / "tampered-character.zip",
    )
    data_root = tmp_path / "profile"

    with pytest.raises(
        CharacterPackInstallError,
        match="size_mismatch|file_hash_mismatch",
    ):
        install_character_pack(tampered, data_root=data_root)

    assert not installed_character_pack_path(
        FAKE_CHARACTER_ID,
        data_root=data_root,
    ).exists()


def test_installed_payload_tampering_fails_closed_to_mohan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _archive, data_root = _install_fake_character(tmp_path, monkeypatch)
    profile = (
        installed_character_pack_path(FAKE_CHARACTER_ID, data_root=data_root)
        / "assets"
        / "characters"
        / FAKE_CHARACTER_ID
        / "persona"
        / "profile.json"
    )
    profile.write_bytes(profile.read_bytes() + b" ")

    with (
        caplog.at_level(logging.ERROR, logger="mohan.character_selection"),
        pytest.raises(RuntimeError, match="bundled default character remains active"),
    ):
        service_container.create_character_source(FAKE_CHARACTER_ID)

    assert active_character_source().character_id == "mohan"
    assert "size_mismatch" in caplog.text


def test_development_archive_is_explicit_and_not_persistently_installed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = build_fake_character_pack(tmp_path)
    data_root = tmp_path / "profile"
    monkeypatch.setenv(DATA_DIR_ENV, str(data_root))
    monkeypatch.setenv(ACTIVE_CHARACTER_ENV, FAKE_CHARACTER_ID)
    monkeypatch.setenv(DEVELOPMENT_CHARACTER_PACK_ARCHIVE_ENV, str(archive))

    selected = service_container.create_default_character_source()

    assert selected.character_id == FAKE_CHARACTER_ID
    assert not installed_character_pack_path(
        FAKE_CHARACTER_ID,
        data_root=data_root,
    ).exists()


def test_incompatible_development_archive_fails_closed_to_mohan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    archive = build_fake_character_pack(tmp_path)

    def make_incompatible(manifest: dict[str, object]) -> None:
        manifest["engine_compatibility"] = {
            "api_version": 1,
            "min_engine_version": "9.0.0",
            "max_engine_version_exclusive": "10.0.0",
            "required_features": [],
        }

    incompatible = rewrite_character_pack_manifest(
        archive,
        tmp_path / "incompatible-character.zip",
        make_incompatible,
    )
    monkeypatch.setenv(ACTIVE_CHARACTER_ENV, FAKE_CHARACTER_ID)
    monkeypatch.setenv(DEVELOPMENT_CHARACTER_PACK_ARCHIVE_ENV, str(incompatible))

    with (
        caplog.at_level(logging.ERROR, logger="mohan.character_selection"),
        pytest.raises(RuntimeError, match="incompatible_engine"),
    ):
        service_container.create_default_character_source()

    assert active_character_source().character_id == "mohan"
    assert "bundled default character remains active" in caplog.text


def test_missing_external_outfit_falls_back_to_bare_base_with_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _install_fake_character(tmp_path, monkeypatch)
    service_container.create_character_source(FAKE_CHARACTER_ID)
    store = tmp_path / "outfits"
    official_root = ROOT / "assets" / "official-packs"
    service = WardrobeService(store, official_pack_root=official_root)

    with caplog.at_level(logging.WARNING, logger="mohan.character_appearance"):
        outfits = service.outfits("en")

    assert len(outfits) == 1
    assert outfits[0].outfit_id == BUILTIN_OUTFIT_ID
    assert outfits[0].built_in
    assert outfits[0].ensemble is None
    assert FAKE_CANONICAL_NAME in outfits[0].display_name
    assert FAKE_OUTFIT_PACK_ID in caplog.text
    assert "using the bare base" in caplog.text
    assert OFFICIAL_OUTFIT_PACK_ID not in {outfit.outfit_id for outfit in outfits}

    garment = resolve_active_selection(
        store,
        "garment",
        official_pack_root=official_root,
    )
    assert garment.status == "builtin"
    assert garment.effective_pack_id == "builtin"

    headwear = WardrobeAppearanceService(
        store,
        official_pack_root=official_root,
    ).options("headwear", "en")
    assert tuple(option.option_id for option in headwear) == ("none",)


def test_linkeyun_source_resolves_its_official_pack_and_builtin_sentinel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = tmp_path / "flameblade.lin-keyun-1.0.2.zip"
    character_pack_builder.build_character_pack(
        archive,
        output_format="zip",
        source_path="assets/characters/lin-keyun/pack-source.json",
    )
    monkeypatch.setenv(ACTIVE_CHARACTER_ENV, "lin-keyun")
    monkeypatch.setenv(DEVELOPMENT_CHARACTER_PACK_ARCHIVE_ENV, str(archive))

    source = service_container.create_default_character_source()
    ports = service_container.create_presentation_ports()
    shared_root = source.assets.asset_root / "assets" / "official-packs"
    character_root = (
        source.assets.asset_root
        / "assets"
        / "characters"
        / "lin-keyun"
        / "official-packs"
    )
    assert ports.official_pack_roots == (shared_root, character_root)

    store = tmp_path / "outfits"
    packs = list_installed_outfits(
        store,
        official_pack_root=ports.official_pack_roots,
    )
    assert {pack.pack_id for pack in packs} == {
        BUILTIN_MAKEUP_PACK_ID,
        "linkeyun.official.modern-office",
    }
    assert installed_pack_path(
        store,
        "linkeyun.official.modern-office",
        official_pack_root=ports.official_pack_roots,
    ) == character_root / "linkeyun.official.modern-office.mohan-outfit"

    built_in = WardrobeService(
        store,
        official_pack_root=ports.official_pack_roots,
    ).outfits("en")[0]
    assert built_in.ensemble is not None
    assert built_in.ensemble.pack_id == "linkeyun.official.modern-office"
    garment = resolve_active_selection(
        store,
        "garment",
        official_pack_root=ports.official_pack_roots,
    )
    assert garment.status == "installed"
    assert garment.effective_pack_id == "linkeyun.official.modern-office"


def test_external_official_ensemble_is_only_the_builtin_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_character(tmp_path, monkeypatch)
    service_container.create_character_source(FAKE_CHARACTER_ID)
    names = {
        "zh-TW": "測試服裝",
        "zh-CN": "测试服装",
        "en": "Test Outfit",
        "ja-JP": "テスト衣装",
    }
    official = SimpleNamespace(
        pack_id=official_outfit_pack_id(),
        ensemble_id=official_outfit_ensemble_id(),
        pack_display_names=names,
        ensemble_display_names=names,
        selections=(
            SimpleNamespace(
                category="garment",
                item_id="test-outfit",
                variant_id="default",
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


def test_switching_back_to_mohan_restores_compatibility_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_character(tmp_path, monkeypatch)
    service_container.create_character_source(FAKE_CHARACTER_ID)
    source = service_container.create_character_source("mohan")

    assert source.character_id == "mohan"
    assert official_outfit_pack_id() == OFFICIAL_OUTFIT_PACK_ID
    assert builtin_makeup_pack_id() == BUILTIN_MAKEUP_PACK_ID
    assert official_native_hair_alias() == OFFICIAL_NATIVE_HAIR_ALIAS
    assert official_native_headwear_alias() == OFFICIAL_NATIVE_HEADWEAR_ALIAS
    assert service_container.create_presentation_ports().official_pack_roots == (
        ROOT / "assets" / "official-packs",
    )
