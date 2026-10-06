"""Fail-closed validation for standalone character-pack directories and ZIPs."""

from __future__ import annotations

lazy import base64
lazy import binascii
lazy import hashlib
lazy import json
lazy import re
lazy import zipfile
lazy from collections.abc import Iterable, Mapping
lazy from pathlib import Path
lazy from domain.character_pack.archive import _ValidationFailure, _PackageReader, _open_reader, _validate_safe_path, _fold_path

lazy from domain.character_pack.models import (
    CharacterPackDependency,
    CharacterPackFile,
    CharacterPackManifest,
    CharacterPackReference,
    CharacterPackSignature,
    CharacterPackValidationIssue,
    CharacterPackValidationResult,
    EngineCompatibility,
    LicenseDeclaration,
    SignatureVerifier,
    ValidationLimits,
)

DEFAULT_LIMITS = ValidationLimits()
CONTROL_CHARACTER_BOUNDARY = 32
SCHEMA = "flameblade.character-pack.v1"
MANIFEST_PATH = "manifest.json"
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
LICENSE_COMPONENTS = (
    "program_data",
    "character_art",
    "persona_dialogue",
    "voice",
)
LICENSE_STATUSES = frozenset({
    "declared_license",
    "all_rights_reserved",
    "owner_decision_pending",
})
DEPENDENCY_KINDS = frozenset({"outfit_pack", "dlc"})
ACCESS_STATUSES = frozenset({"public", "private", "owner_decision_pending"})
REDISTRIBUTION_STATUSES = frozenset({"allowed", "prohibited", "owner_decision_pending"})
FORBIDDEN_SUFFIXES = frozenset({
    ".bat", ".cmd", ".com", ".dll", ".exe", ".jar", ".js", ".msi",
    ".ps1", ".py", ".pyc", ".pyd", ".scr", ".sh", ".vbs",
})
TOP_LEVEL_REQUIRED = frozenset({
    "schema",
    "pack_id",
    "pack_version",
    "display_names",
    "character",
    "engine_compatibility",
    "distribution",
    "licenses",
    "source_refs",
    "approval_refs",
    "files",
    "package_hash",
})
TOP_LEVEL_OPTIONAL = frozenset({"dependencies", "signature"})
IDENTIFIER = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?\Z")
SEMVER = re.compile(r"(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MEDIA_TYPE = re.compile(r"[a-z0-9][a-z0-9!#$&^_.+-]{0,63}/[a-z0-9][a-z0-9!#$&^_.+-]{0,63}\Z")
FEATURE = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?\Z")
KEY_ID = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._:-]{0,126}[A-Za-z0-9])?\Z")
MAX_NAME_LENGTH = 160
MAX_SCOPE_LENGTH = 500
ED25519_SIGNATURE_BYTES = 64


