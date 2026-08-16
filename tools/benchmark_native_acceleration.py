from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import importlib
lazy import json
lazy import math
lazy import statistics
lazy import sys
lazy import time
lazy from collections.abc import Callable
lazy from pathlib import Path
lazy from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from domain import lip_sync, pcm_audio


def _frame() -> bytes:
    samples = (
        round(
            4_200 * math.sin(2 * math.pi * 800 * index / 24_000)
            + 2_400 * math.sin(2 * math.pi * 1_200 * index / 24_000)
        )
        for index in range(480)
    )
    return b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples)


def _stereo_frame(mono_frame: bytes) -> bytes:
    samples = (
        int.from_bytes(mono_frame[index : index + 2], "little", signed=True)
        for index in range(0, len(mono_frame), 2)
    )
    stereo_samples = (
        channel_sample
        for mono_sample in samples
        for channel_sample in (mono_sample, mono_sample)
    )
    return b"".join(
        sample.to_bytes(2, "little", signed=True) for sample in stereo_samples
    )


def _jit_status() -> dict[str, bool]:
    jit = getattr(sys, "_jit", None)
    return {
        "available": bool(jit is not None and jit.is_available()),
        "enabled": bool(jit is not None and jit.is_enabled()),
    }


def _normalize_result(result: object) -> object:
    if isinstance(result, float):
        return round(result, 12)
    if isinstance(result, bytes):
        return len(result), hashlib.sha256(result).hexdigest()
    if isinstance(result, tuple):
        return tuple(_normalize_result(value) for value in result)
    if isinstance(result, list):
        return tuple(_normalize_result(value) for value in result)
    if isinstance(result, pcm_audio.Pcm16RateState):
        return result.tail_frame, result.phase
    return result


def _measure(
    operation: Callable[[], Any], iterations: int, rounds: int
) -> dict[str, object]:
    times: list[float] = []
    checksum: object | None = None
    for _ in range(rounds):
        started = time.perf_counter()
        current = None
        for _index in range(iterations):
            current = operation()
        times.append(time.perf_counter() - started)
        current = _normalize_result(current)
        if checksum is not None and current != checksum:
            raise RuntimeError(
                "benchmark operation produced a non-deterministic result"
            )
        checksum = current
    return {
        "iterations": iterations,
        "median_seconds": round(statistics.median(times), 9),
        "checksum": repr(checksum),
    }


def _warm_up(operation: Callable[[], Any], iterations: int) -> object:
    current = None
    for _index in range(iterations):
        current = operation()
    return _normalize_result(current)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5_000)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--warmup-iterations", type=int, default=500)
    arguments = parser.parse_args()
    if (
        arguments.iterations < 1
        or arguments.rounds < 1
        or arguments.warmup_iterations < 1
    ):
        parser.error("iterations, rounds, and warmup iterations must be positive")
    try:
        native = importlib.import_module("_mohan_accel")
    except ModuleNotFoundError:
        print(
            json.dumps(
                {
                    "result": "NATIVE_ACCELERATOR_NOT_BUILT",
                    "measurements": {},
                },
                indent=2,
            )
        )
        return 2

    frame = _frame()
    stereo = _stereo_frame(frame)
    operations = {
        "analyze_pcm16": (
            lambda: lip_sync.analyze_pcm16(frame),
            lambda: native.analyze_pcm16(frame),
        ),
        "infer_vowel_pcm16": (
            lambda: lip_sync.infer_vowel_pcm16(frame, 24_000),
            lambda: native.infer_vowel_pcm16(frame, 24_000),
        ),
        "scale_pcm16": (
            lambda: pcm_audio.scale_pcm16(frame, 0.72),
            lambda: native.scale_pcm16(frame, 0.72),
        ),
        "stereo_to_mono_pcm16": (
            lambda: pcm_audio.stereo_to_mono_pcm16(stereo),
            lambda: native.stereo_to_mono_pcm16(stereo),
        ),
        "rate_convert_pcm16": (
            lambda: pcm_audio.rate_convert_pcm16(frame, 1, 24_000, 48_000),
            lambda: native.rate_convert_pcm16(frame, 1, 24_000, 48_000),
        ),
    }
    measurements: dict[str, object] = {}
    for name, (python_operation, native_operation) in operations.items():
        python_warmup = _warm_up(python_operation, arguments.warmup_iterations)
        native_warmup = _warm_up(native_operation, arguments.warmup_iterations)
        if python_warmup != native_warmup:
            raise RuntimeError(f"native {name} changed the functional result")
        python_result = _measure(
            python_operation, arguments.iterations, arguments.rounds
        )
        native_result = _measure(
            native_operation, arguments.iterations, arguments.rounds
        )
        if python_result["checksum"] != native_result["checksum"]:
            raise RuntimeError(f"native {name} changed the functional result")
        measurements[name] = {
            "python": python_result,
            "native": native_result,
            "relative_speedup": round(
                python_result["median_seconds"] / native_result["median_seconds"],
                4,
            ),
        }
    print(
        json.dumps(
            {
                "result": "NATIVE_ACCELERATOR_BENCHMARK_OK",
                "native_version": getattr(native, "__version__", "unknown"),
                "python_version": sys.version,
                "jit": _jit_status(),
                "workload": {
                    "sample_rate_hz": 24_000,
                    "frame_samples": 480,
                    "frame_duration_ms": 20,
                    "cue_rate_hz": 50,
                    "warmup_iterations": arguments.warmup_iterations,
                },
                "measurements": measurements,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
