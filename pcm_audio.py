"""Compatibility alias for :mod:`domain.pcm_audio`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.pcm_audio")
