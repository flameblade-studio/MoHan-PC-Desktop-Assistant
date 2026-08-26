"""Authoritative natural microtiming ranges for the companion face."""

from __future__ import annotations

BLINK_INTERVAL_MS = (2_800, 6_200)
BLINK_DURATION_MS = (118, 145)
# The face clock is 50 Hz. Blink state changes land only on exact 20 ms
# boundaries. The repeated semantic states are intentional: they match the
# human-approved visual schedule exactly and prevent interpolated ghost lids.
FACE_TICK_MS = 20
BLINK_HALF_CLOSE_TIMES_MS = (0, FACE_TICK_MS)
BLINK_CLOSED_TIMES_MS = tuple(range(FACE_TICK_MS * 2, FACE_TICK_MS * 6, FACE_TICK_MS))
BLINK_HALF_OPEN_TIMES_MS = tuple(range(FACE_TICK_MS * 6, FACE_TICK_MS * 9, FACE_TICK_MS))
BLINK_REST_AT_MS = FACE_TICK_MS * 9
# Compatibility aliases for half-body scheduling and external audits.
BLINK_CLOSE_AT_MS = BLINK_CLOSED_TIMES_MS[0]
BLINK_REOPEN_AT_MS = BLINK_HALF_OPEN_TIMES_MS[0]
BLINK_CLOSED_HOLD_MS = BLINK_REOPEN_AT_MS - BLINK_CLOSE_AT_MS
ATTENTION_GLANCE_INTERVAL_MS = (38_000, 78_000)
SACCADE_INTERVAL_MS = (4_000, 11_000)
MINIMUM_AUDIT_SAMPLES = 3


def audit_interval_samples(
    name: str,
    samples_ms: tuple[int, ...],
    *,
    allowed_range: tuple[int, int],
) -> tuple[str, ...]:
    """Reject out-of-range or mechanically periodic face-event schedules."""

    if len(samples_ms) < MINIMUM_AUDIT_SAMPLES:
        return (f"{name}:insufficient-microtiming-samples",)
    lower, upper = allowed_range
    issues = []
    if lower >= upper:
        issues.append(f"{name}:invalid-microtiming-range")
    if any(sample < lower or sample > upper for sample in samples_ms):
        issues.append(f"{name}:microtiming-out-of-range")
    if len(set(samples_ms)) == 1:
        issues.append(f"{name}:mechanical-fixed-period")
    deltas = tuple(end - start for start, end in zip(samples_ms, samples_ms[1:]))
    if deltas and len(set(deltas)) == 1:
        issues.append(f"{name}:mechanical-linear-period")
    return tuple(issues)
