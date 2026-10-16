"""Typed boundaries for character-owned data and assets."""

from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath
lazy from typing import Protocol, runtime_checkable

lazy from domain.character_pack.character_data_models import (
    CharacterAppearanceDefaults,
    CharacterRigManifest,
    DialogueLocale,
    ExpressionStateCatalog,
    MohanCharacterData,
    VoiceProfile,
)
lazy from domain.character_runtime_bindings import CharacterRuntimeBindings


@dataclass(frozen=True, slots=True)
class CharacterCanvas:
    """One immutable character-rendering canvas contract."""

    width: int
    height: int
    mode: str

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("Character canvas dimensions must be positive.")
        if not self.mode:
            raise ValueError("Character canvas mode must be explicit.")


@dataclass(frozen=True, slots=True)
class CharacterBodyProfileReference:
    """Versioned body identity shared by a character's visual components."""

    profile_id: str
    version: int

    def __post_init__(self) -> None:
        if not self.profile_id or self.version < 1:
            raise ValueError("Character body profiles require an id and positive version.")


@runtime_checkable
class CharacterAssets(Protocol):
    """Resolve character-owned paths below one stable asset root."""

    @property
    def asset_root(self) -> Path: ...

    @property
    def official_pack_roots(self) -> tuple[Path, ...]: ...

    def resolve_path(self, relative_path: str) -> Path: ...

    def resolve_optional_path(self, relative_path: str) -> Path | None: ...


@runtime_checkable
class CharacterPersona(Protocol):
    """Read character identity, address, persona, and event dialogue."""

    @property
    def canonical_name(self) -> str: ...

    @property
    def aliases(self) -> tuple[str, ...]: ...

    @property
    def profile_defaults(self) -> Mapping[str, str]: ...

    def display_name(self, language: str) -> str: ...

    def default_user_title(self, language: str) -> str: ...

    def persona_prompt(self, language: str) -> str: ...

    def dialogue_locale(self, language: str) -> DialogueLocale: ...

    def dialogue_line(
        self,
        language: str,
        key: str,
        *,
        variation_index: int = 0,
    ) -> str: ...

    def personalize_text(
        self,
        text: str,
        *,
        assistant_name: str,
        user_title: str,
        organization_name: str,
    ) -> str: ...


@runtime_checkable
class CharacterAppearanceContract(Protocol):
    """Read the body, view ring, canvases, and layer order of a character."""

    @property
    def appearance_defaults(self) -> CharacterAppearanceDefaults: ...

    @property
    def body_profile(self) -> CharacterBodyProfileReference: ...

    @property
    def view_ids(self) -> tuple[str, ...]: ...

    @property
    def fullbody_canvas(self) -> CharacterCanvas: ...

    @property
    def halfbody_canvas(self) -> CharacterCanvas: ...

    @property
    def layer_order(self) -> tuple[str, ...]: ...

    @property
    def rig_manifest(self) -> CharacterRigManifest: ...

    @property
    def runtime_bindings(self) -> CharacterRuntimeBindings: ...


@runtime_checkable
class CharacterVoice(Protocol):
    """Read the selected character's validated voice preferences."""

    @property
    def voice_profile(self) -> VoiceProfile: ...


@runtime_checkable
class CharacterSource(Protocol):
    """Composition boundary for one complete character data source."""

    @property
    def character_data(self) -> MohanCharacterData: ...

    @property
    def character_data_root(self) -> Path: ...

    @property
    def expression_catalog(self) -> ExpressionStateCatalog: ...

    @property
    def assets(self) -> CharacterAssets: ...

    @property
    def persona(self) -> CharacterPersona: ...

    @property
    def appearance(self) -> CharacterAppearanceContract: ...

    @property
    def voice(self) -> CharacterVoice: ...


class ProfileSettingsPort(Protocol):
    """Saved product settings consumed by character-neutral presentation code."""

    def setting(self, key: str, default: object = None) -> object: ...


@dataclass(frozen=True, slots=True)
class CharacterEngineProfile:
    """One composition-root snapshot of character-owned engine inputs."""

    assets: CharacterAssets
    runtime_bindings: CharacterRuntimeBindings
    rig_manifest: CharacterRigManifest
    pose_atlas_generation: int
    pose_atlas_relative_root: str
    pose_atlas_layered_relative_root: str

    def __post_init__(self) -> None:
        if self.pose_atlas_generation < 1:
            raise ValueError("PoseAtlas generations must be positive.")
        for value in (
            self.pose_atlas_relative_root,
            self.pose_atlas_layered_relative_root,
        ):
            path = PurePosixPath(value)
            if (
                not value
                or "\\" in value
                or path.is_absolute()
                or any(part in {"", ".", ".."} for part in path.parts)
            ):
                raise ValueError("PoseAtlas roots must use canonical relative paths.")


