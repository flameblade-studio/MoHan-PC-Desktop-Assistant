"""Compatibility alias for :mod:`domain.character_pose`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.character_pose")
