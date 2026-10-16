"""Strict source adapter for character data bundled with the product shell."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import logging
lazy from builtins import sentinel
lazy from collections.abc import Mapping
lazy from collections.abc import Iterable
lazy from pathlib import Path, PurePosixPath
lazy from types import MappingProxyType, SimpleNamespace
lazy from typing import cast

lazy from domain.body_pack import BodyPackMismatchError, parse_body_pack_reference
lazy from domain.character_layer_plan import (
    CharacterLayerAsset,
    CharacterLayerMask,
    parse_character_layer_views,
)
lazy from domain.character_expression_data_loader import load_expression_catalog
lazy from domain.character_pack.character_data import load_mohan_character_data
lazy from domain.character_pack.character_data_models import canonical_character_locale
lazy from domain.character_pack.character_data_models import (
    CharacterRigManifest,
    DialogueLocale,
    ExpressionStateCatalog,
    MohanCharacterData,
    VoiceProfile,
)
lazy from domain.character_pose import canonical_view_id
lazy from domain.character_rig_data_loader import load_rig_manifest
lazy from domain.character_runtime_bindings import (
    CharacterRuntimeBindings,
    load_character_runtime_bindings,
)
lazy from domain.character_source import (
    CharacterAppearanceContract,
    CharacterAssets,
    CharacterBodyProfileReference,
    CharacterCanvas,
    CharacterPersona,
    CharacterVoice,
)
lazy from domain.character_pack.character_data_models import CharacterAppearanceDefaults
lazy from infrastructure.body_pack_reader import BodyPackReader, resolve_character_body_binding
lazy from infrastructure.installed_body_packs import installed_body_pack_root


_UNRESOLVED_BODY_PACK = sentinel("_UNRESOLVED_BODY_PACK")
LOGGER = logging.getLogger(__name__)


class BundledCharacterSource(
    CharacterAssets,
    CharacterPersona,
    CharacterAppearanceContract,
    CharacterVoice,
):
    """Load the one character intentionally bundled with the MoHan product."""

    def __init__(
        self,
        asset_root: Path,
        character_id: str,
        *,
        body_pack_roots: Iterable[Path] | None = None,
        load_body_layers: bool = True,
    ) -> None:
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
        self._body_pack_roots = tuple(
            Path(root) for root in (
                body_pack_roots
                if body_pack_roots is not None
                else (installed_body_pack_root(),)
            )
        )
        self._body_pack_reference = None
        self._character_layer_views = MappingProxyType({})
        self._resolved_body_pack: BodyPackReader | object | None = _UNRESOLVED_BODY_PACK
        self._body_pack_resolution_error: BodyPackMismatchError | None = None
        if load_body_layers:
            self._load_character_body_manifest()
        else:
            self._resolved_body_pack = None

    def _load_character_body_manifest(self) -> None:
        """Load the bundled body declaration without resolving its download yet."""

        manifest_path = self._character_root / "body" / "manifest.json"
        if not manifest_path.is_file():
            self._resolved_body_pack = None
            return
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            self._body_pack_reference = parse_body_pack_reference(raw["body_pack"])
            self._character_layer_views = parse_character_layer_views(raw["layer_views"])
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Bundled character body manifest is invalid: {manifest_path}: {error}") from None

    def _character_body_path(self, relative_path: str) -> Path:
        normalized = _character_relative_path(relative_path)
        candidate = (self._asset_root / Path(*normalized.parts)).resolve(strict=True)
        if not candidate.is_relative_to(self._character_root):
            raise BodyPackMismatchError(
                "unsafe_path", "Bundled character layer paths must remain below the character root.", relative_path,
            )
        return candidate

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
    def rig_manifest(self) -> CharacterRigManifest:
        """Expose the rig that was validated while this source was built."""

        return self._rig

    @property
    def appearance_defaults(self) -> CharacterAppearanceDefaults:
        return self._data.appearance_defaults

    @property
    def asset_root(self) -> Path:
        return self._asset_root

    @property
    def official_pack_roots(self) -> tuple[Path, ...]:
        return (self._asset_root / "assets" / "official-packs",)

    @property
    def manifest(self) -> object:
        """Expose the body dependency in the same shape as CharacterPackReader."""

        return SimpleNamespace(body_pack=self._body_pack_reference)

    @property
    def resolved_body_pack(self) -> BodyPackReader | None:
        """Resolve MoHan's optional body pack without breaking the legacy route."""

        if self._body_pack_reference is None:
            return None
        if self._resolved_body_pack is _UNRESOLVED_BODY_PACK:
            try:
                binding = resolve_character_body_binding(
                    self._body_pack_reference,
                    self._rig,
                    self._body_pack_roots,
                    self._character_layer_views,
                )
            except BodyPackMismatchError as error:
                self._body_pack_resolution_error = error
                self._resolved_body_pack = None
                LOGGER.warning(
                    "mohan_body_pack_fallback code=%s path=%s message=%s",
                    error.code,
                    error.path or self._body_pack_reference.id,
                    error,
                )
            else:
                self._resolved_body_pack = binding.resolved_body_pack
        return cast(BodyPackReader | None, self._resolved_body_pack)

    @property
    def body_pack_fallback_active(self) -> bool:
        """Return whether MoHan is intentionally using the established look."""

        return (
            self._body_pack_reference is not None
            and self._body_pack_resolution_error is not None
            and self._resolved_body_pack is None
        )

    @property
    def body_pack_download_required(self) -> bool:
        """Expose a presentation-safe download hint without exposing raw paths."""

        return self.body_pack_fallback_active

    @property
    def body_pack_resolution_error(self) -> BodyPackMismatchError | None:
        """Expose the retained validation diagnostic to composition and evidence."""

        return self._body_pack_resolution_error

    @property
    def character_layer_views(self) -> Mapping[str, object]:
        """Return the manifest-bound scattered layer plans."""

        return self._character_layer_views

    def load_character_layer(self, record: CharacterLayerAsset | CharacterLayerMask) -> bytes:
        """Read a scattered layer and recheck its manifest-bound SHA-256."""

        try:
            path = self._character_body_path(record.path)
        except FileNotFoundError:
            raise BodyPackMismatchError("missing_file", "A bundled character layer is missing.", record.path) from None
        try:
            payload = path.read_bytes()
        except OSError as error:
            raise BodyPackMismatchError("read_error", str(error), record.path) from None
        digest = hashlib.sha256(payload).hexdigest()
        if digest != record.sha256:
            raise BodyPackMismatchError("file_hash_mismatch", f"Character layer changed: {record.path}", record.path)
        return payload

    def resolve_path(self, relative_path: str) -> Path:
        normalized = _character_relative_path(relative_path)
        candidate = self._asset_root.joinpath(*normalized.parts)
        if not candidate.resolve(strict=True).is_relative_to(self._asset_root):
            raise ValueError("Character asset paths must remain below the asset root.")
        return candidate

    def resolve_optional_path(self, relative_path: str) -> Path | None:
        normalized = _character_relative_path(relative_path)
        candidate = self._asset_root.joinpath(*normalized.parts)
        if not candidate.exists():
            return None
        return self.resolve_path(relative_path)

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

    def dialogue_locale(self, language: str) -> DialogueLocale:
        locale = canonical_character_locale(language)
        return self._data.dialogues[locale]

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
    def runtime_bindings(self) -> CharacterRuntimeBindings:
        return self._runtime_bindings


class LegacyMohanCharacterSource(BundledCharacterSource):
    """Preserve the established MoHan source API while using strict data files."""

    def __init__(
        self,
        asset_root: Path,
        *,
        body_pack_roots: Iterable[Path] | None = None,
        load_body_layers: bool = True,
    ) -> None:
        super().__init__(
            asset_root,
            "mohan",
            body_pack_roots=body_pack_roots,
            load_body_layers=load_body_layers,
        )

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
