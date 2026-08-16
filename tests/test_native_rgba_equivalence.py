from __future__ import annotations

lazy import importlib
lazy import random

lazy import pytest

lazy from application.native_rgba_acceleration import (
    NativeRgbaAcceleration,
    RgbaAccelerationError,
    alpha_over_rgba_python,
    composite_region_rgba_python,
    crossfade_rgba_python,
)

try:
    NATIVE = importlib.import_module("_mohan_accel")
except ModuleNotFoundError:
    NATIVE = None

REQUIRED_OPERATIONS = (
    "alpha_over_rgba",
    "crossfade_rgba",
    "composite_region_rgba",
)
NATIVE_READY = NATIVE is not None and all(
    hasattr(NATIVE, operation) for operation in REQUIRED_OPERATIONS
)

pytestmark = pytest.mark.skipif(
    not NATIVE_READY,
    reason="optional _mohan_accel RGBA functions are not built",
)


def _random_bytes(generator: random.Random, length: int) -> bytes:
    return bytes(generator.randrange(256) for _ in range(length))


def test_native_alpha_over_matches_python_for_deterministic_frames() -> None:
    generator = random.Random(2026081401)
    cases = [
        (b"", b""),
        (bytes((1, 2, 3, 4)), bytes((99, 88, 77, 0))),
        (bytes((1, 2, 3, 4)), bytes((99, 88, 77, 255))),
    ]
    cases.extend(
        (
            _random_bytes(generator, pixels * 4),
            _random_bytes(generator, pixels * 4),
        )
        for pixels in (2, 17, 257, 4_096)
    )
    for target, source in cases:
        assert NATIVE.alpha_over_rgba(target, source) == (
            alpha_over_rgba_python(target, source)
        )


def test_native_crossfade_matches_python_for_every_rounding_boundary() -> None:
    generator = random.Random(2026081402)
    first = _random_bytes(generator, 4_096 * 4)
    second = _random_bytes(generator, len(first))
    for weight in (0, 1, 32_767, 32_768, 65_534, 65_535):
        assert NATIVE.crossfade_rgba(first, second, weight) == (
            crossfade_rgba_python(first, second, weight)
        )


def test_native_parallel_boundary_remains_bit_exact() -> None:
    threshold = NATIVE.__rgba_parallel_pixel_threshold__
    assert threshold == 262_144
    for pixels in (threshold - 1, threshold):
        target = bytes((17, 37, 59, 211)) * pixels
        source = bytes((181, 97, 43, 127)) * pixels
        assert NATIVE.alpha_over_rgba(target, source) == (
            alpha_over_rgba_python(target, source)
        )
        assert NATIVE.crossfade_rgba(target, source, 32_768) == (
            crossfade_rgba_python(target, source, 32_768)
        )


def test_native_region_composite_matches_masks_offsets_and_alpha() -> None:
    generator = random.Random(2026081403)
    target_width = 19
    target_height = 13
    source_width = 7
    source_height = 5
    target = _random_bytes(generator, target_width * target_height * 4)
    source = bytearray(_random_bytes(generator, source_width * source_height * 4))
    source[3] = 0
    source[-1] = 0
    approved = bytearray([1] * (target_width * target_height))
    identity = bytearray(target_width * target_height)
    occlusion = bytearray(target_width * target_height)
    for pixel in (44, 45, 63, 64):
        occlusion[pixel] = 1
    arguments = (
        target,
        target_width,
        target_height,
        bytes(source),
        source_width,
        source_height,
        3,
        2,
        bytes(approved),
        bytes(identity),
        (bytes(occlusion),),
    )
    assert NATIVE.composite_region_rgba(*arguments) == (
        composite_region_rgba_python(*arguments)
    )


def test_native_parallel_region_boundary_remains_bit_exact() -> None:
    width = 512
    for height in (511, 512):
        pixels = width * height
        target = bytes((17, 37, 59, 211)) * pixels
        source = bytes((181, 97, 43, 127)) * pixels
        arguments = (
            target,
            width,
            height,
            source,
            width,
            height,
            0,
            0,
            b"\x01" * pixels,
            b"\x00" * pixels,
            (b"\x00" * pixels,),
        )
        assert NATIVE.composite_region_rgba(*arguments) == (
            composite_region_rgba_python(*arguments)
        )


def test_native_and_python_reject_equivalent_invalid_contracts() -> None:
    invalid_calls = (
        (
            lambda: NATIVE.alpha_over_rgba(b"\x00" * 4, b"\x00" * 8),
            lambda: alpha_over_rgba_python(b"\x00" * 4, b"\x00" * 8),
        ),
        (
            lambda: NATIVE.crossfade_rgba(b"", b"", 65_536),
            lambda: crossfade_rgba_python(b"", b"", 65_536),
        ),
        (
            lambda: NATIVE.composite_region_rgba(
                b"\x00" * 4,
                1,
                1,
                bytes((1, 2, 3, 255)),
                1,
                1,
                -1,
                0,
                b"\x01",
                b"\x00",
                (),
            ),
            lambda: composite_region_rgba_python(
                b"\x00" * 4,
                1,
                1,
                bytes((1, 2, 3, 255)),
                1,
                1,
                -1,
                0,
                b"\x01",
                b"\x00",
                (),
            ),
        ),
    )
    for native_call, python_call in invalid_calls:
        with pytest.raises((ValueError, OverflowError)):
            native_call()
        with pytest.raises(RgbaAccelerationError):
            python_call()


def test_native_boundary_rejects_mutable_or_view_backed_buffers() -> None:
    target = bytes((1, 2, 3, 4))
    source = bytes((5, 6, 7, 8))
    for mutable_or_view in (bytearray(target), memoryview(target)):
        with pytest.raises(TypeError):
            NATIVE.alpha_over_rgba(mutable_or_view, source)
        with pytest.raises(TypeError):
            NATIVE.crossfade_rgba(target, mutable_or_view, 1)
        with pytest.raises(TypeError):
            NATIVE.composite_region_rgba(
                target,
                1,
                1,
                source,
                1,
                1,
                0,
                0,
                mutable_or_view,
                b"\x00",
                (),
            )


def test_adapter_uses_built_rgba_functions_without_fallback() -> None:
    accelerator = NativeRgbaAcceleration()
    target = bytes((10, 20, 30, 40)) * 16
    source = bytes((50, 60, 70, 80)) * 16
    assert accelerator.alpha_over_rgba(target, source) == (
        alpha_over_rgba_python(target, source)
    )
    assert accelerator.crossfade_rgba(target, source, 12_345) == (
        crossfade_rgba_python(target, source, 12_345)
    )
    status = accelerator.status()
    assert status.available
    assert status.disabled_operations == ()
    assert status.operation_failures == ()
    assert set(status.verified_operations) >= {
        "alpha_over_rgba",
        "crossfade_rgba",
    }
