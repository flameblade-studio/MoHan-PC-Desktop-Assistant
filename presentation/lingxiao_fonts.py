"""Register the bundled Lingxiao font files exactly once per process."""

from __future__ import annotations

lazy from pathlib import Path

lazy from PySide6.QtGui import QFontDatabase

lazy from presentation.presentation_resources import resource_path

__all__ = ("register_bundled_fonts",)

_FONT_ROOT = "assets/fonts"
_registered = False
_registered_paths: tuple[Path, ...] = ()


def register_bundled_fonts() -> tuple[Path, ...]:
    """Register every bundled TTF once and return the registered paths."""

    global _registered, _registered_paths
    if _registered:
        return _registered_paths

    root = resource_path(_FONT_ROOT)
    if not root.is_dir():
        raise RuntimeError(f"Bundled font directory is missing: {root}")
    paths = tuple(sorted(root.rglob("*.ttf")))
    failures = tuple(
        path
        for path in paths
        if QFontDatabase.addApplicationFont(str(path)) == -1
    )
    if failures:
        names = ", ".join(path.name for path in failures)
        raise RuntimeError(f"Bundled font registration failed: {names}")
    _registered_paths = paths
    _registered = True
    return _registered_paths
