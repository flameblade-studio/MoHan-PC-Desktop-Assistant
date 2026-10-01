from __future__ import annotations

"""Stable median-based guard for the two offline startup phases."""

lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from tools.measure_startup import measure

RUNS = 7

# Ticket #207 measured origin/main-equivalent HEAD e84d42a on 2026-09-29:
# first paint median 12,873.556 ms, Q3 13,057.751 ms, IQR 238.712 ms.
# The 1.25 regression allowance (16,091.945 ms) is larger than the observed
# Q3 + 6*IQR noise floor (14,490.023 ms), so it defines this stable limit.
FIRST_PAINT_LIMIT_MS = 16_091.945

# The same baseline's deferred phase measured median 5,012.562 ms,
# Q3 5,197.803 ms and IQR 207.346 ms.  Its Q3 + 6*IQR noise floor
# (6,441.879 ms) is slightly larger than median*1.25 (6,265.703 ms), so the
# noisier value is the limit.  This deliberately avoids a gate stricter than
# the measured host variation.
DEFERRED_COMPLETE_LIMIT_MS = 6_441.879


def test_offline_startup_medians_stay_within_measured_limits() -> None:
    report = measure(RUNS)
    summary = report["summary"]
    first_paint = summary["first_paint_ms"]["median_ms"]
    deferred = summary["deferred_complete_ms"]["median_ms"]
    # Always report the measured medians so limits can be calibrated against
    # the CI runners that enforce them, not only the developer workstation.
    print(
        f"STARTUP_MEDIANS first_paint_ms={first_paint:.3f} "
        f"deferred_complete_ms={deferred:.3f}",
        flush=True,
    )

    assert first_paint <= FIRST_PAINT_LIMIT_MS, (
        f"first-paint median {first_paint:.3f} ms exceeds "
        f"{FIRST_PAINT_LIMIT_MS:.3f} ms"
    )
    assert deferred <= DEFERRED_COMPLETE_LIMIT_MS, (
        f"deferred-startup median {deferred:.3f} ms exceeds "
        f"{DEFERRED_COMPLETE_LIMIT_MS:.3f} ms"
    )
