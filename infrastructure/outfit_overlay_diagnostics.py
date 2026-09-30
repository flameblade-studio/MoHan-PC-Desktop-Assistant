"""Privacy-safe, deduplicated diagnostics for appearance fallback events."""

from __future__ import annotations

lazy import logging
lazy import re
lazy from collections.abc import Iterable
lazy from pathlib import PurePosixPath
lazy from domain.outfit_pack import SUPPORTED_SILHOUETTES, LEGACY_MAKEUP_SILHOUETTES
lazy from domain.character_pose import LEGACY_VIEW_ALIASES

_LOGGER = logging.getLogger("mohan.outfit_overlay")
_FALLBACK_EVENT = "outfit_overlay_fallback"
_KNOWN_VIEWS = frozenset((*SUPPORTED_SILHOUETTES, *LEGACY_MAKEUP_SILHOUETTES, *LEGACY_VIEW_ALIASES))
_SAFE_PACK_ID = re.compile(r"[a-z0-9][a-z0-9_.-]{0,127}\Z")


def _safe_pack_id(value: object) -> str | None:
    return value if isinstance(value, str) and _SAFE_PACK_ID.fullmatch(value) else None


def _safe_asset_path(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or re.match(r"[A-Za-z]:", normalized):
        return None
    if ".." in path.parts:
        return f"../{path.name}" if re.fullmatch(r"[a-z0-9_.+-]+\.png", path.name) else None
    if re.fullmatch(r"assets/[a-z0-9_.+-]+\.(?:png|webp|svg)", normalized):
        return normalized
    if re.fullmatch(r"[a-z0-9_.-]+\.mohan-outfit", normalized):
        return normalized
    return None


def _exception_chain(error: BaseException) -> Iterable[BaseException]:
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def record_outfit_fallback(
    error: BaseException,
    *,
    view_id: str,
    seen: set[tuple[str, str]],
) -> None:
    """Log one structured record per reason and view without local paths."""

    chain = tuple(_exception_chain(error))
    reason = next(
        (value for item in chain if isinstance(value := getattr(item, "reason", None), str)),
        type(chain[-1]).__name__,
    )
    if reason not in {"duplicate_pack_id", "asset_path_traversal", "manifest_asset_hash_mismatch"}:
        reason = type(chain[-1]).__name__
    safe_view = view_id if view_id in _KNOWN_VIEWS else "invalid_view_id"
    identity = (safe_view, reason)
    if identity in seen:
        return
    seen.add(identity)
    pack_id = next(
        (value for item in chain if (value := _safe_pack_id(getattr(item, "pack_id", None))) is not None),
        None,
    )
    asset_path = next(
        (value for item in chain if (value := _safe_asset_path(getattr(item, "asset_path", None))) is not None),
        None,
    )
    _LOGGER.warning(
        _FALLBACK_EVENT,
        extra={
            "outfit_reason": reason,
            "outfit_view": safe_view,
            "outfit_pack_id": pack_id,
            "outfit_asset_path": asset_path,
        },
    )
