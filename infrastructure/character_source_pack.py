"""Fail-closed reader that exposes a validated character-pack directory."""

from __future__ import annotations

lazy import hashlib
lazy import stat
lazy from collections.abc import Iterable, Mapping
lazy from pathlib import Path, PurePosixPath

lazy from domain.character_pack.character_data_models import (
    EXPRESSION_SCHEMA as CHARACTER_EXPRESSION_SCHEMA,
    RIG_SCHEMA as CHARACTER_RIG_SCHEMA,
    CharacterRigManifest,
    ExpressionStateCatalog,
    MohanCharacterData,
    VoiceProfile,
)
lazy from domain.character_pack.appearance_data import APPEARANCE_DEFAULTS_SCHEMA
lazy from domain.character_expression_data import load_expression_catalog
lazy from domain.character_pack.character_data import load_mohan_character_data
lazy from domain.character_pack.models import (
    CharacterPackComponent,
    CharacterPackFile,
    CharacterPackManifest,
    CharacterPackValidationResult,
    SignatureVerifier,
    ValidationLimits,
)
lazy from domain.character_pack.validation import DEFAULT_LIMITS, validate_character_pack
lazy from domain.character_pose import canonical_view_id
lazy from domain.character_rig_data import load_rig_manifest
lazy from domain.character_source import (
    CharacterAppearanceContract,
    CharacterAppearanceDefaults,
    CharacterAssets,
    CharacterBodyProfileReference,
    CharacterCanvas,
    CharacterPersona,
    CharacterVoice,
)
lazy from domain.language_support import canonical_ui_language

