from __future__ import annotations

lazy import logging
lazy import sys
lazy from types import ModuleType

lazy import pytest

lazy from application.native_rgba_acceleration import (
    CROSSFADE_MAX,
    NativeRgbaAcceleration,
    RgbaAccelerationError,
    alpha_over_rgba_python,
    composite_region_rgba_python,
    crossfade_rgba_python,
)

CALL_COUNT = 2


def _rgba(*pixels: tuple[int, int, int, int]) -> bytes:
    return bytes(channel for pixel in pixels for channel in pixel)


def _module(**operations: object) -> ModuleType:
    module = ModuleType("_mohan_accel")
    module.__version__ = "test"
    for name, operation in operations.items():
        setattr(module, name, operation)
    return module


def test_python_alpha_over_matches_existing_integer_contract() -> None:
    target = _rgba((20, 40, 60, 80), (7, 8, 9, 10))
    source = _rgba((200, 100, 50, 128), (255, 0, 255, 0))
    assert alpha_over_rgba_python(target, source) == _rgba(
        (110, 70, 54, 167),
        (7, 8, 9, 10),
    )


def test_python_crossfade_is_exact_at_boundaries_and_midpoint() -> None:
    first = _rgba((0, 1, 127, 255))
    second = _rgba((255, 127, 1, 0))
    assert crossfade_rgba_python(first, second, 0) == first
    assert crossfade_rgba_python(first, second, CROSSFADE_MAX) == second
    assert crossfade_rgba_python(first, second, 32_768) == _rgba((128, 64, 64, 127))


def test_python_region_composite_honors_masks_and_transparent_bounds() -> None:
    target = _rgba(*([(10, 10, 10, 10)] * 6))
    source = _rgba((200, 100, 50, 255), (1, 2, 3, 0))
    approved = bytes((0, 1, 1, 0, 0, 0))
    identity = bytes(6)
    occlusion = bytes((0, 1, 0, 0, 0, 0))
    output = composite_region_rgba_python(
        target,
        3,
        2,
        source,
        2,
        1,
        1,
        0,
        approved,
        identity,
        (occlusion,),
    )
    assert output == target

    transparent_off_canvas = composite_region_rgba_python(
        _rgba((0, 0, 0, 0)),
        1,
        1,
        _rgba((99, 88, 77, 0)),
        1,
        1,
        -1,
        0,
        b"\x01",
        b"\x00",
    )
    assert transparent_off_canvas == _rgba((0, 0, 0, 0))


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            lambda: alpha_over_rgba_python(b"\x00" * 3, b"\x00" * 3),
            "divisible by four",
        ),
        (
            lambda: alpha_over_rgba_python(b"\x00" * 4, b"\x00" * 8),
            "sizes must match",
        ),
        (
            lambda: crossfade_rgba_python(b"", b"", -1),
            "between 0 and 65535",
        ),
        (
            lambda: crossfade_rgba_python(b"", b"", True),
            "between 0 and 65535",
        ),
        (
            lambda: composite_region_rgba_python(
                b"\x00" * 4,
                1,
                1,
                _rgba((1, 2, 3, 1)),
                1,
                1,
                -1,
                0,
                b"\x01",
                b"\x00",
            ),
            "leaves the target canvas",
        ),
        (
            lambda: composite_region_rgba_python(
                b"\x00" * 4,
                1,
                1,
                _rgba((1, 2, 3, 1)),
                1,
                1,
                0,
                0,
                b"\x02",
                b"\x00",
            ),
            "masks must be binary",
        ),
        (
            lambda: composite_region_rgba_python(
                b"\x00" * 4,
                1,
                1,
                _rgba((1, 2, 3, 1)),
                1,
                1,
                0,
                0,
                b"\x01",
                b"\x01",
            ),
            "approved target region",
        ),
    ],
)
def test_python_contract_rejects_invalid_inputs(call, message: str) -> None:
    with pytest.raises(RgbaAccelerationError, match=message):
        call()


def test_python_contract_rejects_anchor_outside_native_coordinate_range() -> None:
    with pytest.raises(RgbaAccelerationError, match="supported range"):
        composite_region_rgba_python(
            b"\x00" * 4,
            1,
            1,
            _rgba((1, 2, 3, 0)),
            1,
            1,
            sys.maxsize + 1,
            0,
            b"\x01",
            b"\x00",
        )


def test_missing_native_module_loads_once_and_transparently_falls_back() -> None:
    attempts: list[str] = []

    def missing(name: str) -> ModuleType:
        attempts.append(name)
        raise ModuleNotFoundError(name)

    accelerator = NativeRgbaAcceleration(module_loader=missing)
    target = _rgba((1, 2, 3, 4))
    source = _rgba((5, 6, 7, 128))
    expected = alpha_over_rgba_python(target, source)
    assert accelerator.alpha_over_rgba(target, source) == expected
    assert accelerator.alpha_over_rgba(target, source) == expected
    status = accelerator.status()
    assert attempts == ["_mohan_accel"]
    assert not status.available
    assert "ModuleNotFoundError" in (status.load_error or "")
    assert status.operation_failures == ()


def test_native_operation_is_first_call_verified_then_used_directly() -> None:
    calls = 0

    def native(target: bytes, source: bytes) -> bytes:
        nonlocal calls
        calls += 1
        return alpha_over_rgba_python(target, source)

    accelerator = NativeRgbaAcceleration(
        module_loader=lambda _name: _module(alpha_over_rgba=native)
    )
    target = _rgba((10, 20, 30, 40))
    source = _rgba((50, 60, 70, 80))
    expected = alpha_over_rgba_python(target, source)
    assert accelerator.alpha_over_rgba(target, source) == expected
    assert accelerator.alpha_over_rgba(target, source) == expected
    status = accelerator.status()
    assert calls == CALL_COUNT
    assert status.verified_operations == ("alpha_over_rgba",)
    assert status.disabled_operations == ()


