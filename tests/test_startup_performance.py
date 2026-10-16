from __future__ import annotations

"""Record-only measurement of the two offline startup phases.

The owner decided on 2026-10-02 that startup timing is recorded, not gated:
CI runners vary too much for a fixed limit to be meaningful.  The test still
fails when startup cannot complete or reports an invalid measurement.
"""

lazy import json
lazy import math
lazy import os
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from tools.measure_startup import measure

RUNS = 7
RECORD_PATH = ROOT / ".quality-tmp" / "startup-medians.json"


def _record(first_paint: float, deferred: float) -> None:
    line = (
        f"STARTUP_MEDIANS first_paint_ms={first_paint:.3f} "
        f"deferred_complete_ms={deferred:.3f}"
    )
    print(line, flush=True)
    RECORD_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECORD_PATH.write_text(
        json.dumps({"first_paint_ms": first_paint, "deferred_complete_ms": deferred}) + "\n",
        encoding="utf-8",
    )
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(f"- {line}\n")


def test_offline_startup_completes_and_records_medians() -> None:
    report = measure(RUNS)
    summary = report["summary"]
    first_paint = summary["first_paint_ms"]["median_ms"]
    deferred = summary["deferred_complete_ms"]["median_ms"]
    _record(first_paint, deferred)

    for name, value in (("first-paint", first_paint), ("deferred-startup", deferred)):
        assert math.isfinite(value) and value > 0, f"{name} median is invalid: {value!r}"
