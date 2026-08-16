"""Compatibility alias for infrastructure.face_renderer."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.face_renderer")
