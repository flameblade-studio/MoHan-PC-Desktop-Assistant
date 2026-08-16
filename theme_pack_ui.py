"""Compatibility alias for :mod:`presentation.theme_pack_ui`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("presentation.theme_pack_ui")
