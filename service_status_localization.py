"""Compatibility alias for :mod:`presentation.service_status_localization`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module(
    "presentation.service_status_localization"
)
