"""Compatibility alias for :mod:`presentation.preview_app`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("presentation.preview_app")
