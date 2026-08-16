"""Compatibility alias for :mod:`application.appearance_session`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.appearance_session")
