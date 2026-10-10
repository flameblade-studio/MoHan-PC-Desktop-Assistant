from __future__ import annotations

lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest

lazy from application import service_container
lazy from application.character_runtime_bootstrap import ACTIVE_CHARACTER_ENV
lazy from application.wardrobe_service import BUILTIN_OUTFIT_ID, WardrobeService
lazy from domain.outfit_pack import (
    OFFICIAL_PACK_ROOT,
    OutfitPackError,
    install_outfit_pack,
    official_pack_ids,
    set_official_pack_id_reservations,
)
lazy from domain.outfit_pack_official import OFFICIAL_OUTFIT_PACK_ID, OFFICIAL_PACK_IDS
lazy from infrastructure.installed_character_packs import install_character_pack
lazy from tests.character_pack_fixtures import (
    FAKE_CHARACTER_ID,
    FAKE_OUTFIT_PACK_ID,
    build_fake_character_pack,
)


@pytest.fixture(autouse=True)
def _restore_default_character(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    clean_profile = tmp_path / "default-profile"
    monkeypatch.setenv("MOHAN_DATA_DIR", str(clean_profile))
    monkeypatch.delenv(ACTIVE_CHARACTER_ENV, raising=False)
    monkeypatch.delenv(
        "MOHAN_DEV_CHARACTER_PACK_ARCHIVE",
        raising=False,
    )
    set_official_pack_id_reservations(())
    service_container.create_character_source("mohan")
    yield
    monkeypatch.setenv("MOHAN_DATA_DIR", str(clean_profile))
    monkeypatch.delenv(ACTIVE_CHARACTER_ENV, raising=False)
    monkeypatch.delenv(
        "MOHAN_DEV_CHARACTER_PACK_ARCHIVE",
        raising=False,
    )
    set_official_pack_id_reservations(())
    service_container.create_character_source("mohan")


def test_official_pack_ids_keep_inactive_installed_character_reservations() -> None:
    inactive_character_pack_id = "test.inactive-role.official-outfit"
    set_official_pack_id_reservations({inactive_character_pack_id})

    assert official_pack_ids() == OFFICIAL_PACK_IDS | {inactive_character_pack_id}


def test_incomplete_installed_character_scan_blocks_user_outfit_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "user-pack.mohan-outfit"
    source.write_bytes(b"validated by the test double")
    monkeypatch.setattr(
        "domain.outfit_pack.inspect_outfit_pack",
        lambda _source: SimpleNamespace(pack_id="user.safe-looking-pack"),
    )
    monkeypatch.setattr(
        "domain.outfit_pack.copy_pack_archive",
        lambda *_args: pytest.fail("an incomplete reservation scan must fail closed"),
    )
    set_official_pack_id_reservations((), complete=False)

    with pytest.raises(OutfitPackError, match="reserved"):
        install_outfit_pack(source, tmp_path / "outfits")


def test_external_to_mohan_round_trip_rejects_official_id_spoof_and_loads_wardrobe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    character_archive = build_fake_character_pack(tmp_path)
    data_root = tmp_path / "profile"
    install_character_pack(character_archive, data_root=data_root)
    monkeypatch.setenv("MOHAN_DATA_DIR", str(data_root))

    external = service_container.create_character_source(FAKE_CHARACTER_ID)
    assert external.character_id == FAKE_CHARACTER_ID
    assert (OFFICIAL_PACK_IDS | {FAKE_OUTFIT_PACK_ID}) <= official_pack_ids()

    store = tmp_path / "outfits"
    official_archive = (
        OFFICIAL_PACK_ROOT / f"{OFFICIAL_OUTFIT_PACK_ID}.mohan-outfit"
    )
    with pytest.raises(OutfitPackError, match="reserved"):
        install_outfit_pack(official_archive, store)
    assert not (store / "packages").exists()

    external_outfits = WardrobeService(store).outfits("en")
    assert [outfit.outfit_id for outfit in external_outfits] == [BUILTIN_OUTFIT_ID]
    assert external_outfits[0].ensemble is None

    mohan = service_container.create_character_source("mohan")
    assert mohan.character_id == "mohan"
    outfits = WardrobeService(store).outfits("en")
    builtin_outfits = [outfit for outfit in outfits if outfit.outfit_id == BUILTIN_OUTFIT_ID]
    assert len(builtin_outfits) == 1
    assert builtin_outfits[0].ensemble is not None
    assert builtin_outfits[0].ensemble.pack_id == OFFICIAL_OUTFIT_PACK_ID
