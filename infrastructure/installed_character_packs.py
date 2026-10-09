"""Install and load validated standalone character packs for the product shell."""

from __future__ import annotations

lazy import hashlib
lazy import tempfile
lazy import zipfile
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath

lazy from domain.character_pack.models import (
    CharacterPackManifest,
    CharacterPackValidationResult,
    SignatureVerifier,
    ValidationLimits,
)
lazy from domain.character_pack.validation import DEFAULT_LIMITS, validate_character_pack
lazy from domain.engine_capabilities import EngineCapabilities, current_engine_capabilities
lazy from infrastructure.character_source_pack import (
    CharacterPackReadError,
    CharacterPackReader,
)
lazy from infrastructure.platform_services import resolved_data_dir

INSTALLED_CHARACTER_PACKS_DIRECTORY = "character-packs"
DEVELOPMENT_CHARACTER_PACK_ARCHIVE_ENV = "MOHAN_DEV_CHARACTER_PACK_ARCHIVE"
COPY_BUFFER_BYTES = 1024 * 1024
MAX_CHARACTER_ID_LENGTH = 128


class CharacterPackInstallError(RuntimeError):
    """A standalone character pack could not be installed or loaded safely."""


@dataclass(frozen=True, slots=True)
class CharacterPackInstallation:
    """Measured identity of one completed local character-pack installation."""

    path: Path
    character_id: str
    pack_id: str
    pack_version: str
    package_hash: str
    checked_files: int
    checked_bytes: int


class _DevelopmentCharacterPackReader(CharacterPackReader):
    """Keep an explicitly requested development archive extraction alive."""

    def __init__(
        self,
        source: Path,
        temporary_directory: tempfile.TemporaryDirectory[str],
        *,
        engine: EngineCapabilities,
        limits: ValidationLimits,
        signature_verifier: SignatureVerifier | None,
    ) -> None:
        self._temporary_directory = temporary_directory
        super().__init__(
            source,
            engine_version=engine.version,
            engine_api_version=engine.api_version,
            engine_features=engine.features,
            limits=limits,
            signature_verifier=signature_verifier,
        )


def installed_character_pack_root(data_root: str | Path | None = None) -> Path:
    """Return the per-user package root beside the existing MoHan profile data."""

    root = resolved_data_dir() if data_root is None else Path(data_root)
    return root.expanduser() / INSTALLED_CHARACTER_PACKS_DIRECTORY


def installed_character_pack_path(
    character_id: str,
    *,
    data_root: str | Path | None = None,
) -> Path:
    """Return the deterministic installation path for one portable character id."""

    return installed_character_pack_root(data_root) / _character_id(character_id)


def install_character_pack(
    archive: str | Path,
    *,
    data_root: str | Path | None = None,
    engine: EngineCapabilities | None = None,
    limits: ValidationLimits = DEFAULT_LIMITS,
    signature_verifier: SignatureVerifier | None = None,
) -> CharacterPackInstallation:
    """Validate a downloaded ZIP and publish one non-overwriting installation."""

    capabilities = current_engine_capabilities() if engine is None else engine
    validation = _validated_archive(
        archive,
        engine=capabilities,
        limits=limits,
        signature_verifier=signature_verifier,
    )
    manifest = _manifest(validation)
    destination = installed_character_pack_path(
        manifest.character_id,
        data_root=data_root,
    )
    root = destination.parent
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve(strict=True)
    destination = root / manifest.character_id
    if destination.exists() or destination.is_symlink():
        raise CharacterPackInstallError(
            f"Character pack {manifest.character_id!r} is already installed at {destination}."
        )
    with tempfile.TemporaryDirectory(
        prefix=f".{manifest.character_id}-install-",
        dir=root,
    ) as temporary:
        staged = Path(temporary) / "pack"
        _extract_validated_archive(Path(archive), staged, manifest, limits)
        _read_character_source(
            staged,
            expected_character_id=manifest.character_id,
            engine=capabilities,
            limits=limits,
            signature_verifier=signature_verifier,
        )
        try:
            staged.rename(destination)
        except OSError as error:
            raise CharacterPackInstallError(
                "The validated character pack could not be published atomically."
            ) from error
    return CharacterPackInstallation(
        destination,
        manifest.character_id,
        manifest.pack_id,
        manifest.pack_version,
        manifest.package_hash,
        validation.checked_files,
        validation.checked_bytes,
    )


def load_installed_character_pack(
    character_id: str,
    *,
    data_root: str | Path | None = None,
    engine: EngineCapabilities | None = None,
    limits: ValidationLimits = DEFAULT_LIMITS,
    signature_verifier: SignatureVerifier | None = None,
) -> CharacterPackReader:
    """Load one installed directory only after complete current-engine validation."""

    capabilities = current_engine_capabilities() if engine is None else engine
    source = installed_character_pack_path(character_id, data_root=data_root)
    return _read_character_source(
        source,
        expected_character_id=character_id,
        engine=capabilities,
        limits=limits,
        signature_verifier=signature_verifier,
    )