IDENTITY_SCHEMA = "flameblade.character-identity-profile.v1"
PERSONA_SCHEMA = "flameblade.character-persona.v1"
DIALOGUE_SCHEMA = "flameblade.character-dialogue.v1"
EVENTS_SCHEMA = "flameblade.character-events.v1"
VOICE_SCHEMA = "flameblade.character-voice-profile.v1"
FULLBODY_RIG_SCHEMA = CHARACTER_RIG_SCHEMA
HALFBODY_RIG_SCHEMA = CHARACTER_RIG_SCHEMA
EXPRESSION_STATE_SCHEMA = CHARACTER_EXPRESSION_SCHEMA
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
_FULLBODY_EXPRESSION_SCHEMA = "mohan.complete-expression-manifest.v1"
_HALFBODY_EXPRESSION_SCHEMA = "mohan.complete-halfbody-expressions.v1"
_KNOWN_EXPRESSION_SCHEMAS = frozenset(
    {
        EXPRESSION_STATE_SCHEMA,
        _FULLBODY_EXPRESSION_SCHEMA,
        _HALFBODY_EXPRESSION_SCHEMA,
    }
)


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
    CharacterVoice,
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
        character_root, character_data_components = _character_data_contract(manifest)
        rig_component = _required_component(
            manifest,
            "fullbody_rig",
            FULLBODY_RIG_SCHEMA,
        )
        expression_component = _required_expression_component(manifest)
        _require_component_path(
            rig_component,
            _rooted_path(character_root, "rig/rig-manifest.json"),
        )
        _require_component_path(
            expression_component,
            _rooted_path(character_root, "expressions/state-catalog.json"),
        )
        loaded_components = (
            *character_data_components,
            rig_component,
            expression_component,
        )
        _verify_component_files(root, records, loaded_components)
        character_root_path = root.joinpath(*character_root.parts)
        character_data = _load_character_data(character_root_path, character_root.as_posix())
        rig = _load_rig(root, rig_component)
        expression_catalog = _load_expression_catalog(root, expression_component)
        _verify_component_files(root, records, loaded_components)

        canonical_name = str(character_data.identity.defaults["assistant_name"])
        if manifest.canonical_name != canonical_name or dict(manifest.display_names) != {
            language: character_data.personas[language].identity.display_name
            for language in LANGUAGES
        }:
            raise CharacterPackReadError(
                "invalid_component",
                "Manifest identity does not match the validated character data.",
                _rooted_path(character_root, "persona/profile.json"),
            )
        profile = (rig.body_profile_id, rig.body_profile_version)
        if profile != (rig_component.body_profile_id, rig_component.body_profile_version):
            raise CharacterPackReadError(
                "incompatible_body_profile",
                "The rig component binding does not match its validated content.",
                rig_component.path,
            )
        if profile != (
            expression_component.body_profile_id,
            expression_component.body_profile_version,
        ):
            raise CharacterPackReadError(
                "incompatible_body_profile",
                "The expression component binding does not match the character rig.",
                expression_component.path,
            )
        if expression_catalog.character_id != rig.character_id:
            raise CharacterPackReadError(
                "invalid_component",
                "The expression catalog and rig must identify the same character.",
                expression_component.path,
            )
        profile_id, profile_version = profile
        if profile_id is None or profile_version is None:
            raise CharacterPackReadError(
                "incompatible_body_profile",
                "The character rig requires a body-profile binding.",
                rig_component.path,
            )

        fullbody_canvas = CharacterCanvas(
            rig.full_body_canvas.width,
            rig.full_body_canvas.height,
            rig.full_body_canvas.mode,
        )
        halfbody_canvas = CharacterCanvas(
            rig.half_body_asset_canvas.width,
            rig.half_body_asset_canvas.height,
            rig.half_body_asset_canvas.mode,
        )

        # Assign only after every outer and child contract has passed. A rejected
        # package therefore cannot leak a partially initialized source.
        self._validation_result = result
        self._manifest = manifest
        self._root = root
        self._records = records
        self._canonical_name = canonical_name
        wake_word = str(character_data.identity.defaults["wake_word"])
        self._aliases = () if wake_word == canonical_name else (wake_word,)
        self._default_user_title = str(character_data.identity.defaults["user_title"])
        self._persona_prompts = {
            language: character_data.personas[language].system_prompt
            for language in LANGUAGES
        }
        self._dialogue = {
            language: character_data.dialogues[language]
            for language in LANGUAGES
        }
        self._appearance_defaults = character_data.appearance_defaults
        self._voice_profile = character_data.voice
        self._body_profile = CharacterBodyProfileReference(profile_id, profile_version)
        self._fullbody_canvas = fullbody_canvas
        self._halfbody_canvas = halfbody_canvas
        self._view_ids = tuple(canonical_view_id(yaw) for yaw in rig.view_ring.yaws)
        self._layer_order = rig.layer_z_order

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
    def voice(self) -> CharacterVoice:
        return self

    @property
    def voice_profile(self) -> VoiceProfile:
        return self._voice_profile

    @property
    def appearance_defaults(self) -> CharacterAppearanceDefaults:
        return self._appearance_defaults

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
        return self._canonical_name

    @property
    def aliases(self) -> tuple[str, ...]:
        return self._aliases

    def display_name(self, language: str) -> str:
        canonical_ui_language(language)
        return self._canonical_name

    def default_user_title(self, language: str) -> str:
        canonical_ui_language(language)
        return self._default_user_title

    def persona_prompt(self, language: str) -> str:
        return self._persona_prompts[canonical_ui_language(language)]

    def dialogue_line(
        self,
        language: str,
        key: str,
        *,
        variation_index: int = 0,
    ) -> str:
        dialogue = self._dialogue[canonical_ui_language(language)]
        lines = dialogue.phrasebook.get(key, ())
        if not lines:
            lines = dialogue.line_sets.get(key, ())
        if not lines and key in dialogue.templates:
            lines = (dialogue.templates[key],)
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
    if not matches:
        raise CharacterPackReadError(
            "missing_component",
            f"Exactly one required {kind} component is needed.",
        )
    if len(matches) > 1:
        raise CharacterPackReadError(
            "duplicate_component",
            f"Exactly one required {kind} component is needed.",
        )
    component = next(iter(matches))
    if not component.required:
        raise CharacterPackReadError(
            "missing_component",
            f"The {kind} component must be required.",
            component.path,
        )
    if component.schema != schema:
        raise CharacterPackReadError(
            "unsupported_component_schema",
            f"The {kind} component must use {schema}.",
            component.path,
        )
    return component


