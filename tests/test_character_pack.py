"""Synthetic, deterministic character-pack acceptance and hostile-input checks."""
from __future__ import annotations

lazy import base64
lazy import copy
lazy import hashlib
lazy import io
lazy import json
lazy import os
lazy import stat
lazy import struct
lazy import sys
lazy import zipfile
lazy from dataclasses import replace
lazy from contextlib import contextmanager
lazy from pathlib import Path

lazy import pytest

lazy from domain.character_pack.models import CharacterPackSignature, ValidationLimits
lazy from domain.character_pack import archive as character_archive
lazy from domain.character_pack.archive import _read_limited
lazy from domain.character_pack.validation import (
    SCHEMA,
    compute_package_hash,
    validate_character_pack,
)

ENGINE_VERSION = "1.2.3"
COMPONENTS = ("program_data", "character_art", "persona_dialogue", "voice")
PAYLOAD = b'{"source":"synthetic-test-only"}\n'
EXPECTED_FILES = 1
MINIMAL_LIMIT = 1
SIGNATURE_BYTES = 64
DEFAULT_LIMITS = ValidationLimits()


def minimal_manifest() -> dict:
    digest = hashlib.sha256(PAYLOAD).hexdigest()
    return {
        "schema": SCHEMA,
        "pack_id": "example.synthetic",
        "pack_version": "1.0.0",
        "display_names": {"zh-TW": "合成測試", "zh-CN": "合成测试", "en": "Synthetic test", "ja-JP": "合成テスト"},
        "character": {"id": "example.synthetic", "canonical_name": "Synthetic", "aliases": ["Fixture"]},
        "engine_compatibility": {
            "api_version": 1, "min_engine_version": "1.0.0",
            "max_engine_version_exclusive": "2.0.0", "required_features": [],
        },
        "distribution": {"standalone_downloadable": True, "access": "owner_decision_pending", "redistribution": "owner_decision_pending"},
        "licenses": {
            component: {"status": "owner_decision_pending", "rights_holder": "Synthetic fixture author", "license_expression": None, "notice_path": None}
            for component in COMPONENTS
        },
        "source_refs": [{"path": "provenance/source.json", "sha256": digest, "scope": "synthetic fixture only"}],
        "approval_refs": [],
        "files": [{"path": "provenance/source.json", "sha256": digest, "bytes": len(PAYLOAD), "media_type": "application/json", "license_component": "program_data"}],
        "package_hash": "0" * 64,
    }


def write_package(tmp_path: Path, manifest: dict, kind: str, *, extra: dict[str, bytes] | None = None) -> Path:
    manifest["package_hash"] = compute_package_hash(manifest)
    entries = {"manifest.json": (json.dumps(manifest, ensure_ascii=False) + "\n").encode("utf-8"), "provenance/source.json": PAYLOAD}
    entries.update(extra or {})
    if kind == "zip":
        path = tmp_path / "character.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        return path
    path = tmp_path / "character"
    for name, data in entries.items():
        destination = path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    return path


def assert_rejected(source: Path, code: str, **kwargs) -> None:
    result = validate_character_pack(source, engine_version=ENGINE_VERSION, **kwargs)
    assert not result.valid
    assert result.manifest is None
    assert result.issues[0].code == code


@pytest.mark.parametrize("kind", ["directory", "zip"])
def test_minimal_package_passes(tmp_path: Path, kind: str) -> None:
    manifest = minimal_manifest()
    source = write_package(tmp_path, manifest, kind)
    before = source.stat().st_mtime_ns
    result = validate_character_pack(source, engine_version=ENGINE_VERSION)
    assert result.valid and not result.issues
    assert result.source_kind == kind
    assert result.checked_files == EXPECTED_FILES
    assert result.checked_bytes == len(PAYLOAD)
    assert result.package_hash == manifest["package_hash"]
    assert result.manifest.access == "owner_decision_pending"
    assert result.manifest.aliases == ("Fixture",)
    assert result.signature_status == "absent"
    assert source.stat().st_mtime_ns == before


