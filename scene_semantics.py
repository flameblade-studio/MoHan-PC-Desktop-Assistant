"""Compatibility alias for :mod:`domain.scene_semantics`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.scene_semantics")
