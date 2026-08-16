"""Compatibility alias for :mod:`domain.full_body_asset_audit`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.full_body_asset_audit")
