"""Measure optional Rust RGBA operations against their Python references."""

from __future__ import annotations

lazy import argparse
lazy import importlib
lazy import json
lazy import statistics
lazy import sys
lazy import time
lazy from collections.abc import Callable
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.native_rgba_acceleration import (
    alpha_over_rgba_python,
    composite_region_rgba_python,
    crossfade_rgba_python,
)


def _measure(operation: Callable[[], bytes], iterations: int) -> list[int]:
    samples: list[int] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        operation()
        samples.append(time.perf_counter_ns() - started)
    return samples


def _summary(samples: list[int]) -> dict[str, float | int]:
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))
    return {
        "iterations": len(samples),
        "median_ms": statistics.median(samples) / 1_000_000,
        "p95_ms": ordered[p95_index] / 1_000_000,
    }


def _case(
    native_operation: Callable[[], bytes],
    python_operation: Callable[[], bytes],
    iterations: int,
) -> dict[str, object]:
    expected = python_operation()
    actual = native_operation()
    if actual != expected:
        raise RuntimeError("Native RGBA benchmark failed bit-exact validation.")
    for _ in range(3):
        native_operation()
        python_operation()
    python_samples = _measure(python_operation, iterations)
    native_samples = _measure(native_operation, iterations)
    python_median = statistics.median(python_samples)
    native_median = statistics.median(native_samples)
    return {
        "bit_exact": True,
        "python": _summary(python_samples),
        "native": _summary(native_samples),
        "median_speedup": (
            None if native_median == 0 else python_median / native_median
        ),
    }


def run(width: int, height: int, iterations: int) -> dict[str, object]:
    native = importlib.import_module("_mohan_accel")
    required = (
        "alpha_over_rgba",
        "crossfade_rgba",
        "composite_region_rgba",
    )
    missing = tuple(name for name in required if not hasattr(native, name))
    if missing:
        raise RuntimeError(
            "Built native module is missing RGBA operations: " + ", ".join(missing)
        )
    pixels = width * height
    target = bytes((17, 37, 59, 211)) * pixels
    source = bytes((181, 97, 43, 127)) * pixels
    approved = b"\x01" * pixels
    identity = b"\x00" * pixels
    occlusion = b"\x00" * pixels
    parallel_threshold = getattr(
        native,
        "__rgba_parallel_pixel_threshold__",
        None,
    )
    return {
        "schema": 2,
        "width": width,
        "height": height,
        "pixels": pixels,
        "iterations": iterations,
        "parallel_pixel_threshold": parallel_threshold,
        "rayon_enabled": parallel_threshold is not None,
        "simd_claimed": False,
        "operations": {
            "alpha_over_rgba": _case(
                lambda: native.alpha_over_rgba(target, source),
                lambda: alpha_over_rgba_python(target, source),
                iterations,
            ),
            "crossfade_rgba": _case(
                lambda: native.crossfade_rgba(target, source, 32_768),
                lambda: crossfade_rgba_python(target, source, 32_768),
                iterations,
            ),
            "composite_region_rgba": _case(
                lambda: native.composite_region_rgba(
                    target,
                    width,
                    height,
                    source,
                    width,
                    height,
                    0,
                    0,
                    approved,
                    identity,
                    (occlusion,),
                ),
                lambda: composite_region_rgba_python(
                    target,
                    width,
                    height,
                    source,
                    width,
                    height,
                    0,
                    0,
                    approved,
                    identity,
                    (occlusion,),
                ),
                iterations,
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--height", type=int, default=256)
    parser.add_argument("--iterations", type=int, default=9)
    arguments = parser.parse_args()
    if arguments.width <= 0 or arguments.height <= 0 or arguments.iterations <= 0:
        parser.error("width, height, and iterations must be positive")
    print(
        json.dumps(
            run(arguments.width, arguments.height, arguments.iterations),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