def _required_expression_component(
    manifest: CharacterPackManifest,
) -> CharacterPackComponent:
    candidates = tuple(
        component
        for component in manifest.components
        if component.kind == "expression_manifest"
    )
    unsupported = tuple(
        component
        for component in candidates
        if component.required and component.schema not in _KNOWN_EXPRESSION_SCHEMAS
    )
    if unsupported:
        component = unsupported[0]
        raise CharacterPackReadError(
            "unsupported_component_schema",
            "A required expression component uses an unsupported schema.",
            component.path,
        )
    matches = tuple(
        component
        for component in candidates
        if component.schema == EXPRESSION_STATE_SCHEMA
    )
    if not matches:
        raise CharacterPackReadError(
            "missing_component",
            "Exactly one required expression-state component is needed.",
        )
    if len(matches) > 1:
        raise CharacterPackReadError(
            "duplicate_component",
            "Exactly one required expression-state component is needed.",
        )
    component = next(iter(matches))
    if not component.required:
        raise CharacterPackReadError(
            "missing_component",
            "The expression-state component must be required.",
            component.path,
        )
    return component


def _character_data_contract(
    manifest: CharacterPackManifest,
) -> tuple[PurePosixPath, tuple[CharacterPackComponent, ...]]:
    persona = _required_schema_components(
        manifest,
        "persona",
        {IDENTITY_SCHEMA: 1, PERSONA_SCHEMA: len(LANGUAGES)},
    )
    dialogue = _required_schema_components(
        manifest,
        "dialogue",
        {DIALOGUE_SCHEMA: len(LANGUAGES), EVENTS_SCHEMA: 1},
    )
    voice = _required_schema_components(
        manifest,
        "voice_profile",
        {VOICE_SCHEMA: 1},
    )
    appearance = _required_schema_components(
        manifest,
        "appearance_defaults",
        {APPEARANCE_DEFAULTS_SCHEMA: 1},
    )
    identity_component = persona[IDENTITY_SCHEMA][0]
    character_root = _component_root(
        identity_component,
        PurePosixPath("persona/profile.json"),
    )
    _require_component_paths(
        persona[PERSONA_SCHEMA],
        {
            _rooted_path(character_root, f"persona/{language}.json")
            for language in LANGUAGES
        },
        "persona",
    )
    _require_component_paths(
        dialogue[DIALOGUE_SCHEMA],
        {
            _rooted_path(character_root, f"dialogue/{language}.json")
            for language in LANGUAGES
        },
        "dialogue",
    )
    _require_component_path(
        dialogue[EVENTS_SCHEMA][0],
        _rooted_path(character_root, "dialogue/events.json"),
    )
    _require_component_path(
        voice[VOICE_SCHEMA][0],
        _rooted_path(character_root, "voice/profile.json"),
    )
    _require_component_path(
        appearance[APPEARANCE_DEFAULTS_SCHEMA][0],
        _rooted_path(character_root, "appearance/defaults.json"),
    )
    return (
        character_root,
        (
            identity_component,
            *persona[PERSONA_SCHEMA],
            *dialogue[DIALOGUE_SCHEMA],
            dialogue[EVENTS_SCHEMA][0],
            voice[VOICE_SCHEMA][0],
            appearance[APPEARANCE_DEFAULTS_SCHEMA][0],
        ),
    )


