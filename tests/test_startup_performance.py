from __future__ import annotations

"""Stable median-based guard for the two offline startup phases."""

lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from tools.measure_startup import measure

RUNS = 7

# Ticket #207 remeasured HEAD 0653c21 plus the mouth-ROI fix on 2026-10-01:
# seven fresh-process/profile, offline/offscreen runs per batch, perf_counter_ns,
# Tukey hinges, temporary profiles on the workspace volume. Evidence:
# .qa/ticket-207/after-6.json (same measure() worker through a source-selection
# wrapper) and after-7.json (standard tools/measure_startup.py confirmation).
# The quietest batch (CPU 4.36% -> 5.98%) measured first-paint median
# 6,673.457 ms, Q1 6,551.234, Q3 6,776.851, IQR 225.617 ms.
# Standard confirmation: median 6,738.926, Q1 6,448.319, Q3 6,980.792,
# IQR 532.473 ms. Keep the larger observed Q3 + 6*IQR noise floor
# (10,175.630 ms), above quiet median*1.25 (8,341.821 ms), to cover the
# confirmation's wider host variation while tightening the old 16,091.945 ms.
FIRST_PAINT_LIMIT_MS = 10_175.630

# The same 2026-10-01 quiet batch's first-paint -> deferred-complete phase
# measured median 4,444.861 ms, Q1 4,398.338, Q3 4,581.320, IQR 182.983 ms.
# Standard confirmation: median 4,392.861, Q1 4,387.040, Q3 4,517.197,
# IQR 130.157 ms. The larger Q3 + 6*IQR noise floor (5,679.218 ms) exceeds
# quiet median*1.25 (5,556.076 ms) and the confirmation noise floor
# (5,298.139 ms). Preserve that noise allowance and tighten the old
# 6,441.879 ms. Both phases retain the original seven-run median assertions.
DEFERRED_COMPLETE_LIMIT_MS = 5_679.218


def test_offline_startup_medians_stay_within_measured_limits() -> None:
    report = measure(RUNS)
    summary = report["summary"]
    first_paint = summary["first_paint_ms"]["median_ms"]
    deferred = summary["deferred_complete_ms"]["median_ms"]

    assert first_paint <= FIRST_PAINT_LIMIT_MS, (
        f"first-paint median {first_paint:.3f} ms exceeds "
        f"{FIRST_PAINT_LIMIT_MS:.3f} ms"
    )
    assert deferred <= DEFERRED_COMPLETE_LIMIT_MS, (
        f"deferred-startup median {deferred:.3f} ms exceeds "
        f"{DEFERRED_COMPLETE_LIMIT_MS:.3f} ms"
    )
