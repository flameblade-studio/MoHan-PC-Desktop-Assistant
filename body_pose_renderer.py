"""Compatibility alias for :mod:`application.body_pose_renderer`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.body_pose_renderer")