@pytest.mark.parametrize("kind", ["directory", "zip"])
@pytest.mark.parametrize(("field", "value", "code"), [
    ("schema", "flameblade.character-pack.v2", "unsupported_schema"),
    ("pack_version", "1.0", "invalid_manifest"),
    ("pack_version", "01.0.0", "invalid_manifest"),
    ("pack_version", "1.0.0-beta", "invalid_manifest"),
    ("pack_version", "1.0." + "9" * 5000, "invalid_manifest"),
    ("pack_id", [], "invalid_manifest"),
    ("unexpected_field", True, "invalid_manifest"),
    ("files", [], "invalid_manifest"),
    ("signature", {"algorithm": "unknown", "key_id": "test", "value": ""}, "invalid_signature"),
    ("source_refs", [], "invalid_manifest"),
])
def test_invalid_schema_fields(tmp_path: Path, kind: str, field: str, value: object, code: str) -> None:
    manifest = minimal_manifest()
    manifest[field] = value
    assert_rejected(write_package(tmp_path, manifest, kind), code)


@pytest.mark.parametrize("kind", ["directory", "zip"])
@pytest.mark.parametrize("path", ["../escape.json", "/absolute.json", "C:/absolute.json", "a/../b.json", "a\\b.json", "./file.json", "a//b.json", "a:stream", "CON.txt", "COM\u00b9.txt", "lpt\u00b2.json", "COM\u00b3", "file. ", "a\x00b", "a\nb", "a?b", "cafe\u0301.json"])
def test_manifest_paths_fail_closed(tmp_path: Path, kind: str, path: str) -> None:
    manifest = minimal_manifest()
    manifest["files"][0]["path"] = path
    assert_rejected(write_package(tmp_path, manifest, kind), "unsafe_path")


@pytest.mark.parametrize("path", ["../escape.json", "/absolute.json", "C:/absolute.json"])
def test_zip_member_traversal(tmp_path: Path, path: str) -> None:
    source = write_package(tmp_path, minimal_manifest(), "zip", extra={path: b"untrusted"})
    assert_rejected(source, "unsafe_path")
    assert not (tmp_path / "escape.json").exists()


@pytest.mark.parametrize("kind", ["directory", "zip"])
@pytest.mark.parametrize(("case", "code"), [
    ("missing", "missing_file"), ("hash", "file_hash_mismatch"),
    ("size", "size_mismatch"), ("reference", "reference_hash_mismatch"),
    ("duplicate", "duplicate_path"), ("license", "license_incomplete"),
    ("rights", "invalid_manifest"), ("distribution_type", "invalid_manifest"),
    ("executable", "forbidden_file"),
])
def test_payload_and_rights_rejections(tmp_path: Path, kind: str, case: str, code: str) -> None:
    manifest = minimal_manifest()
    if case == "missing":
        manifest["files"][0]["path"] = manifest["source_refs"][0]["path"] = "missing.json"
    elif case == "hash":
        manifest["files"][0]["sha256"] = manifest["source_refs"][0]["sha256"] = "0" * 64
    elif case == "size":
        manifest["files"][0]["bytes"] += 1
    elif case == "reference":
        manifest["source_refs"][0]["sha256"] = "0" * 64
    elif case == "duplicate":
        manifest["files"].append(copy.deepcopy(manifest["files"][0]))
    elif case == "license":
        del manifest["licenses"]["voice"]
    elif case == "rights":
        del manifest["licenses"]["voice"]["rights_holder"]
    elif case == "distribution_type":
        manifest["distribution"]["access"] = []
    elif case == "executable":
        manifest["files"][0]["path"] = "execute.py"
    assert_rejected(write_package(tmp_path, manifest, kind), code)


@pytest.mark.parametrize("version", ["0.9.9", "2.0.0", "3.0.0"])
@pytest.mark.parametrize("kind", ["directory", "zip"])
def test_incompatible_engine(tmp_path: Path, kind: str, version: str) -> None:
    result = validate_character_pack(write_package(tmp_path, minimal_manifest(), kind), engine_version=version)
    assert result.issues[0].code == "incompatible_engine"
    assert not result.valid


