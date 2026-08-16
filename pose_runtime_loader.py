"""Compatibility alias for :mod:`domain.pose_runtime_loader`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.pose_runtime_loader")