def _required_schema_components(
    manifest: CharacterPackManifest,
    kind: str,
    expected: Mapping[str, int],
) -> dict[str, tuple[CharacterPackComponent, ...]]:
    candidates = tuple(
        component for component in manifest.components if component.kind == kind
    )
    for component in candidates:
        if component.schema not in expected:
            raise CharacterPackReadError(
                "unsupported_component_schema",
                f"A required {kind} component uses an unsupported schema.",
                component.path,
            )
    grouped: dict[str, tuple[CharacterPackComponent, ...]] = {}
    for schema, count in expected.items():
        matches = tuple(
            component for component in candidates if component.schema == schema
        )
        if len(matches) < count or any(not component.required for component in matches):
            raise CharacterPackReadError(
                "missing_component",
                f"The {kind} contract requires {count} required {schema} component(s).",
            )
        if len(matches) > count:
            raise CharacterPackReadError(
                "duplicate_component",
                f"The {kind} contract requires exactly {count} {schema} component(s).",
            )
        grouped[schema] = matches
    return grouped


def _component_root(
    component: CharacterPackComponent,
    suffix: PurePosixPath,
) -> PurePosixPath:
    path = _relative_path(component.path)
    if len(path.parts) < len(suffix.parts) or path.parts[-len(suffix.parts) :] != suffix.parts:
        raise CharacterPackReadError(
            "invalid_component",
            f"The component path must end with {suffix.as_posix()}.",
            component.path,
        )
    return PurePosixPath(*path.parts[: -len(suffix.parts)])


def _rooted_path(root: PurePosixPath, relative: str) -> str:
    return PurePosixPath(*root.parts, *PurePosixPath(relative).parts).as_posix()


def _require_component_path(
    component: CharacterPackComponent,
    expected: str,
) -> None:
    if component.path != expected:
        raise CharacterPackReadError(
            "invalid_component",
            f"The component path must be {expected}.",
            component.path,
        )


def _require_component_paths(
    components: tuple[CharacterPackComponent, ...],
    expected: set[str],
    label: str,
) -> None:
    actual = {component.path for component in components}
    if actual != expected:
        unexpected = sorted(actual - expected)
        path = unexpected[0] if unexpected else None
        raise CharacterPackReadError(
            "invalid_component",
            f"The {label} components must use the canonical locale paths.",
            path,
        )


def _verify_component_files(
    root: Path,
    records: Mapping[str, CharacterPackFile],
    components: tuple[CharacterPackComponent, ...],
) -> None:
    for component in components:
        _read_verified_file(root, records[component.path])


def _load_character_data(root: Path, relative_root: str) -> MohanCharacterData:
    try:
        return load_mohan_character_data(root)
    except (OSError, UnicodeError, ValueError) as error:
        raise CharacterPackReadError(
            "invalid_component",
            f"Character data validation failed: {type(error).__name__}.",
            relative_root,
        ) from None


def _load_rig(root: Path, component: CharacterPackComponent) -> CharacterRigManifest:
    path = root.joinpath(*PurePosixPath(component.path).parts)
    try:
        return load_rig_manifest(path)
    except (OSError, UnicodeError, ValueError) as error:
        raise CharacterPackReadError(
            "invalid_component",
            f"Character rig validation failed: {type(error).__name__}.",
            component.path,
        ) from None


def _load_expression_catalog(
    root: Path,
    component: CharacterPackComponent,
) -> ExpressionStateCatalog:
    path = root.joinpath(*PurePosixPath(component.path).parts)
    try:
        return load_expression_catalog(path)
    except (OSError, UnicodeError, ValueError) as error:
        raise CharacterPackReadError(
            "invalid_component",
            f"Expression catalog validation failed: {type(error).__name__}.",
            component.path,
        ) from None


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
    "APPEARANCE_DEFAULTS_SCHEMA",
    "DIALOGUE_SCHEMA",
    "EVENTS_SCHEMA",
    "EXPRESSION_STATE_SCHEMA",
    "FULLBODY_RIG_SCHEMA",
    "HALFBODY_RIG_SCHEMA",
    "IDENTITY_SCHEMA",
    "PERSONA_SCHEMA",
    "VOICE_SCHEMA",
    "CharacterPackReadError",
    "CharacterPackReader",
)
