"""Character-neutral packaged-resource path resolution."""

from __future__ import annotations

lazy import sys
lazy from pathlib import Path

RESOURCE_BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def resource_path(relative: str) -> Path:
    """Resolve one packaged resource without selecting product-owned content."""

    return RESOURCE_BASE / relative


__all__ = ("RESOURCE_BASE", "resource_path")
