"""Fetch, verify, and atomically install the locked private MoHan pack."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import re
lazy import sys
lazy import tempfile
lazy import zipfile
lazy from collections.abc import Callable, Mapping, Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath
lazy from typing import IO, Any
lazy from urllib.error import HTTPError, URLError
lazy from urllib.parse import quote, urlparse
lazy from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from domain.character_pack.models import CharacterPackManifest, CharacterPackValidationResult
lazy from domain.character_pack.validation import validate_character_pack
lazy from domain.engine_capabilities import EngineCapabilities, current_engine_capabilities
lazy from tools.verify_character_pack_lock import (
    DEFAULT_LOCK,
    SOURCE_REPOSITORY,
    CharacterPackLock,
    load_character_pack_lock,
)

TOKEN_ENVIRONMENT = "MOHAN_CHARACTER_PACK_TOKEN"
GITHUB_API_ROOT = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
USER_AGENT = "MoHan-Character-Pack-Fetch"
MAX_RELEASE_METADATA_BYTES = 1024 * 1024
COPY_BUFFER_BYTES = 1024 * 1024
MAX_TOKEN_CHARACTERS = 4096
HTTP_SUCCESS_MINIMUM = 200
HTTP_SUCCESS_EXCLUSIVE_MAXIMUM = 300
TOKEN_CONTROL_PATTERN = re.compile(r"[\x00-\x20\x7f]")
ArchiveDownloader = Callable[[CharacterPackLock, str, Path], None]
UrlOpen = Callable[[Request, float], Any]


class CharacterPackFetchError(RuntimeError):
    """A private pack could not be installed safely."""


@dataclass(frozen=True, slots=True)
class CharacterPackFetchResult:
    """Identity and measured size of one completed local installation."""

    output: Path
    pack_id: str
    pack_version: str
    package_hash: str
    checked_files: int
    checked_bytes: int


class _AuthorizationSafeRedirectHandler(HTTPRedirectHandler):
    """Keep credentials on api.github.com and require HTTPS redirects."""

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
        if parsed.scheme != "https":
            return None
        redirected = super().redirect_request(request, response, code, message, headers, new_url)
        if redirected is None:
            return None
        if parsed.hostname != urlparse(request.full_url).hostname:
            redirected.remove_header("Authorization")
        return redirected


def fetch_character_pack(
    output: str | Path,
    *,
    lock_path: str | Path = DEFAULT_LOCK,
    environment: Mapping[str, str] | None = None,
    download: ArchiveDownloader | None = None,
    engine: EngineCapabilities | None = None,
) -> CharacterPackFetchResult:
    """Install only a checksum-locked, validator-approved release ZIP."""
    capabilities = current_engine_capabilities() if engine is None else engine
    resolved_lock = _resolve_lock_path(lock_path)
    lock = load_character_pack_lock(resolved_lock)
    token = _token_from_environment(os.environ if environment is None else environment)
    destination = Path(output).resolve(strict=False)
    if destination.exists() or destination.is_symlink():
        raise CharacterPackFetchError(f"output must not already exist: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    downloader = _download_from_github if download is None else download
    with tempfile.TemporaryDirectory(
        prefix="mohan-character-pack-fetch-",
        dir=destination.parent,
    ) as temporary:
        temporary_root = Path(temporary)
        archive_path = temporary_root / lock.archive.asset_name
        staged_output = temporary_root / "validated-pack"
        try:
            downloader(lock, token, archive_path)
        except CharacterPackFetchError:
            raise
        except Exception as error:
            raise CharacterPackFetchError("character-pack download failed without installing files") from error
        _measure_locked_archive(archive_path, lock)
        validation = _validate_downloaded_archive(archive_path, lock, capabilities)
        manifest = validation.manifest
        if manifest is None:
            raise CharacterPackFetchError("character-pack validator returned no manifest")
        _require_locked_manifest(manifest, validation, lock)
        _extract_validated_archive(archive_path, staged_output, manifest, lock)
        if destination.exists() or destination.is_symlink():
            raise CharacterPackFetchError("output appeared while the character pack was being verified")
        staged_output.rename(destination)
    return CharacterPackFetchResult(
        destination,
        lock.pack_id,
        lock.pack_version,
        lock.package_hash,
        validation.checked_files,
        validation.checked_bytes,
    )


def _download_from_github(
    lock: CharacterPackLock,
    token: str,
    destination: Path,
    *,
    open_url: UrlOpen | None = None,
) -> None:
    opener = _urlopen if open_url is None else open_url
    release_url = (
        f"{GITHUB_API_ROOT}/repos/{lock.source.repository}/releases/tags/"
        f"{quote(lock.source.release_tag, safe='')}"
    )
    release = _request_json(release_url, token, opener)
    asset_url = _locked_asset_api_url(release, lock)
    request = _github_request(asset_url, token, accept="application/octet-stream")
    try:
        with opener(request, 120.0) as response:
            _require_success_status(response)
            _stream_exact_archive(response, destination, lock.archive.bytes)
    except CharacterPackFetchError:
        destination.unlink(missing_ok=True)
        raise
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        destination.unlink(missing_ok=True)
        raise CharacterPackFetchError("private GitHub release asset download failed") from error


def _urlopen(request: Request, timeout: float) -> Any:
    opener = build_opener(_AuthorizationSafeRedirectHandler())
    return opener.open(request, timeout=timeout)


def _request_json(url: str, token: str, open_url: UrlOpen) -> dict[str, Any]:
    request = _github_request(url, token, accept="application/vnd.github+json")
    try:
        with open_url(request, 30.0) as response:
            _require_success_status(response)
            data = _read_limited(response, MAX_RELEASE_METADATA_BYTES)
        document = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except CharacterPackFetchError:
        raise
    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        RecursionError,
        TypeError,
        ValueError,
    ) as error:
        raise CharacterPackFetchError("private GitHub release metadata request failed") from error
    if not isinstance(document, dict):
        raise CharacterPackFetchError("private GitHub release metadata must be a JSON object")
    return dict(document)


def _github_request(url: str, token: str, *, accept: str) -> Request:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.github.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise CharacterPackFetchError("private release requests must use the GitHub HTTPS API host")
    return Request(
        url,
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )


def _locked_asset_api_url(release: Mapping[str, object], lock: CharacterPackLock) -> str:
    raw_assets = release.get("assets")
    if not isinstance(raw_assets, list):
        raise CharacterPackFetchError("private release metadata has no assets list")
    matches = [
        dict(raw)
        for raw in raw_assets
        if isinstance(raw, dict) and raw.get("name") == lock.archive.asset_name
    ]
    if len(matches) != 1:
        raise CharacterPackFetchError("private release must contain exactly one locked ZIP asset")
    asset = matches[0]
    size = asset.get("size")
    if size != lock.archive.bytes:
        raise CharacterPackFetchError("private release asset byte count differs from the lock")
    url = asset.get("url")
    if not isinstance(url, str):
        raise CharacterPackFetchError("private release asset has no API download URL")
    parsed = urlparse(url)
    expected_prefix = f"/repos/{SOURCE_REPOSITORY}/releases/assets/"
    asset_id = parsed.path.removeprefix(expected_prefix)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.github.com"
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith(expected_prefix)
        or not asset_id.isascii()
        or not asset_id.isdigit()
    ):
        raise CharacterPackFetchError("private release asset URL is outside the approved repository")
    return url


def _stream_exact_archive(response: Any, destination: Path, expected_bytes: int) -> None:
    total = 0
    try:
        with destination.open("xb") as output:
            while chunk := response.read(min(COPY_BUFFER_BYTES, expected_bytes + 1 - total)):
                output.write(chunk)
                total += len(chunk)
                if total > expected_bytes:
                    raise CharacterPackFetchError("downloaded ZIP exceeds the locked byte count")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    if total != expected_bytes:
        destination.unlink(missing_ok=True)
        raise CharacterPackFetchError("downloaded ZIP byte count differs from the lock")


def _measure_locked_archive(path: Path, lock: CharacterPackLock) -> tuple[int, str]:
    if path.is_symlink() or path.is_junction() or not path.is_file():
        raise CharacterPackFetchError("download did not produce a regular ZIP file")
    actual_bytes = path.stat().st_size
    if actual_bytes != lock.archive.bytes:
        raise CharacterPackFetchError("downloaded ZIP byte count differs from the lock")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(COPY_BUFFER_BYTES):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != lock.archive.sha256:
        raise CharacterPackFetchError("downloaded ZIP SHA-256 differs from the lock")
    return actual_bytes, actual_sha256


def _validate_downloaded_archive(
    archive_path: Path,
    lock: CharacterPackLock,
    engine: EngineCapabilities,
) -> CharacterPackValidationResult:
    # Judge compatibility against the engine actually running, never against the
    # requirements the pack itself declares, or every pack would trivially pass.
    result = validate_character_pack(
        archive_path,
        engine_version=engine.version,
        engine_api_version=engine.api_version,
        engine_features=engine.features,
        limits=lock.validation_limits,
    )
    if not result.valid:
        if result.issues:
            issue = result.issues[0]
            location = f" path={issue.path}" if issue.path is not None else ""
            detail = f"{issue.code}{location}"
        else:
            detail = "unknown_validation_failure"
        raise CharacterPackFetchError(f"downloaded ZIP failed character-pack validation: {detail}")
    if result.source_kind != "zip":
        raise CharacterPackFetchError("downloaded character pack must be a ZIP archive")
    return result


def _require_locked_manifest(
    manifest: CharacterPackManifest,
    validation: CharacterPackValidationResult,
    lock: CharacterPackLock,
) -> None:
    differences: list[str] = []
    if manifest.pack_id != lock.pack_id:
        differences.append("pack_id")
    if manifest.pack_version != lock.pack_version:
        differences.append("pack_version")
    if manifest.package_hash != lock.package_hash or validation.package_hash != lock.package_hash:
        differences.append("package_hash")
    locked_files = {item.path: (item.sha256, item.bytes) for item in lock.files}
    downloaded_files = {item.path: (item.sha256, item.bytes) for item in manifest.files}
    if locked_files != downloaded_files:
        differences.append("files")
    if differences:
        raise CharacterPackFetchError(
            "downloaded character-pack manifest differs from lock fields: " + ", ".join(differences)
        )


def _extract_validated_archive(
    archive_path: Path,
    destination: Path,
    manifest: CharacterPackManifest,
    lock: CharacterPackLock,
) -> None:
    destination.mkdir()
    records = {item.path: (item.bytes, item.sha256) for item in manifest.files}
    try:
        with zipfile.ZipFile(archive_path) as archive:
            manifest_info = archive.getinfo("manifest.json")
            _copy_member(
                archive,
                manifest_info,
                destination / "manifest.json",
                expected_bytes=manifest_info.file_size,
                maximum_bytes=lock.validation_limits.max_manifest_bytes,
                expected_sha256=None,
            )
            for path in sorted(records):
                expected_bytes, expected_sha256 = records[path]
                info = archive.getinfo(path)
                target = destination.joinpath(*PurePosixPath(path).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                _copy_member(
                    archive,
                    info,
                    target,
                    expected_bytes=expected_bytes,
                    maximum_bytes=expected_bytes,
                    expected_sha256=expected_sha256,
                )
    except CharacterPackFetchError:
        raise
    except (OSError, EOFError, KeyError, RuntimeError, zipfile.BadZipFile) as error:
        raise CharacterPackFetchError("validated ZIP could not be extracted safely") from error


def _copy_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    target: Path,
    *,
    expected_bytes: int,
    maximum_bytes: int,
    expected_sha256: str | None,
) -> None:
    if info.file_size != expected_bytes or expected_bytes > maximum_bytes:
        raise CharacterPackFetchError(f"ZIP member exceeds its extraction limit: {info.filename}")
    digest = hashlib.sha256()
    total = 0
    with archive.open(info) as source, target.open("xb") as output:
        while chunk := source.read(min(COPY_BUFFER_BYTES, maximum_bytes + 1 - total)):
            output.write(chunk)
            digest.update(chunk)
            total += len(chunk)
            if total > maximum_bytes:
                raise CharacterPackFetchError(f"ZIP member exceeds its extraction limit: {info.filename}")
    if total != info.file_size or total != expected_bytes:
        raise CharacterPackFetchError(f"ZIP member byte count changed during extraction: {info.filename}")
    if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
        raise CharacterPackFetchError(f"ZIP member SHA-256 changed during extraction: {info.filename}")


def _token_from_environment(environment: Mapping[str, str]) -> str:
    token = environment.get(TOKEN_ENVIRONMENT)
    if (
        not isinstance(token, str)
        or not token
        or len(token) > MAX_TOKEN_CHARACTERS
        or TOKEN_CONTROL_PATTERN.search(token)
    ):
        raise CharacterPackFetchError(
            f"Set {TOKEN_ENVIRONMENT} to the repository-scoped read-only token before fetching the private pack."
        )
    return token


def _resolve_lock_path(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve(strict=False)


def _require_success_status(response: object) -> None:
    status = getattr(response, "status", HTTP_SUCCESS_MINIMUM)
    if (
        not isinstance(status, int)
        or status < HTTP_SUCCESS_MINIMUM
        or status >= HTTP_SUCCESS_EXCLUSIVE_MAXIMUM
    ):
        raise CharacterPackFetchError("private GitHub release request returned a non-success status")


def _read_limited(stream: IO[bytes], limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := stream.read(min(64 * 1024, limit + 1 - total)):
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            raise CharacterPackFetchError("private release metadata exceeds its size limit")
    return b"".join(chunks)


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CharacterPackFetchError(f"private release metadata has duplicate key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise CharacterPackFetchError(f"private release metadata uses unsupported JSON constant: {value}")


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parsed = parser.parse_args(arguments)
    try:
        result = fetch_character_pack(parsed.output, lock_path=parsed.lock)
    except (CharacterPackFetchError, ValueError, OSError) as error:
        print(f"CHARACTER_PACK_FETCH_ERROR={error}", file=sys.stderr)
        return 1
    print(f"CHARACTER_PACK_INSTALLED={result.output}")
    print(f"PACK_ID={result.pack_id}")
    print(f"PACK_VERSION={result.pack_version}")
    print(f"PACKAGE_HASH={result.package_hash}")
    print(f"CHECKED_FILES={result.checked_files}")
    print(f"CHECKED_BYTES={result.checked_bytes}")
    print("CHARACTER_PACK_FETCH_VALID=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
