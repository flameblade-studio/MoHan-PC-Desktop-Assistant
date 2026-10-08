"""Fail-closed local installation of checksum-locked private character packs."""

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
GITHUB_REQUEST_COUNT = 2
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


def _manifest(payload: bytes = PAYLOAD) -> dict[str, Any]:
    payload_hash = hashlib.sha256(payload).hexdigest()
    pending = {
        "status": "owner_decision_pending",
        "rights_holder": "CHOU MING HUA",
        "license_expression": None,
        "notice_path": None,
    }
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "pack_id": "flameblade.mohan",
        "pack_version": "1.0.0",
        "display_names": {
            "zh-TW": "墨寒角色包",
            "zh-CN": "墨寒角色包",
            "en": "MoHan Character Pack",
            "ja-JP": "墨寒キャラクターパック",
        },
        "character": {"id": "mohan", "canonical_name": "墨寒", "aliases": ["MoHan"]},
        "engine_compatibility": {
            "api_version": 1,
            "min_engine_version": "4.6.0",
            "max_engine_version_exclusive": "5.0.0",
            "required_features": [],
        },
        "distribution": {
            "standalone_downloadable": True,
            "access": "private",
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


def _pack_bytes(payload: bytes = PAYLOAD, *, declared_payload: bytes | None = None) -> bytes:
    manifest = _manifest(payload if declared_payload is None else declared_payload)
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(_zip_info("manifest.json"), manifest_bytes)
        archive.writestr(_zip_info(PAYLOAD_PATH), payload)
    return output.getvalue()


def _lock_document(archive: bytes) -> dict[str, object]:
    manifest = _manifest()
    file_entry = manifest["files"][0]
    return {
        "schema": verifier.LOCK_SCHEMA,
        "schema_version": verifier.LOCK_SCHEMA_VERSION,
        "pack_id": manifest["pack_id"],
        "pack_version": manifest["pack_version"],
        "package_hash": manifest["package_hash"],
        "archive": {
            "asset_name": "flameblade.mohan-1.0.0.zip",
            "sha256": hashlib.sha256(archive).hexdigest(),
            "bytes": len(archive),
        },
        "source": {
            "repository": verifier.SOURCE_REPOSITORY,
            "release_tag": "mohan-pack-v1.0.0",
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


def _write_lock(path: Path, archive: bytes) -> Path:
    path.write_text(
        json.dumps(_lock_document(archive), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _fake_download(archive: bytes, seen_tokens: list[str] | None = None):
    def download(lock: verifier.CharacterPackLock, token: str, destination: Path) -> None:
        assert lock.archive.asset_name == destination.name
        if seen_tokens is not None:
            seen_tokens.append(token)
        destination.write_bytes(archive)

    return download


def test_fetch_validates_then_atomically_installs_with_environment_token(tmp_path: Path) -> None:
    archive = _pack_bytes()
    lock_path = _write_lock(tmp_path / "character-pack.lock.json", archive)
    output = tmp_path / "installed"
    seen_tokens: list[str] = []
    result = fetcher.fetch_character_pack(
        output,
        lock_path=lock_path,
        environment={fetcher.TOKEN_ENVIRONMENT: "test-secret"},
        download=_fake_download(archive, seen_tokens),
    )
    assert result.package_hash == _manifest()["package_hash"]
    assert result.checked_files == 1
    assert (output / PAYLOAD_PATH).read_bytes() == PAYLOAD
    assert (output / "manifest.json").is_file()
    assert seen_tokens == ["test-secret"]


def test_missing_token_fails_before_download_and_leaves_no_output(tmp_path: Path) -> None:
    archive = _pack_bytes()
    lock_path = _write_lock(tmp_path / "character-pack.lock.json", archive)
    output = tmp_path / "installed"
    called = False

    def download(_lock: verifier.CharacterPackLock, _token: str, _destination: Path) -> None:
        nonlocal called
        called = True

    with pytest.raises(fetcher.CharacterPackFetchError, match=fetcher.TOKEN_ENVIRONMENT):
        fetcher.fetch_character_pack(
            output,
            lock_path=lock_path,
            environment={},
            download=download,
        )
    assert not called
    assert not output.exists()


def test_checksum_mismatch_fails_closed_without_installing_files(tmp_path: Path) -> None:
    archive = _pack_bytes()
    lock_path = _write_lock(tmp_path / "character-pack.lock.json", archive)
    output = tmp_path / "installed"
    with pytest.raises(fetcher.CharacterPackFetchError, match="SHA-256"):
        fetcher.fetch_character_pack(
            output,
            lock_path=lock_path,
            environment={fetcher.TOKEN_ENVIRONMENT: "test-secret"},
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
            environment={fetcher.TOKEN_ENVIRONMENT: "test-secret"},
            download=_fake_download(invalid_archive),
        )
    assert not output.exists()


def test_downloader_exception_never_echoes_environment_token(tmp_path: Path) -> None:
    archive = _pack_bytes()
    lock_path = _write_lock(tmp_path / "character-pack.lock.json", archive)
    secret = "never-print-this-token"

    def download(_lock: verifier.CharacterPackLock, token: str, _destination: Path) -> None:
        raise RuntimeError(f"upstream included {token}")

    with pytest.raises(fetcher.CharacterPackFetchError) as captured:
        fetcher.fetch_character_pack(
            tmp_path / "installed",
            lock_path=lock_path,
            environment={fetcher.TOKEN_ENVIRONMENT: secret},
            download=download,
        )
    assert secret not in str(captured.value)
    assert not (tmp_path / "installed").exists()


def test_github_downloader_uses_locked_asset_api_with_fake_responses(tmp_path: Path) -> None:
    archive = _pack_bytes()
    lock_path = _write_lock(tmp_path / "character-pack.lock.json", archive)
    lock = verifier.load_character_pack_lock(lock_path)
    asset_url = (
        "https://api.github.com/repos/flameblade-studio/"
        "mohan-character-pack/releases/assets/123456"
    )
    metadata = json.dumps({
        "assets": [{
            "name": lock.archive.asset_name,
            "size": lock.archive.bytes,
            "url": asset_url,
        }],
    }).encode("utf-8")
    requests: list[Request] = []

    def fake_open(request: Request, _timeout: float) -> _Response:
        requests.append(request)
        if request.full_url == asset_url:
            return _Response(archive)
        return _Response(metadata)

    output = tmp_path / lock.archive.asset_name
    fetcher._download_from_github(
        lock,
        "test-secret",
        output,
        open_url=fake_open,
    )
    assert output.read_bytes() == archive
    assert len(requests) == GITHUB_REQUEST_COUNT
    assert all(request.get_header("Authorization") == "Bearer test-secret" for request in requests)
    assert requests[1].get_header("Accept") == "application/octet-stream"


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
            environment={fetcher.TOKEN_ENVIRONMENT: "test-secret"},
            download=_fake_download(archive),
            engine=engine,
        )
    assert not output.exists()
