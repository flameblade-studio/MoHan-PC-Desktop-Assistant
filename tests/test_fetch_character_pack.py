"""Fail-closed local installation of checksum-locked public character packs."""

from __future__ import annotations

lazy import hashlib
lazy import io
lazy import json
lazy import zipfile
lazy from pathlib import Path
lazy from typing import Any
lazy from urllib.request import Request

lazy import pytest

lazy from domain.character_pack.validation import SCHEMA, compute_package_hash
lazy from domain.engine_capabilities import EngineCapabilities
lazy from tools import fetch_character_pack as fetcher
lazy from tools import verify_character_pack_lock as verifier

MIB = 1024 * 1024
PAYLOAD_PATH = "provenance/source.json"
PAYLOAD = b'{"source":"synthetic"}\n'


class _Response(io.BytesIO):
    status = 200


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _manifest(
    payload: bytes = PAYLOAD,
    *,
    pack_id: str = "flameblade.mohan",
    pack_version: str = "1.0.0",
) -> dict[str, Any]:
    payload_hash = hashlib.sha256(payload).hexdigest()
    pending = {
        "status": "owner_decision_pending",
        "rights_holder": "CHOU MING HUA",
        "license_expression": None,
        "notice_path": None,
    }
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "pack_id": pack_id,
        "pack_version": pack_version,
        "display_names": {
            "zh-TW": "墨寒角色包",
            "zh-CN": "墨寒角色包",
            "en": "MoHan Character Pack",
            "ja-JP": "墨寒キャラクターパック",
        },
        "character": {
            "id": pack_id.rsplit(".", maxsplit=1)[-1],
            "canonical_name": "測試角色",
            "aliases": ["Test Character"],
        },
        "engine_compatibility": {
            "api_version": 1,
            "min_engine_version": "4.6.0",
            "max_engine_version_exclusive": "5.0.0",
            "required_features": [],
        },
        "distribution": {
            "standalone_downloadable": True,
            "access": "public",
            "redistribution": "owner_decision_pending",
        },
        "licenses": {
            "program_data": pending,
            "character_art": pending,
            "persona_dialogue": pending,
            "voice": pending,
        },
        "source_refs": [{"path": PAYLOAD_PATH, "sha256": payload_hash, "scope": "Synthetic test only."}],
        "approval_refs": [],
        "files": [{
            "path": PAYLOAD_PATH,
            "sha256": payload_hash,
            "bytes": len(payload),
            "media_type": "application/json",
            "license_component": "program_data",
        }],
        "components": [],
        "dependencies": [],
        "package_hash": "0" * 64,
    }
    manifest["package_hash"] = compute_package_hash(manifest)
    return manifest


def _pack_bytes(
    payload: bytes = PAYLOAD,
    *,
    declared_payload: bytes | None = None,
    pack_id: str = "flameblade.mohan",
    pack_version: str = "1.0.0",
) -> bytes:
    manifest = _manifest(
        payload if declared_payload is None else declared_payload,
        pack_id=pack_id,
        pack_version=pack_version,
    )
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(_zip_info("manifest.json"), manifest_bytes)
        archive.writestr(_zip_info(PAYLOAD_PATH), payload)
    return output.getvalue()


def _lock_document(
    archive: bytes,
    *,
    pack_id: str = "flameblade.mohan",
    pack_version: str = "1.0.0",
) -> dict[str, object]:
    manifest = _manifest(pack_id=pack_id, pack_version=pack_version)
    file_entry = manifest["files"][0]
    release_name = pack_id.removeprefix("flameblade.")
    return {
        "schema": verifier.LOCK_SCHEMA,
        "schema_version": verifier.LOCK_SCHEMA_VERSION,
        "pack_id": manifest["pack_id"],
        "pack_version": manifest["pack_version"],
        "package_hash": manifest["package_hash"],
        "archive": {
            "asset_name": f"{pack_id}-{pack_version}.zip",
            "sha256": hashlib.sha256(archive).hexdigest(),
            "bytes": len(archive),
        },
        "source": {
            "repository": verifier.SOURCE_REPOSITORY,
            "release_tag": f"{release_name}-pack-v{pack_version}",
        },
        "engine_compatibility": manifest["engine_compatibility"],
        "validation_limits": {
            "max_archive_bytes": 8 * MIB,
            "max_zip_directory_bytes": MIB,
            "max_manifest_bytes": MIB,
            "max_file_bytes": MIB,
            "max_total_bytes": 8 * MIB,
            "max_files": 32,
            "max_compression_ratio": 100,
        },
        "files": [{
            "path": file_entry["path"],
            "sha256": file_entry["sha256"],
            "bytes": file_entry["bytes"],
        }],
    }


