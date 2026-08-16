"""Compatibility alias for :mod:`infrastructure.multimodal_model_provider`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module(
    "infrastructure.multimodal_model_provider"
)
