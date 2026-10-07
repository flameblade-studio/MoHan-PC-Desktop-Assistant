"""Typed boundaries for character-owned data and assets."""

from __future__ import annotations

lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Protocol, runtime_checkable


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
class CharacterSource(Protocol):
    """Composition boundary for one complete character data source."""

    @property
    def assets(self) -> CharacterAssets: ...

    @property
    def persona(self) -> CharacterPersona: ...

    @property
    def appearance(self) -> CharacterAppearanceContract: ...


__all__ = (
    "CharacterAppearanceContract",
    "CharacterAssets",
    "CharacterBodyProfileReference",
    "CharacterCanvas",
    "CharacterPersona",
    "CharacterSource",
)
