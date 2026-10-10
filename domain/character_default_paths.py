"""MoHan product defaults retained for public character-data compatibility."""

from __future__ import annotations

lazy from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CHARACTER_ROOT = _PROJECT_ROOT / "assets" / "characters" / "mohan"
DEFAULT_RIG_MANIFEST_PATH = _DEFAULT_CHARACTER_ROOT / "rig" / "rig-manifest.json"
DEFAULT_EXPRESSION_CATALOG_PATH = (
    _DEFAULT_CHARACTER_ROOT / "expressions" / "state-catalog.json"
)

__all__ = ("DEFAULT_EXPRESSION_CATALOG_PATH", "DEFAULT_RIG_MANIFEST_PATH")