def test_api_and_feature_compatibility(tmp_path: Path) -> None:
    manifest = minimal_manifest()
    manifest["engine_compatibility"]["required_features"] = ["blink"]
    source = write_package(tmp_path, manifest, "directory")
    assert_rejected(source, "missing_engine_feature")
    assert_rejected(source, "incompatible_engine", engine_api_version=2)
    assert validate_character_pack(source, engine_version="1.0.0", engine_features=["blink"]).valid


@pytest.mark.parametrize("kind", ["directory", "zip"])
@pytest.mark.parametrize(("limit", "code"), [
    ("max_file_bytes", "file_too_large"), ("max_manifest_bytes", "file_too_large"),
    ("max_total_bytes", "package_too_large"), ("max_files", "too_many_files"),
])
def test_resource_limits(tmp_path: Path, kind: str, limit: str, code: str) -> None:
    source = write_package(tmp_path, minimal_manifest(), kind)
    assert_rejected(source, code, limits=replace(DEFAULT_LIMITS, **{limit: MINIMAL_LIMIT}))


def test_zip_bomb_and_archive_limit(tmp_path: Path) -> None:
    source = write_package(tmp_path, minimal_manifest(), "zip")
    assert_rejected(source, "archive_too_large", limits=replace(DEFAULT_LIMITS, max_archive_bytes=MINIMAL_LIMIT))
    with zipfile.ZipFile(source, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bomb.bin", b"0" * (256 * 1024))
    assert_rejected(source, "suspicious_compression_ratio")


def test_zip_directory_and_symlink_entries(tmp_path: Path) -> None:
    source = write_package(tmp_path, minimal_manifest(), "zip")
    with zipfile.ZipFile(source, "a") as archive:
        archive.writestr("provenance/", b"")
    assert validate_character_pack(source, engine_version=ENGINE_VERSION).valid
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(source, "a") as archive:
        archive.writestr(info, "../outside")
    assert_rejected(source, "unsafe_path")


def test_directory_symlink_without_os_privileges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = write_package(tmp_path, minimal_manifest(), "directory")
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path.name == "source.json" or original(path))
    assert_rejected(source, "unsafe_path")


@pytest.mark.parametrize("kind", ["directory", "zip"])
def test_undeclared_files(tmp_path: Path, kind: str) -> None:
    assert_rejected(write_package(tmp_path, minimal_manifest(), kind, extra={"extra.bin": b"extra"}), "undeclared_file")


def test_logical_hash_is_order_independent_and_metadata_bound(tmp_path: Path) -> None:
    manifest = minimal_manifest()
    expected = compute_package_hash(manifest)
    manifest["display_names"] = dict(reversed(list(manifest["display_names"].items())))
    manifest["licenses"] = dict(reversed(list(manifest["licenses"].items())))
    assert compute_package_hash(manifest) == expected
    assert validate_character_pack(write_package(tmp_path, manifest, "directory"), engine_version=ENGINE_VERSION).valid
    manifest["pack_version"] = "1.0.1"
    assert compute_package_hash(manifest) != expected


def test_tampered_manifest_hash(tmp_path: Path) -> None:
    source = write_package(tmp_path, minimal_manifest(), "directory")
    path = source / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["distribution"]["access"] = "public"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert_rejected(source, "package_hash_mismatch")


@pytest.mark.parametrize("content", ['{"schema":"a","schema":"b"}', '{"schema":NaN}', "[]", "{", "\ufeff{}", '{"schema":' + "9" * 5000 + "}"])
def test_bad_json(tmp_path: Path, content: str) -> None:
    source = tmp_path / "character"
    source.mkdir()
    (source / "manifest.json").write_text(content, encoding="utf-8")
    result = validate_character_pack(source, engine_version=ENGINE_VERSION)
    assert not result.valid and result.manifest is None
    assert result.issues[0].code in {"invalid_manifest", "duplicate_json_key"}


