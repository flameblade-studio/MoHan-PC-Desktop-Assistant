"""Build a byte-preserving, reproducible character pack."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import shutil
lazy import sys
lazy import tempfile
lazy import zipfile
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath
lazy from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from domain.character_pack.models import ValidationLimits
lazy from domain.character_pack.validation import SCHEMA, compute_package_hash, validate_character_pack
lazy from domain.outfit_pack import inspect_outfit_pack
lazy from domain.version_info import FALLBACK_VERSION

DEFAULT_INVENTORY = Path("docs/character-pack/mohan-inventory.json")
DEFAULT_SOURCE = Path("assets/characters/mohan/pack-source.json")
BUILD_SOURCE_SCHEMA = "flameblade.character-pack-build-source.v1"
PACK_SCOPES = frozenset({"runtime_data", "product_validation_data"})
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
LIMIT_FIELDS = (
    "max_archive_bytes",
    "max_zip_directory_bytes",
    "max_manifest_bytes",
    "max_file_bytes",
    "max_total_bytes",
    "max_files",
    "max_compression_ratio",
)
MEDIA_TYPES = {
    ".ico": "image/vnd.microsoft.icon",
    ".json": "application/json",
    ".mohan-outfit": "application/vnd.flameblade.mohan-outfit+zip",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
REGULAR_FILE_MODE = 0o100644
COPY_BUFFER_BYTES = 1024 * 1024


class CharacterPackBuildError(ValueError):
    """The build inputs cannot produce a valid character pack."""


@dataclass(frozen=True, slots=True)
class CharacterPackBuildResult:
    """Measured result of one validated directory or ZIP build."""

    output: Path
    output_format: str
    package_hash: str
    payload_files: int
    payload_bytes: int
    output_bytes: int | None
    validation_limits: ValidationLimits


@dataclass(frozen=True, slots=True)
class _Payload:
    path: str
    source: Path
    sha256: str
    bytes: int
    category: str
    media_type: str
    license_component: str


def build_character_pack(
    output: str | Path,
    *,
    output_format: str,
    repo_root: str | Path = ROOT,
    inventory_path: str | Path = DEFAULT_INVENTORY,
    source_path: str | Path = DEFAULT_SOURCE,
) -> CharacterPackBuildResult:
    """Build and validate one pack without changing any repository payload."""
    if output_format not in {"directory", "zip"}:
        raise CharacterPackBuildError("output_format must be directory or zip")
    root = Path(repo_root).resolve(strict=True)
    destination = Path(output).resolve(strict=False)
    if destination.exists() or destination.is_symlink():
        raise CharacterPackBuildError(f"output already exists: {destination}")
    inventory_file = _input_path(root, inventory_path)
    source_file = _input_path(root, source_path)
    source = _load_json_object(source_file)
    _require_source_header(source)
    character_id = _text(source.get("character_id"), "character_id")
    limits = _validation_limits(source.get("validation_limits"))
    inventory = _load_json_object(inventory_file)
    payloads = _inventory_payloads(root, inventory, character_id=character_id)
    manifest = _manifest(source, payloads, root)
    manifest["package_hash"] = compute_package_hash(manifest)
    manifest_bytes = _json_bytes(manifest)
    if len(manifest_bytes) > limits.max_manifest_bytes:
        raise CharacterPackBuildError("manifest.json exceeds the recorded validation limit")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="character-pack-",
        dir=destination.parent,
    ) as temporary:
        staged = Path(temporary) / ("pack.zip" if output_format == "zip" else "pack")
        if output_format == "zip":
            _write_zip(staged, manifest_bytes, payloads)
        else:
            _write_directory(staged, manifest_bytes, payloads)
        _validate_staged(staged, manifest, limits)
        staged.replace(destination)
    output_bytes = destination.stat().st_size if output_format == "zip" else None
    return CharacterPackBuildResult(
        output=destination,
        output_format=output_format,
        package_hash=_text(manifest["package_hash"], "package_hash"),
        payload_files=len(payloads),
        payload_bytes=sum(item.bytes for item in payloads),
        output_bytes=output_bytes,
        validation_limits=limits,
    )


def _input_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise CharacterPackBuildError(f"build input is outside the repository: {value}")
    return resolved


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CharacterPackBuildError(f"unreadable UTF-8 JSON input: {path.name}") from error
    return _object(value, path.name)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CharacterPackBuildError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_source_header(source: Mapping[str, object]) -> None:
    if source.get("schema") != BUILD_SOURCE_SCHEMA or source.get("schema_version") != 1:
        raise CharacterPackBuildError(f"build source must use {BUILD_SOURCE_SCHEMA} version 1")


def _validation_limits(value: object) -> ValidationLimits:
    entry = _object(value, "validation_limits")
    _exact_keys(entry, LIMIT_FIELDS, "validation_limits")
    measured: dict[str, int] = {}
    for field in LIMIT_FIELDS:
        item = entry[field]
        if not isinstance(item, int) or isinstance(item, bool) or item < 1:
            raise CharacterPackBuildError(f"validation_limits.{field} must be a positive integer")
        measured[field] = item
    return ValidationLimits(**measured)


def _inventory_payloads(
    root: Path,
    inventory: Mapping[str, object],
    *,
    character_id: str,
) -> tuple[_Payload, ...]:
    rows = _array(inventory.get("files"), "inventory.files")
    payloads: list[_Payload] = []
    seen: set[str] = set()
    character_root = f"assets/characters/{character_id}/"
    for raw in rows:
        row = _object(raw, "inventory.files[]")
        if row.get("scope") not in PACK_SCOPES:
            continue
        relative = _text(row.get("path"), "inventory.files[].path")
        if "!" in relative:
            continue
        if relative.startswith("assets/characters/") and not relative.startswith(
            character_root
        ):
            continue
        if relative in seen:
            raise CharacterPackBuildError(f"duplicate inventory payload: {relative}")
        seen.add(relative)
        source = _repository_payload(root, relative)
        expected_bytes = _non_negative_int(row.get("bytes"), f"{relative}.bytes")
        expected_hash = _text(row.get("sha256"), f"{relative}.sha256")
        actual_bytes, actual_hash = _measure_file(source)
        if (actual_bytes, actual_hash) != (expected_bytes, expected_hash):
            raise CharacterPackBuildError(f"inventory bytes or SHA-256 are stale: {relative}")
        category = _text(row.get("category"), f"{relative}.category")
        media_type = MEDIA_TYPES.get(PurePosixPath(relative).suffix.lower())
        if media_type is None:
            raise CharacterPackBuildError(f"payload has no declared media type: {relative}")
        payloads.append(
            _Payload(
                path=relative,
                source=source,
                sha256=actual_hash,
                bytes=actual_bytes,
                category=category,
                media_type=media_type,
                license_component=_license_component(relative, category),
            )
        )
    payloads.sort(key=lambda item: item.path)
    if not payloads:
        raise CharacterPackBuildError("inventory selected no physical product payloads")
    return tuple(payloads)


def _repository_payload(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or "\\" in relative or any(part in {"", ".", ".."} for part in pure.parts):
        raise CharacterPackBuildError(f"inventory path is not repository-relative: {relative}")
    candidate = root.joinpath(*pure.parts)
    if candidate.is_symlink() or candidate.is_junction() or not candidate.is_file():
        raise CharacterPackBuildError(f"inventory payload is not a regular file: {relative}")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise CharacterPackBuildError(f"inventory payload escapes the repository: {relative}")
    return resolved


def _measure_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(COPY_BUFFER_BYTES):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


# Every character-data category must map explicitly; an unknown one fails the
# build instead of silently landing in program_data with the wrong license class.
CHARACTER_DATA_LICENSE_COMPONENTS = {
    "character_voice_data": "voice",
    "character_dialogue_data": "persona_dialogue",
    "character_persona_data": "persona_dialogue",
    "character_runtime_dialogue_data": "persona_dialogue",
    "character_ui_identifier_data": "persona_dialogue",
    "character_rig_data": "program_data",
    "character_runtime_binding_data": "program_data",
    "character_expression_catalog": "program_data",
}


def _license_component(path: str, category: str) -> str:
    if path.startswith("assets/characters/"):
        if category not in CHARACTER_DATA_LICENSE_COMPONENTS:
            raise CharacterPackBuildError(f"character data category has no license component: {category} ({path})")
        return CHARACTER_DATA_LICENSE_COMPONENTS[category]
    if PurePosixPath(path).suffix.lower() in {".ico", ".mohan-outfit", ".png", ".svg"}:
        return "character_art"
    return "program_data"


def _manifest(
    source: Mapping[str, object],
    payloads: Sequence[_Payload],
    root: Path,
) -> dict[str, object]:
    payload_by_path = {item.path: item for item in payloads}
    identity = _identity(source.get("identity"), root, payload_by_path)
    compatibility = _engine_compatibility(source.get("engine_compatibility"))
    files = [
        {
            "path": item.path,
            "sha256": item.sha256,
            "bytes": item.bytes,
            "media_type": item.media_type,
            "license_component": item.license_component,
        }
        for item in payloads
    ]
    manifest: dict[str, object] = {
        "schema": SCHEMA,
        "pack_id": _text(source.get("pack_id"), "pack_id"),
        "pack_version": _text(source.get("pack_version"), "pack_version"),
        "display_names": identity["display_names"],
        "character": {
            "id": _text(source.get("character_id"), "character_id"),
            "canonical_name": identity["canonical_name"],
            "aliases": identity["aliases"],
        },
        "engine_compatibility": compatibility,
        "distribution": dict(_object(source.get("distribution"), "distribution")),
        "licenses": dict(_object(source.get("licenses"), "licenses")),
        "source_refs": _references(source.get("source_refs"), payload_by_path, "source_refs"),
        "approval_refs": _references(source.get("approval_refs"), payload_by_path, "approval_refs"),
        "files": files,
        "components": _components(source.get("components"), payload_by_path),
        "package_hash": "0" * 64,
    }
    dependencies = _dependencies(source.get("dependencies", []))
    if dependencies:
        manifest["dependencies"] = dependencies
    return manifest


def _identity(
    value: object,
    root: Path,
    payloads: Mapping[str, _Payload],
) -> dict[str, object]:
    identity = _object(value, "identity")
    _exact_keys(identity, ("profile", "personas"), "identity")
    profile_path = _text(identity["profile"], "identity.profile")
    profile = _declared_json(root, profile_path, payloads)
    if profile.get("schema") != "flameblade.character-identity-profile.v1":
        raise CharacterPackBuildError("identity profile uses an unexpected schema")
    defaults = _object(profile.get("defaults"), "identity profile defaults")
    canonical_name = _text(defaults.get("assistant_name"), "identity canonical name")
    personalization = _object(profile.get("personalization"), "identity personalization")
    aliases: list[str] = []
    folded = {canonical_name.casefold()}
    _append_aliases(
        aliases,
        folded,
        _array(personalization.get("assistant_tokens"), "identity assistant tokens"),
    )
    persona_paths = _object(identity["personas"], "identity.personas")
    _exact_keys(persona_paths, LANGUAGES, "identity.personas")
    display_names: dict[str, str] = {}
    for language in LANGUAGES:
        persona_path = _text(persona_paths[language], f"identity.personas.{language}")
        persona = _declared_json(root, persona_path, payloads)
        if persona.get("schema") != "flameblade.character-persona.v1":
            raise CharacterPackBuildError(f"{persona_path} uses an unexpected schema")
        locale_identity = _object(persona.get("identity"), f"{persona_path}.identity")
        display_names[language] = _text(locale_identity.get("display_name"), f"{persona_path}.display_name")
        _append_aliases(
            aliases,
            folded,
            [locale_identity.get("assistant_alias")],
        )
    return {
        "canonical_name": canonical_name,
        "aliases": aliases,
        "display_names": display_names,
    }


def _append_aliases(aliases: list[str], folded: set[str], values: Sequence[object]) -> None:
    for value in values:
        alias = _text(value, "character alias")
        identity = alias.casefold()
        if identity not in folded:
            folded.add(identity)
            aliases.append(alias)


def _declared_json(
    root: Path,
    relative: str,
    payloads: Mapping[str, _Payload],
) -> dict[str, Any]:
    payload = payloads.get(relative)
    if payload is None:
        raise CharacterPackBuildError(f"build source refers to an undeclared payload: {relative}")
    return _load_json_object(root.joinpath(*PurePosixPath(relative).parts))


def _engine_compatibility(value: object) -> dict[str, object]:
    entry = _object(value, "engine_compatibility")
    fields = ("api_version", "min_engine_version", "max_engine_version_exclusive", "required_features")
    _exact_keys(entry, fields, "engine_compatibility")
    minimum = _text(entry["min_engine_version"], "engine_compatibility.min_engine_version")
    maximum = _text(entry["max_engine_version_exclusive"], "engine_compatibility.max_engine_version_exclusive")
    if minimum != FALLBACK_VERSION:
        raise CharacterPackBuildError("pack-source minimum engine version is stale")
    try:
        major, _minor, _patch = (int(part) for part in FALLBACK_VERSION.split("."))
    except ValueError as error:
        raise CharacterPackBuildError("domain.version_info.FALLBACK_VERSION is not stable semver") from error
    if maximum != f"{major + 1}.0.0":
        raise CharacterPackBuildError("pack-source maximum engine version must be the next major version")
    return {
        "api_version": entry["api_version"],
        "min_engine_version": minimum,
        "max_engine_version_exclusive": maximum,
        "required_features": list(_array(entry["required_features"], "required_features")),
    }


def _references(
    value: object,
    payloads: Mapping[str, _Payload],
    label: str,
) -> list[dict[str, object]]:
    references: list[dict[str, object]] = []
    for raw in _array(value, label):
        entry = _object(raw, f"{label}[]")
        _exact_keys(entry, ("path", "scope"), f"{label}[]")
        path = _text(entry["path"], f"{label}[].path")
        payload = payloads.get(path)
        if payload is None:
            raise CharacterPackBuildError(f"{label} refers to an undeclared payload: {path}")
        references.append({
            "path": path,
            "sha256": payload.sha256,
            "scope": _text(entry["scope"], f"{label}[].scope"),
        })
    references.sort(key=lambda item: _text(item["path"], "reference path"))
    return references


def _components(
    value: object,
    payloads: Mapping[str, _Payload],
) -> list[dict[str, object]]:
    components: list[dict[str, object]] = []
    for raw in _array(value, "components"):
        entry = _object(raw, "components[]")
        fields = ("id", "kind", "schema", "path", "required", "body_profile")
        _exact_keys(entry, fields, "components[]")
        path = _text(entry["path"], "components[].path")
        payload = payloads.get(path)
        if payload is None:
            raise CharacterPackBuildError(f"component refers to an undeclared payload: {path}")
        schema = _text(entry["schema"], "components[].schema")
        _validate_component_source(payload, schema, entry.get("body_profile"))
        components.append({
            "id": _text(entry["id"], "components[].id"),
            "kind": _text(entry["kind"], "components[].kind"),
            "schema": schema,
            "path": path,
            "sha256": payload.sha256,
            "required": entry["required"],
            "body_profile": entry["body_profile"],
        })
    components.sort(key=lambda item: _text(item["id"], "component id"))
    return components


def _dependencies(value: object) -> list[dict[str, object]]:
    dependencies: list[dict[str, object]] = []
    fields = ("id", "kind", "min_version", "max_version_exclusive", "required")
    for raw in _array(value, "dependencies"):
        entry = _object(raw, "dependencies[]")
        _exact_keys(entry, fields, "dependencies[]")
        dependencies.append(
            {
                "id": _text(entry["id"], "dependencies[].id"),
                "kind": _text(entry["kind"], "dependencies[].kind"),
                "min_version": _text(
                    entry["min_version"],
                    "dependencies[].min_version",
                ),
                "max_version_exclusive": _text(
                    entry["max_version_exclusive"],
                    "dependencies[].max_version_exclusive",
                ),
                "required": entry["required"],
            }
        )
    dependencies.sort(key=lambda item: _text(item["id"], "dependency id"))
    return dependencies


def _validate_component_source(payload: _Payload, schema: str, body_profile: object) -> None:
    if payload.source.suffix == ".mohan-outfit":
        inspect_outfit_pack(payload.source)
        if schema != "mohan-outfit-pack.v2":
            raise CharacterPackBuildError(f"outfit component schema is stale: {payload.path}")
        return
    document = _load_json_object(payload.source)
    if document.get("schema") != schema:
        raise CharacterPackBuildError(f"component schema does not match its payload: {payload.path}")
    if (
        schema == "flameblade.character-rig.v1"
        and _body_profile_identity(document.get("body_profile"))
        != _body_profile_identity(body_profile)
    ):
        raise CharacterPackBuildError("rig component body profile differs from the rig manifest")


def _body_profile_identity(value: object) -> tuple[object, object]:
    profile = _object(value, "body profile")
    return profile.get("id"), profile.get("version")


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _write_directory(root: Path, manifest: bytes, payloads: Sequence[_Payload]) -> None:
    root.mkdir()
    (root / "manifest.json").write_bytes(manifest)
    for payload in payloads:
        destination = root.joinpath(*PurePosixPath(payload.path).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(payload.source, destination)


def _write_zip(path: Path, manifest: bytes, payloads: Sequence[_Payload]) -> None:
    with zipfile.ZipFile(
        path,
        "w",
        compression=zipfile.ZIP_STORED,
        allowZip64=False,
    ) as archive:
        archive.writestr(_zip_info("manifest.json"), manifest)
        for payload in payloads:
            archive.writestr(_zip_info(payload.path), payload.source.read_bytes())


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = REGULAR_FILE_MODE << 16
    info.extra = b""
    info.comment = b""
    return info


def _validate_staged(
    staged: Path,
    manifest: Mapping[str, object],
    limits: ValidationLimits,
) -> None:
    compatibility = _object(manifest["engine_compatibility"], "engine_compatibility")
    result = validate_character_pack(
        staged,
        engine_version=_text(compatibility["min_engine_version"], "min_engine_version"),
        engine_api_version=_positive_int(compatibility["api_version"], "api_version"),
        engine_features=_string_sequence(compatibility["required_features"], "required_features"),
        limits=limits,
    )
    if not result.valid:
        issue = result.issues[0] if result.issues else None
        detail = issue.code if issue is not None else "unknown_validation_failure"
        raise CharacterPackBuildError(f"built character pack failed validation: {detail}")
    if result.package_hash != manifest["package_hash"]:
        raise CharacterPackBuildError("validated package hash differs from the build result")


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CharacterPackBuildError(f"{label} must be an object")
    return dict(value)


def _array(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CharacterPackBuildError(f"{label} must be an array")
    return list(value)


def _exact_keys(value: Mapping[str, object], fields: Sequence[str], label: str) -> None:
    if set(value) != set(fields):
        raise CharacterPackBuildError(f"{label} has missing or unknown fields")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CharacterPackBuildError(f"{label} must be non-empty text")
    return value


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CharacterPackBuildError(f"{label} must be a non-negative integer")
    return value


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise CharacterPackBuildError(f"{label} must be a positive integer")
    return value


def _string_sequence(value: object, label: str) -> tuple[str, ...]:
    items = _array(value, label)
    return tuple(_text(item, label) for item in items)


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=("directory", "zip"), required=True, dest="output_format")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parsed = parser.parse_args(arguments)
    try:
        result = build_character_pack(
            parsed.output,
            output_format=parsed.output_format,
            repo_root=parsed.repo_root,
            inventory_path=parsed.inventory,
            source_path=parsed.source,
        )
    except CharacterPackBuildError as error:
        parser.error(str(error))
    print(f"CHARACTER_PACK_BUILT={result.output}")
    print(f"CHARACTER_PACK_FORMAT={result.output_format}")
    print(f"PACKAGE_HASH={result.package_hash}")
    print(f"PAYLOAD_FILES={result.payload_files}")
    print(f"PAYLOAD_BYTES={result.payload_bytes}")
    if result.output_bytes is not None:
        print(f"ARCHIVE_BYTES={result.output_bytes}")
    print(
        "VALIDATION_LIMITS="
        f"archive:{result.validation_limits.max_archive_bytes},"
        f"total:{result.validation_limits.max_total_bytes}"
    )
    print("CHARACTER_PACK_VALID=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
