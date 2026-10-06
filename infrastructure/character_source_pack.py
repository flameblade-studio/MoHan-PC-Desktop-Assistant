"""Fail-closed reader that exposes a validated character-pack directory."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import re
lazy import stat
lazy from collections.abc import Iterable, Mapping
lazy from pathlib import Path, PurePosixPath

lazy from domain.character_pack.models import (
    CharacterPackComponent,
    CharacterPackFile,
    CharacterPackManifest,
    CharacterPackValidationResult,
    SignatureVerifier,
    ValidationLimits,
)
lazy from domain.character_pack.validation import DEFAULT_LIMITS, validate_character_pack
lazy from domain.character_source import (
    CharacterAppearanceContract,
    CharacterAssets,
    CharacterBodyProfileReference,
    CharacterCanvas,
    CharacterPersona,
)
lazy from domain.language_support import canonical_ui_language

PERSONA_SCHEMA = "flameblade.character-persona.v1"
DIALOGUE_SCHEMA = "flameblade.character-dialogue.v1"
FULLBODY_RIG_SCHEMA = "flameblade.character-fullbody-rig.v1"
HALFBODY_RIG_SCHEMA = "flameblade.character-halfbody-rig.v1"
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
MAX_COMPONENT_TEXT_LENGTH = 16_384
_EVENT_KEY = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?\Z")


class CharacterPackReadError(ValueError):
    """A stable rejection code and safe explanation for an unusable pack."""

    def __init__(self, code: str, message: str, path: str | None = None) -> None:
        location = f" ({path})" if path else ""
        super().__init__(f"Character pack rejected [{code}]{location}: {message}")
        self.code = code
        self.path = path


class CharacterPackReader(
    CharacterAssets,
    CharacterPersona,
    CharacterAppearanceContract,
):
    """Validate a complete data directory before exposing any character value."""

    def __init__(
        self,
        source: str | Path,
        *,
        engine_version: str,
        engine_api_version: int = 1,
        engine_features: Iterable[str] = (),
        limits: ValidationLimits = DEFAULT_LIMITS,
        signature_verifier: SignatureVerifier | None = None,
    ) -> None:
        result = validate_character_pack(
            source,
            engine_version=engine_version,
            engine_api_version=engine_api_version,
            engine_features=engine_features,
            limits=limits,
            signature_verifier=signature_verifier,
        )
        manifest = _validated_directory_manifest(result)
        root = Path(source).resolve(strict=True)
        records = {record.path: record for record in manifest.files}
        persona_component = _required_component(manifest, "persona", PERSONA_SCHEMA)
        dialogue_component = _required_component(manifest, "dialogue", DIALOGUE_SCHEMA)
        fullbody_component = _required_component(
            manifest,
            "fullbody_rig",
            FULLBODY_RIG_SCHEMA,
        )
        halfbody_component = _required_component(
            manifest,
            "halfbody_rig",
            HALFBODY_RIG_SCHEMA,
        )
        persona_data = _parse_persona(
            _component_document(root, records, persona_component),
            persona_component,
        )
        dialogue_data = _parse_dialogue(
            _component_document(root, records, dialogue_component),
            dialogue_component,
        )
        fullbody_canvas, view_ids, layer_order = _parse_fullbody_rig(
            _component_document(root, records, fullbody_component),
            fullbody_component,
        )
        halfbody_canvas = _parse_halfbody_rig(
            _component_document(root, records, halfbody_component),
            halfbody_component,
        )
        body_profile = _body_profile(fullbody_component, halfbody_component)

        # Assign only after every outer and child contract has passed. A rejected
        # package therefore cannot leak a partially initialized source.
        self._validation_result = result
        self._manifest = manifest
        self._root = root
        self._records = records
        self._display_names = dict(manifest.display_names)
        self._titles, self._persona_prompts = persona_data
        self._dialogue = dialogue_data
        self._body_profile = body_profile
        self._fullbody_canvas = fullbody_canvas
        self._halfbody_canvas = halfbody_canvas
        self._view_ids = view_ids
        self._layer_order = layer_order

    @property
    def validation_result(self) -> CharacterPackValidationResult:
        return self._validation_result

    @property
    def manifest(self) -> CharacterPackManifest:
        return self._manifest

    @property
    def assets(self) -> CharacterAssets:
        return self

    @property
    def persona(self) -> CharacterPersona:
        return self

    @property
    def appearance(self) -> CharacterAppearanceContract:
        return self

    @property
    def asset_root(self) -> Path:
        return self._root

    def resolve_path(self, relative_path: str) -> Path:
        path = _relative_path(relative_path)
        name = path.as_posix()
        record = self._records.get(name)
        directory_prefix = f"{name}/"
        if record is None and not any(
            declared.startswith(directory_prefix) for declared in self._records
        ):
            raise CharacterPackReadError(
                "undeclared_path",
                "The requested path is outside the validated file inventory.",
                name,
            )
        candidate = self._root.joinpath(*path.parts)
        _require_contained_path(self._root, candidate, name)
        if record is None:
            if not candidate.is_dir():
                raise CharacterPackReadError(
                    "missing_file",
                    "The requested character asset directory is missing.",
                    name,
                )
        else:
            _read_verified_file(self._root, record)
        return candidate

    @property
    def canonical_name(self) -> str:
        return self._manifest.canonical_name

    @property
    def aliases(self) -> tuple[str, ...]:
        return self._manifest.aliases

    def display_name(self, language: str) -> str:
        return self._display_names[canonical_ui_language(language)]

    def default_user_title(self, language: str) -> str:
        return self._titles[canonical_ui_language(language)]

    def persona_prompt(self, language: str) -> str:
        return self._persona_prompts[canonical_ui_language(language)]

    def dialogue_line(
        self,
        language: str,
        key: str,
        *,
        variation_index: int = 0,
    ) -> str:
        lines = self._dialogue[canonical_ui_language(language)].get(key, ())
        return lines[variation_index % len(lines)] if lines else ""

    @property
    def body_profile(self) -> CharacterBodyProfileReference:
        return self._body_profile

    @property
    def view_ids(self) -> tuple[str, ...]:
        return self._view_ids

    @property
    def fullbody_canvas(self) -> CharacterCanvas:
        return self._fullbody_canvas

    @property
    def halfbody_canvas(self) -> CharacterCanvas:
        return self._halfbody_canvas

    @property
    def layer_order(self) -> tuple[str, ...]:
        return self._layer_order


def _validated_directory_manifest(
    result: CharacterPackValidationResult,
) -> CharacterPackManifest:
    if not result.valid or result.manifest is None:
        issue = result.issues[0]
        raise CharacterPackReadError(issue.code, issue.message, issue.path)
    if result.source_kind != "directory":
        raise CharacterPackReadError(
            "directory_required",
            "Runtime character sources require a validated directory.",
        )
    return result.manifest


def _required_component(
    manifest: CharacterPackManifest,
    kind: str,
    schema: str,
) -> CharacterPackComponent:
    matches = tuple(component for component in manifest.components if component.kind == kind)
    if len(matches) != 1 or not matches[0].required:
        raise CharacterPackReadError(
            "missing_component",
            f"Exactly one required {kind} component is needed.",
        )
    component = matches[0]
    if component.schema != schema:
        raise CharacterPackReadError(
            "unsupported_component_schema",
            f"The {kind} component must use {schema}.",
            component.path,
        )
    return component


def _component_document(
    root: Path,
    records: Mapping[str, CharacterPackFile],
    component: CharacterPackComponent,
) -> dict[str, object]:
    record = records[component.path]
    data = _read_verified_file(root, record)
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CharacterPackReadError(
            "invalid_component",
            f"Component JSON is not valid UTF-8 data: {type(error).__name__}.",
            component.path,
        ) from None
    if not isinstance(value, dict):
        raise CharacterPackReadError(
            "invalid_component",
            "Component JSON must contain one object.",
            component.path,
        )
    return value


def _parse_persona(
    value: dict[str, object],
    component: CharacterPackComponent,
) -> tuple[dict[str, str], dict[str, str]]:
    entry = _exact_keys(
        value,
        {"schema", "schema_version", "default_user_titles", "persona_prompts"},
        component.path,
    )
    _schema_header(entry, component)
    return (
        _localized_text(entry["default_user_titles"], component.path),
        _localized_text(entry["persona_prompts"], component.path),
    )


def _parse_dialogue(
    value: dict[str, object],
    component: CharacterPackComponent,
) -> dict[str, dict[str, tuple[str, ...]]]:
    entry = _exact_keys(value, {"schema", "schema_version", "locales"}, component.path)
    _schema_header(entry, component)
    locales = entry["locales"]
    if not isinstance(locales, dict) or set(locales) != set(LANGUAGES):
        raise CharacterPackReadError(
            "invalid_component",
            "Dialogue must contain exactly the four supported locales.",
            component.path,
        )
    parsed: dict[str, dict[str, tuple[str, ...]]] = {}
    for language in LANGUAGES:
        catalog = locales[language]
        if not isinstance(catalog, dict):
            raise CharacterPackReadError(
                "invalid_component",
                "Each dialogue locale must be an event object.",
                component.path,
            )
        events: dict[str, tuple[str, ...]] = {}
        for key, raw_lines in catalog.items():
            if not isinstance(key, str) or not _EVENT_KEY.fullmatch(key):
                raise CharacterPackReadError(
                    "invalid_component",
                    "Dialogue event keys must be portable identifiers.",
                    component.path,
                )
            if not isinstance(raw_lines, list) or not raw_lines:
                raise CharacterPackReadError(
                    "invalid_component",
                    "Dialogue events require at least one line.",
                    component.path,
                )
            events[key] = tuple(
                _nonempty_text(line, "Dialogue lines", component.path)
                for line in raw_lines
            )
        parsed[language] = events
    return parsed


def _parse_fullbody_rig(
    value: dict[str, object],
    component: CharacterPackComponent,
) -> tuple[CharacterCanvas, tuple[str, ...], tuple[str, ...]]:
    entry = _exact_keys(
        value,
        {"schema", "schema_version", "canvas", "views", "layers"},
        component.path,
    )
    _schema_header(entry, component)
    return (
        _canvas(entry["canvas"], component.path),
        _unique_text_list(entry["views"], "views", component.path),
        _unique_text_list(entry["layers"], "layers", component.path),
    )


def _parse_halfbody_rig(
    value: dict[str, object],
    component: CharacterPackComponent,
) -> CharacterCanvas:
    entry = _exact_keys(
        value,
        {"schema", "schema_version", "canvas"},
        component.path,
    )
    _schema_header(entry, component)
    return _canvas(entry["canvas"], component.path)


def _schema_header(
    entry: Mapping[str, object],
    component: CharacterPackComponent,
) -> None:
    if entry["schema"] != component.schema or entry["schema_version"] != 1:
        raise CharacterPackReadError(
            "unsupported_component_schema",
            "The component schema name and version must match its manifest entry.",
            component.path,
        )


def _body_profile(
    fullbody: CharacterPackComponent,
    halfbody: CharacterPackComponent,
) -> CharacterBodyProfileReference:
    profile = (fullbody.body_profile_id, fullbody.body_profile_version)
    if profile != (halfbody.body_profile_id, halfbody.body_profile_version):
        raise CharacterPackReadError(
            "incompatible_body_profile",
            "Full-body and half-body rigs must share one body profile.",
        )
    profile_id, version = profile
    if profile_id is None or version is None:
        raise CharacterPackReadError(
            "incompatible_body_profile",
            "Visual components require a body-profile binding.",
        )
    return CharacterBodyProfileReference(profile_id, version)


def _localized_text(value: object, path: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != set(LANGUAGES):
        raise CharacterPackReadError(
            "invalid_component",
            "Localized values must contain exactly the four supported locales.",
            path,
        )
    return {
        language: _nonempty_text(value[language], "Localized values", path)
        for language in LANGUAGES
    }


def _canvas(value: object, path: str) -> CharacterCanvas:
    entry = _exact_keys(value, {"width", "height", "mode"}, path)
    width = entry["width"]
    height = entry["height"]
    mode = entry["mode"]
    if (
        not isinstance(width, int)
        or isinstance(width, bool)
        or not isinstance(height, int)
        or isinstance(height, bool)
        or width < 1
        or height < 1
        or not isinstance(mode, str)
        or mode != "RGBA"
    ):
        raise CharacterPackReadError(
            "invalid_component",
            "Character canvases require positive dimensions and RGBA mode.",
            path,
        )
    return CharacterCanvas(width, height, mode)


def _unique_text_list(value: object, label: str, path: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise CharacterPackReadError(
            "invalid_component",
            f"Character {label} require a non-empty list.",
            path,
        )
    result = tuple(_nonempty_text(item, f"Character {label}", path) for item in value)
    if len(set(result)) != len(result):
        raise CharacterPackReadError(
            "invalid_component",
            f"Character {label} must remain unique.",
            path,
        )
    return result


def _nonempty_text(value: object, label: str, path: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > MAX_COMPONENT_TEXT_LENGTH
    ):
        raise CharacterPackReadError(
            "invalid_component",
            f"{label} must contain bounded non-empty text.",
            path,
        )
    return value


def _exact_keys(
    value: object,
    expected: set[str],
    path: str,
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise CharacterPackReadError(
            "invalid_component",
            "Component data has missing or unknown fields.",
            path,
        )
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CharacterPackReadError(
                "invalid_component",
                "Component JSON object keys must be unique.",
                key,
            )
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise CharacterPackReadError(
        "invalid_component",
        f"Component JSON cannot contain {value}.",
    )


def _read_verified_file(root: Path, record: CharacterPackFile) -> bytes:
    candidate = root.joinpath(*PurePosixPath(record.path).parts)
    _require_contained_path(root, candidate, record.path)
    metadata = candidate.stat(follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != record.bytes:
        raise CharacterPackReadError(
            "size_mismatch",
            "A character asset no longer matches the validated byte count.",
            record.path,
        )
    data = candidate.read_bytes()
    if hashlib.sha256(data).hexdigest() != record.sha256:
        raise CharacterPackReadError(
            "file_hash_mismatch",
            "A character asset no longer matches the validated SHA-256.",
            record.path,
        )
    return data


def _require_contained_path(root: Path, candidate: Path, name: str) -> None:
    if candidate.is_symlink() or candidate.is_junction():
        raise CharacterPackReadError(
            "unsafe_path",
            "Character asset paths cannot use symbolic links or junctions.",
            name,
        )
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        raise CharacterPackReadError(
            "missing_file",
            "A validated character asset is no longer present.",
            name,
        ) from None
    if not resolved.is_relative_to(root):
        raise CharacterPackReadError(
            "unsafe_path",
            "A character asset path escapes the validated package root.",
            name,
        )
    for ancestor in candidate.parents:
        if ancestor == root:
            break
        if ancestor.is_symlink() or ancestor.is_junction():
            raise CharacterPackReadError(
                "unsafe_path",
                "Character asset ancestors cannot use symbolic links or junctions.",
                name,
            )


def _relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CharacterPackReadError(
            "unsafe_path",
            "Character asset paths must use relative POSIX syntax.",
        )
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CharacterPackReadError(
            "unsafe_path",
            "Character asset paths must use canonical relative syntax.",
            value,
        )
    return path


__all__ = (
    "DIALOGUE_SCHEMA",
    "FULLBODY_RIG_SCHEMA",
    "HALFBODY_RIG_SCHEMA",
    "PERSONA_SCHEMA",
    "CharacterPackReadError",
    "CharacterPackReader",
)