def test_license_options_and_dependencies_preserved(tmp_path: Path) -> None:
    manifest = minimal_manifest()
    manifest["licenses"]["character_art"]["status"] = "all_rights_reserved"
    manifest["licenses"]["program_data"].update(status="declared_license", license_expression="LicenseRef-Synthetic")
    manifest["dependencies"] = [{"id": "example.outfit", "kind": "outfit_pack", "min_version": "1.0.0", "max_version_exclusive": "2.0.0", "required": False}]
    result = validate_character_pack(write_package(tmp_path, manifest, "directory"), engine_version=ENGINE_VERSION)
    assert result.valid
    assert result.manifest.dependencies[0].kind == "outfit_pack"
    assert not result.manifest.dependencies[0].required
    assert result.manifest.licenses[1].status == "all_rights_reserved"
    manifest["dependencies"][0]["kind"] = []
    assert_rejected(write_package(tmp_path, manifest, "directory"), "invalid_manifest")


def test_signature_requires_trusted_verification(tmp_path: Path) -> None:
    manifest = minimal_manifest()
    manifest["signature"] = {"algorithm": "ed25519", "key_id": "example.key", "value": base64.b64encode(b"s" * SIGNATURE_BYTES).decode("ascii")}
    source = write_package(tmp_path, manifest, "directory")
    assert_rejected(source, "signature_verifier_required")
    assert_rejected(source, "signature_verification_failed", signature_verifier=lambda _signature, _digest: False)

    def verifier(signature: CharacterPackSignature, digest: bytes) -> bool:
        assert signature.key_id == "example.key"
        assert digest == bytes.fromhex(manifest["package_hash"])
        return True

    assert validate_character_pack(source, engine_version=ENGINE_VERSION, signature_verifier=verifier).signature_status == "verified"

    def broken_verifier(_signature: CharacterPackSignature, _digest: bytes) -> bool:
        raise RuntimeError("fixture verifier unavailable")

    assert_rejected(source, "signature_verification_failed", signature_verifier=broken_verifier)


def test_unreadable_sources_and_invalid_limits(tmp_path: Path) -> None:
    assert_rejected(tmp_path / "missing", "source_not_found")
    source = tmp_path / "broken.zip"
    source.write_bytes(b"invalid zip bytes")
    assert_rejected(source, "invalid_archive")
    assert_rejected(source, "invalid_limits", limits=replace(DEFAULT_LIMITS, max_files=0))
    source = write_package(tmp_path, minimal_manifest(), "directory")
    (source / "manifest.json").unlink()
    assert_rejected(source, "missing_manifest")


@pytest.mark.parametrize("kind", ["directory", "zip"])
def test_hash_bound_approval_and_license_notices(tmp_path: Path, kind: str) -> None:
    manifest = minimal_manifest()
    manifest["approval_refs"] = [{"path": "provenance/source.json", "sha256": hashlib.sha256(PAYLOAD).hexdigest(), "scope": "synthetic appearance only"}]
    manifest["licenses"]["program_data"]["notice_path"] = "provenance/source.json"
    source = write_package(tmp_path, manifest, kind)
    assert validate_character_pack(source, engine_version=ENGINE_VERSION).valid
    manifest["approval_refs"][0]["sha256"] = "f" * 64
    assert_rejected(write_package(tmp_path, manifest, kind), "reference_hash_mismatch")


def test_new_domain_is_presentation_independent() -> None:
    assert not any(name.startswith(("presentation", "PySide6")) for name in sys.modules)


def test_documented_minimal_example_is_valid(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1] / "docs/character-pack"
    manifest = json.loads((root / "minimal-manifest.json").read_text(encoding="utf-8"))
    assert (root / "example-source.json").read_bytes() == PAYLOAD
    source = write_package(tmp_path, copy.deepcopy(manifest), "directory")
    assert compute_package_hash(manifest) == manifest["package_hash"]
    assert validate_character_pack(source, engine_version=ENGINE_VERSION).valid