def _write_lock(
    path: Path,
    archive: bytes,
    *,
    pack_id: str = "flameblade.mohan",
    pack_version: str = "1.0.0",
) -> Path:
    path.write_text(
        json.dumps(
            _lock_document(archive, pack_id=pack_id, pack_version=pack_version),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _fake_download(archive: bytes, seen_pack_ids: list[str] | None = None):
    def download(lock: verifier.CharacterPackLock, destination: Path) -> None:
        assert lock.archive.asset_name == destination.name
        if seen_pack_ids is not None:
            seen_pack_ids.append(lock.pack_id)
        destination.write_bytes(archive)

    return download


def test_fetch_validates_then_atomically_installs_without_credentials(tmp_path: Path) -> None:
    archive = _pack_bytes()
    lock_path = _write_lock(tmp_path / "character-pack.lock.json", archive)
    output = tmp_path / "installed"
    seen_pack_ids: list[str] = []
    result = fetcher.fetch_character_pack(
        output,
        lock_path=lock_path,
        download=_fake_download(archive, seen_pack_ids),
    )
    assert result.package_hash == _manifest()["package_hash"]
    assert result.checked_files == 1
    assert (output / PAYLOAD_PATH).read_bytes() == PAYLOAD
    assert (output / "manifest.json").is_file()
    assert seen_pack_ids == ["flameblade.mohan"]


def test_fetch_supports_a_second_public_pack_selected_by_lock(tmp_path: Path) -> None:
    pack_id = "flameblade.lin-keyun"
    archive = _pack_bytes(pack_id=pack_id)
    lock_path = _write_lock(
        tmp_path / "lin-keyun-pack.lock.json",
        archive,
        pack_id=pack_id,
    )
    output = tmp_path / "installed"
    result = fetcher.fetch_character_pack(
        output,
        lock_path=lock_path,
        download=_fake_download(archive),
    )
    assert result.pack_id == pack_id
    assert (output / PAYLOAD_PATH).read_bytes() == PAYLOAD


def test_checksum_mismatch_fails_closed_without_installing_files(tmp_path: Path) -> None:
    archive = _pack_bytes()
    lock_path = _write_lock(tmp_path / "character-pack.lock.json", archive)
    output = tmp_path / "installed"
    with pytest.raises(fetcher.CharacterPackFetchError, match="SHA-256"):
        fetcher.fetch_character_pack(
            output,
            lock_path=lock_path,
            download=_fake_download(archive[:-1] + bytes([archive[-1] ^ 1])),
        )
    assert not output.exists()


def test_validator_rejection_fails_closed_after_archive_checksum_passes(tmp_path: Path) -> None:
    invalid_archive = _pack_bytes(
        b'{"source":"tampered"}\n',
        declared_payload=PAYLOAD,
    )
    document = _lock_document(invalid_archive)
    lock_path = tmp_path / "character-pack.lock.json"
    lock_path.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    output = tmp_path / "installed"
    with pytest.raises(fetcher.CharacterPackFetchError, match="validation"):
        fetcher.fetch_character_pack(
            output,
            lock_path=lock_path,
            download=_fake_download(invalid_archive),
        )
    assert not output.exists()


def test_downloader_exception_is_wrapped_without_upstream_details(tmp_path: Path) -> None:
    archive = _pack_bytes()
    lock_path = _write_lock(tmp_path / "character-pack.lock.json", archive)
    upstream_detail = "upstream transport detail"

    def download(_lock: verifier.CharacterPackLock, _destination: Path) -> None:
        raise RuntimeError(upstream_detail)

    with pytest.raises(fetcher.CharacterPackFetchError) as captured:
        fetcher.fetch_character_pack(
            tmp_path / "installed",
            lock_path=lock_path,
            download=download,
        )
    assert upstream_detail not in str(captured.value)
    assert not (tmp_path / "installed").exists()


def test_github_downloader_uses_public_locked_release_url_without_authorization(tmp_path: Path) -> None:
    archive = _pack_bytes()
    lock_path = _write_lock(tmp_path / "character-pack.lock.json", archive)
    lock = verifier.load_release_character_pack_lock(lock_path)
    asset_url = (
        "https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/"
        "releases/download/mohan-pack-v1.0.0/flameblade.mohan-1.0.0.zip"
    )
    requests: list[Request] = []

    def fake_open(request: Request, _timeout: float) -> _Response:
        requests.append(request)
        assert request.full_url == asset_url
        return _Response(archive)

    output = tmp_path / lock.archive.asset_name
    fetcher._download_from_github(
        lock,
        output,
        open_url=fake_open,
    )
    assert output.read_bytes() == archive
    assert len(requests) == 1
    assert requests[0].get_header("Authorization") is None
    assert requests[0].get_header("Accept") == "application/octet-stream"


@pytest.mark.parametrize(
    "engine",
    [
        EngineCapabilities("5.0.0", 1, frozenset()),
        EngineCapabilities("4.6.0", 2, frozenset()),
        EngineCapabilities("4.5.9", 1, frozenset()),
    ],
)
def test_fetch_checks_the_running_engine_not_the_packs_own_claims(tmp_path: Path, engine: EngineCapabilities) -> None:
    archive = _pack_bytes()
    lock_path = _write_lock(tmp_path / "character-pack.lock.json", archive)
    output = tmp_path / "installed"
    with pytest.raises(fetcher.CharacterPackFetchError, match="validation"):
        fetcher.fetch_character_pack(
            output,
            lock_path=lock_path,
            download=_fake_download(archive),
            engine=engine,
        )
    assert not output.exists()


def test_extraction_failure_removes_staging_and_final_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = _pack_bytes()
    lock_path = _write_lock(tmp_path / "character-pack.lock.json", archive)
    output = tmp_path / "installed"

    def fail_after_partial_extract(
        _archive_path: Path,
        destination: Path,
        _manifest: object,
        _lock: object,
    ) -> None:
        destination.mkdir()
        (destination / "partial").write_bytes(b"partial")
        raise fetcher.CharacterPackFetchError("simulated extraction failure")

    monkeypatch.setattr(fetcher, "_extract_validated_archive", fail_after_partial_extract)
    with pytest.raises(fetcher.CharacterPackFetchError, match="simulated extraction failure"):
        fetcher.fetch_character_pack(
            output,
            lock_path=lock_path,
            download=_fake_download(archive),
        )
    assert not output.exists()
    assert not tuple(tmp_path.glob("character-pack-fetch-*"))
