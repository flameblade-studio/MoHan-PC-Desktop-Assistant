from __future__ import annotations

lazy from datetime import UTC, datetime


def local_aware_time() -> datetime:
    """Return the current local time with an explicit UTC offset."""
    return datetime.now(UTC).astimezone()


def local_wall_time() -> datetime:
    """Return legacy-compatible local wall time without timezone metadata.

    MoHan's existing SQLite rows use local ISO timestamps without offsets.
    Keeping that representation avoids mixing aware and naive values while
    making every new wall-clock read explicit and independently testable.
    """
    return local_aware_time().replace(tzinfo=None)


def local_wall_time_from_timestamp(timestamp: float) -> datetime:
    """Convert a POSIX timestamp to MoHan's local wall-clock representation."""
    return datetime.fromtimestamp(timestamp, UTC).astimezone().replace(tzinfo=None)
