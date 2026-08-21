"""Measure integrated Rust acceleration using deterministic synthetic buffers."""

from __future__ import annotations

# Eager by design: asyncio.to_thread and its concurrent.futures lookup share
# module state where PEP 810 proxies are not API-compatible.
import asyncio
lazy import argparse
lazy import ctypes
lazy import gc
lazy import hashlib
lazy import importlib
lazy import json
lazy import operator
lazy import random
lazy import statistics
lazy import sys
lazy import threading
lazy import time
lazy import tracemalloc
lazy import zipfile
lazy from collections.abc import Callable
lazy from itertools import pairwise
lazy from pathlib import Path
lazy from types import ModuleType
lazy from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from domain.python315_concurrency import ThreadPoolExecutor
lazy from application.native_acceleration import NativeAcceleration
lazy from application.native_rgba_acceleration import (
    NativeRgbaAcceleration,
    alpha_over_rgba_python,
    composite_region_rgba_python,
    crossfade_rgba_python,
)
lazy from domain import lip_sync

SHA256_HEX_LENGTH = 64
SHA256_RAW_LENGTH = 32
FLOAT_PAIR_LENGTH = 2
FLOAT_TOLERANCE = 1e-12
MIN_SCHEDULE_TICKS = 2

EVIDENCE_PATH = Path("docs/release-evidence/native-acceleration-local.json")
PCM_SAMPLE_RATE = 24_000
PCM_FRAME_SAMPLES = 480
RGBA_SMALL_SIDE = 16
RGBA_LARGE_SIDE = 1_254
SCHEDULE_RATE_HZ = 50
SCHEDULE_INTERVAL_NS = 1_000_000_000 // SCHEDULE_RATE_HZ
NATIVE_EXTENSION_MODULE = "_mohan_accel._mohan_accel"
NATIVE_WHEEL_MEMBER = "_mohan_accel/_mohan_accel.pyd"
NATIVE_OPERATIONS = (
    "analyze_pcm16",
    "infer_vowel_pcm16",
    "scale_pcm16",
    "stereo_to_mono_pcm16",
    "rate_convert_pcm16",
    "alpha_over_rgba",
    "crossfade_rgba",
    "composite_region_rgba",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_sha256(value: str) -> str:
    normalized = value.strip().casefold()
    try:
        raw = bytes.fromhex(normalized)
    except ValueError as error:
        raise RuntimeError("Expected validation wheel SHA-256 is invalid.") from error
    if len(normalized) != SHA256_HEX_LENGTH or len(raw) != SHA256_RAW_LENGTH:
        raise RuntimeError("Expected validation wheel SHA-256 is invalid.")
    return normalized


def _loaded_native_binary(
    native: ModuleType,
    extension_module: ModuleType | None = None,
) -> tuple[Path, str, ModuleType]:
    extension = extension_module or importlib.import_module(NATIVE_EXTENSION_MODULE)
    package_file = getattr(native, "__file__", None)
    extension_file = getattr(extension, "__file__", None)
    if not package_file or not extension_file:
        raise RuntimeError("The loaded native package has no auditable file path.")
    try:
        package_path = Path(package_file).resolve(strict=True)
        extension_path = Path(extension_file).resolve(strict=True)
    except OSError as error:
        raise RuntimeError("The loaded native package path is not readable.") from error
    if extension_path.suffix.casefold() != ".pyd":
        raise RuntimeError("The loaded native implementation is not a Windows .pyd.")
    import_root = package_path.parent.parent
    try:
        portable_path = extension_path.relative_to(import_root).as_posix()
    except ValueError as error:
        raise RuntimeError(
            "The loaded native binary is outside its Python import root."
        ) from error
    if portable_path != NATIVE_WHEEL_MEMBER:
        raise RuntimeError("The loaded native binary has an unexpected portable path.")
    return extension_path, portable_path, extension


def _wheel_native_binary(wheel: Path) -> tuple[str, str, int]:
    try:
        with zipfile.ZipFile(wheel) as archive:
            matches = tuple(
                info
                for info in archive.infolist()
                if not info.is_dir() and info.filename == NATIVE_WHEEL_MEMBER
            )
            if len(matches) != 1:
                raise RuntimeError(
                    "Validation wheel must contain exactly one native binary."
                )
            member = matches[0]
            digest = hashlib.sha256()
            with archive.open(member) as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
    except (OSError, zipfile.BadZipFile) as error:
        raise RuntimeError("Validation wheel is unreadable or invalid.") from error
    return member.filename, digest.hexdigest(), member.file_size


def _native_provenance(
    native: ModuleType,
    *,
    validation_wheel: Path,
    expected_wheel_sha256: str,
    extension_module: ModuleType | None = None,
) -> dict[str, object]:
    expected_sha256 = _normalized_sha256(expected_wheel_sha256)
    try:
        wheel = validation_wheel.resolve(strict=True)
    except OSError as error:
        raise RuntimeError("Validation wheel does not exist.") from error
    if not wheel.is_file():
        raise RuntimeError("Validation wheel is not a regular file.")
    native_version = str(native.__version__)
    expected_prefix = f"mohan_accel-{native_version}-"
    if wheel.suffix.casefold() != ".whl" or not wheel.name.startswith(expected_prefix):
        raise RuntimeError(
            "Validation wheel filename does not match the native version."
        )
    observed_wheel_sha256 = _sha256_file(wheel)
    if observed_wheel_sha256 != expected_sha256:
        raise RuntimeError("Validation wheel SHA-256 does not match the CLI value.")

    extension_path, portable_path, extension = _loaded_native_binary(
        native,
        extension_module,
    )
    loaded_sha256 = _sha256_file(extension_path)
    member_path, member_sha256, member_size = _wheel_native_binary(wheel)
    if loaded_sha256 != member_sha256:
        raise RuntimeError("Loaded native binary does not match the validation wheel.")
    return {
        "loaded_native_binary": {
            "module": extension.__name__,
            "path": portable_path,
            "path_kind": "python-import-root-relative",
            "sha256": loaded_sha256,
            "size_bytes": extension_path.stat().st_size,
        },
        "validation_wheel": {
            "filename": wheel.name,
            "sha256": observed_wheel_sha256,
            "cli_expected_sha256": expected_sha256,
            "sha256_matches_cli": True,
            "native_binary_member": member_path,
            "native_binary_sha256": member_sha256,
            "native_binary_size_bytes": member_size,
            "native_binary_matches_loaded": True,
        },
    }


def _python_runtime() -> str:
    info = sys.version_info
    suffix = "" if info.releaselevel == "final" else f"{info.releaselevel}{info.serial}"
    return f"{info.major}.{info.minor}.{info.micro}{suffix}"


def _jit_enabled() -> bool:
    jit = getattr(sys, "_jit", None)
    return bool(jit is not None and jit.is_available() and jit.is_enabled())


def _pcm_frame(seed: int = 20260814) -> bytes:
    generator = random.Random(seed)
    samples = [generator.randint(-12_000, 12_000) for _ in range(PCM_FRAME_SAMPLES)]
    return b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples)


