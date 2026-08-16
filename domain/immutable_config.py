from __future__ import annotations

lazy from collections.abc import Mapping
lazy from typing import Any


def deep_freeze(value: Any) -> Any:
    """Recursively convert configuration containers to immutable built-ins."""
    if isinstance(value, frozendict):
        return value
    if isinstance(value, Mapping):
        return frozendict(
            (key, deep_freeze(item)) for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(deep_freeze(item) for item in value)
    return value
