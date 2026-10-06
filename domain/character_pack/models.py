"""Typed, presentation-independent character-pack contracts."""

from __future__ import annotations

lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from pathlib import Path


@dataclass(frozen=True, slots=True)
class ValidationLimits:
    """Resource ceilings applied before and while package content is read."""

    max_archive_bytes: int = 256 * 1024 * 1024
    max_zip_directory_bytes: int = 8 * 1024 * 1024
    max_manifest_bytes: int = 1024 * 1024
    max_file_bytes: int = 64 * 1024 * 1024
    max_total_bytes: int = 512 * 1024 * 1024
    max_files: int = 4096
    max_compression_ratio: int = 100


@dataclass(frozen=True, slots=True)
class CharacterPackFile:
    """One payload file declared by the package manifest."""

    path: str
    sha256: str
    bytes: int
    media_type: str
    license_component: str


@dataclass(frozen=True, slots=True)
class LicenseDeclaration:
    """Rights status for one independently licensed content category."""

    component: str
    status: str
    rights_holder: str
    license_expression: str | None
    notice_path: str | None


@dataclass(frozen=True, slots=True)
class CharacterPackReference:
    """Hash-bound provenance or approval record with a limited scope."""

    path: str
    sha256: str
    scope: str


@dataclass(frozen=True, slots=True)
class CharacterPackDependency:
    """An optional relationship to an outfit or DLC package."""

    dependency_id: str
    kind: str
    min_version: str
    max_version_exclusive: str
    required: bool


@dataclass(frozen=True, slots=True)
class CharacterPackComponent:
    """A typed child manifest or sealed data pack referenced by the envelope."""

    component_id: str
    kind: str
    schema: str
    path: str
    sha256: str
    required: bool
    body_profile_id: str | None
    body_profile_version: int | None


@dataclass(frozen=True, slots=True)
class EngineCompatibility:
    """Engine API, version interval, and feature requirements."""

    api_version: int
    min_version: str
    max_version_exclusive: str
    required_features: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CharacterPackSignature:
    """Detached signature metadata over the package logical hash."""

    algorithm: str
    key_id: str
    value: str


@dataclass(frozen=True, slots=True)
class CharacterPackManifest:
    """Validated character-pack identity and security-relevant declarations."""

    schema: str
    pack_id: str
    pack_version: str
    character_id: str
    canonical_name: str
    aliases: tuple[str, ...]
    display_names: tuple[tuple[str, str], ...]
    engine_compatibility: EngineCompatibility
    standalone_downloadable: bool
    access: str
    redistribution: str
    licenses: tuple[LicenseDeclaration, ...]
    source_refs: tuple[CharacterPackReference, ...]
    approval_refs: tuple[CharacterPackReference, ...]
    files: tuple[CharacterPackFile, ...]
    components: tuple[CharacterPackComponent, ...]
    dependencies: tuple[CharacterPackDependency, ...]
    package_hash: str
    signature: CharacterPackSignature | None


@dataclass(frozen=True, slots=True)
class CharacterPackValidationIssue:
    """A stable machine code plus a safe human-readable explanation."""

    code: str
    message: str
    path: str | None = None


@dataclass(frozen=True, slots=True)
class CharacterPackValidationResult:
    """Structured validation outcome; invalid input never yields a manifest."""

    valid: bool
    source: Path
    source_kind: str | None
    manifest: CharacterPackManifest | None
    issues: tuple[CharacterPackValidationIssue, ...]
    checked_files: int
    checked_bytes: int
    package_hash: str | None
    signature_status: str


SignatureVerifier = Callable[[CharacterPackSignature, bytes], bool]
