"""Compatibility alias for :mod:`domain.theme_session`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.theme_session")
