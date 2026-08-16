"""Compatibility alias for :mod:`domain.character_framing`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.character_framing")
