"""Build a configured character pack and verify its version lock."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import re
lazy import tempfile
lazy import zipfile
lazy from collections.abc import Callable, Mapping, Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath
lazy from typing import Any

lazy from domain.character_pack.models import ValidationLimits
lazy from huapu import character_pack_builder as builder

LOCK_SCHEMA = "flameblade.character-pack-lock.v1"
LOCK_SCHEMA_VERSION = 1
DEFAULT_LOCK = Path("character-pack.lock.json")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
SEMVER_PATTERN = re.compile(r"(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\Z")
IDENTIFIER_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?\Z")
FEATURE_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?\Z")
COPY_BUFFER_BYTES = 1024 * 1024
LOCK_KEYS = (
    "schema",
    "schema_version",
    "pack_id",
    "pack_version",
    "package_hash",
    "archive",
    "source",
    "engine_compatibility",
    "validation_limits",
    "files",
)


class CharacterPackLockError(ValueError):
    """The lock is absent, malformed, or inconsistent with its contract."""


@dataclass(frozen=True, slots=True)
class CharacterPackLockSettings:
    """Caller-owned release location and source document policy."""

    schema: str
    schema_version: int
    source_repository: str
    release_tag_prefix: str
    pack_source_path: Path

    def __post_init__(self) -> None:
        if any(
            not value or value != value.strip()
            for value in (self.schema, self.source_repository, self.release_tag_prefix)
        ):
            raise ValueError("character-pack lock settings require non-empty trimmed text")
        if type(self.schema_version) is not int or self.schema_version < 1:
            raise ValueError("character-pack lock schema version must be positive")
        if self.pack_source_path.is_absolute() or ".." in self.pack_source_path.parts:
            raise ValueError("character-pack source path must stay repository-relative")


@dataclass(frozen=True, slots=True)
class CharacterPackReleaseProfile:
    """Source document and release naming for one published character pack."""

    pack_id: str
    lock_path: Path
    source_path: Path
    source_repository: str
    release_tag_prefix: str

    def settings(self) -> CharacterPackLockSettings:
        """Return the strict lock policy for this release series."""
        return CharacterPackLockSettings(
            LOCK_SCHEMA,
            LOCK_SCHEMA_VERSION,
            self.source_repository,
            self.release_tag_prefix,
            self.source_path,
        )


@dataclass(frozen=True, slots=True)
class LockedArchive:
    """Immutable release-archive identity."""

    asset_name: str
    sha256: str
    bytes: int


@dataclass(frozen=True, slots=True)
class LockedSource:
    """Public release location pinned by repository and tag."""

    repository: str
    release_tag: str


@dataclass(frozen=True, slots=True)
class LockedEngineCompatibility:
    """Validator inputs pinned with the package version."""

    api_version: int
    min_engine_version: str
    max_engine_version_exclusive: str
    required_features: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LockedFile:
    """One payload identity retained for actionable drift reports."""

    path: str
    sha256: str
    bytes: int


@dataclass(frozen=True, slots=True)
class CharacterPackLock:
    """Strictly parsed pointer to one configured release asset."""

    pack_id: str
    pack_version: str
    package_hash: str
    archive: LockedArchive
    source: LockedSource
    engine_compatibility: LockedEngineCompatibility
    validation_limits: ValidationLimits
    files: tuple[LockedFile, ...]


@dataclass(frozen=True, slots=True)
class CharacterPackLockResult:
    """Measured verification or update result."""

    valid: bool
    package_hash: str
    archive_sha256: str
    archive_bytes: int
    issues: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _BuiltSnapshot:
    manifest: dict[str, Any]
    build_result: builder.CharacterPackBuildResult
    archive_sha256: str
    archive_bytes: int


def load_character_pack_lock(
    path: str | Path,
    *,
    settings: CharacterPackLockSettings,
) -> CharacterPackLock:
    """Load a unique-key UTF-8 lock and enforce its complete schema."""
    return _parse_lock_document(_read_lock_document(path), settings)


def load_profiled_character_pack_lock(
    path: str | Path,
    *,
    settings_by_pack_id: Mapping[str, CharacterPackLockSettings],
) -> CharacterPackLock:
    """Load a lock using the caller-approved settings for its declared pack."""
    document = _read_lock_document(path)
    pack_id = document.get("pack_id")
    settings = settings_by_pack_id.get(pack_id) if isinstance(pack_id, str) else None
    if settings is None:
        raise CharacterPackLockError(
            "character-pack lock has no supported public release profile"
        )
    return _parse_lock_document(document, settings)


def _read_lock_document(path: str | Path) -> dict[str, Any]:
    """Read one strict lock document without applying a release profile."""
    lock_path = Path(path)
    try:
        document = json.loads(
            lock_path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except CharacterPackLockError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise CharacterPackLockError(f"character-pack lock is unreadable: {lock_path}") from error
    return _object(document, "lock")


def verify_character_pack_lock(
    lock_path: str | Path,
    *,
    repo_root: str | Path,
    build: Callable[..., builder.CharacterPackBuildResult],
    settings: CharacterPackLockSettings,
) -> CharacterPackLockResult:
    """Rebuild the ZIP and compare every pinned identity without rewriting it."""
    root = Path(repo_root).resolve(strict=True)
    resolved_lock = _resolve_lock_path(root, lock_path)
    lock = load_character_pack_lock(resolved_lock, settings=settings)
    with tempfile.TemporaryDirectory(prefix="character-pack-lock-") as temporary:
        archive_path = Path(temporary) / lock.archive.asset_name
        snapshot = _build_snapshot(archive_path, root, build)
        issues = compare_snapshot_to_lock(snapshot, lock, settings=settings)
    return CharacterPackLockResult(
        not issues,
        _text(snapshot.manifest.get("package_hash"), "manifest.package_hash"),
        snapshot.archive_sha256,
        snapshot.archive_bytes,
        issues,
    )


def update_character_pack_lock(
    lock_path: str | Path,
    *,
    repo_root: str | Path,
    archive_output: str | Path | None = None,
    build: Callable[..., builder.CharacterPackBuildResult],
    settings: CharacterPackLockSettings,
) -> CharacterPackLockResult:
    """Explicitly rebuild and atomically replace the lock with measured values."""
    root = Path(repo_root).resolve(strict=True)
    resolved_lock = _resolve_lock_path(root, lock_path)
    snapshot: _BuiltSnapshot
    if archive_output is None:
        with tempfile.TemporaryDirectory(prefix="character-pack-lock-update-") as temporary:
            archive_path = Path(temporary) / _asset_name_from_source(root, settings)
            snapshot = _build_snapshot(archive_path, root, build)
            document = _lock_document(snapshot, settings)
            _write_lock(resolved_lock, document)
    else:
        archive_path = Path(archive_output).resolve(strict=False)
        snapshot = _build_snapshot(archive_path, root, build)
        document = _lock_document(snapshot, settings)
        _write_lock(resolved_lock, document)
    return CharacterPackLockResult(
        True,
        _text(snapshot.manifest.get("package_hash"), "manifest.package_hash"),
        snapshot.archive_sha256,
        snapshot.archive_bytes,
        (),
    )


def compare_snapshot_to_lock(
    snapshot: _BuiltSnapshot,
    lock: CharacterPackLock,
    *,
    settings: CharacterPackLockSettings,
) -> tuple[str, ...]:
    """Return stable, path-specific differences between a build and its lock."""
    manifest = snapshot.manifest
    issues: list[str] = []
    _compare_value(issues, "pack_id", lock.pack_id, manifest.get("pack_id"))
    _compare_value(issues, "pack_version", lock.pack_version, manifest.get("pack_version"))
    _compare_value(issues, "package_hash", lock.package_hash, manifest.get("package_hash"))
    _compare_value(issues, "archive.sha256", lock.archive.sha256, snapshot.archive_sha256)
    _compare_value(issues, "archive.bytes", lock.archive.bytes, snapshot.archive_bytes)
    expected_asset = _release_asset_name(lock.pack_id, lock.pack_version)
    _compare_value(issues, "archive.asset_name", lock.archive.asset_name, expected_asset)
    expected_tag = f"{settings.release_tag_prefix}{lock.pack_version}"
    _compare_value(issues, "source.release_tag", lock.source.release_tag, expected_tag)
    _compare_value(issues, "source.repository", lock.source.repository, settings.source_repository)

    compatibility = _object(manifest.get("engine_compatibility"), "manifest.engine_compatibility")
    actual_compatibility = LockedEngineCompatibility(
        _positive_int(compatibility.get("api_version"), "manifest.engine_compatibility.api_version"),
        _semver(compatibility.get("min_engine_version"), "manifest.engine_compatibility.min_engine_version"),
        _semver(
            compatibility.get("max_engine_version_exclusive"),
            "manifest.engine_compatibility.max_engine_version_exclusive",
        ),
        _features(compatibility.get("required_features")),
    )
    _compare_value(issues, "engine_compatibility", lock.engine_compatibility, actual_compatibility)
    _compare_value(issues, "validation_limits", lock.validation_limits, snapshot.build_result.validation_limits)

    actual_files = _manifest_files(manifest)
    locked_by_path = {item.path: item for item in lock.files}
    actual_by_path = {item.path: item for item in actual_files}
    file_difference = False
    for path in sorted(locked_by_path.keys() - actual_by_path.keys()):
        issues.append(f"payload missing from repository build: {path}")
        file_difference = True
    for path in sorted(actual_by_path.keys() - locked_by_path.keys()):
        issues.append(f"payload added by repository build: {path}")
        file_difference = True
    for path in sorted(locked_by_path.keys() & actual_by_path.keys()):
        expected = locked_by_path[path]
        actual = actual_by_path[path]
        if expected.sha256 != actual.sha256 or expected.bytes != actual.bytes:
            issues.append(
                "payload bytes differ: "
                f"{path} expected_sha256={expected.sha256} actual_sha256={actual.sha256} "
                f"expected_bytes={expected.bytes} actual_bytes={actual.bytes}"
            )
            file_difference = True
    if manifest.get("package_hash") != lock.package_hash and not file_difference:
        issues.append("manifest metadata differs while every locked payload byte remains identical")
    return tuple(issues)


def compare_manifest_to_lock(
    manifest: Mapping[str, object],
    lock: CharacterPackLock,
) -> tuple[str, ...]:
    """Compare a validated downloaded manifest with all logical lock fields."""
    issues: list[str] = []
    _compare_value(issues, "pack_id", lock.pack_id, manifest.get("pack_id"))
    _compare_value(issues, "pack_version", lock.pack_version, manifest.get("pack_version"))
    _compare_value(issues, "package_hash", lock.package_hash, manifest.get("package_hash"))
    locked_by_path = {item.path: item for item in lock.files}
    actual_by_path = {item.path: item for item in _manifest_files(manifest)}
    issues.extend(
        f"locked payload is missing from downloaded pack: {path}"
        for path in sorted(locked_by_path.keys() - actual_by_path.keys())
    )
    issues.extend(
        f"downloaded pack contains an unlocked payload: {path}"
        for path in sorted(actual_by_path.keys() - locked_by_path.keys())
    )
    issues.extend(
        f"downloaded payload identity differs from lock: {path}"
        for path in sorted(locked_by_path.keys() & actual_by_path.keys())
        if locked_by_path[path] != actual_by_path[path]
    )
    return tuple(issues)


def render_character_pack_lock(document: Mapping[str, object]) -> str:
    """Render deterministic UTF-8 JSON with LF line endings."""
    return json.dumps(document, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + "\n"


def _build_snapshot(
    archive_path: Path,
    root: Path,
    build: Callable[..., builder.CharacterPackBuildResult],
) -> _BuiltSnapshot:
    built = build(
        archive_path,
        output_format="zip",
        repo_root=root,
    )
    manifest = _manifest_from_zip(archive_path, built.validation_limits.max_manifest_bytes)
    package_hash = _sha256(manifest.get("package_hash"), "manifest.package_hash")
    if package_hash != built.package_hash:
        raise CharacterPackLockError("builder result and ZIP manifest package hashes differ")
    archive_bytes, archive_sha256 = _measure_file(archive_path)
    if built.output_bytes != archive_bytes:
        raise CharacterPackLockError("builder result and ZIP byte counts differ")
    return _BuiltSnapshot(manifest, built, archive_sha256, archive_bytes)


def _lock_document(
    snapshot: _BuiltSnapshot,
    settings: CharacterPackLockSettings,
) -> dict[str, object]:
    manifest = snapshot.manifest
    pack_id = _identifier(manifest.get("pack_id"), "manifest.pack_id")
    pack_version = _semver(manifest.get("pack_version"), "manifest.pack_version")
    compatibility = _object(manifest.get("engine_compatibility"), "manifest.engine_compatibility")
    files = [
        {"path": item.path, "sha256": item.sha256, "bytes": item.bytes}
        for item in _manifest_files(manifest)
    ]
    limits = snapshot.build_result.validation_limits
    document: dict[str, object] = {
        "schema": settings.schema,
        "schema_version": settings.schema_version,
        "pack_id": pack_id,
        "pack_version": pack_version,
        "package_hash": _sha256(manifest.get("package_hash"), "manifest.package_hash"),
        "archive": {
            "asset_name": _release_asset_name(pack_id, pack_version),
            "sha256": snapshot.archive_sha256,
            "bytes": snapshot.archive_bytes,
        },
        "source": {
            "repository": settings.source_repository,
            "release_tag": f"{settings.release_tag_prefix}{pack_version}",
        },
        "engine_compatibility": {
            "api_version": compatibility.get("api_version"),
            "min_engine_version": compatibility.get("min_engine_version"),
            "max_engine_version_exclusive": compatibility.get("max_engine_version_exclusive"),
            "required_features": compatibility.get("required_features"),
        },
        "validation_limits": {
            field: getattr(limits, field)
            for field in builder.LIMIT_FIELDS
        },
        "files": files,
    }
    _parse_lock_document(document, settings)
    return document


def _parse_lock_document(
    document: Mapping[str, object],
    settings: CharacterPackLockSettings,
) -> CharacterPackLock:
    _exact_keys(document, LOCK_KEYS, "lock")
    if document.get("schema") != settings.schema or document.get("schema_version") != settings.schema_version:
        raise CharacterPackLockError(
            f"lock must use {settings.schema} version {settings.schema_version}"
        )
    pack_id = _identifier(document.get("pack_id"), "pack_id")
    pack_version = _semver(document.get("pack_version"), "pack_version")
    package_hash = _sha256(document.get("package_hash"), "package_hash")

    raw_archive = _object(document.get("archive"), "archive")
    _exact_keys(raw_archive, ("asset_name", "sha256", "bytes"), "archive")
    archive = LockedArchive(
        _text(raw_archive.get("asset_name"), "archive.asset_name"),
        _sha256(raw_archive.get("sha256"), "archive.sha256"),
        _positive_int(raw_archive.get("bytes"), "archive.bytes"),
    )
    expected_asset = _release_asset_name(pack_id, pack_version)
    if archive.asset_name != expected_asset:
        raise CharacterPackLockError(f"archive.asset_name must be {expected_asset}")

    raw_source = _object(document.get("source"), "source")
    _exact_keys(raw_source, ("repository", "release_tag"), "source")
    source = LockedSource(
        _text(raw_source.get("repository"), "source.repository"),
        _text(raw_source.get("release_tag"), "source.release_tag"),
    )
    if source.repository != settings.source_repository:
        raise CharacterPackLockError(
            f"source.repository must be {settings.source_repository}"
        )
    expected_tag = f"{settings.release_tag_prefix}{pack_version}"
    if source.release_tag != expected_tag:
        raise CharacterPackLockError(f"source.release_tag must be {expected_tag}")

    raw_compatibility = _object(document.get("engine_compatibility"), "engine_compatibility")
    compatibility_keys = (
        "api_version",
        "min_engine_version",
        "max_engine_version_exclusive",
        "required_features",
    )
    _exact_keys(raw_compatibility, compatibility_keys, "engine_compatibility")
    compatibility = LockedEngineCompatibility(
        _positive_int(raw_compatibility.get("api_version"), "engine_compatibility.api_version"),
        _semver(raw_compatibility.get("min_engine_version"), "engine_compatibility.min_engine_version"),
        _semver(
            raw_compatibility.get("max_engine_version_exclusive"),
            "engine_compatibility.max_engine_version_exclusive",
        ),
        _features(raw_compatibility.get("required_features")),
    )

    raw_limits = _object(document.get("validation_limits"), "validation_limits")
    _exact_keys(raw_limits, builder.LIMIT_FIELDS, "validation_limits")
    measured_limits = {
        field: _positive_int(raw_limits.get(field), f"validation_limits.{field}")
        for field in builder.LIMIT_FIELDS
    }
    limits = ValidationLimits(**measured_limits)
    files = _lock_files(document.get("files"))
    if archive.bytes > limits.max_archive_bytes:
        raise CharacterPackLockError("archive.bytes exceeds validation_limits.max_archive_bytes")
    if len(files) + 1 > limits.max_files:
        raise CharacterPackLockError("files exceed validation_limits.max_files")
    if sum(item.bytes for item in files) > limits.max_total_bytes:
        raise CharacterPackLockError("files exceed validation_limits.max_total_bytes")
    return CharacterPackLock(
        pack_id,
        pack_version,
        package_hash,
        archive,
        source,
        compatibility,
        limits,
        files,
    )


def _lock_files(value: object) -> tuple[LockedFile, ...]:
    rows = _array(value, "files")
    if not rows:
        raise CharacterPackLockError("files must contain at least one payload")
    files: list[LockedFile] = []
    for raw in rows:
        entry = _object(raw, "files[]")
        _exact_keys(entry, ("path", "sha256", "bytes"), "files[]")
        files.append(
            LockedFile(
                _safe_path(entry.get("path"), "files[].path"),
                _sha256(entry.get("sha256"), "files[].sha256"),
                _non_negative_int(entry.get("bytes"), "files[].bytes"),
            )
        )
    paths = tuple(item.path for item in files)
    if paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
        raise CharacterPackLockError("files must use unique paths in code-point order")
    return tuple(files)


def _manifest_files(manifest: Mapping[str, object]) -> tuple[LockedFile, ...]:
    rows = _array(manifest.get("files"), "manifest.files")
    files: list[LockedFile] = []
    for raw in rows:
        entry = _object(raw, "manifest.files[]")
        files.append(
            LockedFile(
                _safe_path(entry.get("path"), "manifest.files[].path"),
                _sha256(entry.get("sha256"), "manifest.files[].sha256"),
                _non_negative_int(entry.get("bytes"), "manifest.files[].bytes"),
            )
        )
    paths = tuple(item.path for item in files)
    if paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
        raise CharacterPackLockError("manifest files must use unique paths in code-point order")
    return tuple(files)


def _asset_name_from_source(
    root: Path,
    settings: CharacterPackLockSettings,
) -> str:
    source_path = root / settings.pack_source_path
    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise CharacterPackLockError("pack-source.json is unreadable") from error
    source_object = _object(source, "pack source")
    pack_id = _identifier(source_object.get("pack_id"), "pack source pack_id")
    pack_version = _semver(source_object.get("pack_version"), "pack source pack_version")
    return _release_asset_name(pack_id, pack_version)


def _release_asset_name(pack_id: str, pack_version: str) -> str:
    return f"{pack_id}-{pack_version}.zip"


def _manifest_from_zip(path: Path, maximum_bytes: int) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            info = archive.getinfo("manifest.json")
            if info.file_size > maximum_bytes:
                raise CharacterPackLockError("built manifest exceeds its explicit validation limit")
            document = json.loads(
                archive.read(info),
                object_pairs_hook=_unique_object,
                parse_constant=_reject_json_constant,
            )
    except CharacterPackLockError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, RecursionError, zipfile.BadZipFile) as error:
        raise CharacterPackLockError("built ZIP manifest is unreadable") from error
    return _object(document, "manifest")


def _measure_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while chunk := stream.read(COPY_BUFFER_BYTES):
            digest.update(chunk)
            total += len(chunk)
    return total, digest.hexdigest()


def _write_lock(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            stream.write(render_character_pack_lock(document))
            temporary_path = Path(stream.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _resolve_lock_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve(strict=False)


def _compare_value(issues: list[str], label: str, expected: object, actual: object) -> None:
    if expected != actual:
        issues.append(f"{label} differs: expected={expected!r} actual={actual!r}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CharacterPackLockError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise CharacterPackLockError(f"unsupported JSON constant: {value}")


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CharacterPackLockError(f"{label} must be an object")
    return dict(value)


def _array(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CharacterPackLockError(f"{label} must be an array")
    return list(value)


def _exact_keys(value: Mapping[str, object], keys: Sequence[str], label: str) -> None:
    if set(value) != set(keys):
        raise CharacterPackLockError(f"{label} has missing or unknown fields")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CharacterPackLockError(f"{label} must be non-empty trimmed text")
    return value


def _identifier(value: object, label: str) -> str:
    text = _text(value, label)
    if IDENTIFIER_PATTERN.fullmatch(text) is None:
        raise CharacterPackLockError(f"{label} must be a portable identifier")
    return text


def _semver(value: object, label: str) -> str:
    text = _text(value, label)
    if SEMVER_PATTERN.fullmatch(text) is None:
        raise CharacterPackLockError(f"{label} must use MAJOR.MINOR.PATCH")
    return text


def _sha256(value: object, label: str) -> str:
    text = _text(value, label)
    if SHA256_PATTERN.fullmatch(text) is None:
        raise CharacterPackLockError(f"{label} must be a lowercase SHA-256 digest")
    return text


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise CharacterPackLockError(f"{label} must be a positive integer")
    return value


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CharacterPackLockError(f"{label} must be a non-negative integer")
    return value


def _features(value: object) -> tuple[str, ...]:
    features = tuple(_text(item, "required_features[]") for item in _array(value, "required_features"))
    if len(set(features)) != len(features) or any(FEATURE_PATTERN.fullmatch(item) is None for item in features):
        raise CharacterPackLockError("required_features must contain unique portable identifiers")
    return features


def _safe_path(value: object, label: str) -> str:
    text = _text(value, label)
    path = PurePosixPath(text)
    if path.is_absolute() or "\\" in text or any(part in {"", ".", ".."} for part in path.parts):
        raise CharacterPackLockError(f"{label} must stay relative to the package root")
    return text
