"""Pure policy for selecting pose-shared legacy makeup views."""

from __future__ import annotations

lazy from collections.abc import Callable


def select_legacy_makeup_view_id(
    declares_view: Callable[[str], bool] | None,
    silhouette: str,
) -> str | None:
    """Return the pose-shared legacy key when the active pack declares it."""
    if not callable(declares_view):
        return None
    legacy_view_id = f"{silhouette}-legacy"
    return legacy_view_id if declares_view(legacy_view_id) else None