def load_development_character_pack_archive(
    archive: str | Path,
    *,
    expected_character_id: str,
    engine: EngineCapabilities | None = None,
    limits: ValidationLimits = DEFAULT_LIMITS,
    signature_verifier: SignatureVerifier | None = None,
) -> CharacterPackReader:
    """Load an explicitly named development ZIP without installing it persistently."""

    capabilities = current_engine_capabilities() if engine is None else engine
    expected = _character_id(expected_character_id)
    validation = _validated_archive(
        archive,
        engine=capabilities,
        limits=limits,
        signature_verifier=signature_verifier,
    )
    manifest = _manifest(validation)
    if manifest.character_id != expected:
        raise CharacterPackInstallError(
            "The development archive character id does not match the active selection."
        )
    temporary = tempfile.TemporaryDirectory(prefix=f"mohan-dev-{expected}-")
    staged = Path(temporary.name) / "pack"
    try:
        _extract_validated_archive(Path(archive), staged, manifest, limits)
        source = _DevelopmentCharacterPackReader(
            staged,
            temporary,
            engine=capabilities,
            limits=limits,
            signature_verifier=signature_verifier,
        )
        _require_character_id(source, expected)
    except BaseException:
        temporary.cleanup()
        raise
    return source


def _validated_archive(
    archive: str | Path,
    *,
    engine: EngineCapabilities,
    limits: ValidationLimits,
    signature_verifier: SignatureVerifier | None,
) -> CharacterPackValidationResult:
    result = validate_character_pack(
        archive,
        engine_version=engine.version,
        engine_api_version=engine.api_version,
        engine_features=engine.features,
        limits=limits,
        signature_verifier=signature_verifier,
    )
    if not result.valid or result.manifest is None:
        if result.issues:
            issue = result.issues[0]
            location = f" ({issue.path})" if issue.path else ""
            detail = f"[{issue.code}]{location}: {issue.message}"
        else:
            detail = "[unknown_validation_failure]: no validation issue was returned"
        raise CharacterPackInstallError(f"Character pack rejected {detail}")
    if result.source_kind != "zip":
        raise CharacterPackInstallError(
            "Character-pack installation requires a validated ZIP archive."
        )
    return result


def _manifest(result: CharacterPackValidationResult) -> CharacterPackManifest:
    manifest = result.manifest
    if manifest is None:
        raise CharacterPackInstallError(
            "Character-pack validation did not return a manifest."
        )
    return manifest


def _read_character_source(
    source: Path,
    *,
    expected_character_id: str,
    engine: EngineCapabilities,
    limits: ValidationLimits,
    signature_verifier: SignatureVerifier | None,
) -> CharacterPackReader:
    expected = _character_id(expected_character_id)
    try:
        reader = CharacterPackReader(
            source,
            engine_version=engine.version,
            engine_api_version=engine.api_version,
            engine_features=engine.features,
            limits=limits,
            signature_verifier=signature_verifier,
        )
    except (CharacterPackReadError, OSError, ValueError) as error:
        raise CharacterPackInstallError(str(error)) from error
    _require_character_id(reader, expected)
    return reader


def _require_character_id(reader: CharacterPackReader, expected: str) -> None:
    if reader.manifest.character_id != expected:
        raise CharacterPackInstallError(
            "The validated character-pack id does not match its installation path."
        )


def _extract_validated_archive(
    archive_path: Path,
    destination: Path,
    manifest: CharacterPackManifest,
    limits: ValidationLimits,
) -> None:
    destination.mkdir()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            manifest_info = archive.getinfo("manifest.json")
            _copy_member(
                archive,
                manifest_info,
                destination / "manifest.json",
                expected_bytes=manifest_info.file_size,
                maximum_bytes=limits.max_manifest_bytes,
                expected_sha256=None,
            )
            for record in sorted(manifest.files, key=lambda item: item.path):
                info = archive.getinfo(record.path)
                target = destination.joinpath(*PurePosixPath(record.path).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                _copy_member(
                    archive,
                    info,
                    target,
                    expected_bytes=record.bytes,
                    maximum_bytes=limits.max_file_bytes,
                    expected_sha256=record.sha256,
                )
    except CharacterPackInstallError:
        raise
    except (OSError, EOFError, KeyError, RuntimeError, zipfile.BadZipFile) as error:
        raise CharacterPackInstallError(
            "The validated character-pack ZIP changed or could not be extracted safely."
        ) from error


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
        raise CharacterPackInstallError(
            f"Character-pack member changed size during installation: {info.filename}."
        )
    digest = hashlib.sha256()
    total = 0
    with archive.open(info) as source, target.open("xb") as output:
        while chunk := source.read(min(COPY_BUFFER_BYTES, maximum_bytes + 1 - total)):
            output.write(chunk)
            digest.update(chunk)
            total += len(chunk)
            if total > maximum_bytes:
                raise CharacterPackInstallError(
                    f"Character-pack member exceeded its limit: {info.filename}."
                )
    if total != expected_bytes:
        raise CharacterPackInstallError(
            f"Character-pack member changed byte count: {info.filename}."
        )
    if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
        raise CharacterPackInstallError(
            f"Character-pack member changed SHA-256: {info.filename}."
        )


def _character_id(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_CHARACTER_ID_LENGTH
        or not value.isascii()
        or value[0] == "-"
        or value[-1] == "-"
        or any(not (character.islower() or character.isdigit() or character == "-") for character in value)
    ):
        raise CharacterPackInstallError(
            "Character ids use lowercase ASCII letters, digits, and internal hyphens."
        )
    return value


__all__ = (
    "DEVELOPMENT_CHARACTER_PACK_ARCHIVE_ENV",
    "INSTALLED_CHARACTER_PACKS_DIRECTORY",
    "CharacterPackInstallError",
    "CharacterPackInstallation",
    "install_character_pack",
    "installed_character_pack_path",
    "installed_character_pack_root",
    "load_development_character_pack_archive",
    "load_installed_character_pack",
)
