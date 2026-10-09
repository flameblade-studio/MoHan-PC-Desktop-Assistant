"""Typed boundaries for character-owned data and assets."""

from __future__ import annotations

lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Protocol, runtime_checkable

lazy from domain.character_pack.character_data_models import (
    CharacterAppearanceDefaults,
    CharacterRigManifest,
    DialogueLocale,
    VoiceProfile,
)


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

    def resolve_path(self, relative_path: str) -> Path: ...

    def resolve_optional_path(self, relative_path: str) -> Path | None: ...


@runtime_checkable
class CharacterPersona(Protocol):
    """Read character identity, address, persona, and event dialogue."""

    @property
    def canonical_name(self) -> str: ...

    @property
    def aliases(self) -> tuple[str, ...]: ...

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


@runtime_checkable
class CharacterAppearanceContract(Protocol):
    """Read the body, view ring, canvases, and layer order of a character."""

    @property
    def appearance_defaults(self) -> CharacterAppearanceDefaults: ...

    @property
    def rig_manifest(self) -> CharacterRigManifest: ...

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


@runtime_checkable
class CharacterVoice(Protocol):
    """Read the selected character's validated voice preferences."""

    @property
    def voice_profile(self) -> VoiceProfile: ...


@runtime_checkable
class CharacterSource(Protocol):
    """Composition boundary for one complete character data source."""

    @property
    def assets(self) -> CharacterAssets: ...

    @property
    def persona(self) -> CharacterPersona: ...

    @property
    def appearance(self) -> CharacterAppearanceContract: ...

    @property
    def voice(self) -> CharacterVoice: ...


_active_character_source: CharacterSource | None = None


def activate_character_source(source: CharacterSource | None) -> None:
    """Select the validated character source used by data-backed domain defaults."""

    global _active_character_source
    if source is not None and not isinstance(source, CharacterSource):
        raise TypeError("The active character source must satisfy CharacterSource.")
    _active_character_source = source


def character_appearance_defaults(
    source: CharacterSource | None = None,
) -> CharacterAppearanceDefaults:
    """Read appearance defaults from an injected or active character source."""

    return active_character_source(source).appearance.appearance_defaults


def character_voice_profile(source: CharacterSource | None = None) -> VoiceProfile:
    """Read voice preferences from an injected or active character source."""

    return active_character_source(source).voice.voice_profile


def active_character_source(source: CharacterSource | None = None) -> CharacterSource:
    """Return the selected source or fail before character-specific work starts."""

    selected = source if source is not None else _active_character_source
    if selected is None:
        raise RuntimeError("The composition root must activate a character source first.")
    return selected


__all__ = (
    "CharacterAppearanceContract",
    "CharacterAppearanceDefaults",
    "CharacterAssets",
    "CharacterBodyProfileReference",
    "CharacterCanvas",
    "CharacterPersona",
    "CharacterSource",
    "CharacterVoice",
    "activate_character_source",
    "active_character_source",
    "character_appearance_defaults",
    "character_voice_profile",
)