def _rgba_frame(side: int, pixel: tuple[int, int, int, int]) -> bytes:
    return bytes(pixel) * (side * side)


def _measure(
    operation: Callable[[], object],
    *,
    iterations: int,
    warmup: int,
) -> dict[str, float | int]:
    for _ in range(warmup):
        operation()
    samples: list[int] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        operation()
        samples.append(time.perf_counter_ns() - started)
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))
    return {
        "iterations": iterations,
        "median_ms": round(statistics.median(samples) / 1_000_000, 6),
        "p95_ms": round(ordered[p95_index] / 1_000_000, 6),
    }


def _comparison(
    python_operation: Callable[[], object],
    native_operation: Callable[[], object],
    *,
    iterations: int,
    warmup: int,
    equivalent: Callable[[object, object], bool] | None = None,
) -> dict[str, object]:
    expected = python_operation()
    actual = native_operation()
    comparator = equivalent or operator.eq
    if not comparator(actual, expected):
        raise RuntimeError("Native and Python results differ for a synthetic workload.")
    python_summary = _measure(
        python_operation,
        iterations=iterations,
        warmup=warmup,
    )
    native_summary = _measure(
        native_operation,
        iterations=iterations,
        warmup=warmup,
    )
    python_median = float(python_summary["median_ms"])
    native_median = float(native_summary["median_ms"])
    return {
        "equivalent": True,
        "python_jit": python_summary,
        "rust": native_summary,
        "median_speedup": (
            None if native_median == 0 else round(python_median / native_median, 4)
        ),
    }


def _float_pair_close(actual: object, expected: object) -> bool:
    if not isinstance(actual, tuple) or not isinstance(expected, tuple):
        return False
    if len(actual) != FLOAT_PAIR_LENGTH or len(expected) != FLOAT_PAIR_LENGTH:
        return False
    return all(
        abs(float(left) - float(right)) <= FLOAT_TOLERANCE
        for left, right in zip(actual, expected, strict=True)
    )


