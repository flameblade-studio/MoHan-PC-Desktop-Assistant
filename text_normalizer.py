"""Compatibility alias for :mod:`domain.text_normalizer`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.text_normalizer")