def test_streaming_limit_stops_after_one_excess_byte() -> None:
    limit = 1024
    stream = io.BytesIO(b"x" * (limit * 100))
    with pytest.raises(ValueError, match="read limit"):
        _read_limited(stream, limit, "synthetic.bin")
    assert stream.tell() == limit + 1


@pytest.mark.parametrize("parent", ["provenance", "PROVENANCE"])
@pytest.mark.parametrize("child", ["provenance/source.json", "PROVENANCE/source.json"])
@pytest.mark.parametrize("parent_first", [True, False])
def test_zip_file_cannot_be_an_implicit_directory(tmp_path: Path, parent: str, child: str, parent_first: bool) -> None:
    source = write_package(tmp_path, minimal_manifest(), "zip")
    with zipfile.ZipFile(source) as archive:
        entries = [(child if info.filename == "provenance/source.json" else info.filename, archive.read(info)) for info in archive.infolist()]
    entry = (parent, b"file blocking the source directory")
    entries = [entry, *entries] if parent_first else [*entries, entry]
    with zipfile.ZipFile(source, "w") as archive:
        for name, data in entries:
            archive.writestr(name, data)
    assert_rejected(source, "unsafe_path")


@pytest.mark.parametrize(("name", "file_type"), [("folder", stat.S_IFDIR), ("folder/", stat.S_IFREG)])
def test_zip_entry_name_must_agree_with_type(tmp_path: Path, name: str, file_type: int) -> None:
    source = write_package(tmp_path, minimal_manifest(), "zip")
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    info.external_attr = (file_type | 0o755) << 16
    with zipfile.ZipFile(source, "a") as archive:
        archive.writestr(info, b"")
    assert_rejected(source, "invalid_archive")


@pytest.mark.parametrize("case", ["encrypted", "unsupported_compression", "bad_crc"])
def test_damaged_or_unsupported_zip_members_fail_closed(tmp_path: Path, case: str) -> None:
    source = write_package(tmp_path, minimal_manifest(), "zip")
    data = bytearray(source.read_bytes())
    central = data.index(b"PK\x01\x02")
    if case == "encrypted":
        struct.pack_into("<H", data, 6, 1)
        struct.pack_into("<H", data, central + 8, 1)
        code = "encrypted_member"
    elif case == "unsupported_compression":
        struct.pack_into("<H", data, 8, 99)
        struct.pack_into("<H", data, central + 10, 99)
        code = "invalid_archive"
    else:
        name_size, extra_size = struct.unpack_from("<HH", data, 26)
        data[30 + name_size + extra_size] ^= 1
        code = "invalid_archive"
    source.write_bytes(data)
    assert_rejected(source, code)


@pytest.mark.parametrize("kind", ["directory", "zip"])
def test_all_resource_boundaries_are_inclusive(tmp_path: Path, kind: str) -> None:
    manifest = minimal_manifest()
    source = write_package(tmp_path, manifest, kind)
    manifest_size = len((json.dumps(manifest, ensure_ascii=False) + "\n").encode("utf-8"))
    limits = replace(
        DEFAULT_LIMITS,
        max_manifest_bytes=manifest_size,
        max_file_bytes=len(PAYLOAD),
        max_total_bytes=manifest_size + len(PAYLOAD),
        max_files=3,
        max_archive_bytes=source.stat().st_size if kind == "zip" else DEFAULT_LIMITS.max_archive_bytes,
    )
    result = validate_character_pack(source, engine_version="1.0.0", limits=limits)
    assert result.valid and result.checked_bytes == len(PAYLOAD)


def test_directory_and_zip_share_the_same_logical_hash(tmp_path: Path) -> None:
    directory = write_package(tmp_path, minimal_manifest(), "directory")
    archive = write_package(tmp_path, minimal_manifest(), "zip")
    results = [validate_character_pack(source, engine_version=ENGINE_VERSION) for source in (directory, archive)]
    assert all(result.valid for result in results)
    assert results[0].package_hash == results[1].package_hash


