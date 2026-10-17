"""Resolve a character source body binding at the infrastructure boundary."""

from __future__ import annotations

lazy import logging
lazy from collections.abc import Iterable
lazy from pathlib import Path

lazy from domain.body_pack import BodyPackMismatchError
lazy from domain.character_pack.character_data_models import CharacterRigManifest
lazy from domain.character_pack.models import CharacterPackManifest
lazy from infrastructure.body_pack_reader import (
    CharacterBodyBinding,
    resolve_character_body_binding,
)


LOGGER = logging.getLogger(__name__)


def resolve_body_binding_with_fallback(
    manifest: CharacterPackManifest,
    rig: CharacterRigManifest,
    body_pack_roots: Iterable[str | Path],
) -> tuple[CharacterBodyBinding, BodyPackMismatchError | None]:
    """Keep MoHan's current-look fallback while other packs fail closed."""

    try:
        return resolve_character_body_binding(
            manifest.body_pack, rig, body_pack_roots, manifest.layer_views,
        ), None
    except BodyPackMismatchError as error:
        if manifest.character_id != "mohan":
            raise
        LOGGER.warning(
            "mohan_body_pack_fallback code=%s path=%s message=%s",
            error.code,
            error.path or getattr(manifest.body_pack, "id", None),
            error,
        )
        return resolve_character_body_binding(
            None, rig, (), manifest.layer_views,
        ), error


__all__ = ("resolve_body_binding_with_fallback",)
