"""Compatibility alias for infrastructure.face_assets."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.face_assets")
