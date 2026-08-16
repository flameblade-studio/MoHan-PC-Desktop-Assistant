"""Compatibility alias for :mod:`application.multimodal_fusion_hub`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.multimodal_fusion_hub")
