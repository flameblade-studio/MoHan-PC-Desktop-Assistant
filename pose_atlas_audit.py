"""Compatibility alias for :mod:`domain.pose_atlas_audit`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.pose_atlas_audit")
