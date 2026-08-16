"""Compatibility alias for :mod:`presentation.auxiliary_ui_localization`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("presentation.auxiliary_ui_localization")
