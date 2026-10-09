from __future__ import annotations

lazy from pathlib import Path

lazy import pytest

lazy from tests import character_pack_fixtures
lazy from domain.character_pack.models import (
    CharacterPackManifest,
    CharacterPackValidationResult,
    SignatureVerifier,
    ValidationLimits,
)
lazy from domain.engine_capabilities import EngineCapabilities
lazy from infrastructure import installed_character_packs
lazy from infrastructure.installed_character_packs import (
    CharacterPackInstallError,
    install_character_pack,
    installed_character_pack_path,
    list_installed_character_packs,
)
lazy from tests.character_pack_fixtures import (
    FAKE_CHARACTER_ID,
    build_fake_character_pack,
    rewrite_character_pack_manifest,
)


def test_install_rejects_source_replaced_after_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = build_fake_character_pack(tmp_path)
    replacement = rewrite_character_pack_manifest(
        archive,
        tmp_path / "replacement-character.zip",
        lambda manifest: manifest.update(pack_version="2.0.0"),
    )
    data_root = tmp_path / "profile"
    original_validate = installed_character_packs._validated_archive
    original_extract = installed_character_packs._extract_validated_archive
    validation_finished = False

    def validate_then_record(
        source_path: str | Path,
        *,
        engine: EngineCapabilities,
        limits: ValidationLimits,
        signature_verifier: SignatureVerifier | None,
    ) -> CharacterPackValidationResult:
        nonlocal validation_finished
        if Path(source_path) == archive:
            raise RuntimeError("Validation must use the private ZIP snapshot.")
        result = original_validate(
            source_path,
            engine=engine,
            limits=limits,
            signature_verifier=signature_verifier,
        )
        validation_finished = True
        return result

    def replace_source() -> None:
        if not validation_finished:
            raise RuntimeError("The source replacement happened before validation.")
        replacement.replace(archive)

    def replace_source_then_extract(
        snapshot_path: Path,
        destination: Path,
        manifest: CharacterPackManifest,
        limits: ValidationLimits,
    ) -> None:
        replace_source()
        original_extract(snapshot_path, destination, manifest, limits)

    monkeypatch.setattr(
        installed_character_packs,
        "_validated_archive",
        validate_then_record,
    )
    monkeypatch.setattr(
        installed_character_packs,
        "_extract_validated_archive",
        replace_source_then_extract,
    )

    with pytest.raises(
        CharacterPackInstallError,
        match="source character-pack ZIP changed",
    ):
        install_character_pack(archive, data_root=data_root)

    assert not installed_character_pack_path(
        FAKE_CHARACTER_ID,
        data_root=data_root,
    ).exists()


def test_list_installed_character_packs_returns_empty_for_missing_root(
    tmp_path: Path,
) -> None:
    assert list_installed_character_packs(data_root=tmp_path / "missing") == ()


def test_list_installed_character_packs_validates_and_orders_multiple_packs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_source = tmp_path / "first"
    second_source = tmp_path / "second"
    first_source.mkdir()
    second_source.mkdir()
    first_archive = build_fake_character_pack(first_source)
    monkeypatch.setattr(
        character_pack_fixtures,
        "FAKE_CHARACTER_ID",
        "test-sentinel-two",
    )
    second_archive = build_fake_character_pack(second_source)
    data_root = tmp_path / "profile"

    install_character_pack(first_archive, data_root=data_root)
    install_character_pack(second_archive, data_root=data_root)

    readers = list_installed_character_packs(data_root=data_root)

    assert tuple(reader.manifest.character_id for reader in readers) == (
        FAKE_CHARACTER_ID,
        "test-sentinel-two",
    )


def test_list_installed_character_packs_rejects_a_corrupted_pack(
    tmp_path: Path,
) -> None:
    archive = build_fake_character_pack(tmp_path)
    data_root = tmp_path / "profile"
    install_character_pack(archive, data_root=data_root)
    profile = (
        installed_character_pack_path(FAKE_CHARACTER_ID, data_root=data_root)
        / "assets"
        / "characters"
        / FAKE_CHARACTER_ID
        / "persona"
        / "profile.json"
    )
    profile.write_bytes(profile.read_bytes() + b" ")

    with pytest.raises(CharacterPackInstallError):
        list_installed_character_packs(data_root=data_root)
