from __future__ import annotations

lazy import shutil
lazy from pathlib import Path
lazy import json

lazy import pytest

lazy from tools import fetch_body_pack as fetcher
lazy from tests.body_pack_fixtures import (
    SOURCE_MANIFEST_BYTES,
    build_body_pack_release_fixture,
)


def test_body_pack_lock_accepts_valid_checksums_and_declares_license(
    tmp_path: Path,
) -> None:
    fixture = build_body_pack_release_fixture(tmp_path / "release")

    lock = fetcher.load_body_pack_release_lock(fixture.lock_path)

    assert lock.reference == fixture.reference
    assert lock.license == "CC-BY-NC-ND-4.0"
    assert lock.source_manifest_path == "docs/body-pack/source.json"
    assert lock.source_manifest_bytes == SOURCE_MANIFEST_BYTES
    assert lock.source_manifest_sha256 == "1" * 64
    assert {record.path for record in lock.files} == set(fixture.payloads)


def test_fetch_installs_only_the_locked_release_atomically(
    tmp_path: Path,
) -> None:
    fixture = build_body_pack_release_fixture(tmp_path / "release")
    data_root = tmp_path / "profile"

    def copy_locked_archive(_lock, destination: Path) -> None:
        shutil.copyfile(fixture.archive_path, destination)

    result = fetcher.fetch_body_pack(
        lock_path=fixture.lock_path,
        expected_reference=fixture.reference,
        data_root=data_root,
        download=copy_locked_archive,
    )

    assert result.output == data_root / "body-packs" / "mohan-body-v2"
    assert result.pack_id == "mohan-body-v2"
    assert result.pack_version == "1.0.0"
    assert result.fingerprint == fixture.reference.fingerprint
    assert (result.output / "LICENSE.txt").read_bytes() == fixture.payloads["LICENSE.txt"]
    assert (result.output / "NOTICE.md").read_bytes() == fixture.payloads["NOTICE.md"]
    assert (result.output / "manifest.json").read_bytes() == fixture.payloads["manifest.json"]
    assert not list((data_root / "body-packs").glob(".mohan-body-v2-fetch-*"))


def test_fetch_rejects_wrong_version_or_fingerprint_before_download(
    tmp_path: Path,
) -> None:
    fixture = build_body_pack_release_fixture(tmp_path / "release")
    calls: list[Path] = []

    def unexpected_download(_lock, destination: Path) -> None:
        calls.append(destination)

    with pytest.raises(fetcher.BodyPackFetchError, match="version_mismatch"):
        fetcher.fetch_body_pack(
            lock_path=fixture.lock_path,
            expected_reference={
                "id": "mohan-body-v2",
                "version": "1.0.1",
                "fingerprint": fixture.reference.fingerprint,
            },
            data_root=tmp_path / "version-profile",
            download=unexpected_download,
        )

    with pytest.raises(fetcher.BodyPackFetchError, match="fingerprint_mismatch"):
        fetcher.fetch_body_pack(
            lock_path=fixture.lock_path,
            expected_reference={
                "id": "mohan-body-v2",
                "version": "1.0.0",
                "fingerprint": "0" * 64,
            },
            data_root=tmp_path / "fingerprint-profile",
            download=unexpected_download,
        )

    assert calls == []


def test_bad_archive_checksum_leaves_no_install_directory(
    tmp_path: Path,
) -> None:
    fixture = build_body_pack_release_fixture(tmp_path / "release")
    data_root = tmp_path / "profile"

    def write_bad_archive(_lock, destination: Path) -> None:
        destination.write_bytes(b"tampered archive")

    with pytest.raises(fetcher.BodyPackFetchError, match="byte count differs from lock"):
        fetcher.fetch_body_pack(
            lock_path=fixture.lock_path,
            data_root=data_root,
            download=write_bad_archive,
        )

    assert not (data_root / "body-packs" / "mohan-body-v2").exists()
    assert not list((data_root / "body-packs").glob(".mohan-body-v2-fetch-*"))


@pytest.mark.parametrize("digest", ["A" * 64, "f" * 63, "f" * 65])
def test_body_pack_lock_rejects_malformed_sha256_values(
    tmp_path: Path,
    digest: str,
) -> None:
    fixture = build_body_pack_release_fixture(tmp_path / "release")
    lock = json.loads(fixture.lock_path.read_text(encoding="utf-8"))
    lock["archive"]["sha256"] = digest
    malformed = tmp_path / "malformed-lock.json"
    malformed.write_text(json.dumps(lock), encoding="utf-8", newline="\n")

    with pytest.raises(fetcher.BodyPackLockError, match="64 lowercase hexadecimal"):
        fetcher.load_body_pack_release_lock(malformed)


def test_same_size_archive_tampering_is_rejected_by_sha256(
    tmp_path: Path,
) -> None:
    fixture = build_body_pack_release_fixture(tmp_path / "release")
    data_root = tmp_path / "profile"

    def write_same_size_tampering(_lock, destination: Path) -> None:
        original = fixture.archive_path.read_bytes()
        destination.write_bytes(bytes((original[0] ^ 1,)) + original[1:])

    with pytest.raises(fetcher.BodyPackFetchError, match="SHA-256 differs from lock"):
        fetcher.fetch_body_pack(
            lock_path=fixture.lock_path,
            data_root=data_root,
            download=write_same_size_tampering,
        )

    assert not (data_root / "body-packs" / "mohan-body-v2").exists()
    assert not list((data_root / "body-packs").glob(".mohan-body-v2-fetch-*"))
