"""Stable concurrency exports for CPython 3.15 lazy standard-library names."""

from __future__ import annotations

import concurrent.futures
from concurrent.futures import Future, as_completed
from concurrent.futures.thread import ThreadPoolExecutor

# CPython 3.15rc1 exposes ThreadPoolExecutor lazily from
# concurrent.futures, while asyncio calls the module attribute directly.
# Resolve that public export once at the shared compatibility boundary so
# import order cannot leave asyncio with a non-callable lazy proxy.
concurrent.futures.ThreadPoolExecutor = ThreadPoolExecutor

__all__ = ("Future", "ThreadPoolExecutor", "as_completed")
