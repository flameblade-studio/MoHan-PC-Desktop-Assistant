"""Rebuild and verify the reproducible MoHan body-pack release lock."""
from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import shutil
lazy import stat
lazy import sys
lazy import zipfile
lazy from pathlib import Path, PurePosixPath
lazy from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools import fetch_body_pack

SOURCE_PATH = ROOT / "docs" / "body-pack" / "source.json"
LOCK_PATH = ROOT / "docs" / "body-pack" / "mohan-body-v2.lock.json"
BODY_ROOT = ROOT / "assets" / "body-packs" / "mohan-body-v2"
SOURCE_ROOT = BODY_ROOT / "source"
LAYER_ROOT = ROOT / "assets" / "characters" / "lin-keyun" / "body"
WORK_ROOT = ROOT / ".quality-tmp" / "body-release-1"
TEMP_ROOT = WORK_ROOT / "tmp"
BUILD_ROOT = WORK_ROOT / "build"
ARCHIVE_A = WORK_ROOT / "archive-a.zip"
ARCHIVE_B = WORK_ROOT / "archive-b.zip"
EXPECTED_FINGERPRINT = "2e9aa87c52b77946b517d18110a7e1bb5dad3961f66840a9d0bbbcaf4c7f6f39"
BODY_LICENSE = "CC-BY-NC-ND-4.0"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class BodyPackLockVerificationError(RuntimeError):
    """The source rebuild or locked body-pack release differs."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BodyPackLockVerificationError(f"Expected a JSON object: {path}")
    return value


def _configure_temp_environment() -> None:
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = str(TEMP_ROOT.resolve())
    os.environ["TEMP"] = path
    os.environ["TMP"] = path
    os.environ["TMPDIR"] = path
    import tempfile
    tempfile.tempdir = path


def _remove_work_path(path: Path) -> None:
    resolved_root = WORK_ROOT.resolve()
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(resolved_root) or resolved == resolved_root:
        raise BodyPackLockVerificationError(f"Refusing to clean outside the temporary build root: {path}")
    if path.is_symlink() or path.is_junction():
        raise BodyPackLockVerificationError(f"Temporary build path cannot be a link: {path}")
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _activate_mohan_runtime() -> None:
    from application.character_runtime_bootstrap import (
        DEFAULT_CHARACTER_ID,
        activate_product_character_runtime,
    )
    activate_product_character_runtime(ROOT, character_id=DEFAULT_CHARACTER_ID)


def _copy_legal_text(pack_root: Path) -> None:
    for name in ("LICENSE.txt", "NOTICE.md"):
        source = BODY_ROOT / name
        if not source.is_file():
            raise BodyPackLockVerificationError(f"Required legal file is missing: {source}")
        text = source.read_text(encoding="utf-8")
        (pack_root / name).write_text(text, encoding="utf-8", newline="\n")


def _build_package() -> tuple[Path, dict[str, Any], dict[str, Any]]:
    _configure_temp_environment()
    if BUILD_ROOT.exists():
        _remove_work_path(BUILD_ROOT)
    _activate_mohan_runtime()
    from tools import build_body_pack
    from domain.body_pack import parse_body_pack

    source = _read_json(SOURCE_PATH)
    pack = source["pack"]
    version = pack["version"]
    if pack["license"] != BODY_LICENSE:
        raise BodyPackLockVerificationError("source.json license differs from the approved body license")
    if pack["expected_fingerprint"] != EXPECTED_FINGERPRINT:
        raise BodyPackLockVerificationError("source.json expected fingerprint differs from the approved identity")

    stats = build_body_pack.build_release_body_pack(build_body_pack.BuildRequest(
        product_root=ROOT,
        bald_root=SOURCE_ROOT / "bald-natural11",
        layers_root=SOURCE_ROOT,
        output=BUILD_ROOT,
        license_text=BODY_LICENSE,
        mode="all",
        layer_mode="copy",
        fixed_core_root=SOURCE_ROOT / "final-core-masks",
        fixed_half_root=SOURCE_ROOT / "approved-cheek-b-body-11",
        character_layers_root=LAYER_ROOT,
        source_manifest=SOURCE_PATH,
        version=version,
    ))
    package_root = BUILD_ROOT / "mohan-body-v2"
    _copy_legal_text(package_root)
    manifest = _read_json(package_root / "manifest.json")
    parsed = parse_body_pack(manifest)
    if parsed.fingerprint != EXPECTED_FINGERPRINT:
        raise BodyPackLockVerificationError(
            f"Rebuilt fingerprint differs from the approved identity: {parsed.fingerprint}"
        )
    if manifest["license"] != BODY_LICENSE:
        raise BodyPackLockVerificationError("Rebuilt body manifest has a different license")
    return package_root, manifest, stats


def _file_records(package_root: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(package_root.rglob("*")):
        if path.is_symlink() or path.is_junction():
            raise BodyPackLockVerificationError(f"Release package contains a link: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(package_root).as_posix()
        pure = PurePosixPath(relative)
        if pure.is_absolute() or "\\" in relative or ".." in pure.parts or ":" in relative:
            raise BodyPackLockVerificationError(f"Unsafe release member path: {relative}")
        payload = path.read_bytes()
        records.append({"path": relative, "bytes": len(payload), "sha256": _sha256(payload)})
    return sorted(records, key=lambda item: item["path"])


def _referenced_body_files(manifest: dict[str, Any]) -> dict[str, str]:
    found: dict[str, str] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if set(value) == {"path", "sha256"}:
                path = value["path"]
                digest = value["sha256"]
                if path in found and found[path] != digest:
                    raise BodyPackLockVerificationError(f"Manifest binds conflicting hashes: {path}")
                found[path] = digest
            else:
                for item in value.values():
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for key in ("full_body", "half_body", "face_core_masks"):
        visit(manifest.get(key, {}))
    return found


def _verify_package_inventory(package_root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records = _file_records(package_root)
    actual_pngs = {item["path"]: item["sha256"] for item in records if item["path"].endswith(".png")}
    referenced = _referenced_body_files(manifest)
    if actual_pngs != referenced:
        raise BodyPackLockVerificationError(
            "Rebuilt PNG inventory differs from the body manifest: "
            f"unreferenced={sorted(set(actual_pngs) - set(referenced))}, "
            f"missing={sorted(set(referenced) - set(actual_pngs))}"
        )
    if {row["path"] for row in records} != {"manifest.json", "LICENSE.txt", "NOTICE.md", *actual_pngs}:
        raise BodyPackLockVerificationError("Release package contains an unsupported member")
    return records


def build_reproducible_zip(package_root: Path, archive_path: Path) -> dict[str, Any]:
    """Use the builder's canonical deterministic ZIP implementation."""
    from tools import build_body_pack
    return build_body_pack.build_reproducible_zip(package_root, archive_path)