_active_character_source: CharacterSource | None = None
_active_character_engine_profile: CharacterEngineProfile | None = None


def activate_character_source(source: CharacterSource | None) -> None:
    """Select the validated character source used by data-backed domain defaults."""

    global _active_character_source
    if source is not None and not isinstance(source, CharacterSource):
        raise TypeError("The active character source must satisfy CharacterSource.")
    _active_character_source = source


def activate_character_engine_profile(profile: CharacterEngineProfile | None) -> None:
    """Install the character runtime snapshot built by the product shell."""

    global _active_character_engine_profile
    if profile is not None and not isinstance(profile, CharacterEngineProfile):
        raise TypeError("The active character engine profile must use the typed contract.")
    _active_character_engine_profile = profile


def character_appearance_defaults(
    source: CharacterSource | None = None,
) -> CharacterAppearanceDefaults:
    """Read appearance defaults from an injected or active character source."""

    return active_character_source(source).appearance.appearance_defaults


def character_voice_profile(source: CharacterSource | None = None) -> VoiceProfile:
    """Read voice preferences from an injected or active character source."""

    return active_character_source(source).voice.voice_profile


def active_character_data(
    source: CharacterSource | None = None,
) -> MohanCharacterData:
    """Read the selected source's validated character-owned data catalog."""

    return active_character_source(source).character_data


def active_expression_catalog(
    source: CharacterSource | None = None,
) -> ExpressionStateCatalog:
    """Read the selected source's validated expression-state catalog."""

    return active_character_source(source).expression_catalog


def active_character_data_path(
    relative_path: str,
    source: CharacterSource | None = None,
) -> Path:
    """Resolve one validated data file below the selected character root."""

    relative = PurePosixPath(relative_path)
    if (
        not relative_path
        or "\\" in relative_path
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError("Character data paths must use canonical relative syntax.")
    root = active_character_source(source).character_data_root
    candidate = root.joinpath(*relative.parts).resolve(strict=True)
    if not candidate.is_relative_to(root.resolve(strict=True)):
        raise ValueError("Character data paths must remain below the character root.")
    return candidate


def profile_setting(settings: ProfileSettingsPort, key: str) -> str:
    """Read one saved profile value with the active character's injected default."""

    default = active_character_source().persona.profile_defaults[key]
    return str(settings.setting(key, default)).strip()


def personalize_text(settings: ProfileSettingsPort, text: str) -> str:
    """Apply saved identity values through the active character adapter."""

    persona = active_character_source().persona
    return persona.personalize_text(
        text,
        assistant_name=profile_setting(settings, "assistant_name"),
        user_title=profile_setting(settings, "user_title"),
        organization_name=profile_setting(settings, "organization_name"),
    )


def active_character_source(source: CharacterSource | None = None) -> CharacterSource:
    """Return the selected source or fail before character-specific work starts."""

    selected = source if source is not None else _active_character_source
    if selected is None:
        raise RuntimeError("The composition root must activate a character source first.")
    return selected


def active_character_engine_profile(
    profile: CharacterEngineProfile | None = None,
) -> CharacterEngineProfile:
    """Return injected engine inputs or fail before character work starts."""

    selected = profile if profile is not None else _active_character_engine_profile
    if selected is None:
        raise RuntimeError("The composition root must activate a character engine profile first.")
    return selected


__all__ = (
    "CharacterAppearanceContract",
    "CharacterAppearanceDefaults",
    "CharacterAssets",
    "CharacterBodyProfileReference",
    "CharacterCanvas",
    "CharacterEngineProfile",
    "CharacterPersona",
    "CharacterSource",
    "CharacterVoice",
    "ProfileSettingsPort",
    "activate_character_engine_profile",
    "activate_character_source",
    "active_character_data",
    "active_character_data_path",
    "active_character_engine_profile",
    "active_character_source",
    "active_expression_catalog",
    "character_appearance_defaults",
    "character_voice_profile",
    "personalize_text",
    "profile_setting",
)