def _viseme_close(actual: object, expected: object) -> bool:
    if not isinstance(actual, tuple) or not isinstance(expected, tuple):
        return False
    return (
        actual[1] == expected[1] and abs(float(actual[0]) - float(expected[0])) <= FLOAT_TOLERANCE
    )


def _performance_evidence(
    native: ModuleType,
    *,
    small_iterations: int,
    large_iterations: int,
) -> dict[str, object]:
    pcm = _pcm_frame()
    small_target = _rgba_frame(RGBA_SMALL_SIDE, (17, 37, 59, 211))
    small_source = _rgba_frame(RGBA_SMALL_SIDE, (181, 97, 43, 127))
    large_target = _rgba_frame(RGBA_LARGE_SIDE, (17, 37, 59, 211))
    large_source = _rgba_frame(RGBA_LARGE_SIDE, (181, 97, 43, 127))
    large_pixels = RGBA_LARGE_SIDE * RGBA_LARGE_SIDE
    approved = b"\x01" * large_pixels
    identity = b"\x00" * large_pixels
    occlusion = b"\x00" * large_pixels
    threshold = int(native.__rgba_parallel_pixel_threshold__)
    large_warmup = 1

    return {
        "pcm_empty_analysis": _comparison(
            lambda: lip_sync.analyze_pcm16(b""),
            lambda: native.analyze_pcm16(b""),
            iterations=small_iterations,
            warmup=50,
            equivalent=_float_pair_close,
        ),
        "pcm_20ms_analysis": _comparison(
            lambda: lip_sync.analyze_pcm16(pcm),
            lambda: native.analyze_pcm16(pcm),
            iterations=small_iterations,
            warmup=50,
            equivalent=_float_pair_close,
        ),
        "pcm_20ms_viseme": _comparison(
            lambda: lip_sync.infer_vowel_pcm16(pcm, PCM_SAMPLE_RATE),
            lambda: native.infer_vowel_pcm16(pcm, PCM_SAMPLE_RATE),
            iterations=small_iterations,
            warmup=50,
            equivalent=_viseme_close,
        ),
        "rgba_16x16_alpha": _comparison(
            lambda: alpha_over_rgba_python(small_target, small_source),
            lambda: native.alpha_over_rgba(small_target, small_source),
            iterations=small_iterations,
            warmup=50,
        ),
        "rgba_1254x1254_alpha": _comparison(
            lambda: alpha_over_rgba_python(large_target, large_source),
            lambda: native.alpha_over_rgba(large_target, large_source),
            iterations=large_iterations,
            warmup=large_warmup,
        ),
        "rgba_1254x1254_crossfade": _comparison(
            lambda: crossfade_rgba_python(large_target, large_source, 32_768),
            lambda: native.crossfade_rgba(large_target, large_source, 32_768),
            iterations=large_iterations,
            warmup=large_warmup,
        ),
        "rgba_1254x1254_region": _comparison(
            lambda: composite_region_rgba_python(
                large_target,
                RGBA_LARGE_SIDE,
                RGBA_LARGE_SIDE,
                large_source,
                RGBA_LARGE_SIDE,
                RGBA_LARGE_SIDE,
                0,
                0,
                approved,
                identity,
                (occlusion,),
            ),
            lambda: native.composite_region_rgba(
                large_target,
                RGBA_LARGE_SIDE,
                RGBA_LARGE_SIDE,
                large_source,
                RGBA_LARGE_SIDE,
                RGBA_LARGE_SIDE,
                0,
                0,
                approved,
                identity,
                (occlusion,),
            ),
            iterations=large_iterations,
            warmup=large_warmup,
        ),
        "rgba_parallel_threshold": {
            "pixels": threshold,
            "large_workload_pixels": large_pixels,
            "large_workload_crosses_threshold": large_pixels >= threshold,
        },
    }


def _thread_progress_evidence(native: ModuleType) -> bool:
    pcm = _pcm_frame(2026081402)
    side = 512
    target = _rgba_frame(side, (23, 47, 71, 223))
    source = _rgba_frame(side, (197, 101, 53, 119))
    progress = 0
    progress_lock = threading.Lock()
    stop = threading.Event()

    def heartbeat() -> None:
        nonlocal progress
        while not stop.is_set():
            with progress_lock:
                progress += 1
            time.sleep(0)

    def pcm_work() -> None:
        for _ in range(250):
            native.infer_vowel_pcm16(pcm, PCM_SAMPLE_RATE)

    def rgba_work() -> None:
        for _ in range(8):
            native.crossfade_rgba(target, source, 32_768)

    monitor = threading.Thread(target=heartbeat, daemon=True)
    monitor.start()
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(pcm_work) for _ in range(4)]
        futures.extend(executor.submit(rgba_work) for _ in range(2))
        for future in futures:
            future.result(timeout=30)
    stop.set()
    monitor.join(timeout=2)

    return progress > 0


