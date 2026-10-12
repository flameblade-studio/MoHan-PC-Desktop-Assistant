"""Small locked MoHan body-pack release fixtures for downloader coverage."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import zipfile
lazy from dataclasses import dataclass
lazy from io import BytesIO
lazy from pathlib import Path
lazy from typing import Any

lazy from PIL import Image
lazy from domain.body_pack import BodyPackReference, compute_body_pack_fingerprint
lazy from domain.character_pose import canonical_view_id

BODY_PACK_ID = "mohan-body-v2"
BODY_PACK_VERSION = "1.0.0"
BODY_PACK_LICENSE = "CC-BY-NC-ND-4.0"
SOURCE_MANIFEST_BYTES = 128
SOURCE_REPOSITORY = "flameblade-studio/MoHan-PC-Desktop-Assistant"
RELEASE_TAG = f"{BODY_PACK_ID}-pack-v{BODY_PACK_VERSION}"
ASSET_NAME = f"flameblade.{BODY_PACK_ID}-{BODY_PACK_VERSION}.zip"
VALIDATION_LIMITS = {
    "max_archive_bytes": 1_073_741_824,
    "max_compression_ratio": 100,
    "max_file_bytes": 67_108_864,
    "max_files": 4096,
    "max_manifest_bytes": 1_048_576,
    "max_total_uncompressed_bytes": 1_073_741_824,
    "max_zip_dir_bytes": 8_388_608,
}


@dataclass(frozen=True, slots=True)
class BodyPackReleaseFixture:
    lock_path: Path
    archive_path: Path
    payloads: dict[str, bytes]
    reference: BodyPackReference


def build_body_pack_release_fixture(base: Path) -> BodyPackReleaseFixture:
    """Write an exact lock and deterministic local archive for release tests."""

    base.mkdir(parents=True, exist_ok=True)
    full_png = _png((1024, 1536), (40, 60, 80, 255))
    half_png = _png((1254, 1254), (10, 20, 30, 255))
    mask_png = _png((1024, 1536), (255, 255, 255, 255))
    records = {
        "frames/full/front.png": full_png,
        "frames/half/portrait.png": half_png,
        "masks/front.png": mask_png,
    }
    full_views = {
        canonical_view_id(yaw): {"rest": _file("frames/full/front.png", full_png)}
        for yaw in range(-180, 180, 15)
    }
    face_core_masks = {
        canonical_view_id(yaw): _file("masks/front.png", mask_png)
        for yaw in range(-180, 180, 15)
    }
    manifest: dict[str, Any] = {
        "schema": "mohan.body-pack.v1",
        "id": BODY_PACK_ID,
        "version": BODY_PACK_VERSION,
        "license": BODY_PACK_LICENSE,
        "full_body": full_views,
        "half_body": {
            "portrait": {"rest": _file("frames/half/portrait.png", half_png)},
        },
        "face_core_masks": face_core_masks,
    }
    manifest["fingerprint"] = compute_body_pack_fingerprint(manifest)
    manifest_bytes = _json_bytes(manifest)
    payloads = {
        "manifest.json": manifest_bytes,
        **records,
        "LICENSE.txt": b"CC BY-NC-ND 4.0 synthetic test license\n",
        "NOTICE.md": b"Synthetic test notice; no release asset is included.\n",
    }
    archive_path = base / ASSET_NAME
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)
    reference = BodyPackReference(
        BODY_PACK_ID,
        BODY_PACK_VERSION,
        str(manifest["fingerprint"]),
    )
    lock = {
        "schema": "flameblade.body-pack-lock.v1",
        "schema_version": 1,
        "pack_id": BODY_PACK_ID,
        "pack_version": BODY_PACK_VERSION,
        "package_hash": reference.fingerprint,
        "archive": {
            "asset_name": ASSET_NAME,
            "bytes": archive_path.stat().st_size,
            "sha256": _sha256(archive_path.read_bytes()),
        },
        "source": {
            "repository": SOURCE_REPOSITORY,
            "release_tag": RELEASE_TAG,
        },
        "source_manifest": {
            "path": "docs/body-pack/source.json",
            "bytes": SOURCE_MANIFEST_BYTES,
            "sha256": "1" * 64,
        },
        "license": BODY_PACK_LICENSE,
        "body_pack": {
            "id": reference.id,
            "version": reference.version,
            "fingerprint": reference.fingerprint,
            "manifest_bytes": len(manifest_bytes),
            "manifest_sha256": _sha256(manifest_bytes),
        },
        "files": [
            {"path": name, "bytes": len(payload), "sha256": _sha256(payload)}
            for name, payload in sorted(payloads.items())
        ],
        "validation_limits": VALIDATION_LIMITS,
    }
    lock_path = base / "body-pack.lock.json"
    lock_path.write_bytes(_json_bytes(lock))
    return BodyPackReleaseFixture(lock_path, archive_path, payloads, reference)


def _png(size: tuple[int, int], color: tuple[int, int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGBA", size, color).save(output, format="PNG", optimize=True)
    return output.getvalue()


def _file(path: str, payload: bytes) -> dict[str, str]:
    return {"path": path, "sha256": _sha256(payload)}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(document: object) -> bytes:
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
