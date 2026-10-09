"""Build a byte-preserving, reproducible MoHan character pack."""

from __future__ import annotations

lazy import argparse
lazy import sys
lazy from collections.abc import Sequence
lazy from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from application.service_container import create_default_character_source
lazy from domain.character_pack.validation import SCHEMA
lazy from domain.character_pack.appearance_data import (
    APPEARANCE_DEFAULTS_SCHEMA,
    load_character_appearance_defaults,
)
lazy from domain.character_pack.character_data_models import CharacterDataError
lazy from domain.outfit_pack import inspect_outfit_pack
lazy from domain.version_info import FALLBACK_VERSION
lazy from huapu import character_pack_builder as _core

DEFAULT_INVENTORY = Path("docs/character-pack/mohan-inventory.json")
DEFAULT_SOURCE = Path("assets/characters/mohan/pack-source.json")
BUILD_SOURCE_SCHEMA = _core.BUILD_SOURCE_SCHEMA
PACK_SCOPES = _core.PACK_SCOPES
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
LIMIT_FIELDS = _core.LIMIT_FIELDS
MEDIA_TYPES = {
    ".ico": "image/vnd.microsoft.icon",
    ".json": "application/json",
    ".md": "text/markdown",
    ".mohan-outfit": "application/vnd.flameblade.mohan-outfit+zip",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}
FIXED_ZIP_TIME = _core.FIXED_ZIP_TIME
REGULAR_FILE_MODE = _core.REGULAR_FILE_MODE
COPY_BUFFER_BYTES = _core.COPY_BUFFER_BYTES

CharacterPackBuildError = _core.CharacterPackBuildError
CharacterPackBuildResult = _core.CharacterPackBuildResult
CharacterPackBuildSettings = _core.CharacterPackBuildSettings

# Every character-data category maps explicitly; unknown data fails closed.
CHARACTER_DATA_LICENSE_COMPONENTS = {
    "character_license_notice": "program_data",
    "character_appearance_defaults": "program_data",
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
            raise CharacterPackBuildError(
                f"character data category has no license component: {category} ({path})"
            )
        return CHARACTER_DATA_LICENSE_COMPONENTS[category]
    if PurePosixPath(path).suffix.lower() in {".ico", ".mohan-outfit", ".png", ".svg"}:
        return "character_art"
    return "program_data"


def _validate_mohan_component(path: Path, schema: str) -> bool:
    if schema == APPEARANCE_DEFAULTS_SCHEMA:
        try:
            load_character_appearance_defaults(path)
        except CharacterDataError as error:
            raise CharacterPackBuildError(
                f"appearance defaults component is invalid: {path.as_posix()}"
            ) from error
        return True
    if path.suffix != ".mohan-outfit":
        return False
    inspect_outfit_pack(path)
    if schema != "mohan-outfit-pack.v2":
        raise CharacterPackBuildError(f"outfit component schema is stale: {path.as_posix()}")
    return True


DEFAULT_BUILD_SETTINGS = CharacterPackBuildSettings(
    manifest_schema=SCHEMA,
    build_source_schema=BUILD_SOURCE_SCHEMA,
    characters_root="assets/characters",
    engine_version=FALLBACK_VERSION,
    languages=LANGUAGES,
    pack_scopes=PACK_SCOPES,
    media_types=MEDIA_TYPES,
    identity_profile_schema="flameblade.character-identity-profile.v1",
    persona_schema="flameblade.character-persona.v1",
    rig_schema="flameblade.character-rig.v1",
    license_classifier=_license_component,
    special_component_validator=_validate_mohan_component,
)


def build_character_pack(
    output: str | Path,
    *,
    output_format: str,
    repo_root: str | Path = ROOT,
    inventory_path: str | Path = DEFAULT_INVENTORY,
    source_path: str | Path = DEFAULT_SOURCE,
) -> CharacterPackBuildResult:
    """Build through Huapu while retaining the historical MoHan API."""
    create_default_character_source()
    return _core.build_character_pack(
        output,
        output_format=output_format,
        repo_root=repo_root,
        inventory_path=inventory_path,
        source_path=source_path,
        settings=DEFAULT_BUILD_SETTINGS,
    )


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