async def _asyncio_progress(native: ModuleType) -> int:
    pcm = _pcm_frame(2026081402)
    side = 512
    target = _rgba_frame(side, (23, 47, 71, 223))
    source = _rgba_frame(side, (197, 101, 53, 119))
    ticks = 0
    finished = asyncio.Event()

    async def pulse() -> None:
        nonlocal ticks
        while not finished.is_set():
            ticks += 1
            await asyncio.sleep(0)

    def pcm_work() -> None:
        for _ in range(250):
            native.infer_vowel_pcm16(pcm, PCM_SAMPLE_RATE)

    def rgba_work() -> None:
        for _ in range(8):
            native.crossfade_rgba(target, source, 32_768)

    pulse_task = asyncio.create_task(pulse())
    try:
        await asyncio.wait_for(
            asyncio.gather(
                asyncio.to_thread(pcm_work),
                asyncio.to_thread(rgba_work),
            ),
            timeout=30,
        )
    finally:
        finished.set()
        await pulse_task
    return ticks


def _concurrency_evidence(native: ModuleType) -> dict[str, object]:
    thread_progressed = _thread_progress_evidence(native)

    async def exercise_loop() -> int:
        return await _asyncio_progress(native)

    loop_ticks = asyncio.run(exercise_loop())
    return {
        "completed_without_deadlock": True,
        "fixed_worker_count": 6,
        "python_heartbeat_progressed": thread_progressed,
        "asyncio_loop_progressed": loop_ticks > 0,
    }


def _timing_summary_ms(samples_ns: list[int]) -> dict[str, float | int]:
    if not samples_ns:
        raise ValueError("Timing evidence requires at least one sample.")
    ordered = sorted(samples_ns)
    p95_index = min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))
    return {
        "samples": len(samples_ns),
        "median_ms": round(statistics.median(samples_ns) / 1_000_000, 6),
        "p95_ms": round(ordered[p95_index] / 1_000_000, 6),
        "maximum_ms": round(ordered[-1] / 1_000_000, 6),
    }


def _sleep_until(deadline_ns: int) -> None:
    while True:
        remaining_ns = deadline_ns - time.perf_counter_ns()
        if remaining_ns <= 0:
            return
        time.sleep(remaining_ns / 1_000_000_000)


def _schedule_50hz_evidence(
    native: ModuleType,
    *,
    tick_count: int,
) -> dict[str, object]:
    if tick_count < MIN_SCHEDULE_TICKS:
        raise ValueError("50 Hz schedule evidence requires at least two ticks.")
    pcm = _pcm_frame(2026081405)
    expected = lip_sync.infer_vowel_pcm16(pcm, PCM_SAMPLE_RATE)
    dispatches_ns: list[int] = []
    lateness_ns: list[int] = []
    processing_ns: list[int] = []
    run_started_ns = time.perf_counter_ns()
    completed_ns = run_started_ns

    for tick in range(1, tick_count + 1):
        deadline_ns = run_started_ns + tick * SCHEDULE_INTERVAL_NS
        _sleep_until(deadline_ns)
        dispatched_ns = time.perf_counter_ns()
        actual = native.infer_vowel_pcm16(pcm, PCM_SAMPLE_RATE)
        completed_ns = time.perf_counter_ns()
        if not _viseme_close(actual, expected):
            raise RuntimeError("50 Hz schedule run changed the native viseme result.")
        dispatches_ns.append(dispatched_ns)
        lateness_ns.append(max(0, dispatched_ns - deadline_ns))
        processing_ns.append(completed_ns - dispatched_ns)

    intervals_ns = [current - previous for previous, current in pairwise(dispatches_ns)]
    observed_span_ns = dispatches_ns[-1] - dispatches_ns[0]
    observed_rate_hz = (
        None
        if observed_span_ns <= 0
        else round((tick_count - 1) * 1_000_000_000 / observed_span_ns, 6)
    )
    return {
        "evidence_kind": "descriptive-local-scheduler-observation",
        "completed": True,
        "hard_realtime_claimed": False,
        "requested_rate_hz": SCHEDULE_RATE_HZ,
        "target_interval_ms": SCHEDULE_INTERVAL_NS / 1_000_000,
        "tick_count": tick_count,
        "workload": "One deterministic 20 ms PCM viseme inference per tick.",
        "clock": "time.perf_counter_ns",
        "scheduler": "Absolute deadlines with time.sleep; no busy waiting.",
        "observed_rate_hz": observed_rate_hz,
        "elapsed_ms": round((completed_ns - run_started_ns) / 1_000_000, 6),
        "observed_intervals_ms": _timing_summary_ms(intervals_ns),
        "deadline_lateness_ms": _timing_summary_ms(lateness_ns),
        "native_processing_ms": _timing_summary_ms(processing_ns),
    }