def compute_package_hash(manifest: Mapping[str, object]) -> str:
    """Return the logical hash shared by equivalent directory and ZIP packages.

    The digest covers canonical manifest metadata and its complete file index.
    ``package_hash`` and ``signature`` are omitted to avoid self-reference. Each
    indexed payload byte is covered through its separately verified SHA-256.
    """
    basis = dict(manifest)
    basis.pop("package_hash", None)
    basis.pop("signature", None)
    canonical = json.dumps(
        basis,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(SCHEMA.encode("ascii") + b"\0" + canonical).hexdigest()


def validate_character_pack(
    source: str | Path,
    *,
    engine_version: str,
    engine_api_version: int = 1,
    engine_features: Iterable[str] = (),
    limits: ValidationLimits = DEFAULT_LIMITS,
    signature_verifier: SignatureVerifier | None = None,
) -> CharacterPackValidationResult:
    """Validate one directory or ZIP without extracting or changing it."""
    source_path = Path(source)
    source_kind: str | None = None
    checked_files = 0
    checked_bytes = 0
    package_hash: str | None = None
    signature_status = "absent"
    try:
        _validate_limits(limits)
        current_version = _semantic_version(engine_version, "engine_version")
        if not isinstance(engine_api_version, int) or isinstance(engine_api_version, bool) or engine_api_version < 1:
            raise _ValidationFailure("invalid_engine", "Engine API version must be a positive integer.")
        supported_features = _feature_set(engine_features, "engine_features")
        reader = _open_reader(source_path, limits)
        with reader:
            source_kind = reader.source_kind
            if MANIFEST_PATH not in reader.names:
                raise _ValidationFailure("missing_manifest", "The package must contain manifest.json.")
            manifest_bytes = reader.read(MANIFEST_PATH, limits.max_manifest_bytes)
            raw_manifest = _decode_manifest(manifest_bytes)
            manifest = _parse_manifest(raw_manifest)
            _validate_engine_compatibility(
                manifest.engine_compatibility,
                current_version,
                engine_api_version,
                supported_features,
            )
            package_hash = compute_package_hash(raw_manifest)
            if package_hash != manifest.package_hash:
                raise _ValidationFailure("package_hash_mismatch", "The logical package hash does not match the manifest.")
            checked_files, checked_bytes = _validate_payload(reader, manifest, limits)
            signature_status = _validate_signature(manifest, signature_verifier)
        return CharacterPackValidationResult(
            True,
            source_path,
            source_kind,
            manifest,
            (),
            checked_files,
            checked_bytes,
            package_hash,
            signature_status,
        )
    except _ValidationFailure as error:
        return CharacterPackValidationResult(
            False,
            source_path,
            source_kind,
            None,
            (CharacterPackValidationIssue(error.code, str(error), error.path),),
            checked_files,
            checked_bytes,
            package_hash,
            signature_status,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, zipfile.BadZipFile) as error:
        return CharacterPackValidationResult(
            False,
            source_path,
            source_kind,
            None,
            (CharacterPackValidationIssue("unreadable_package", f"The package could not be read safely: {type(error).__name__}."),),
            checked_files,
            checked_bytes,
            package_hash,
            signature_status,
        )


def _validate_limits(limits: ValidationLimits) -> None:
    values = (
        limits.max_archive_bytes,
        limits.max_zip_directory_bytes,
        limits.max_manifest_bytes,
        limits.max_file_bytes,
        limits.max_total_bytes,
        limits.max_files,
        limits.max_compression_ratio,
    )
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in values):
        raise _ValidationFailure("invalid_limits", "Validation limits must be positive integers.")


def _decode_manifest(data: bytes) -> dict[str, object]:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_json_constant)
    except _ValidationFailure:
        raise
    except (UnicodeError, ValueError, RecursionError):
        raise _ValidationFailure("invalid_manifest", "manifest.json must be unique-key UTF-8 JSON.") from None
    if not isinstance(value, dict):
        raise _ValidationFailure("invalid_manifest", "manifest.json must contain a JSON object.")
    return value


def _reject_json_constant(value: str) -> None:
    raise _ValidationFailure("invalid_manifest", f"JSON constant {value} is unsupported.")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _ValidationFailure("duplicate_json_key", "JSON object keys must be unique.", key)
        result[key] = value
    return result


def _parse_manifest(value: dict[str, object]) -> CharacterPackManifest:
    _exact_keys(value, TOP_LEVEL_REQUIRED, TOP_LEVEL_OPTIONAL, "manifest")
    if value["schema"] != SCHEMA:
        raise _ValidationFailure("unsupported_schema", f"Only {SCHEMA} is supported.")
    pack_id = _identifier(value["pack_id"], "pack_id")
    pack_version = _semantic_version_text(value["pack_version"], "pack_version")
    display_names = _localized_names(value["display_names"])
    character_id, canonical_name, aliases = _character(value["character"])
    compatibility = _compatibility(value["engine_compatibility"])
    standalone, access, redistribution = _distribution(value["distribution"])
    licenses = _licenses(value["licenses"])
    source_refs = _references(value["source_refs"], "source_refs", require_entries=True)
    approval_refs = _references(value["approval_refs"], "approval_refs", require_entries=False)
    files = _files(value["files"])
    dependencies = _dependencies(value.get("dependencies", []))
    package_hash = _sha256(value["package_hash"], "package_hash")
    signature = _signature(value.get("signature"))
    _validate_manifest_references(licenses, source_refs, approval_refs, files)
    return CharacterPackManifest(
        SCHEMA,
        pack_id,
        pack_version,
        character_id,
        canonical_name,
        aliases,
        display_names,
        compatibility,
        standalone,
        access,
        redistribution,
        licenses,
        source_refs,
        approval_refs,
        files,
        dependencies,
        package_hash,
        signature,
    )


