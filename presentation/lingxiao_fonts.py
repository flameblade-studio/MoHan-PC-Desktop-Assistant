"""Register the bundled Lingxiao font files exactly once per process."""

from __future__ import annotations

lazy import logging
lazy from pathlib import Path

lazy from PySide6.QtGui import QFontDatabase

lazy from presentation.presentation_resources import resource_path

__all__ = ("register_bundled_fonts",)

_FONT_ROOT = "assets/fonts"
_LOGGER = logging.getLogger(__name__)
_registered = False
_registered_paths: tuple[Path, ...] = ()


def register_bundled_fonts() -> tuple[Path, ...]:
    """Register every bundled TTF once and return the registered paths."""

    global _registered, _registered_paths
    if _registered:
        return _registered_paths

    root = resource_path(_FONT_ROOT)
    if not root.is_dir():
        _LOGGER.warning("Bundled font directory is missing: %s", root)
        _registered_paths = ()
        _registered = True
        return _registered_paths
    paths = tuple(sorted(root.rglob("*.ttf")))
    registered_paths: list[Path] = []
    for path in paths:
        try:
            font_id = QFontDatabase.addApplicationFont(str(path))
        except (OSError, RuntimeError) as error:
            _LOGGER.warning("Bundled font registration failed for %s: %s", path, error)
            continue
        if font_id < 0:
            _LOGGER.warning("Bundled font registration failed for %s", path)
            continue
        registered_paths.append(path)
    _registered_paths = tuple(registered_paths)
    _registered = True
    return _registered_paths