def _fault_isolation_evidence() -> dict[str, object]:
    pcm_module = ModuleType("_mohan_accel")
    pcm_calls = 0

    def fail_pcm(_data: bytes, _factor: float) -> bytes:
        nonlocal pcm_calls
        pcm_calls += 1
        raise RuntimeError("synthetic native PCM fault")

    pcm_module.scale_pcm16 = fail_pcm
    pcm_acceleration = NativeAcceleration(module_loader=lambda _name: pcm_module)
    pcm = _pcm_frame(2026081403)
    pcm_acceleration.scale_pcm16(pcm, 0.5)
    pcm_acceleration.scale_pcm16(pcm, 0.5)

    rgba_module = ModuleType("_mohan_accel")
    rgba_calls = 0

    def fail_rgba(_target: bytes, _source: bytes, _weight: int) -> bytes:
        nonlocal rgba_calls
        rgba_calls += 1
        raise RuntimeError("synthetic native RGBA fault")

    rgba_module.crossfade_rgba = fail_rgba
    rgba_acceleration = NativeRgbaAcceleration(module_loader=lambda _name: rgba_module)
    target = bytes((17, 37, 59, 211)) * 64
    source = bytes((181, 97, 43, 127)) * 64
    rgba_acceleration.crossfade_rgba(target, source, 32_768)
    rgba_acceleration.crossfade_rgba(target, source, 32_768)

    return {
        "pcm_operation_disabled_after_first_fault": pcm_calls == 1,
        "pcm_native_calls_after_two_requests": pcm_calls,
        "pcm_observed_failure_count": dict(
            pcm_acceleration.status().operation_failures
        ).get("scale_pcm16", 0),
        "rgba_operation_disabled_after_first_fault": rgba_calls == 1,
        "rgba_native_calls_after_two_requests": rgba_calls,
        "rgba_disabled_operations": list(
            rgba_acceleration.status().disabled_operations
        ),
    }


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("page_fault_count", ctypes.c_ulong),
        ("peak_working_set_size", ctypes.c_size_t),
        ("working_set_size", ctypes.c_size_t),
        ("quota_peak_paged_pool_usage", ctypes.c_size_t),
        ("quota_paged_pool_usage", ctypes.c_size_t),
        ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
        ("quota_non_paged_pool_usage", ctypes.c_size_t),
        ("pagefile_usage", ctypes.c_size_t),
        ("peak_pagefile_usage", ctypes.c_size_t),
        ("private_usage", ctypes.c_size_t),
    ]


def _working_set_bytes() -> int | None:
    if sys.platform != "win32":
        return None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    get_memory = kernel32.K32GetProcessMemoryInfo
    get_memory.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(_ProcessMemoryCounters),
        ctypes.c_ulong,
    )
    get_memory.restype = ctypes.c_int
    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    ok = get_memory(
        kernel32.GetCurrentProcess(),
        ctypes.byref(counters),
        counters.cb,
    )
    return int(counters.working_set_size) if ok else None


def _memory_evidence(native: ModuleType) -> dict[str, object]:
    pcm = _pcm_frame(2026081404)
    side = 512
    target = _rgba_frame(side, (17, 37, 59, 211))
    source = _rgba_frame(side, (181, 97, 43, 127))
    gc.collect()
    rss_before = _working_set_bytes()
    tracemalloc.start()
    traced_before, _ = tracemalloc.get_traced_memory()
    for _ in range(1_000):
        native.infer_vowel_pcm16(pcm, PCM_SAMPLE_RATE)
    for _ in range(40):
        native.crossfade_rgba(target, source, 32_768)
    gc.collect()
    traced_after, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_after = _working_set_bytes()
    return {
        "pcm_iterations": 1_000,
        "rgba_iterations": 40,
        "traced_current_growth_bytes": traced_after - traced_before,
        "traced_peak_bytes": traced_peak,
        "rss_growth_bytes": (
            None if rss_before is None or rss_after is None else rss_after - rss_before
        ),
        "interpretation": "Short local observation only; not a long-duration soak test.",
    }


