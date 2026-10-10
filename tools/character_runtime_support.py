"""Compatibility import for the canonical product-character bootstrap."""

from __future__ import annotations

lazy from pathlib import Path

lazy from application.character_runtime_bootstrap import (
    activate_product_character_runtime,
)

ROOT = Path(__file__).resolve().parents[1]


def activate_bundled_mohan_character_runtime(
    repo_root: Path = ROOT,
) -> None:
    """Preserve the prior tool API while delegating to the one product bootstrap."""

    activate_product_character_runtime(repo_root)


__all__ = (
    "activate_bundled_mohan_character_runtime",
    "activate_product_character_runtime",
)
