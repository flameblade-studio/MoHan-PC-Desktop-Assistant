"""Compatibility alias for :mod:`domain.character_body_profile`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.character_body_profile")
