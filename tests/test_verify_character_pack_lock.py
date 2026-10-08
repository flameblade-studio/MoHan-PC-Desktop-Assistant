"""Version-lock generation and repository drift reporting."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import zipfile
lazy from collections.abc import Callable, Mapping
lazy from pathlib import Path

lazy import pytest

lazy from domain.character_pack.models import ValidationLimits
lazy from domain.character_pack.validation import compute_package_hash
lazy from tools import build_character_pack as builder
lazy from tools import verify_character_pack_lock as verifier

MIB = 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]
PRIVATE_TOKEN_NAME = "MOHAN_CHARACTER_PACK_TOKEN"
LIMITS = ValidationLimits(
    max_archive_bytes=8 * MIB,
    max_zip_directory_bytes=MIB,
    max_manifest_bytes=MIB,
    max_file_bytes=MIB,
    max_total_bytes=8 * MIB,
    max_files=128,
    max_compression_ratio=100,
)


def _prepare_repo(path: Path) -> Path:
    source = path / builder.DEFAULT_SOURCE
    source.parent.mkdir(parents=True)
    source.write_text(
        json.dumps(
            {"pack_id": "flameblade.mohan", "pack_version": "1.0.0"},
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _manifest(payloads: Mapping[str, bytes]) -> dict[str, object]:
    files = [
        {
            "path": path,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "media_type": "application/json",
            "license_component": "program_data",
        }
        for path, data in sorted(payloads.items())
    ]
    manifest: dict[str, object] = {
        "schema": "flameblade.character-pack.v1",
        "pack_id": "flameblade.mohan",
        "pack_version": "1.0.0",
        "engine_compatibility": {
            "api_version": 1,
            "min_engine_version": "4.6.0",
            "max_engine_version_exclusive": "5.0.0",
            "required_features": [],
        },
        "files": files,
        "package_hash": "0" * 64,
    }
    manifest["package_hash"] = compute_package_hash(manifest)
    return manifest


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _fake_builder(payloads: Mapping[str, bytes]) -> Callable[..., builder.CharacterPackBuildResult]:
    frozen_payloads = dict(payloads)

    def build(
        output: str | Path,
        *,
        output_format: str,
        repo_root: str | Path,
    ) -> builder.CharacterPackBuildResult:
        assert output_format == "zip"
        assert Path(repo_root).is_dir()
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest = _manifest(frozen_payloads)
        manifest_bytes = (
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr(_zip_info("manifest.json"), manifest_bytes)
            for path, data in sorted(frozen_payloads.items()):
                archive.writestr(_zip_info(path), data)
        return builder.CharacterPackBuildResult(
            output_path,
            "zip",
            str(manifest["package_hash"]),
            len(frozen_payloads),
            sum(len(data) for data in frozen_payloads.values()),
            output_path.stat().st_size,
            LIMITS,
        )

    return build


def test_update_then_verify_uses_reproducible_s6_build_contract(tmp_path: Path) -> None:
    root = _prepare_repo(tmp_path / "repo")
    lock_path = root / "character-pack.lock.json"
    build = _fake_builder({"payload/a.json": b'{"value":1}\n'})
    updated = verifier.update_character_pack_lock(lock_path, repo_root=root, build=build)
    locked_bytes = lock_path.read_bytes()
    verified = verifier.verify_character_pack_lock(lock_path, repo_root=root, build=build)
    lock = verifier.load_character_pack_lock(lock_path)
    assert updated.valid
    assert verified.valid, verified.issues
    assert lock.pack_id == "flameblade.mohan"
    assert lock.pack_version == "1.0.0"
    assert lock.source.repository == verifier.SOURCE_REPOSITORY
    assert lock.source.release_tag == "mohan-pack-v1.0.0"
    assert lock.archive.asset_name == "flameblade.mohan-1.0.0.zip"
    assert lock.files[0].path == "payload/a.json"
    assert lock_path.read_bytes() == locked_bytes


def test_verify_reports_missing_added_and_changed_payloads_without_rewriting(tmp_path: Path) -> None:
    root = _prepare_repo(tmp_path / "repo")
    lock_path = root / "character-pack.lock.json"
    original = _fake_builder({"payload/a.json": b"a", "payload/b.json": b"b"})
    changed = _fake_builder({"payload/a.json": b"changed", "payload/c.json": b"c"})
    verifier.update_character_pack_lock(lock_path, repo_root=root, build=original)
    locked_bytes = lock_path.read_bytes()
    result = verifier.verify_character_pack_lock(lock_path, repo_root=root, build=changed)
    assert not result.valid
    assert any("payload bytes differ: payload/a.json" in issue for issue in result.issues)
    assert "payload missing from repository build: payload/b.json" in result.issues
    assert "payload added by repository build: payload/c.json" in result.issues
    assert lock_path.read_bytes() == locked_bytes


def test_update_can_keep_the_exact_release_archive(tmp_path: Path) -> None:
    root = _prepare_repo(tmp_path / "repo")
    lock_path = root / "character-pack.lock.json"
    archive_path = tmp_path / "flameblade.mohan-1.0.0.zip"
    result = verifier.update_character_pack_lock(
        lock_path,
        repo_root=root,
        archive_output=archive_path,
        build=_fake_builder({"payload/a.json": b"release"}),
    )
    assert archive_path.is_file()
    assert archive_path.stat().st_size == result.archive_bytes
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == result.archive_sha256


def test_lock_rejects_a_repository_other_than_the_owner_approved_private_repo(tmp_path: Path) -> None:
    root = _prepare_repo(tmp_path / "repo")
    lock_path = root / "character-pack.lock.json"
    verifier.update_character_pack_lock(
        lock_path,
        repo_root=root,
        build=_fake_builder({"payload/a.json": b"a"}),
    )
    document = json.loads(lock_path.read_text(encoding="utf-8"))
    document["source"]["repository"] = "attacker/example"
    lock_path.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(verifier.CharacterPackLockError, match="source.repository"):
        verifier.load_character_pack_lock(lock_path)


def test_repository_lock_uses_the_owner_approved_private_release_identity() -> None:
    lock = verifier.load_character_pack_lock(ROOT / "character-pack.lock.json")
    assert lock.pack_id == "flameblade.mohan"
    assert lock.pack_version == "1.0.1"
    assert lock.source.repository == verifier.SOURCE_REPOSITORY
    assert lock.source.release_tag == "mohan-pack-v1.0.1"
    assert lock.archive.asset_name == "flameblade.mohan-1.0.1.zip"
    assert lock.files


def test_consistency_workflow_uses_no_private_token_or_private_repository_download() -> None:
    workflow = (
        ROOT / ".github" / "workflows" / "character-pack-lock.yml"
    ).read_text(encoding="utf-8")
    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "python tools/verify_character_pack_lock.py" in workflow
    assert PRIVATE_TOKEN_NAME not in workflow
    assert "fetch_character_pack.py" not in workflow
