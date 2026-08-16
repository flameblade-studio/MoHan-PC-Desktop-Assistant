"""Compatibility alias for :mod:`domain.speech_boundary`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.speech_boundary")