def _exact_keys(
    value: object,
    required: frozenset[str],
    optional: frozenset[str],
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict) or not required <= set(value) <= required | optional:
        raise _ValidationFailure("invalid_manifest", f"{label} has missing or unknown fields.")
    return value


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise _ValidationFailure("invalid_manifest", f"{label} must be a portable identifier.")
    return value


def _semantic_version_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not SEMVER.fullmatch(value):
        raise _ValidationFailure("invalid_manifest", f"{label} must use MAJOR.MINOR.PATCH.")
    return value


def _semantic_version(value: object, label: str) -> tuple[int, int, int]:
    text = _semantic_version_text(value, label)
    major, minor, patch = text.split(".")
    return int(major), int(minor), int(patch)


def _localized_names(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, dict) or set(value) != set(LANGUAGES):
        raise _ValidationFailure("invalid_manifest", "display_names must contain exactly the four languages.")
    names: list[tuple[str, str]] = []
    for language in LANGUAGES:
        text = _text(value[language], f"display_names.{language}", MAX_NAME_LENGTH)
        names.append((language, text))
    return tuple(names)


def _character(value: object) -> tuple[str, str, tuple[str, ...]]:
    entry = _exact_keys(value, frozenset({"id", "canonical_name", "aliases"}), frozenset(), "character")
    character_id = _identifier(entry["id"], "character.id")
    canonical_name = _text(entry["canonical_name"], "character.canonical_name", MAX_NAME_LENGTH)
    aliases = entry["aliases"]
    if not isinstance(aliases, list) or any(not isinstance(alias, str) for alias in aliases):
        raise _ValidationFailure("invalid_manifest", "character.aliases must be a string list.")
    cleaned = tuple(_text(alias, "character.aliases", MAX_NAME_LENGTH) for alias in aliases)
    if any(not alias or len(alias) > MAX_NAME_LENGTH for alias in cleaned) or len({alias.casefold() for alias in cleaned}) != len(cleaned):
        raise _ValidationFailure("invalid_manifest", "character.aliases must contain unique non-empty names.")
    return character_id, canonical_name, cleaned


def _compatibility(value: object) -> EngineCompatibility:
    entry = _exact_keys(
        value,
        frozenset({"api_version", "min_engine_version", "max_engine_version_exclusive", "required_features"}),
        frozenset(),
        "engine_compatibility",
    )
    api_version = entry["api_version"]
    if not isinstance(api_version, int) or isinstance(api_version, bool) or api_version < 1:
        raise _ValidationFailure("invalid_manifest", "engine_compatibility.api_version must be positive.")
    minimum = _semantic_version_text(entry["min_engine_version"], "min_engine_version")
    maximum = _semantic_version_text(entry["max_engine_version_exclusive"], "max_engine_version_exclusive")
    if _semantic_version(minimum, "min_engine_version") >= _semantic_version(maximum, "max_engine_version_exclusive"):
        raise _ValidationFailure("invalid_manifest", "The engine version interval must be non-empty.")
    features = _feature_list(entry["required_features"], "required_features")
    return EngineCompatibility(api_version, minimum, maximum, features)


