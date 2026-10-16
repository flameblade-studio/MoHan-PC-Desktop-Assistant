"""Observe failed binary samples while retaining CPython's sampling behavior."""

from __future__ import annotations

lazy import json
lazy import linecache
lazy import re
lazy import runpy
lazy import sys
lazy from collections import Counter
lazy from pathlib import Path
lazy from profiling.sampling.binary_collector import BinaryCollector

DIAGNOSTICS_PREFIX = "MOHAN_TACHYON_SAMPLE_ERRORS="
ERROR_FAMILIES = (
    "Failed to parse initial frame in chain",
    "Unhandled frame owner",
    "ReadProcessMemory",
    "SuspendThread",
    "ResumeThread",
    "GetThreadContext",
)


def _error_key(error: BaseException) -> tuple[str, str, str, int | None, str, int]:
    message = str(error)
    family = next((name for name in ERROR_FAMILIES if name in message), "other")
    windows_error = re.search(r"Windows error (\d+)", message)
    code = getattr(error, "winerror", None)
    if code is None and windows_error is not None:
        code = int(windows_error[1])
    traceback = error.__traceback__
    operation = "collector"
    location = "unknown"
    line = 0
    while traceback is not None:
        frame = traceback.tb_frame
        source = linecache.getline(frame.f_code.co_filename, traceback.tb_lineno)
        if "unwinder.pause_threads(" in source:
            operation = "pause_threads"
        elif "unwinder.resume_threads(" in source:
            operation = "resume_threads"
        elif "unwinder.get_" in source:
            operation = "read_stack"
        else:
            traceback = traceback.tb_next
            continue
        line = traceback.tb_lineno
        location = f"{Path(frame.f_code.co_filename).name}:{frame.f_code.co_name}"
        traceback = traceback.tb_next
    return operation, type(error).__name__, family, code, location, line


def _error_rows(
    counts: Counter[tuple[str, str, str, int | None, str, int]],
) -> list[dict[str, object]]:
    return [
        {
            "operation": operation,
            "exception_type": exception_type,
            "message_family": family,
            "windows_error": code,
            "source": location,
            "line": line,
            "count": count,
        }
        for (operation, exception_type, family, code, location, line), count
        in counts.items()
    ]


def main() -> None:
    # CPython calls this no-op inside its counted-error handler. sys.exception()
    # observes that same exception, including pause/read/resume and collector
    # failures. Successful samples have no extra call or timing instrumentation.
    original = BinaryCollector.collect_failed_sample
    counts: Counter[tuple[str, str, str, int | None, str, int]] = Counter()

    def observe(collector: BinaryCollector) -> None:
        error = sys.exception()
        if error is not None:
            counts[_error_key(error)] += 1
        original(collector)

    BinaryCollector.collect_failed_sample = observe
    try:
        runpy.run_module("profiling.sampling", run_name="__main__")
    finally:
        BinaryCollector.collect_failed_sample = original
        print(DIAGNOSTICS_PREFIX + json.dumps(_error_rows(counts)), flush=True)


if __name__ == "__main__":
    main()
