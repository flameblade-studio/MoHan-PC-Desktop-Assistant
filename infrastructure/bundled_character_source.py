"""Strict source adapter for character data bundled with the product shell."""

from __future__ import annotations

lazy from collections.abc import Mapping
lazy from pathlib import Path, PurePosixPath

lazy from domain.character_expression_data import load_expression_catalog
lazy from domain.character_pack.character_data import (
    canonical_character_locale,
    load_mohan_character_data,
)
lazy from domain.character_pack.character_data_models import (
    CharacterRigManifest,
    ExpressionStateCatalog,
    MohanCharacterData,
    VoiceProfile,
)
lazy from domain.character_pose import canonical_view_id
lazy from domain.character_rig_data import load_rig_manifest
lazy from domain.character_runtime_bindings import (
    CharacterRuntimeBindings,
    load_character_runtime_bindings,
)
lazy from domain.character_source import (
    CharacterAppearanceContract,
    CharacterAppearanceDefaults,
    CharacterAssets,
    CharacterBodyProfileReference,
    CharacterCanvas,
    CharacterPersona,
    CharacterVoice,
)


class BundledCharacterSource(
    CharacterAssets,
    CharacterPersona,
    CharacterAppearanceContract,
    CharacterVoice,
):
    """Load the one character intentionally bundled with the MoHan product."""

    def __init__(self, asset_root: Path, character_id: str) -> None:
        self._asset_root = Path(asset_root).resolve(strict=True)
        self._character_id = _character_id(character_id)
        if self._character_id != "mohan":
            raise ValueError("The product bundle contains only its default character.")
        character_root = self._asset_root / "assets" / "characters" / self._character_id
        self._character_root = character_root.resolve(strict=True)
        if not self._character_root.is_relative_to(self._asset_root):
            raise ValueError("Bundled character data must remain below the asset root.")
        self._data = load_mohan_character_data(self._character_root)
        self._rig = load_rig_manifest(self._character_root / "rig" / "rig-manifest.json")
        self._runtime_bindings = load_character_runtime_bindings(
            self._character_root / "rig" / "runtime-bindings.json"
        )
        self._expressions = load_expression_catalog(
            self._character_root / "expressions" / "state-catalog.json"
        )
        if self._expressions.character_id != self._rig.character_id:
            raise ValueError("Bundled character rig and expressions must identify the same character.")

    @property
    def character_id(self) -> str:
        return self._character_id

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
        return self._data.voice

    @property
    def character_data(self) -> MohanCharacterData:
        return self._data

    @property
    def character_data_root(self) -> Path:
        return self._character_root

    @property
    def expression_catalog(self) -> ExpressionStateCatalog:
        return self._expressions

    @property
    def appearance_defaults(self) -> CharacterAppearanceDefaults:
        return self._data.appearance_defaults

    @property
    def asset_root(self) -> Path:
        return self._asset_root

    def resolve_path(self, relative_path: str) -> Path:
        normalized = _character_relative_path(relative_path)
        candidate = self._asset_root.joinpath(*normalized.parts)
        if not candidate.resolve(strict=True).is_relative_to(self._asset_root):
            raise ValueError("Character asset paths must remain below the asset root.")
        return candidate

    @property
    def canonical_name(self) -> str:
        return str(self._data.identity.defaults["assistant_name"])

    @property
    def aliases(self) -> tuple[str, ...]:
        wake_word = str(self._data.identity.defaults["wake_word"])
        return () if wake_word == self.canonical_name else (wake_word,)

    @property
    def profile_defaults(self) -> Mapping[str, str]:
        return self._data.identity.defaults

    def display_name(self, language: str) -> str:
        locale = canonical_character_locale(language)
        return self._data.personas[locale].identity.display_name

    def default_user_title(self, language: str) -> str:
        locale = canonical_character_locale(language)
        return self._data.personas[locale].identity.default_user_title

    def persona_prompt(self, language: str) -> str:
        locale = canonical_character_locale(language)
        return self._data.personas[locale].system_prompt

    def dialogue_line(
        self,
        language: str,
        key: str,
        *,
        variation_index: int = 0,
    ) -> str:
        locale = canonical_character_locale(language)
        dialogue = self._data.dialogues[locale]
        lines = dialogue.phrasebook.get(key, ())
        if not lines:
            lines = dialogue.line_sets.get(key, ())
        if not lines and key in dialogue.templates:
            lines = (dialogue.templates[key],)
        return lines[variation_index % len(lines)] if lines else ""

    def personalize_text(
        self,
        text: str,
        *,
        assistant_name: str,
        user_title: str,
        organization_name: str,
    ) -> str:
        identity = self._data.identity
        replacements = {
            **dict.fromkeys(identity.assistant_tokens, assistant_name),
            **dict.fromkeys(identity.user_title_tokens, user_title),
        }
        if organization_name:
            replacements[identity.organization_token] = organization_name
        result = text
        for source, target in replacements.items():
            if target:
                result = result.replace(source, target)
        return result

    @property
    def body_profile(self) -> CharacterBodyProfileReference:
        return CharacterBodyProfileReference(
            profile_id=self._rig.body_profile_id,
            version=self._rig.body_profile_version,
        )

    @property
    def view_ids(self) -> tuple[str, ...]:
        return tuple(canonical_view_id(yaw) for yaw in self._rig.view_ring.yaws)

    @property
    def fullbody_canvas(self) -> CharacterCanvas:
        canvas = self._rig.full_body_canvas
        return CharacterCanvas(canvas.width, canvas.height, canvas.mode)

    @property
    def halfbody_canvas(self) -> CharacterCanvas:
        canvas = self._rig.half_body_asset_canvas
        return CharacterCanvas(canvas.width, canvas.height, canvas.mode)

    @property
    def layer_order(self) -> tuple[str, ...]:
        return self._rig.layer_z_order

    @property
    def rig_manifest(self) -> CharacterRigManifest:
        return self._rig

    @property
    def runtime_bindings(self) -> CharacterRuntimeBindings:
        return self._runtime_bindings


class LegacyMohanCharacterSource(BundledCharacterSource):
    """Preserve the established MoHan source API while using strict data files."""

    def __init__(self, asset_root: Path) -> None:
        super().__init__(asset_root, "mohan")

    def display_name(self, language: str) -> str:
        canonical_character_locale(language)
        return self.canonical_name

    def default_user_title(self, language: str) -> str:
        canonical_character_locale(language)
        return str(self._data.identity.defaults["user_title"])


def _character_id(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("A bundled character identifier is required.")
    if not value.isascii() or any(
        not (character.islower() or character.isdigit() or character == "-")
        for character in value
    ):
        raise ValueError("Bundled character identifiers use lowercase ASCII slugs.")
    return value


def _character_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Character asset paths must use relative POSIX syntax.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("Character asset paths must use canonical relative syntax.")
    return path


__all__ = ("BundledCharacterSource", "LegacyMohanCharacterSource")
