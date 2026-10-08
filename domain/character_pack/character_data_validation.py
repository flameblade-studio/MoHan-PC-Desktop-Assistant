"""Shared strict primitives for versioned character-data loaders."""

from __future__ import annotations

lazy import json
lazy import math
lazy from pathlib import Path

lazy from domain.character_pack.character_data_models import (
    PAIR_LENGTH,
    RECT_LENGTH,
    TRIPLE_LENGTH,
    CanvasSpec,
    CharacterDataError,
)


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CharacterDataError(f"Character data contains a duplicate key: {key!r}.")
        result[key] = value
    return result


def _reject_non_finite_number(value: str) -> None:
    raise CharacterDataError(f"Character data contains a non-finite number: {value}.")


def _read_payload(path: Path) -> dict[str, object]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CharacterDataError(f"Cannot read character data: {path.name}.") from error
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_non_finite_number,
        )
    except (TypeError, ValueError) as error:
        raise CharacterDataError(
            f"Character data is not valid strict JSON: {path.name}."
        ) from error
    if not isinstance(payload, dict):
        raise CharacterDataError("Character data root must be an object.")
    return payload


def _object(
    value: object,
    *,
    name: str,
    keys: frozenset[str],
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise CharacterDataError(
            f"{name} must contain exactly: {', '.join(sorted(keys))}."
        )
    return value


def _array(value: object, *, name: str) -> list[object]:
    if not isinstance(value, list):
        raise CharacterDataError(f"{name} must be an array.")
    return value


def _text(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CharacterDataError(f"{name} must be non-empty trimmed text.")
    return value


def _integer(value: object, *, name: str, minimum: int | None = None) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise CharacterDataError(f"{name} must be a supported integer.")
    return value


def _number(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CharacterDataError(f"{name} must be a finite number.")
    result = float(value)
    if not math.isfinite(result):
        raise CharacterDataError(f"{name} must be a finite number.")
    return result


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise CharacterDataError(f"{name} must be boolean.")
    return value


def _unique_texts(value: object, *, name: str) -> tuple[str, ...]:
    result = tuple(
        _text(item, name=f"{name} item")
        for item in _array(value, name=name)
    )
    if not result or len(result) != len(set(result)):
        raise CharacterDataError(f"{name} must contain unique text values.")
    return result


def _int_pair(value: object, *, name: str) -> tuple[int, int]:
    items = _array(value, name=name)
    if len(items) != PAIR_LENGTH:
        raise CharacterDataError(f"{name} must contain two integers.")
    return (
        _integer(items[0], name=f"{name}[0]"),
        _integer(items[1], name=f"{name}[1]"),
    )


def _float_pair(value: object, *, name: str) -> tuple[float, float]:
    items = _array(value, name=name)
    if len(items) != PAIR_LENGTH:
        raise CharacterDataError(f"{name} must contain two numbers.")
    return (
        _number(items[0], name=f"{name}[0]"),
        _number(items[1], name=f"{name}[1]"),
    )


def _float_triple(value: object, *, name: str) -> tuple[float, float, float]:
    items = _array(value, name=name)
    if len(items) != TRIPLE_LENGTH:
        raise CharacterDataError(f"{name} must contain three numbers.")
    return (
        _number(items[0], name=f"{name}[0]"),
        _number(items[1], name=f"{name}[1]"),
        _number(items[2], name=f"{name}[2]"),
    )


def _rect(value: object, *, name: str) -> tuple[int, int, int, int]:
    items = _array(value, name=name)
    if len(items) != RECT_LENGTH:
        raise CharacterDataError(f"{name} must contain x, y, width, and height.")
    result = (
        _integer(items[0], name=f"{name}[0]"),
        _integer(items[1], name=f"{name}[1]"),
        _integer(items[2], name=f"{name}[2]"),
        _integer(items[3], name=f"{name}[3]"),
    )
    if result[2] <= 0 or result[3] <= 0:
        raise CharacterDataError(f"{name} width and height must be positive.")
    return result


def _text_mapping(value: object, *, name: str) -> frozendict[str, str]:
    if not isinstance(value, dict) or not value:
        raise CharacterDataError(f"{name} must be a non-empty object.")
    return frozendict(
        {
            _text(key, name=f"{name} key"): _text(item, name=f"{name}.{key}")
            for key, item in value.items()
        }
    )


def _canvas(value: object, *, name: str) -> CanvasSpec:
    payload = _object(
        value,
        name=name,
        keys=frozenset({"width", "height", "mode"}),
    )
    result = CanvasSpec(
        _integer(payload["width"], name=f"{name}.width", minimum=1),
        _integer(payload["height"], name=f"{name}.height", minimum=1),
        _text(payload["mode"], name=f"{name}.mode"),
    )
    if result.mode != "RGBA":
        raise CharacterDataError(f"{name}.mode must be RGBA.")
    return result
