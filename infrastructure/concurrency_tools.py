from __future__ import annotations

from domain.python315_concurrency import ThreadPoolExecutor


def thread_pool_executor(max_workers: int) -> ThreadPoolExecutor:
    """Create a concrete executor behind a PEP 810 module boundary."""
    return ThreadPoolExecutor(max_workers=max_workers)