def _validate_safe_evidence(evidence: dict[str, Any]) -> None:
    serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    forbidden = (
        "D:\\",
        "C:\\",
        "Users\\",
        "USERNAME",
        "COMPUTERNAME",
        "token",
        "secret",
        "api_key",
    )
    if any(value.casefold() in serialized.casefold() for value in forbidden):
        raise RuntimeError(
            "Evidence contains forbidden identifying or secret material."
        )


def run(
    *,
    small_iterations: int,
    large_iterations: int,
    schedule_ticks: int,
    validation_wheel: Path,
    validation_wheel_sha256: str,
) -> dict[str, Any]:
    native = importlib.import_module("_mohan_accel")
    missing = [name for name in NATIVE_OPERATIONS if not hasattr(native, name)]
    if missing:
        raise RuntimeError("The native module is missing required operations.")
    if not _jit_enabled():
        raise RuntimeError("Run with PYTHON_JIT=1 to measure the Python JIT baseline.")
    provenance = _native_provenance(
        native,
        validation_wheel=validation_wheel,
        expected_wheel_sha256=validation_wheel_sha256,
    )
    performance = _performance_evidence(
        native,
        small_iterations=small_iterations,
        large_iterations=large_iterations,
    )
    concurrency = _concurrency_evidence(native)
    schedule_50hz = _schedule_50hz_evidence(
        native,
        tick_count=schedule_ticks,
    )
    fault_isolation = _fault_isolation_evidence()
    memory = _memory_evidence(native)
    release_ready = bool(
        concurrency["completed_without_deadlock"]
        and concurrency["python_heartbeat_progressed"]
        and concurrency["asyncio_loop_progressed"]
        and schedule_50hz["completed"]
        and fault_isolation["pcm_operation_disabled_after_first_fault"]
        and fault_isolation["rgba_operation_disabled_after_first_fault"]
    )
    evidence: dict[str, Any] = {
        "schema": 2,
        "result": "pass" if release_ready else "blocked",
        "scope": "Rust/PyO3 PCM, lip-sync, and RGBA local integration evidence",
        "data_policy": "Deterministic synthetic buffers only; no user audio or pixels.",
        "runtime": {
            "python": _python_runtime(),
            "jit_enabled": True,
            "native_module_version": str(native.__version__),
        },
        "provenance": provenance,
        "performance": performance,
        "concurrency": concurrency,
        "schedule_50hz": schedule_50hz,
        "fault_isolation": fault_isolation,
        "memory": memory,
        "limitations": [
            "Measurements are descriptive and are not unstable release thresholds.",
            "The 50 Hz schedule run is descriptive; Python and the host OS are not hard real-time.",
            "This is a short local observation, not a long-duration real-device soak.",
            "No physical microphone, camera, or private media was used.",
        ],
    }
    _validate_safe_evidence(evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--small-iterations", type=int, default=500)
    parser.add_argument("--large-iterations", type=int, default=3)
    parser.add_argument("--schedule-ticks", type=int, default=50)
    parser.add_argument("--validation-wheel", type=Path, required=True)
    parser.add_argument("--validation-wheel-sha256", required=True)
    parser.add_argument("--output", type=Path, default=EVIDENCE_PATH)
    arguments = parser.parse_args()
    if arguments.small_iterations <= 0 or arguments.large_iterations <= 0:
        parser.error("iteration counts must be positive")
    if arguments.schedule_ticks < MIN_SCHEDULE_TICKS:
        parser.error("schedule ticks must be at least two")
    if (
        arguments.output.is_absolute()
        or arguments.output.as_posix() != EVIDENCE_PATH.as_posix()
    ):
        parser.error(f"output must be the relative path {EVIDENCE_PATH.as_posix()}")
    validation_wheel = arguments.validation_wheel
    if not validation_wheel.is_absolute():
        validation_wheel = ROOT / validation_wheel
    evidence = run(
        small_iterations=arguments.small_iterations,
        large_iterations=arguments.large_iterations,
        schedule_ticks=arguments.schedule_ticks,
        validation_wheel=validation_wheel,
        validation_wheel_sha256=arguments.validation_wheel_sha256,
    )
    output = ROOT / arguments.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if evidence["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
