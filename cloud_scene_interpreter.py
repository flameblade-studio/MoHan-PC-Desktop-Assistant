"""Compatibility alias for :mod:`domain.cloud_scene_interpreter`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.cloud_scene_interpreter")
