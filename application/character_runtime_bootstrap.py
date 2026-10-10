"""Activate the product-selected character before character-aware imports resolve."""

from __future__ import annotations

lazy import logging
lazy import os
lazy import sys
lazy from collections.abc import Callable
lazy from dataclasses import replace
lazy from functools import partial
lazy from pathlib import Path

lazy from domain.character_pack.models import ValidationLimits
lazy from domain.character_pack.validation import DEFAULT_LIMITS
lazy from domain.character_source import (
    CharacterEngineProfile,
    CharacterSource,
    active_character_engine_profile,
    active_character_source,
    activate_character_engine_profile,
    activate_character_source,
)
lazy from domain.constants import (
    POSE_ATLAS_GENERATION,
    POSE_ATLAS_LAYERED_RELATIVE_ROOT,
    POSE_ATLAS_RELATIVE_ROOT,
)
lazy from infrastructure.bundled_character_source import LegacyMohanCharacterSource
lazy from infrastructure.installed_character_packs import (
    DEVELOPMENT_CHARACTER_PACK_ARCHIVE_ENV,
    CharacterPackInstallError,
    load_development_character_pack_archive,
    load_installed_character_pack,
)

ACTIVE_CHARACTER_ENV = "MOHAN_ACTIVE_CHARACTER"
DEFAULT_CHARACTER_ID = "mohan"
SUPPORTED_CHARACTER_IDS = frozenset({DEFAULT_CHARACTER_ID})
_CHARACTER_SELECTION_LOGGER = logging.getLogger("mohan.character_selection")

_CharacterLoader = Callable[..., CharacterSource]
_OFFICIAL_PACK_CEILING_BYTES = 768 * 1024 * 1024


def _official_character_pack_limits() -> ValidationLimits:
    """Match the 768 MiB ceiling official packs declare in pack-source.json."""

    return replace(
        DEFAULT_LIMITS,
        max_archive_bytes=_OFFICIAL_PACK_CEILING_BYTES,
        max_total_bytes=_OFFICIAL_PACK_CEILING_BYTES,
    )


def _product_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def _engine_profile(source: CharacterSource) -> CharacterEngineProfile:
    return CharacterEngineProfile(
        assets=source.assets,
        runtime_bindings=source.appearance.runtime_bindings,
        rig_manifest=source.appearance.rig_manifest,
        pose_atlas_generation=POSE_ATLAS_GENERATION,
        pose_atlas_relative_root=POSE_ATLAS_RELATIVE_ROOT,
        pose_atlas_layered_relative_root=POSE_ATLAS_LAYERED_RELATIVE_ROOT,
    )


def _activate(source: CharacterSource) -> None:
    activate_character_source(source)
    activate_character_engine_profile(_engine_profile(source))


def activate_product_character_runtime(
    repo_root: Path | None = None,
    *,
    character_id: str | None = None,
    development_archive_loader: _CharacterLoader | None = None,
    installed_loader: _CharacterLoader | None = None,
) -> CharacterSource:
    """Select and activate the configured character exactly once at an entry point."""

    configured_entrypoint = character_id is None
    selected = str(
        character_id
        if character_id is not None
        else os.environ.get(ACTIVE_CHARACTER_ENV, DEFAULT_CHARACTER_ID)
    ).strip()
    if configured_entrypoint:
        try:
            current = active_character_source()
        except RuntimeError:
            pass
        else:
            if current.character_id != selected:
                raise RuntimeError(
                    "The process already activated a different character source: "
                    f"{current.character_id!r}; requested {selected!r}."
                )
            try:
                active_character_engine_profile()
            except RuntimeError:
                activate_character_engine_profile(_engine_profile(current))
            return current
    root = _product_root() if repo_root is None else Path(repo_root)
    bundled_source: CharacterSource = LegacyMohanCharacterSource(root)
    if selected == DEFAULT_CHARACTER_ID:
        _activate(bundled_source)
        return bundled_source

    limits = _official_character_pack_limits()
    load_development = (
        partial(load_development_character_pack_archive, limits=limits)
        if development_archive_loader is None
        else development_archive_loader
    )
    load_installed = (
        partial(load_installed_character_pack, limits=limits)
        if installed_loader is None
        else installed_loader
    )
    try:
        development_archive = os.environ.get(
            DEVELOPMENT_CHARACTER_PACK_ARCHIVE_ENV,
            "",
        ).strip()
        source: CharacterSource = (
            load_development(
                development_archive,
                expected_character_id=selected,
            )
            if development_archive
            else load_installed(selected)
        )
    except (CharacterPackInstallError, OSError, ValueError) as error:
        _activate(bundled_source)
        message = (
            f"Active character {selected!r} was rejected; "
            "the bundled default character remains active: "
            f"{error}"
        )
        _CHARACTER_SELECTION_LOGGER.exception(message)
        raise RuntimeError(message) from error
    _activate(source)
    return source


__all__ = (
    "ACTIVE_CHARACTER_ENV",
    "DEFAULT_CHARACTER_ID",
    "SUPPORTED_CHARACTER_IDS",
    "activate_product_character_runtime",
)
