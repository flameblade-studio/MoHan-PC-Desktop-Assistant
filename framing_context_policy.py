"""Compatibility alias for :mod:`domain.framing_context_policy`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.framing_context_policy")