def _distribution(value: object) -> tuple[bool, str, str]:
    entry = _exact_keys(
        value,
        frozenset({"standalone_downloadable", "access", "redistribution"}),
        frozenset(),
        "distribution",
    )
    if entry["standalone_downloadable"] is not True:
        raise _ValidationFailure("invalid_manifest", "Character packs must be designed for standalone download.")
    access = entry["access"]
    redistribution = entry["redistribution"]
    if not isinstance(access, str) or not isinstance(redistribution, str) or access not in ACCESS_STATUSES or redistribution not in REDISTRIBUTION_STATUSES:
        raise _ValidationFailure("invalid_manifest", "Distribution decisions must use a supported explicit status.")
    return True, access, redistribution


def _licenses(value: object) -> tuple[LicenseDeclaration, ...]:
    if not isinstance(value, dict) or set(value) != set(LICENSE_COMPONENTS):
        raise _ValidationFailure("license_incomplete", "All four license components are required.")
    declarations: list[LicenseDeclaration] = []
    for component in LICENSE_COMPONENTS:
        entry = _exact_keys(
            value[component],
            frozenset({"status", "rights_holder", "license_expression", "notice_path"}),
            frozenset(),
            f"licenses.{component}",
        )
        status_value = entry["status"]
        if not isinstance(status_value, str) or status_value not in LICENSE_STATUSES:
            raise _ValidationFailure("license_incomplete", f"licenses.{component}.status is unsupported.")
        holder = _text(entry["rights_holder"], f"licenses.{component}.rights_holder", MAX_SCOPE_LENGTH)
        expression = entry["license_expression"]
        if status_value == "declared_license":
            expression = _text(expression, f"licenses.{component}.license_expression", MAX_SCOPE_LENGTH)
        elif expression is not None:
            raise _ValidationFailure("license_incomplete", "Only declared licenses carry a license expression.")
        notice = entry["notice_path"]
        if notice is not None:
            notice = _validate_safe_path(notice)
        declarations.append(LicenseDeclaration(component, status_value, holder, expression, notice))
    return tuple(declarations)


def _references(value: object, label: str, *, require_entries: bool) -> tuple[CharacterPackReference, ...]:
    if not isinstance(value, list) or (require_entries and not value):
        raise _ValidationFailure("invalid_manifest", f"{label} must be a {'non-empty ' if require_entries else ''}list.")
    references: list[CharacterPackReference] = []
    for item in value:
        entry = _exact_keys(item, frozenset({"path", "sha256", "scope"}), frozenset(), label)
        references.append(CharacterPackReference(
            _validate_safe_path(entry["path"]),
            _sha256(entry["sha256"], f"{label}.sha256"),
            _text(entry["scope"], f"{label}.scope", MAX_SCOPE_LENGTH),
        ))
    paths = [reference.path for reference in references]
    if len(paths) != len({_fold_path(path) for path in paths}):
        raise _ValidationFailure("duplicate_path", f"{label} contains duplicate paths.")
    return tuple(references)


def _files(value: object) -> tuple[CharacterPackFile, ...]:
    if not isinstance(value, list) or not value:
        raise _ValidationFailure("invalid_manifest", "files must be a non-empty list.")
    records: list[CharacterPackFile] = []
    folded: set[str] = set()
    for item in value:
        entry = _exact_keys(
            item,
            frozenset({"path", "sha256", "bytes", "media_type", "license_component"}),
            frozenset(),
            "files entry",
        )
        path = _validate_safe_path(entry["path"])
        if path == MANIFEST_PATH or Path(path).suffix.casefold() in FORBIDDEN_SUFFIXES:
            raise _ValidationFailure("forbidden_file", "Executable content and manifest self-declarations are forbidden.", path)
        folded_path = _fold_path(path)
        if folded_path in folded:
            raise _ValidationFailure("duplicate_path", "Every payload path must be declared once.", path)
        folded.add(folded_path)
        size = entry["bytes"]
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise _ValidationFailure("invalid_manifest", "File byte counts must be non-negative integers.", path)
        media_type = entry["media_type"]
        component = entry["license_component"]
        if not isinstance(media_type, str) or not MEDIA_TYPE.fullmatch(media_type):
            raise _ValidationFailure("invalid_manifest", "File media types must use type/subtype syntax.", path)
        if component not in LICENSE_COMPONENTS:
            raise _ValidationFailure("license_incomplete", "Every file must name one license component.", path)
        records.append(CharacterPackFile(path, _sha256(entry["sha256"], "files.sha256"), size, media_type, component))
    return tuple(records)


