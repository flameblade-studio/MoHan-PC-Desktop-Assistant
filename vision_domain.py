"""Compatibility alias for :mod:`domain.vision_domain`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.vision_domain")