@pytest.mark.parametrize(("case", "code"), [
    ("count", "too_many_files"),
    ("forged_count", "too_many_files"),
    ("metadata", "zip_directory_too_large"),
    ("bounds", "invalid_archive"),
    ("zip64", "invalid_archive"),
    ("multidisk", "invalid_archive"),
])
def test_zip_preflight_rejects_before_allocating_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, code: str,
) -> None:
    source = write_package(tmp_path, minimal_manifest(), "zip", extra={"extra": b""})
    limits = DEFAULT_LIMITS
    data = bytearray(source.read_bytes())
    end = data.rindex(b"PK\x05\x06")
    if case in {"count", "forged_count"}:
        limits = replace(limits, max_files=2)
        if case == "forged_count":
            struct.pack_into("<HH", data, end + 8, 2, 2)
    elif case == "metadata":
        limits = replace(limits, max_zip_directory_bytes=1)
    elif case == "bounds":
        struct.pack_into("<I", data, end + 16, 0)
    elif case == "zip64":
        struct.pack_into("<HH", data, end + 8, 65535, 65535)
    else:
        struct.pack_into("<H", data, end + 4, 1)
    source.write_bytes(data)
    monkeypatch.setattr(zipfile, "ZipFile", lambda _source: pytest.fail("ZIP index was allocated before preflight rejection"))
    assert_rejected(source, code, limits=limits)


def test_zip_comments_and_local_zip64_headers_are_supported(tmp_path: Path) -> None:
    source = write_package(tmp_path, minimal_manifest(), "zip")
    with zipfile.ZipFile(source) as archive:
        entries = [(info.filename, archive.read(info)) for info in archive.infolist()]
    with zipfile.ZipFile(source, "w") as archive:
        archive.comment = b"ordinary character-pack comment"
        for name, data in entries:
            with archive.open(name, "w", force_zip64=True) as stream:
                stream.write(data)
    assert validate_character_pack(source, engine_version=ENGINE_VERSION).valid


@pytest.mark.parametrize("case", ["valid", "too_many_entries", "bad_payload_hash"])
def test_zip_preflight_and_reads_share_one_closed_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str,
) -> None:
    manifest = minimal_manifest()
    if case == "bad_payload_hash":
        manifest["files"][0]["sha256"] = manifest["source_refs"][0]["sha256"] = "0" * 64
    source = write_package(tmp_path, manifest, "zip")
    original_preflight = character_archive._preflight_zip_directory
    original_zip = zipfile.ZipFile
    streams = []

    def preflight(stream, limits):
        assert not isinstance(stream, (str, Path))
        streams.append(stream)
        original_preflight(stream, limits)

    def indexed_zip(stream):
        assert stream is streams[0]
        return original_zip(stream)

    monkeypatch.setattr(character_archive, "_preflight_zip_directory", preflight)
    monkeypatch.setattr(zipfile, "ZipFile", indexed_zip)
    limits = replace(DEFAULT_LIMITS, max_files=1) if case == "too_many_entries" else DEFAULT_LIMITS
    result = validate_character_pack(source, engine_version=ENGINE_VERSION, limits=limits)
    assert result.valid == (case == "valid")
    assert len(streams) == EXPECTED_FILES and streams[0].closed


def test_directory_entry_limit_stops_enumeration_early(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = write_package(tmp_path, minimal_manifest(), "directory", extra={f"extra-{index}": b"" for index in range(20)})
    limit = 4
    original_scandir = os.scandir
    consumed = []

    def tracked_entries(entries):
        for entry in entries:
            consumed.append(entry.name)
            yield entry

    @contextmanager
    def tracked_scandir(path):
        with original_scandir(path) as entries:
            yield tracked_entries(entries)

    monkeypatch.setattr(os, "scandir", tracked_scandir)
    assert_rejected(source, "too_many_files", limits=replace(DEFAULT_LIMITS, max_files=limit))
    assert len(consumed) == limit + 1
