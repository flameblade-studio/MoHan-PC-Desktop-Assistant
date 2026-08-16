"""Compatibility alias for :mod:`domain.audio_buffer`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.audio_buffer")
