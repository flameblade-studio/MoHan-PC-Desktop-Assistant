"""Tests for body-pack reproducibility and release-lock drift detection."""
from __future__ import annotations

lazy import zipfile
lazy from types import SimpleNamespace

lazy import pytest

lazy from tools import verify_body_pack_lock as verifier


def test_reproducible_zip_is_byte_identical_and_has_canonical_members(tmp_path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "z-last.txt").write_bytes(b"last")
    (package / "a-first.txt").write_bytes(b"first")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    first_result = verifier.build_reproducible_zip(package, first)
    second_result = verifier.build_reproducible_zip(package, second)

    assert (first_result["bytes"], first_result["sha256"]) == (
        second_result["bytes"], second_result["sha256"]
    )
    assert first.read_bytes() == second.read_bytes()
    verifier._check_archive_properties(first, first_result["files"])
    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == ["a-first.txt", "z-last.txt"]
        assert [item.date_time for item in archive.infolist()] == [
            verifier.ZIP_TIMESTAMP,
            verifier.ZIP_TIMESTAMP,
        ]


def test_release_lock_comparison_rejects_file_inventory_drift() -> None:
    fingerprint = "6340691bfdca8f2eb6197f6237481a550f366ddb762905353703e1a513da778c"
    record = {"path": "manifest.json", "bytes": 5, "sha256": "a" * 64}
    document = {
        "pack_id": "mohan-body-v2",
        "pack_version": "1.0.0",
        "package_hash": fingerprint,
        "license": "CC-BY-NC-ND-4.0",
        "archive": {"asset_name": "flameblade.mohan-body-v2-1.0.0.zip", "bytes": 7, "sha256": "b" * 64},
        "source": {"release_tag": "mohan-body-v2-pack-v1.0.0"},
        "body_pack": {"fingerprint": fingerprint},
        "files": [record],
    }
    locked = SimpleNamespace(
        pack_id=document["pack_id"],
        pack_version=document["pack_version"],
        package_hash=document["package_hash"],
        license=document["license"],
        archive=SimpleNamespace(**document["archive"]),
        release_tag=document["source"]["release_tag"],
        reference=SimpleNamespace(fingerprint=fingerprint),
        source_manifest_bytes=12,
        source_manifest_sha256="c" * 64,
        files=(SimpleNamespace(**record),),
    )
    verifier._compare_lock(locked, document, 12, "c" * 64)

    locked.files = (SimpleNamespace(path="manifest.json", bytes=6, sha256="d" * 64),)
    with pytest.raises(verifier.BodyPackLockVerificationError, match="file inventory drifted"):
        verifier._compare_lock(locked, document, 12, "c" * 64)


def test_release_archive_filename_uses_source_pack_version() -> None:
    source = {"pack": {"id": "mohan-body-v2", "version": "2.1.0"}}
    assert verifier._release_archive_path(source).name == "flameblade.mohan-body-v2-2.1.0.zip"