def _dependencies(value: object) -> tuple[CharacterPackDependency, ...]:
    if not isinstance(value, list):
        raise _ValidationFailure("invalid_manifest", "dependencies must be a list.")
    dependencies: list[CharacterPackDependency] = []
    ids: set[str] = set()
    for item in value:
        entry = _exact_keys(
            item,
            frozenset({"id", "kind", "min_version", "max_version_exclusive", "required"}),
            frozenset(),
            "dependencies entry",
        )
        dependency_id = _identifier(entry["id"], "dependencies.id")
        if dependency_id in ids or (not isinstance(entry["kind"], str) or entry["kind"] not in DEPENDENCY_KINDS) or not isinstance(entry["required"], bool):
            raise _ValidationFailure("invalid_manifest", "Dependencies require unique ids, a supported kind, and required flag.")
        ids.add(dependency_id)
        minimum = _semantic_version_text(entry["min_version"], "dependencies.min_version")
        maximum = _semantic_version_text(entry["max_version_exclusive"], "dependencies.max_version_exclusive")
        if _semantic_version(minimum, "dependencies.min_version") >= _semantic_version(maximum, "dependencies.max_version_exclusive"):
            raise _ValidationFailure("invalid_manifest", "Dependency version intervals must be non-empty.")
        dependencies.append(CharacterPackDependency(dependency_id, entry["kind"], minimum, maximum, entry["required"]))
    return tuple(dependencies)


def _signature(value: object) -> CharacterPackSignature | None:
    if value is None:
        return None
    entry = _exact_keys(value, frozenset({"algorithm", "key_id", "value"}), frozenset(), "signature")
    if entry["algorithm"] != "ed25519" or not isinstance(entry["key_id"], str) or not KEY_ID.fullmatch(entry["key_id"]):
        raise _ValidationFailure("invalid_signature", "Only keyed Ed25519 signature metadata is supported.")
    signature_value = entry["value"]
    if not isinstance(signature_value, str):
        raise _ValidationFailure("invalid_signature", "Signature values must be base64 strings.")
    try:
        decoded = base64.b64decode(signature_value, validate=True)
    except (ValueError, binascii.Error):
        raise _ValidationFailure("invalid_signature", "Signature values must be canonical base64.") from None
    if len(decoded) != ED25519_SIGNATURE_BYTES or base64.b64encode(decoded).decode("ascii") != signature_value:
        raise _ValidationFailure("invalid_signature", "Ed25519 signatures must contain 64 bytes.")
    return CharacterPackSignature("ed25519", entry["key_id"], signature_value)


def _validate_manifest_references(
    licenses: tuple[LicenseDeclaration, ...],
    source_refs: tuple[CharacterPackReference, ...],
    approval_refs: tuple[CharacterPackReference, ...],
    files: tuple[CharacterPackFile, ...],
) -> None:
    by_path = {record.path: record for record in files}
    for declaration in licenses:
        if declaration.notice_path is not None and declaration.notice_path not in by_path:
            raise _ValidationFailure("missing_file", "A license notice is not declared in files.", declaration.notice_path)
    for reference in (*source_refs, *approval_refs):
        record = by_path.get(reference.path)
        if record is None:
            raise _ValidationFailure("missing_file", "A provenance or approval reference is not declared in files.", reference.path)
        if record.sha256 != reference.sha256:
            raise _ValidationFailure("reference_hash_mismatch", "A reference hash differs from its file record.", reference.path)


