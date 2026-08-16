"""Compatibility alias for :mod:`domain.prompt_cache`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.prompt_cache")
