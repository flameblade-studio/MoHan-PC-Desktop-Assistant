from __future__ import annotations

import asyncio
lazy import importlib
lazy import random
lazy import threading
lazy import time
lazy from types import ModuleType

lazy import pytest

lazy from application.native_acceleration import NativeAcceleration
lazy from application.native_rgba_acceleration import (
    NativeRgbaAcceleration,
    alpha_over_rgba_python,
    crossfade_rgba_python,
)
lazy from domain import lip_sync, pcm_audio
lazy from domain.python315_concurrency import ThreadPoolExecutor

NATIVE = importlib.import_module("_mohan_accel")
RGBA_SIDE = 512
RGBA_PIXELS = RGBA_SIDE * RGBA_SIDE


def _pcm(samples: list[int]) -> bytes:
    return b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples)


def _pcm_frame(seed: int) -> bytes:
    generator = random.Random(seed)
    return _pcm([generator.randint(-12_000, 12_000) for _ in range(480)])


def _rgba_frame(pixel: tuple[int, int, int, int]) -> bytes:
    return bytes(pixel) * RGBA_PIXELS


def test_native_boundaries_match_deterministic_empty_and_random_inputs() -> None:
    for seed in range(12):
        frame = _pcm_frame(2026081400 + seed)
        assert NATIVE.analyze_pcm16(frame) == pytest.approx(
            lip_sync.analyze_pcm16(frame),
            rel=1e-12,
            abs=1e-12,
        )
        native_level, native_vowel = NATIVE.infer_vowel_pcm16(frame, 24_000)
        python_level, python_vowel = lip_sync.infer_vowel_pcm16(frame, 24_000)
        assert native_level == pytest.approx(
            python_level,
            rel=1e-12,
            abs=1e-12,
        )
        assert native_vowel == python_vowel
        assert NATIVE.scale_pcm16(frame, 0.73) == pcm_audio.scale_pcm16(
            frame,
            0.73,
        )

    assert NATIVE.analyze_pcm16(b"") == lip_sync.analyze_pcm16(b"")
    assert NATIVE.scale_pcm16(b"", 1.0) == b""
    assert NATIVE.alpha_over_rgba(b"", b"") == b""
    assert NATIVE.crossfade_rgba(b"", b"", 0) == b""


def test_pcm_50_hz_and_rgba_parallel_pressure_complete_without_deadlock() -> None:
    pcm = _pcm_frame(20260814)
    target = _rgba_frame((17, 37, 59, 211))
    source = _rgba_frame((181, 97, 43, 127))
    expected_pcm = lip_sync.infer_vowel_pcm16(pcm, 24_000)
    expected_rgba = crossfade_rgba_python(target, source, 32_768)
    progress = 0
    progress_lock = threading.Lock()
    stop = threading.Event()

    def heartbeat() -> None:
        nonlocal progress
        while not stop.is_set():
            with progress_lock:
                progress += 1
            time.sleep(0)

    def pcm_work() -> tuple[float, str]:
        result = (0.0, "A")
        for _ in range(250):
            result = NATIVE.infer_vowel_pcm16(pcm, 24_000)
        return result

    def rgba_work() -> bytes:
        result = b""
        for _ in range(8):
            result = NATIVE.crossfade_rgba(target, source, 32_768)
        return result

    monitor = threading.Thread(target=heartbeat, daemon=True)
    monitor.start()
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(pcm_work) for _ in range(4)]
        futures.extend(executor.submit(rgba_work) for _ in range(2))
        results = [future.result(timeout=30) for future in futures]
    elapsed = time.monotonic() - started
    stop.set()
    monitor.join(timeout=2)

    assert elapsed < 30
    assert results[:4] == [expected_pcm] * 4
    assert results[4:] == [expected_rgba] * 2
    assert progress > 0


def test_native_work_allows_an_asyncio_loop_to_keep_advancing() -> None:
    pcm = _pcm_frame(2026081402)
    target = _rgba_frame((23, 47, 71, 223))
    source = _rgba_frame((197, 101, 53, 119))

    async def exercise() -> int:
        ticks = 0
        finished = asyncio.Event()

        async def heartbeat() -> None:
            nonlocal ticks
            while not finished.is_set():
                ticks += 1
                await asyncio.sleep(0)

        async def native_work() -> None:
            await asyncio.gather(
                asyncio.to_thread(
                    lambda: [NATIVE.infer_vowel_pcm16(pcm, 24_000) for _ in range(400)]
                ),
                asyncio.to_thread(
                    lambda: [
                        NATIVE.alpha_over_rgba(target, source) for _ in range(12)
                    ]
                ),
            )

        pulse = asyncio.create_task(heartbeat())
        try:
            await asyncio.wait_for(native_work(), timeout=30)
        finally:
            finished.set()
            await pulse
        return ticks

    assert asyncio.run(exercise()) > 0


def test_pcm_fault_disables_only_one_operation_while_others_stay_native() -> None:
    module = ModuleType("_mohan_accel")
    calls = {"scale": 0, "analyze": 0}

    def fail_scale(_data: bytes, _factor: float) -> bytes:
        calls["scale"] += 1
        raise RuntimeError("synthetic native PCM fault")

    def analyze(data: bytes) -> tuple[float, float]:
        calls["analyze"] += 1
        return lip_sync.analyze_pcm16(data)

    module.scale_pcm16 = fail_scale
    module.analyze_pcm16 = analyze
    accelerator = NativeAcceleration(module_loader=lambda _name: module)
    frame = _pcm_frame(2026081403)

    assert accelerator.scale_pcm16(frame, 0.5) == pcm_audio.scale_pcm16(frame, 0.5)
    assert accelerator.scale_pcm16(frame, 0.5) == pcm_audio.scale_pcm16(frame, 0.5)
    assert accelerator.analyze_pcm16(frame) == lip_sync.analyze_pcm16(frame)
    assert calls == {"scale": 1, "analyze": 1}
    status = accelerator.status()
    assert status.disabled_operations == ("scale_pcm16",)
    assert status.operation_failures == (("scale_pcm16", 1),)


def test_rgba_fault_disables_only_one_operation_and_uses_stable_fallback() -> None:
    module = ModuleType("_mohan_accel")
    calls = {"crossfade": 0, "alpha": 0}

    def fail_crossfade(
        _first: bytes,
        _second: bytes,
        _weight: int,
    ) -> bytes:
        calls["crossfade"] += 1
        raise RuntimeError("synthetic native RGBA fault")

    def alpha(target: bytes, source: bytes) -> bytes:
        calls["alpha"] += 1
        return alpha_over_rgba_python(target, source)

    module.crossfade_rgba = fail_crossfade
    module.alpha_over_rgba = alpha
    accelerator = NativeRgbaAcceleration(module_loader=lambda _name: module)
    target = bytes((17, 37, 59, 211)) * 64
    source = bytes((181, 97, 43, 127)) * 64
    expected = crossfade_rgba_python(target, source, 32_768)

    assert accelerator.crossfade_rgba(target, source, 32_768) == expected
    assert accelerator.crossfade_rgba(target, source, 32_768) == expected
    assert accelerator.alpha_over_rgba(target, source) == alpha_over_rgba_python(
        target,
        source,
    )
    assert calls == {"crossfade": 1, "alpha": 1}
    status = accelerator.status()
    assert status.disabled_operations == ("crossfade_rgba",)
    assert status.verified_operations == ("alpha_over_rgba",)
