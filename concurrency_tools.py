"""Compatibility alias for :mod:`infrastructure.concurrency_tools`."""

from __future__ import annotations

import importlib
import sys

sys.modules[__name__] = importlib.import_module("infrastructure.concurrency_tools")
