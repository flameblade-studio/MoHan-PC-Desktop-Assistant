from __future__ import annotations


def scalar_int(value: object) -> int:
    if isinstance(value, int | float | str | bytes | bytearray):
        return int(value)
    raise TypeError("Integer conversion requires a scalar value.")


def scalar_float(value: object) -> float:
    if isinstance(value, int | float | str | bytes | bytearray):
        return float(value)
    raise TypeError("Float conversion requires a scalar value.")


def require_value[T](value: T | None, message: str) -> T:
    if value is None:
        raise RuntimeError(message)
    return value
