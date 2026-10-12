"""Select character-owned official frames through the existing appearance resolver."""
from __future__ import annotations

lazy from pathlib import Path
lazy from collections.abc import Mapping
lazy from domain.character_source import CharacterSource, character_appearance_defaults
lazy from domain.constants import POSE_ATLAS_RELATIVE_ROOT
lazy from domain.body_pack import BodyPackMismatchError, BodyPackSource
lazy from domain.outfit_pack import list_installed_ensembles, resolve_active_selection
lazy from domain.outfit_pack_store import OfficialPackRoots, official_pack_roots


class CharacterDefaultLook:
    """Share one selection decision between overlays and both frame renderers."""

    def __init__(self, source: CharacterSource, store: Path, official_roots: OfficialPackRoots) -> None:
        if resolved_body_pack_for_source(source) is not None:
            raise BodyPackMismatchError(
                "body_pack_renderer_required", "Declared body packs require the body-pack renderer",
            )
        self._source = source
        self._store = store
        self._official_roots = official_roots
        self._bindings = source.appearance.runtime_bindings.asset_paths
        self._selection_token: tuple | None = None
        self._native = False

    def native_frames(self) -> bool:
        """Re-resolve when saved selections or installed archives change."""
        defaults = character_appearance_defaults(self._source)
        roots = official_pack_roots(self._official_roots)
        archives = tuple(root / f"{defaults.outfit_pack_id}.mohan-outfit" for root in roots)
        paths = (self._store / "active.json", self._store / "packages", *roots, *archives)
        token = tuple(self._file_token(path) for path in paths)
        if token != self._selection_token:
            native = self._resolve_native_frames()
            self._native = native
            self._selection_token = token
        return self._native

    @staticmethod
    def _file_token(path: Path) -> tuple[int, int] | None:
        try:
            stat = path.stat()
        except FileNotFoundError:
            return None
        return stat.st_mtime_ns, stat.st_size

    def _resolve_native_frames(self) -> bool:
        if "default_look_fullbody" not in self._bindings:
            return (
                self._bindings.get("fullbody_complete_root", POSE_ATLAS_RELATIVE_ROOT)
                != POSE_ATLAS_RELATIVE_ROOT
            )
        defaults = character_appearance_defaults(self._source)
        ensemble = next((item for item in list_installed_ensembles(
            self._store, official_pack_root=self._official_roots,
        ) if (item.pack_id, item.ensemble_id) == (
            defaults.outfit_pack_id, defaults.outfit_ensemble_id,
        )), None)
        if ensemble is None:
            return False
        for item in ensemble.selections:
            if item.category == "makeup":
                continue
            selected = resolve_active_selection(
                self._store, item.category, official_pack_root=self._official_roots,
            )
            if item.item_id is None:
                if selected.status != "builtin":
                    return False
                continue
            expected = (ensemble.pack_id, item.item_id, item.variant_id)
            if (selected.effective_pack_id, selected.effective_item_id,
                    selected.effective_variant_id) != expected:
                return False
        return True

    def fullbody_root(self) -> Path | None:
        if "default_look_fullbody" in self._bindings:
            relative = self._bindings["default_look_fullbody"] if self.native_frames() else None
        else:
            relative = self._bindings.get("fullbody_complete_root", POSE_ATLAS_RELATIVE_ROOT)
            if relative == POSE_ATLAS_RELATIVE_ROOT:
                relative = None
        return self._source.assets.resolve_path(relative) if relative is not None else None

    def halfbody_root(self) -> tuple[Path | None, bool]:
        if "default_look_halfbody" in self._bindings:
            native = self.native_frames()
            relative = (self._bindings["default_look_halfbody"] if native
                        else "assets/expressions/complete-expressions")
        else:
            relative = self._bindings.get("halfbody_complete")
            native = relative is not None and relative != "assets/expressions/complete-expressions"
        return (self._source.assets.resolve_path(relative) if relative is not None else None, native)


def character_frame_paths(character_source: CharacterSource) -> tuple[Mapping[str, str], bool]:
    resolved_body_pack_for_source(character_source)
    runtime_bindings = getattr(getattr(character_source, "appearance", None), "runtime_bindings", None)
    bindings = getattr(runtime_bindings, "asset_paths", {})
    native_frames = (
        bindings.get("fullbody_complete_root", POSE_ATLAS_RELATIVE_ROOT) != POSE_ATLAS_RELATIVE_ROOT
        or bindings.get("halfbody_complete", "assets/expressions/complete-expressions") != "assets/expressions/complete-expressions"
    )
    return bindings, native_frames


def complete_halfbody_path(character_source: CharacterSource, bindings: Mapping[str, str]) -> Path | None:
    _require_legacy_frame_source(character_source)
    return (character_source.assets.resolve_path(bindings["halfbody_complete"])
            if "halfbody_complete" in bindings else None)


def complete_fullbody_path(character_source: CharacterSource, bindings: Mapping[str, str]) -> Path | None:
    _require_legacy_frame_source(character_source)
    relative = bindings.get("fullbody_complete_root", POSE_ATLAS_RELATIVE_ROOT)
    return character_source.assets.resolve_path(relative) if relative != POSE_ATLAS_RELATIVE_ROOT else None


def resolved_body_pack_for_source(source: CharacterSource) -> BodyPackSource | None:
    """Require resolution of a declared dependency before choosing a renderer."""
    body = getattr(source.appearance, "resolved_body_pack", None) if hasattr(source, "appearance") else None
    reference = getattr(getattr(source, "manifest", None), "body_pack", None)
    if reference is not None and body is None:
        raise BodyPackMismatchError("body_pack_missing", "Resolve the declared body pack before rendering")
    return body


def _require_legacy_frame_source(source: CharacterSource) -> None:
    if resolved_body_pack_for_source(source) is not None:
        raise BodyPackMismatchError(
            "body_pack_renderer_required", "Use the declared body pack to render character frames",
        )