def test_non_exact_native_result_is_disabled_without_leaking_pixels(
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = 0

    def wrong(_target: bytes, _source: bytes) -> bytes:
        nonlocal calls
        calls += 1
        return b"\xff\xff\xff\xff"

    accelerator = NativeRgbaAcceleration(
        module_loader=lambda _name: _module(alpha_over_rgba=wrong)
    )
    target = _rgba((10, 20, 30, 40))
    source = _rgba((50, 60, 70, 80))
    with caplog.at_level(logging.WARNING):
        actual = accelerator.alpha_over_rgba(target, source)
    assert actual == alpha_over_rgba_python(target, source)
    assert accelerator.alpha_over_rgba(target, source) == actual
    status = accelerator.status()
    assert calls == 1
    assert status.disabled_operations == ("alpha_over_rgba",)
    assert status.operation_failures == (("alpha_over_rgba", 1),)
    assert target.hex() not in caplog.text
    assert source.hex() not in caplog.text


def test_native_fault_disables_only_that_operation_and_falls_back(
    caplog: pytest.LogCaptureFixture,
) -> None:
    native_calls = 0
    first = _rgba((0, 10, 20, 30))
    second = _rgba((255, 245, 235, 225))

    def fail(*_arguments: object) -> bytes:
        nonlocal native_calls
        native_calls += 1
        raise RuntimeError(f"native render fault {first.hex()}")

    accelerator = NativeRgbaAcceleration(
        module_loader=lambda _name: _module(crossfade_rgba=fail)
    )
    expected = crossfade_rgba_python(first, second, 32_768)
    with caplog.at_level(logging.WARNING):
        assert accelerator.crossfade_rgba(first, second, 32_768) == expected
    assert accelerator.crossfade_rgba(first, second, 32_768) == expected
    assert native_calls == 1
    assert "RuntimeError" in caplog.text
    assert first.hex() not in caplog.text
    assert second.hex() not in caplog.text
    assert accelerator.status().disabled_operations == ("crossfade_rgba",)


def test_native_contract_rejection_does_not_disable_region_operation() -> None:
    native_calls = 0

    def reject_then_render(*arguments: object) -> bytes:
        nonlocal native_calls
        native_calls += 1
        if native_calls == 1:
            raise ValueError("Visible source pixel leaves the target canvas")
        return composite_region_rgba_python(*arguments)

    accelerator = NativeRgbaAcceleration(
        module_loader=lambda _name: _module(
            composite_region_rgba=reject_then_render
        )
    )
    target = _rgba((0, 0, 0, 0))
    source = _rgba((10, 20, 30, 255))
    invalid = (
        target,
        1,
        1,
        source,
        1,
        1,
        -1,
        0,
        b"\x01",
        b"\x00",
        (),
    )
    with pytest.raises(RgbaAccelerationError, match="leaves the target canvas"):
        accelerator.composite_region_rgba(*invalid)
    status = accelerator.status()
    assert status.disabled_operations == ()
    assert status.operation_failures == ()

    valid = (*invalid[:6], 0, 0, *invalid[8:])
    assert accelerator.composite_region_rgba(*valid) == composite_region_rgba_python(
        *valid
    )
    assert native_calls == CALL_COUNT
    assert accelerator.status().verified_operations == ("composite_region_rgba",)


def test_contract_rejection_during_native_verification_does_not_disable_operation() -> None:
    def falsely_accepts(*_arguments: object) -> bytes:
        return b"\x00" * 4

    accelerator = NativeRgbaAcceleration(
        module_loader=lambda _name: _module(
            composite_region_rgba=falsely_accepts
        )
    )
    with pytest.raises(RgbaAccelerationError, match="leaves the target canvas"):
        accelerator.composite_region_rgba(
            _rgba((0, 0, 0, 0)),
            1,
            1,
            _rgba((10, 20, 30, 255)),
            1,
            1,
            -1,
            0,
            b"\x01",
            b"\x00",
            (),
        )
    status = accelerator.status()
    assert status.disabled_operations == ()
    assert status.operation_failures == ()


def test_python_validation_cannot_be_bypassed_by_native_backend() -> None:
    called = False

    def permissive(*_arguments: object) -> bytes:
        nonlocal called
        called = True
        return b""

    accelerator = NativeRgbaAcceleration(
        module_loader=lambda _name: _module(crossfade_rgba=permissive)
    )
    with pytest.raises(RgbaAccelerationError):
        accelerator.crossfade_rgba(b"", b"", True)
    assert not called


def test_region_native_result_must_be_exact_or_operation_is_disabled() -> None:
    calls = 0

    def native(*arguments: object) -> bytes:
        nonlocal calls
        calls += 1
        return composite_region_rgba_python(*arguments)

    accelerator = NativeRgbaAcceleration(
        module_loader=lambda _name: _module(composite_region_rgba=native)
    )
    target = _rgba(*([(0, 0, 0, 0)] * 4))
    source = _rgba((1, 2, 3, 255))
    expected = composite_region_rgba_python(
        target,
        2,
        2,
        source,
        1,
        1,
        1,
        1,
        b"\x01" * 4,
        b"\x00" * 4,
        (),
    )
    assert (
        accelerator.composite_region_rgba(
            target,
            2,
            2,
            source,
            1,
            1,
            1,
            1,
            b"\x01" * 4,
            b"\x00" * 4,
            (),
        )
        == expected
    )
    assert calls == 1
    assert accelerator.status().verified_operations == ("composite_region_rgba",)