def _check_archive_properties(archive_path: Path, records: list[dict[str, Any]]) -> None:
    expected_names = [row["path"] for row in records]
    by_path = {row["path"]: row for row in records}
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != expected_names or names != sorted(names):
            raise BodyPackLockVerificationError("ZIP member list is not exactly sorted and locked")
        for info in infos:
            mode = (info.external_attr >> 16) & 0xFFFF
            if (
                info.is_dir()
                or info.compress_type != zipfile.ZIP_STORED
                or info.date_time != ZIP_TIMESTAMP
                or mode != (stat.S_IFREG | 0o644)
            ):
                raise BodyPackLockVerificationError(f"ZIP member metadata is not canonical: {info.filename}")
            payload = archive.read(info)
            record = by_path[info.filename]
            if len(payload) != record["bytes"] or _sha256(payload) != record["sha256"]:
                raise BodyPackLockVerificationError(f"ZIP member bytes differ from the lock: {info.filename}")


def _create_lock_document(
    *,
    source: dict[str, Any],
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    archive_info: dict[str, Any],
    source_manifest_bytes: int,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    pack = source["pack"]
    version = pack["version"]
    pack_id = pack["id"]
    if pack_id != "mohan-body-v2":
        raise BodyPackLockVerificationError("Unsupported body-pack id in source.json")
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    return {
        "schema": fetch_body_pack.BODY_PACK_LOCK_SCHEMA,
        "schema_version": fetch_body_pack.BODY_PACK_LOCK_VERSION,
        "pack_id": pack_id,
        "pack_version": version,
        "package_hash": manifest["fingerprint"],
        "archive": {
            "asset_name": f"flameblade.{pack_id}-{version}.zip",
            "bytes": archive_info["bytes"],
            "sha256": archive_info["sha256"],
        },
        "source": {
            "repository": fetch_body_pack.SOURCE_REPOSITORY,
            "release_tag": f"{pack_id}-pack-v{version}",
        },
        "source_manifest": {
            "path": "docs/body-pack/source.json",
            "bytes": source_manifest_bytes,
            "sha256": source_manifest_sha256,
        },
        "license": BODY_LICENSE,
        "body_pack": {
            "id": manifest["id"],
            "version": manifest["version"],
            "fingerprint": manifest["fingerprint"],
            "manifest_bytes": len(manifest_bytes),
            "manifest_sha256": _sha256(manifest_bytes),
        },
        "files": records,
        "validation_limits": dict(fetch_body_pack.LOCK_LIMITS),
    }


def _release_archive_path(source: dict[str, Any]) -> Path:
    pack = source["pack"]
    return WORK_ROOT / f"flameblade.{pack['id']}-{pack['version']}.zip"


def _lock_payload_records(lock: Any) -> list[dict[str, Any]]:
    return [{"path": item.path, "bytes": item.bytes, "sha256": item.sha256} for item in lock.files]


def _compare_lock(lock: Any, document: dict[str, Any], source_size: int, source_hash: str) -> None:
    reference = lock.reference
    if (lock.pack_id, lock.pack_version, lock.package_hash, lock.license) != (
        document["pack_id"], document["pack_version"], document["package_hash"], document["license"]
    ):
        raise BodyPackLockVerificationError("Body-pack lock identity or license drifted")
    if lock.archive.asset_name != document["archive"]["asset_name"]:
        raise BodyPackLockVerificationError("Body-pack lock archive asset name drifted")
    if lock.archive.bytes != document["archive"]["bytes"] or lock.archive.sha256 != document["archive"]["sha256"]:
        raise BodyPackLockVerificationError("Body-pack release archive drifted")
    if lock.release_tag != document["source"]["release_tag"]:
        raise BodyPackLockVerificationError("Body-pack release tag drifted")
    if reference.fingerprint != document["body_pack"]["fingerprint"]:
        raise BodyPackLockVerificationError("Body-pack fingerprint drifted")
    if (lock.source_manifest_bytes, lock.source_manifest_sha256) != (source_size, source_hash):
        raise BodyPackLockVerificationError("Body-pack source manifest bytes or SHA-256 drifted")
    if _lock_payload_records(lock) != document["files"]:
        raise BodyPackLockVerificationError("Body-pack locked file inventory drifted")


def _prepare_release() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    _configure_temp_environment()
    source_bytes = SOURCE_PATH.read_bytes()
    source_hash = _sha256(source_bytes)
    source = _read_json(SOURCE_PATH)
    release_archive = _release_archive_path(source)
    package_root, manifest, _stats = _build_package()
    records = _verify_package_inventory(package_root, manifest)
    for path in (ARCHIVE_A, ARCHIVE_B, release_archive):
        if path.exists():
            _remove_work_path(path)
    archive_a = build_reproducible_zip(package_root, ARCHIVE_A)
    archive_b = build_reproducible_zip(package_root, ARCHIVE_B)
    if (archive_a["bytes"], archive_a["sha256"]) != (archive_b["bytes"], archive_b["sha256"]):
        raise BodyPackLockVerificationError("Two consecutive deterministic ZIP builds differ")
    _check_archive_properties(ARCHIVE_A, records)
    _check_archive_properties(ARCHIVE_B, records)
    shutil.copyfile(ARCHIVE_A, release_archive)
    document = _create_lock_document(
        source=source,
        manifest=manifest,
        records=records,
        archive_info=archive_a,
        source_manifest_bytes=len(source_bytes),
        source_manifest_sha256=source_hash,
    )
    return document, manifest, records, archive_a


def update_lock() -> dict[str, Any]:
    document, _manifest, _records, archive_info = _prepare_release()
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    lock = fetch_body_pack.load_body_pack_release_lock(LOCK_PATH)
    _compare_lock(lock, document, len(SOURCE_PATH.read_bytes()), _sha256(SOURCE_PATH.read_bytes()))
    return {
        "mode": "updated",
        "lock": LOCK_PATH.relative_to(ROOT).as_posix(),
        "archive": (WORK_ROOT / document["archive"]["asset_name"]).relative_to(ROOT).as_posix(),
        "archive_bytes": archive_info["bytes"],
        "archive_sha256": archive_info["sha256"],
        "fingerprint": document["package_hash"],
        "files": len(document["files"]),
    }


def verify_lock() -> dict[str, Any]:
    lock = fetch_body_pack.load_body_pack_release_lock(LOCK_PATH)
    document, _manifest, _records, archive_info = _prepare_release()
    source_payload = SOURCE_PATH.read_bytes()
    _compare_lock(lock, document, len(source_payload), _sha256(source_payload))
    if (lock.archive.bytes, lock.archive.sha256) != (archive_info["bytes"], archive_info["sha256"]):
        raise BodyPackLockVerificationError("Rebuilt ZIP differs from the locked release archive")
    return {
        "mode": "verified",
        "lock": LOCK_PATH.relative_to(ROOT).as_posix(),
        "archive_bytes": archive_info["bytes"],
        "archive_sha256": archive_info["sha256"],
        "fingerprint": lock.reference.fingerprint,
        "files": len(lock.files),
    }


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--update", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args(arguments)
    try:
        result = update_lock() if args.update else verify_lock()
    except (BodyPackLockVerificationError, fetch_body_pack.BodyPackFetchError,
            fetch_body_pack.BodyPackLockError, OSError, ValueError, KeyError) as error:
        print(f"BODY_PACK_LOCK_ERROR={error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print("BODY_PACK_LOCK_VALID=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
