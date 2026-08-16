"""Compatibility alias for :mod:`domain.immutable_config`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.immutable_config")
