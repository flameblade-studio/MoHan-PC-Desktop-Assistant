"""Activate the bundled product character for isolated engine tests."""

from __future__ import annotations

lazy import runpy
lazy import sys
lazy from pathlib import Path

lazy from application.character_runtime_bootstrap import (
    activate_product_character_runtime,
)

ROOT = Path(__file__).resolve().parents[1]


def activate_bundled_character_runtime() -> None:
    """Build the same character-engine profile as the product composition root."""

    activate_product_character_runtime(ROOT)


def main(arguments: list[str] | None = None) -> int:
    """Run one legacy direct test after installing its product fixture."""

    selected = sys.argv[1:] if arguments is None else arguments
    if len(selected) != 1:
        raise SystemExit("usage: python -m tests.character_runtime_support TEST_FILE")
    activate_bundled_character_runtime()
    previous_arguments = sys.argv
    try:
        sys.argv = [selected[0]]
        runpy.run_path(selected[0], run_name="__main__")
    finally:
        sys.argv = previous_arguments
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