def _validate_engine_compatibility(
    compatibility: EngineCompatibility,
    engine_version: tuple[int, int, int],
    engine_api_version: int,
    supported_features: frozenset[str],
) -> None:
    minimum = _semantic_version(compatibility.min_version, "min_engine_version")
    maximum = _semantic_version(compatibility.max_version_exclusive, "max_engine_version_exclusive")
    if compatibility.api_version != engine_api_version or not minimum <= engine_version < maximum:
        raise _ValidationFailure("incompatible_engine", "The character pack does not support this engine version or API.")
    missing = set(compatibility.required_features) - supported_features
    if missing:
        raise _ValidationFailure("missing_engine_feature", "The engine does not provide every required package feature.")


def _validate_payload(
    reader: _PackageReader,
    manifest: CharacterPackManifest,
    limits: ValidationLimits,
) -> tuple[int, int]:
    declared = {record.path for record in manifest.files}
    actual = set(reader.names) - {MANIFEST_PATH}
    missing = declared - actual
    extra = actual - declared
    if missing:
        raise _ValidationFailure("missing_file", "A declared package file is missing.", sorted(missing)[0])
    if extra:
        raise _ValidationFailure("undeclared_file", "Every payload file must be declared.", sorted(extra)[0])
    checked_bytes = 0
    for record in manifest.files:
        if record.bytes > limits.max_file_bytes:
            raise _ValidationFailure("file_too_large", "A declared file exceeds the configured size limit.", record.path)
        if reader.declared_size(record.path) != record.bytes:
            raise _ValidationFailure("size_mismatch", "A payload byte count differs from the manifest.", record.path)
        data = reader.read(record.path, limits.max_file_bytes)
        checked_bytes += len(data)
        if len(data) != record.bytes:
            raise _ValidationFailure("size_mismatch", "A payload byte count differs from the manifest.", record.path)
        if hashlib.sha256(data).hexdigest() != record.sha256:
            raise _ValidationFailure("file_hash_mismatch", "A payload SHA-256 differs from the manifest.", record.path)
    return len(manifest.files), checked_bytes


def _validate_signature(
    manifest: CharacterPackManifest,
    verifier: SignatureVerifier | None,
) -> str:
    if manifest.signature is None:
        return "absent"
    if verifier is None:
        raise _ValidationFailure("signature_verifier_required", "Supply a trusted verifier for a signed character pack.")
    try:
        verified = verifier(manifest.signature, bytes.fromhex(manifest.package_hash))
    except Exception:
        raise _ValidationFailure("signature_verification_failed", "The supplied signature verifier failed safely.") from None
    if verified is not True:
        raise _ValidationFailure("signature_verification_failed", "The package signature is not trusted.")
    return "verified"


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise _ValidationFailure("invalid_manifest", f"{label} must be a lowercase SHA-256 digest.")
    return value


def _text(value: object, label: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise _ValidationFailure("invalid_manifest", f"{label} must be text.")
    text = value.strip()
    if not text or len(text) > maximum or any(ord(character) < CONTROL_CHARACTER_BOUNDARY and character not in "\t\n" for character in text):
        raise _ValidationFailure("invalid_manifest", f"{label} must contain supported non-empty text.")
    return text


def _feature_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(feature, str) or not FEATURE.fullmatch(feature) for feature in value):
        raise _ValidationFailure("invalid_manifest", f"{label} must be a portable identifier list.")
    if len(value) != len(set(value)):
        raise _ValidationFailure("invalid_manifest", f"{label} must not contain duplicates.")
    return tuple(value)


def _feature_set(value: Iterable[str], label: str) -> frozenset[str]:
    try:
        features = tuple(value)
    except TypeError:
        raise _ValidationFailure("invalid_engine", f"{label} must be an iterable of feature identifiers.") from None
    if any(not isinstance(feature, str) or not FEATURE.fullmatch(feature) for feature in features):
        raise _ValidationFailure("invalid_engine", f"{label} contains an unsupported feature identifier.")
    return frozenset(features)
