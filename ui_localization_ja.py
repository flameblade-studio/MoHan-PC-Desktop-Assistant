"""Compatibility alias for :mod:`presentation.ui_localization_ja`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("presentation.ui_localization_ja")
