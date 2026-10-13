"""Fetch, checksum, validate, and atomically install the locked MoHan body pack."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import re
lazy import stat
lazy import sys
lazy import tempfile
lazy import zipfile
lazy from collections.abc import Callable, Mapping, Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath
lazy from typing import Any
lazy from urllib.error import HTTPError, URLError
lazy from urllib.parse import quote, urlparse
lazy from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from domain.body_pack import (
    BodyPackError,
    BodyPackReference,
    parse_body_pack,
    parse_body_pack_reference,
)
lazy from infrastructure.installed_body_packs import (
    MOHAN_BODY_PACK_ID,
    BodyPackInstallError,
    install_staged_body_pack,
    installed_body_pack_path,
    installed_body_pack_root,
)
lazy from tools.verify_character_pack_lock import SOURCE_REPOSITORY

BODY_PACK_LOCK_SCHEMA = "flameblade.body-pack-lock.v1"
BODY_PACK_LOCK_VERSION = 1
BODY_PACK_LICENSE = "CC-BY-NC-ND-4.0"
BODY_PACK_VERSION_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-((?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z"
)
DEFAULT_BODY_PACK_LOCK = ROOT / "docs" / "body-pack" / "mohan-body-v2.lock.json"
GITHUB_WEB_ROOT = "https://github.com"
USER_AGENT = "MoHan-Body-Pack-Fetch"
COPY_BUFFER_BYTES = 1024 * 1024
MAX_SOURCE_MANIFEST_BYTES = 1_048_576
HTTP_SUCCESS_MINIMUM = 200
HTTP_SUCCESS_EXCLUSIVE_MAXIMUM = 300
REQUIRED_LEGAL_FILES = frozenset({"LICENSE.txt", "NOTICE.md"})
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
LOCK_LIMITS = {
    "max_archive_bytes": 1_073_741_824,
    "max_compression_ratio": 100,
    "max_file_bytes": 67_108_864,
    "max_files": 4096,
    "max_manifest_bytes": 1_048_576,
    "max_total_uncompressed_bytes": 1_073_741_824,
    "max_zip_dir_bytes": 8_388_608,
}
ArchiveDownloader = Callable[["BodyPackReleaseLock", Path], None]
UrlOpen = Callable[[Request, float], Any]


class BodyPackLockError(ValueError):
    """The body-pack lock is missing, malformed, or outside its release profile."""


class BodyPackFetchError(RuntimeError):
    """A locked body-pack release could not be installed safely."""


@dataclass(frozen=True, slots=True)
class LockedBodyArchive:
    asset_name: str
    bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class LockedBodyFile:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class BodyPackReleaseLock:
    pack_id: str
    pack_version: str
    package_hash: str
    archive: LockedBodyArchive
    repository: str
    release_tag: str
    license: str
    source_manifest_path: str
    source_manifest_bytes: int
    source_manifest_sha256: str
    reference: BodyPackReference
    manifest_bytes: int
    manifest_sha256: str
    files: tuple[LockedBodyFile, ...]
    validation_limits: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class BodyPackFetchResult:
    """Identity and measured local path for one completed installation."""

    output: Path
    pack_id: str
    pack_version: str
    fingerprint: str
    checked_files: int
    checked_bytes: int


class _HttpsRedirectHandler(HTTPRedirectHandler):
    """Allow signed GitHub release redirects only when they remain on HTTPS."""

    def redirect_request(
        self,
        request: Request,
        response: object,
        code: int,
        message: str,
        headers: object,
        new_url: str,
    ) -> Request | None:
        parsed = urlparse(new_url)
        if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None:
            return None
        return super().redirect_request(request, response, code, message, headers, new_url)


def load_body_pack_release_lock(path: str | Path = DEFAULT_BODY_PACK_LOCK) -> BodyPackReleaseLock:
    """Read and enforce the complete pinned body-pack release lock."""

    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        document = json.loads(
            candidate.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except BodyPackLockError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise BodyPackLockError(f"body-pack lock is unreadable: {candidate}") from error
    return _parse_lock_document(document)


def fetch_body_pack(
    *,
    lock_path: str | Path = DEFAULT_BODY_PACK_LOCK,
    data_root: str | Path | None = None,
    expected_reference: BodyPackReference | Mapping[str, object] | None = None,
    download: ArchiveDownloader | None = None,
) -> BodyPackFetchResult:
    """Install only the release ZIP pinned by the body-pack lock."""

    lock = load_body_pack_release_lock(lock_path)
    if expected_reference is not None:
        _require_expected_reference(expected_reference, lock.reference)

    body_root = installed_body_pack_root(data_root)
    try:
        body_root.mkdir(parents=True, exist_ok=True)
        if body_root.is_symlink() or body_root.is_junction():
            raise BodyPackFetchError("the userdata body-pack directory cannot be a link")
        body_root = body_root.resolve(strict=True)
    except BodyPackFetchError:
        raise
    except OSError as error:
        raise BodyPackFetchError("the userdata body-pack directory could not be prepared") from error

    destination = installed_body_pack_path(lock.pack_id, data_root=body_root.parent)
    if destination.exists() or destination.is_symlink() or destination.is_junction():
        raise BodyPackFetchError(f"body pack is already installed at {destination}")
    downloader = _download_from_github if download is None else download
    try:
        with tempfile.TemporaryDirectory(
            prefix=f".{lock.pack_id}-fetch-",
            dir=body_root,
        ) as temporary:
            temporary_root = Path(temporary)
            archive_path = temporary_root / lock.archive.asset_name
            staged_path = temporary_root / "pack"
            try:
                downloader(lock, archive_path)
            except BodyPackFetchError:
                raise
            except Exception as error:
                raise BodyPackFetchError("body-pack download failed without installing files") from error
            _measure_locked_archive(archive_path, lock)
            _validate_archive_members(archive_path, lock)
            _extract_locked_archive(archive_path, staged_path, lock)
            _require_staged_manifest(staged_path, lock)
            _measure_locked_archive(archive_path, lock)
            try:
                installation = install_staged_body_pack(
                    staged_path,
                    lock.reference,
                    data_root=body_root.parent,
                )
            except BodyPackInstallError as error:
                raise BodyPackFetchError(str(error)) from error
    except BodyPackFetchError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise BodyPackFetchError("locked body-pack installation failed safely") from error

    return BodyPackFetchResult(
        installation.path,
        lock.pack_id,
        lock.pack_version,
        lock.reference.fingerprint,
        len(lock.files),
        lock_bytes(lock),
    )


def _download_from_github(lock: BodyPackReleaseLock, destination: Path) -> None:
    request = _public_release_request(lock)
    try:
        with _urlopen(request, 120.0) as response:
            _require_success_status(response)
            _stream_exact_archive(response, destination, lock.archive.bytes)
    except BodyPackFetchError:
        destination.unlink(missing_ok=True)
        raise
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        destination.unlink(missing_ok=True)
        raise BodyPackFetchError("public GitHub body-pack release download failed") from error


def _urlopen(request: Request, timeout: float) -> Any:
    return build_opener(_HttpsRedirectHandler()).open(request, timeout=timeout)


def _public_release_request(lock: BodyPackReleaseLock) -> Request:
    if lock.repository != SOURCE_REPOSITORY:
        raise BodyPackFetchError("body-pack release lock points outside the approved repository")
    repository = quote(lock.repository, safe="/")
    release_tag = quote(lock.release_tag, safe="")
    asset_name = quote(lock.archive.asset_name, safe="")
    url = f"{GITHUB_WEB_ROOT}/{repository}/releases/download/{release_tag}/{asset_name}"
    parsed = urlparse(url)
    expected_path = f"/{repository}/releases/download/{release_tag}/{asset_name}"
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
    ):
        raise BodyPackFetchError("body-pack release request is outside the approved GitHub path")
    return Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )


def _stream_exact_archive(response: Any, destination: Path, expected_bytes: int) -> None:
    total = 0
    try:
        with destination.open("xb") as output:
            while chunk := response.read(min(COPY_BUFFER_BYTES, expected_bytes + 1 - total)):
                output.write(chunk)
                total += len(chunk)
                if total > expected_bytes:
                    raise BodyPackFetchError("downloaded body-pack ZIP exceeds locked bytes")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    if total != expected_bytes:
        destination.unlink(missing_ok=True)
        raise BodyPackFetchError("downloaded body-pack ZIP byte count differs from lock")


def _measure_locked_archive(path: Path, lock: BodyPackReleaseLock) -> tuple[int, str]:
    if path.is_symlink() or path.is_junction() or not path.is_file():
        raise BodyPackFetchError("download did not produce a regular body-pack ZIP")
    actual_bytes = path.stat().st_size
    if actual_bytes != lock.archive.bytes:
        raise BodyPackFetchError("downloaded body-pack ZIP byte count differs from lock")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(COPY_BUFFER_BYTES):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != lock.archive.sha256:
        raise BodyPackFetchError("downloaded body-pack ZIP SHA-256 differs from lock")
    return actual_bytes, actual_sha256


def _validate_archive_members(path: Path, lock: BodyPackReleaseLock) -> None:
    expected = {record.path: record for record in lock.files}
    seen: set[str] = set()
    total_bytes = 0
    central_directory_bytes = 0
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            central_directory_bytes += len(archive.comment)
            if len(infos) > lock.validation_limits["max_files"]:
                raise BodyPackFetchError("body-pack ZIP contains more files than locked limits")
            for info in infos:
                name = _safe_archive_path(info.filename)
                if name in seen:
                    raise BodyPackFetchError(f"body-pack ZIP repeats a file path: {name}")
                seen.add(name)
                record = expected.get(name)
                if record is None:
                    raise BodyPackFetchError(f"body-pack ZIP contains an unlocked file: {name}")
                if info.is_dir() or info.file_size != record.bytes:
                    raise BodyPackFetchError(f"body-pack ZIP member size differs from lock: {name}")
                if info.file_size > _member_limit(name, lock):
                    raise BodyPackFetchError(f"body-pack ZIP member exceeds locked limits: {name}")
                mode = (info.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(mode)
                if file_type not in {0, stat.S_IFREG} or info.flag_bits & 0x1:
                    raise BodyPackFetchError(f"body-pack ZIP member is not a plain file: {name}")
                if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                    raise BodyPackFetchError(f"body-pack ZIP uses unsupported compression: {name}")
                if info.file_size and not info.compress_size:
                    raise BodyPackFetchError(f"body-pack ZIP member has an invalid compression size: {name}")
                if info.compress_size and info.file_size / info.compress_size > lock.validation_limits[
                    "max_compression_ratio"
                ]:
                    raise BodyPackFetchError(f"body-pack ZIP compression ratio exceeds limit: {name}")
                total_bytes += info.file_size
                central_directory_bytes += (
                    len(info.filename.encode("utf-8"))
                    + len(info.extra)
                    + len(info.comment)
                    + 46
                )
                if central_directory_bytes > lock.validation_limits["max_zip_dir_bytes"]:
                    raise BodyPackFetchError("body-pack ZIP central directory exceeds locked limits")
                if total_bytes > lock.validation_limits["max_total_uncompressed_bytes"]:
                    raise BodyPackFetchError("body-pack ZIP uncompressed size exceeds locked limits")
    except BodyPackFetchError:
        raise
    except (OSError, EOFError, RuntimeError, zipfile.BadZipFile) as error:
        raise BodyPackFetchError("downloaded body-pack ZIP directory is invalid") from error
    if seen != set(expected):
        missing = sorted(set(expected) - seen)
        raise BodyPackFetchError("body-pack ZIP is missing locked members: " + ", ".join(missing[:5]))


def _extract_locked_archive(
    archive_path: Path,
    destination: Path,
    lock: BodyPackReleaseLock,
) -> None:
    destination.mkdir()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for record in lock.files:
                info = archive.getinfo(record.path)
                target = destination.joinpath(*PurePosixPath(record.path).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                _copy_member(
                    archive,
                    info,
                    target,
                    expected_bytes=record.bytes,
                    maximum_bytes=_member_limit(record.path, lock),
                    expected_sha256=record.sha256,
                )
    except BodyPackFetchError:
        raise
    except (OSError, EOFError, KeyError, RuntimeError, zipfile.BadZipFile) as error:
        raise BodyPackFetchError("locked body-pack ZIP could not be extracted safely") from error


def _copy_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    target: Path,
    *,
    expected_bytes: int,
    maximum_bytes: int,
    expected_sha256: str,
) -> None:
    if info.file_size != expected_bytes or expected_bytes > maximum_bytes:
        raise BodyPackFetchError(f"body-pack ZIP member size changed: {info.filename}")
    digest = hashlib.sha256()
    total = 0
    with archive.open(info) as source, target.open("xb") as output:
        while chunk := source.read(min(COPY_BUFFER_BYTES, maximum_bytes + 1 - total)):
            output.write(chunk)
            digest.update(chunk)
            total += len(chunk)
            if total > maximum_bytes:
                raise BodyPackFetchError(f"body-pack ZIP member exceeded its limit: {info.filename}")
    if total != expected_bytes:
        raise BodyPackFetchError(f"body-pack ZIP member byte count changed: {info.filename}")
    if digest.hexdigest() != expected_sha256:
        raise BodyPackFetchError(f"body-pack ZIP member SHA-256 differs from lock: {info.filename}")


def _require_staged_manifest(staged: Path, lock: BodyPackReleaseLock) -> None:
    manifest_path = staged / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
    except OSError as error:
        raise BodyPackFetchError("staged body-pack manifest could not be read") from error
    if (
        len(manifest_bytes) != lock.manifest_bytes
        or hashlib.sha256(manifest_bytes).hexdigest() != lock.manifest_sha256
    ):
        raise BodyPackFetchError("body-pack manifest bytes or SHA-256 differ from lock")
    try:
        document = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
        manifest = parse_body_pack(document, lock.reference)
    except BodyPackError as error:
        code = getattr(error, "code", "invalid_manifest")
        raise BodyPackFetchError(f"body-pack manifest rejected [{code}]: {error}") from error
    except (UnicodeError, json.JSONDecodeError, RecursionError, BodyPackLockError) as error:
        raise BodyPackFetchError(f"body-pack manifest is invalid: {error}") from error

    if (
        manifest.id != lock.pack_id
        or manifest.version != lock.pack_version
        or manifest.fingerprint != lock.package_hash
        or manifest.license != lock.license
    ):
        raise BodyPackFetchError(
            "body-pack manifest identity, fingerprint, or license differs from lock"
        )
    declared: dict[str, str] = {}
    for view in (*manifest.full_body, *manifest.half_body):
        for _state, record in view.frames:
            declared[record.path] = record.sha256
    for _view_id, record in manifest.face_core_masks:
        declared[record.path] = record.sha256
    locked_pngs = {
        item.path: item.sha256
        for item in lock.files
        if item.path.endswith(".png")
    }
    if declared != locked_pngs:
        raise BodyPackFetchError("locked body PNG inventory differs from the manifest")
    locked_paths = {item.path for item in lock.files}
    if locked_paths != {"manifest.json", *declared, *REQUIRED_LEGAL_FILES}:
        raise BodyPackFetchError("body-pack lock contains unsupported or missing non-image members")


def _parse_lock_document(document: object) -> BodyPackReleaseLock:
    lock = _object(document, "body-pack lock")
    _require_keys(
        lock,
        {
            "schema",
            "schema_version",
            "pack_id",
            "pack_version",
            "package_hash",
            "archive",
            "source",
            "source_manifest",
            "license",
            "body_pack",
            "files",
            "validation_limits",
        },
        "body-pack lock",
    )
    if lock["schema"] != BODY_PACK_LOCK_SCHEMA or type(lock["schema_version"]) is not int or lock[
        "schema_version"
    ] != BODY_PACK_LOCK_VERSION:
        raise BodyPackLockError("body-pack lock uses an unsupported schema")

    pack_id, pack_version, package_hash = _parse_lock_identity(lock)
    archive = _parse_lock_archive(lock["archive"], pack_id, pack_version)
    repository, release_tag = _parse_lock_source(lock["source"], pack_id, pack_version)
    license_name = _text(lock["license"], "license")
    if license_name != BODY_PACK_LICENSE:
        raise BodyPackLockError("body-pack lock license differs from the approved release license")
    reference, manifest_bytes, manifest_sha256 = _parse_locked_body_metadata(
        lock["body_pack"],
        pack_id,
        pack_version,
        package_hash,
    )
    source_manifest_path, source_manifest_bytes, source_manifest_sha256 = (
        _parse_source_manifest(lock["source_manifest"])
    )
    limits = _parse_validation_limits(lock["validation_limits"])
    files = _parse_locked_files(
        lock["files"],
        limits,
        archive.bytes,
        manifest_bytes,
        manifest_sha256,
    )
    return BodyPackReleaseLock(
        pack_id,
        pack_version,
        package_hash,
        archive,
        repository,
        release_tag,
        license_name,
        source_manifest_path,
        source_manifest_bytes,
        source_manifest_sha256,
        reference,
        manifest_bytes,
        manifest_sha256,
        files,
        limits,
    )


def _parse_lock_identity(lock: Mapping[str, object]) -> tuple[str, str, str]:
    pack_id = _text(lock["pack_id"], "pack_id")
    pack_version = _text(lock["pack_version"], "pack_version")
    package_hash = _sha256(lock["package_hash"], "package_hash")
    if pack_id != MOHAN_BODY_PACK_ID:
        raise BodyPackLockError("body-pack lock does not identify the supported MoHan body release")
    if BODY_PACK_VERSION_PATTERN.fullmatch(pack_version) is None:
        raise BodyPackLockError("pack_version must be a canonical semantic version")
    return pack_id, pack_version, package_hash


def _parse_lock_archive(
    document: object,
    pack_id: str,
    pack_version: str,
) -> LockedBodyArchive:
    archive_document = _object(document, "archive")
    _require_keys(archive_document, {"asset_name", "bytes", "sha256"}, "archive")
    archive = LockedBodyArchive(
        _text(archive_document["asset_name"], "archive.asset_name"),
        _positive_integer(archive_document["bytes"], "archive.bytes"),
        _sha256(archive_document["sha256"], "archive.sha256"),
    )
    expected_asset = f"flameblade.{pack_id}-{pack_version}.zip"
    if archive.asset_name != expected_asset:
        raise BodyPackLockError("body-pack archive asset name differs from pack_id/pack_version")
    return archive


def _parse_lock_source(
    document: object,
    pack_id: str,
    pack_version: str,
) -> tuple[str, str]:
    source_document = _object(document, "source")
    _require_keys(source_document, {"repository", "release_tag"}, "source")
    repository = _text(source_document["repository"], "source.repository")
    release_tag = _text(source_document["release_tag"], "source.release_tag")
    expected_tag = f"{pack_id}-pack-v{pack_version}"
    if repository != SOURCE_REPOSITORY or release_tag != expected_tag:
        raise BodyPackLockError("body-pack lock release source is outside the approved repository/tag")
    return repository, release_tag


def _parse_locked_body_metadata(
    document: object,
    pack_id: str,
    pack_version: str,
    package_hash: str,
) -> tuple[BodyPackReference, int, str]:
    body_document = _object(document, "body_pack")
    _require_keys(
        body_document,
        {"id", "version", "fingerprint", "manifest_bytes", "manifest_sha256"},
        "body_pack",
    )
    try:
        reference = parse_body_pack_reference(
            {
                "id": body_document["id"],
                "version": body_document["version"],
                "fingerprint": body_document["fingerprint"],
            }
        )
    except BodyPackError as error:
        raise BodyPackLockError(f"body_pack reference is invalid: {error}") from error
    manifest_bytes = _positive_integer(body_document["manifest_bytes"], "body_pack.manifest_bytes")
    manifest_sha256 = _sha256(body_document["manifest_sha256"], "body_pack.manifest_sha256")
    if reference.id != pack_id:
        raise BodyPackLockError("body_pack id differs from the lock pack_id")
    if reference.version != pack_version:
        raise BodyPackLockError("body_pack version mismatch [version_mismatch]")
    if package_hash != reference.fingerprint:
        raise BodyPackLockError("package_hash must equal body_pack fingerprint [fingerprint_mismatch]")
    return reference, manifest_bytes, manifest_sha256


def _parse_source_manifest(document: object) -> tuple[str, int, str]:
    source_manifest = _object(document, "source_manifest")
    _require_keys(source_manifest, {"path", "bytes", "sha256"}, "source_manifest")
    try:
        path = _safe_archive_path(_text(source_manifest["path"], "source_manifest.path"))
    except BodyPackFetchError as error:
        raise BodyPackLockError(f"source_manifest path is unsafe: {error}") from error
    if path != "docs/body-pack/source.json":
        raise BodyPackLockError("source_manifest path must identify the locked body-pack build input")
    size = _positive_integer(source_manifest["bytes"], "source_manifest.bytes")
    digest = _sha256(source_manifest["sha256"], "source_manifest.sha256")
    if size > MAX_SOURCE_MANIFEST_BYTES:
        raise BodyPackLockError("source_manifest exceeds the strict lock metadata size limit")
    return path, size, digest


def _parse_validation_limits(document: object) -> Mapping[str, int]:
    limits_document = _object(document, "validation_limits")
    _require_keys(limits_document, set(LOCK_LIMITS), "validation_limits")
    limits = {
        key: _positive_integer(value, f"validation_limits.{key}")
        for key, value in limits_document.items()
    }
    if limits != LOCK_LIMITS:
        raise BodyPackLockError("body-pack validation_limits differ from the approved bounds")
    return limits


def _parse_locked_files(
    document: object,
    limits: Mapping[str, int],
    archive_bytes: int,
    manifest_bytes: int,
    manifest_sha256: str,
) -> tuple[LockedBodyFile, ...]:
    if not isinstance(document, list) or not document:
        raise BodyPackLockError("body-pack lock files must be a non-empty array")
    if len(document) > limits["max_files"]:
        raise BodyPackLockError("body-pack lock declares more files than validation_limits")

    files: list[LockedBodyFile] = []
    by_path: dict[str, LockedBodyFile] = {}
    total_bytes = 0
    for index, raw in enumerate(document):
        record = _parse_locked_file(raw, index, limits)
        if record.path in by_path:
            raise BodyPackLockError(f"body-pack lock repeats file path: {record.path}")
        by_path[record.path] = record
        files.append(record)
        total_bytes += record.bytes
    if total_bytes > limits["max_total_uncompressed_bytes"]:
        raise BodyPackLockError("body-pack lock total file bytes exceed validation_limits")
    if archive_bytes > limits["max_archive_bytes"]:
        raise BodyPackLockError("body-pack archive exceeds validation_limits")
    _validate_locked_file_inventory(by_path, manifest_bytes, manifest_sha256)
    return tuple(files)


def _parse_locked_file(
    document: object,
    index: int,
    limits: Mapping[str, int],
) -> LockedBodyFile:
    item = _object(document, f"files[{index}]")
    _require_keys(item, {"path", "bytes", "sha256"}, f"files[{index}]")
    try:
        path = _safe_archive_path(_text(item["path"], f"files[{index}].path"))
    except BodyPackFetchError as error:
        raise BodyPackLockError(f"files[{index}] path is unsafe: {error}") from error
    size = _positive_integer(item["bytes"], f"files[{index}].bytes")
    digest = _sha256(item["sha256"], f"files[{index}].sha256")
    maximum = limits["max_manifest_bytes"] if path == "manifest.json" else limits["max_file_bytes"]
    if size > maximum:
        raise BodyPackLockError(f"body-pack lock file exceeds its size limit: {path}")
    if path not in {"manifest.json", "LICENSE.txt", "NOTICE.md"} and not path.endswith(".png"):
        raise BodyPackLockError(f"body-pack lock only allows PNG payload and required legal files: {path}")
    return LockedBodyFile(path, size, digest)


def _validate_locked_file_inventory(
    by_path: Mapping[str, LockedBodyFile],
    manifest_bytes: int,
    manifest_sha256: str,
) -> None:
    manifest_record = by_path.get("manifest.json")
    if (
        manifest_record is None
        or manifest_record.bytes != manifest_bytes
        or manifest_record.sha256 != manifest_sha256
    ):
        raise BodyPackLockError("manifest.json lock record differs from body_pack manifest metadata")
    if not set(by_path) >= REQUIRED_LEGAL_FILES:
        raise BodyPackLockError("body-pack lock must include LICENSE.txt and NOTICE.md")
    if not any(path.endswith(".png") for path in by_path):
        raise BodyPackLockError("body-pack lock does not declare any body PNG files")


def _require_expected_reference(
    requested: BodyPackReference | Mapping[str, object],
    released: BodyPackReference,
) -> None:
    try:
        expected = parse_body_pack_reference(requested)
    except BodyPackError as error:
        raise BodyPackFetchError(f"requested body-pack reference is invalid: {error}") from error
    if expected.id != released.id:
        raise BodyPackFetchError(
            f"body-pack id mismatch: character requires {expected.id!r}, release provides {released.id!r}"
        )
    if expected.version != released.version:
        raise BodyPackFetchError(
            f"body-pack version mismatch [version_mismatch]: character requires {expected.version!r}, "
            f"release provides {released.version!r}"
        )
    if expected.fingerprint != released.fingerprint:
        raise BodyPackFetchError(
            "body-pack fingerprint mismatch [fingerprint_mismatch]: the character reference does not "
            "match the locked release"
        )


def _member_limit(path: str, lock: BodyPackReleaseLock) -> int:
    return (
        lock.validation_limits["max_manifest_bytes"]
        if path == "manifest.json"
        else lock.validation_limits["max_file_bytes"]
    )


def _safe_archive_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or value != value.strip()
        or "\\" in value
        or path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
        or ":" in value
    ):
        raise BodyPackFetchError(f"body-pack path is not a safe POSIX relative path: {value!r}")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise BodyPackLockError(f"JSON object key is repeated: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise BodyPackLockError(f"JSON constant is unsupported: {value}")


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise BodyPackLockError(f"{label} must be an object with string keys")
    return value


def _require_keys(value: Mapping[str, object], keys: set[str], label: str) -> None:
    if set(value) != keys:
        missing = sorted(keys - set(value))
        extra = sorted(set(value) - keys)
        raise BodyPackLockError(f"{label} fields differ from schema: missing={missing}, extra={extra}")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise BodyPackLockError(f"{label} must be non-empty trimmed text")
    return value


def _positive_integer(value: object, label: str) -> int:
    if type(value) is not int or value < 1:
        raise BodyPackLockError(f"{label} must be a positive JSON integer")
    return value


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise BodyPackLockError(f"{label} must be 64 lowercase hexadecimal characters")
    return value


def lock_bytes(lock: BodyPackReleaseLock) -> int:
    """Return the total uncompressed bytes represented by the verified lock."""

    return sum(record.bytes for record in lock.files)


def _require_success_status(response: object) -> None:
    status = getattr(response, "status", HTTP_SUCCESS_MINIMUM)
    if (
        not isinstance(status, int)
        or status < HTTP_SUCCESS_MINIMUM
        or status >= HTTP_SUCCESS_EXCLUSIVE_MAXIMUM
    ):
        raise BodyPackFetchError("public GitHub release request returned a non-success status")


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=DEFAULT_BODY_PACK_LOCK)
    parser.add_argument("--data-root", type=Path)
    parsed = parser.parse_args(arguments)
    try:
        result = fetch_body_pack(lock_path=parsed.lock, data_root=parsed.data_root)
    except (BodyPackFetchError, BodyPackLockError, BodyPackInstallError, OSError, ValueError) as error:
        print(f"BODY_PACK_FETCH_ERROR={error}", file=sys.stderr)
        return 1
    print(f"BODY_PACK_INSTALLED={result.output}")
    print(f"BODY_PACK_ID={result.pack_id}")
    print(f"BODY_PACK_VERSION={result.pack_version}")
    print(f"BODY_PACK_FINGERPRINT={result.fingerprint}")
    print(f"CHECKED_FILES={result.checked_files}")
    print(f"CHECKED_BYTES={result.checked_bytes}")
    print("BODY_PACK_FETCH_VALID=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
