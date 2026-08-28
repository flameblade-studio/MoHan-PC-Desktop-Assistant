from __future__ import annotations

lazy import argparse
lazy import json
lazy import os
lazy import statistics
lazy import subprocess
lazy import sys
lazy import time
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import (
    MOTION_FRAME_INTERVAL_MS,
    SPEECH_MOTION_RELEASE_LIMIT,
)
lazy from presentation.companion_window import CompanionWindow
lazy from infrastructure.db import StudioDB

VISEME_FRAME_BUDGET_MS = 30.0
MOTION_FRAME_BUDGET_MS = float(MOTION_FRAME_INTERVAL_MS)
RELEASE_CYCLE_P95_BUDGET_MS = 8.0
RELEASE_CYCLE_P99_BUDGET_MS = float(MOTION_FRAME_INTERVAL_MS)


class RecordingTimer:
    """Record requested deadlines without sleeping or pumping Qt events."""

    def __init__(self) -> None:
        self.intervals_ms: list[int] = []

    def start(self, interval_ms: int) -> None:
        self.intervals_ms.append(interval_ms)


def _percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * ratio))
    return ordered[index]


def _timing_summary(values_ms: list[float]) -> dict[str, float]:
    return {
        "mean_ms": round(statistics.fmean(values_ms), 6),
        "p95_ms": round(_percentile(values_ms, 0.95), 6),
        "p99_ms": round(_percentile(values_ms, 0.99), 6),
    }


def _create_window(
    temp_dir: str,
) -> tuple[QApplication, CompanionWindow]:
    os.environ["LOCALAPPDATA"] = temp_dir
    db_path = Path(temp_dir) / "YanJianStudio" / "MoHan" / "mohan.db"
    preflight = StudioDB(db_path)
    preflight.set_setting("tts_enabled", False)
    preflight.close()
    app = QApplication([])
    window = CompanionWindow(startup_speech=False)
    window.show()
    app.processEvents()
    for timer in window.findChildren(QTimer):
        timer.stop()
    return app, window


def _configure_audio_speech(window: CompanionWindow) -> None:
    window.idle_pose = "front"
    window.state = "speaking"
    window.speech_playing = True
    window.speech_pose_suffix = "_front"
    window.speech_closed_expression = "idle_front"
    window.speech_mid_expression = "mouth_mid_front"
    window.speech_open_expression = "speaking_front"
    window.speech_gesture_expression = None
    window.speech_motion_y = 0.0
    window.speech_motion_target_y = 0.0
    window.ambient_motion_x = 0.0
    window.ambient_motion_y = 0.0
    window.gesture_motion_x = 0.0
    window.gesture_motion_y = 0.0
    window._start_mouth_animation(audio_driven=True)


def _viseme_workload(
    window: CompanionWindow,
    iterations: int,
    *,
    measure: bool,
) -> tuple[list[float], dict[str, object]]:
    vowels = (
        *("A",) * 4,
        *("I",) * 4,
        *("U",) * 4,
        *("E",) * 4,
        *("O",) * 4,
        *("CONSONANT",) * 4,
    )
    levels = (0.42, 0.58, 0.72, 0.51)
    timings_ms: list[float] = []
    selected_counts: dict[str, int] = {}
    jaw_checksum = 0
    motion_checksum = 0
    position_checksum = 0
    for index in range(iterations):
        started = time.perf_counter()
        window._audio_viseme_cue(
            levels[index % len(levels)],
            vowels[index % len(vowels)],
        )
        if measure:
            timings_ms.append((time.perf_counter() - started) * 1000.0)
        selected = window.viseme_dynamics.current
        selected_counts[selected] = selected_counts.get(selected, 0) + 1
        jaw_checksum += round(
            window.viseme_dynamics.jaw_aperture * 1_000_000
        )
        motion_checksum += round(window.speech_motion_y * 1_000_000)
        position_checksum += window.character.pos().y()
    return timings_ms, {
        "iterations": iterations,
        "selected": dict(sorted(selected_counts.items())),
        "jaw": jaw_checksum,
        "motion": motion_checksum,
        "position": position_checksum,
    }


def _benchmark_visemes(
    window: CompanionWindow,
) -> tuple[dict[str, float], dict[str, object]]:
    _configure_audio_speech(window)
    _viseme_workload(window, 160, measure=False)
    _configure_audio_speech(window)
    timings_ms, checksum = _viseme_workload(window, 480, measure=True)
    summary = _timing_summary(timings_ms)
    assert summary["mean_ms"] < VISEME_FRAME_BUDGET_MS / 2, summary
    assert summary["p95_ms"] < VISEME_FRAME_BUDGET_MS, summary
    return summary, checksum


def _motion_workload(
    window: CompanionWindow,
    iterations: int,
    *,
    measure: bool,
) -> tuple[list[float], dict[str, int]]:
    timings_ms: list[float] = []
    motion_checksum = 0
    position_checksum = 0
    for index in range(iterations):
        if index % 2:
            window.speech_motion_y = 0.0
            window.speech_motion_target_y = -4.0
        else:
            window.speech_motion_y = -4.0
            window.speech_motion_target_y = 0.0
        started = time.perf_counter()
        window._motion_tick()
        if measure:
            timings_ms.append((time.perf_counter() - started) * 1000.0)
        motion_checksum += round(window.speech_motion_y * 1_000_000)
        position_checksum += window.character.pos().y()
    return timings_ms, {
        "iterations": iterations,
        "motion": motion_checksum,
        "position": position_checksum,
    }


def _benchmark_motion_frames(
    window: CompanionWindow,
) -> tuple[dict[str, float], dict[str, int]]:
    window.state = "speaking"
    window.ambient_motion_x = 0.0
    window.ambient_motion_y = 0.0
    window.gesture_motion_x = 0.0
    window.gesture_motion_y = 0.0
    _motion_workload(window, 240, measure=False)
    timings_ms, checksum = _motion_workload(window, 1_200, measure=True)
    summary = _timing_summary(timings_ms)
    assert summary["mean_ms"] < MOTION_FRAME_BUDGET_MS / 4, summary
    assert summary["p99_ms"] < MOTION_FRAME_BUDGET_MS, summary
    return summary, checksum


def _release_cycle(
    window: CompanionWindow,
    attempts_attribute: str,
    scale: float,
) -> tuple[int, int, int, int]:
    timer = RecordingTimer()
    window.character_scale = scale
    window.state = "speaking"
    window.audio_driven_mouth = True
    window.mouth_closing = False
    window.ambient_motion_y = 0.0
    window.speech_motion_y = -4.0
    window.speech_motion_target_y = -4.0
    setattr(window, attempts_attribute, 0)
    window._begin_speech_motion_release()
    max_attempts = 0
    motion_ticks = 0
    for calls in range(1, SPEECH_MOTION_RELEASE_LIMIT + 2):
        motion_before_wait = window.speech_motion_y
        ambient_before_wait = window.ambient_motion_y
        composed_before_wait = ambient_before_wait + motion_before_wait
        pending = window._wait_for_speech_motion_release(
            timer,  # type: ignore[arg-type]
            attempts_attribute,
        )
        if pending:
            assert window.speech_motion_y == motion_before_wait, (
                "finish wait must not advance the independently timed motion"
            )
            assert window.ambient_motion_y == ambient_before_wait
        else:
            assert window.speech_motion_y == 0.0
            assert (
                window.ambient_motion_y + window.speech_motion_y
                == composed_before_wait
            ), "completion must transfer ownership without moving a pixel"
        max_attempts = max(
            max_attempts,
            int(getattr(window, attempts_attribute, 0)),
        )
        if not pending:
            break
        window._motion_tick()
        motion_ticks += 1
    else:
        raise AssertionError("speech motion release exceeded its hard limit")
    assert timer.intervals_ms
    assert all(
        interval == MOTION_FRAME_INTERVAL_MS
        for interval in timer.intervals_ms
    )
    assert calls <= SPEECH_MOTION_RELEASE_LIMIT
    assert window.speech_motion_y == 0.0
    assert getattr(window, attempts_attribute) == 0
    assert motion_ticks == len(timer.intervals_ms)
    return calls, max_attempts, len(timer.intervals_ms), motion_ticks


def _assert_hard_release_limit(
    window: CompanionWindow,
    attempts_attribute: str,
) -> None:
    timer = RecordingTimer()
    window.character_scale = 1.8
    window.ambient_motion_y = 0.0
    window.speech_motion_y = -4.0
    window.speech_motion_target_y = 0.0
    setattr(window, attempts_attribute, 0)
    motion_ticks = 0
    with patch.object(window, "_motion_tick", return_value=None) as motion_tick:
        for calls in range(1, SPEECH_MOTION_RELEASE_LIMIT + 2):
            motion_before_wait = window.speech_motion_y
            ambient_before_wait = window.ambient_motion_y
            composed_before_wait = ambient_before_wait + motion_before_wait
            pending = window._wait_for_speech_motion_release(
                timer,  # type: ignore[arg-type]
                attempts_attribute,
            )
            if not pending:
                assert window.speech_motion_y == 0.0
                assert (
                    window.ambient_motion_y + window.speech_motion_y
                    == composed_before_wait
                ), "hard-limit transfer must not move a pixel"
                break
            assert window.speech_motion_y == motion_before_wait, (
                "finish wait must remain a pure observer before the hard limit"
            )
            assert window.ambient_motion_y == ambient_before_wait
            window._motion_tick()
            motion_ticks += 1
        else:
            raise AssertionError(
                "non-converging speech motion escaped the hard limit"
            )
    assert motion_tick.call_count == motion_ticks
    assert calls == SPEECH_MOTION_RELEASE_LIMIT
    assert len(timer.intervals_ms) == SPEECH_MOTION_RELEASE_LIMIT - 1
    assert motion_ticks == SPEECH_MOTION_RELEASE_LIMIT - 1
    assert all(
        interval == MOTION_FRAME_INTERVAL_MS
        for interval in timer.intervals_ms
    )
    assert window.speech_motion_y == 0.0
    assert getattr(window, attempts_attribute) == 0


def _benchmark_release_wait(
    window: CompanionWindow,
) -> tuple[dict[str, float], dict[str, int]]:
    attributes = (
        "speech_motion_release_attempts",
        "realtime_motion_release_attempts",
    )
    scales = (0.75, 1.0, 1.8)
    assert window.motion_timer.interval() == MOTION_FRAME_INTERVAL_MS
    timings_ms: list[float] = []
    calls_checksum = 0
    timer_starts_checksum = 0
    motion_ticks_checksum = 0
    max_calls = 0
    max_attempts = 0
    for index in range(180):
        started = time.perf_counter()
        calls, attempts, timer_starts, motion_ticks = _release_cycle(
            window,
            attributes[index % len(attributes)],
            scales[index % len(scales)],
        )
        timings_ms.append((time.perf_counter() - started) * 1000.0)
        calls_checksum += calls
        timer_starts_checksum += timer_starts
        motion_ticks_checksum += motion_ticks
        max_calls = max(max_calls, calls)
        max_attempts = max(max_attempts, attempts)

    for attempts_attribute in attributes:
        _assert_hard_release_limit(window, attempts_attribute)

    summary = _timing_summary(timings_ms)
    assert summary["p95_ms"] < RELEASE_CYCLE_P95_BUDGET_MS, summary
    assert summary["p99_ms"] < RELEASE_CYCLE_P99_BUDGET_MS, summary
    assert max_calls <= SPEECH_MOTION_RELEASE_LIMIT
    assert max_attempts < SPEECH_MOTION_RELEASE_LIMIT
    return summary, {
        "cycles": len(timings_ms),
        "calls": calls_checksum,
        "timer_starts": timer_starts_checksum,
        "motion_ticks": motion_ticks_checksum,
        "max_calls": max_calls,
        "max_attempts": max_attempts,
        "hard_limit": SPEECH_MOTION_RELEASE_LIMIT,
        "scheduled_interval_ms": MOTION_FRAME_INTERVAL_MS,
    }


def _worker(expected_jit: bool) -> dict[str, object]:
    jit = getattr(sys, "_jit", None)
    if not jit or not jit.is_available():
        raise RuntimeError("this audit requires a JIT-capable Python 3.15 build")
    if jit.is_enabled() is not expected_jit:
        raise RuntimeError(
            f"PYTHON_JIT was not applied: expected {expected_jit}, "
            f"observed {jit.is_enabled()}"
        )

    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        app, window = _create_window(temp_dir)
        try:
            viseme_timing, viseme_checksum = _benchmark_visemes(window)
            window.mouth_visual_timer.stop()
            motion_timing, motion_checksum = _benchmark_motion_frames(window)
            release_timing, release_checksum = _benchmark_release_wait(window)
        finally:
            window.close()
            window.db.close()
            app.processEvents()
    return {
        "jit_enabled": jit.is_enabled(),
        "timing": {
            "viseme_50hz": viseme_timing,
            "motion_16ms": motion_timing,
            "release_cycle": release_timing,
        },
        "checksum": {
            "viseme_50hz": viseme_checksum,
            "motion_16ms": motion_checksum,
            "release_cycle": release_checksum,
        },
    }


def _run_mode(mode: str) -> dict[str, object]:
    environment = os.environ.copy()
    environment["PYTHON_JIT"] = mode
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment.pop("MOHAN_DISABLE_JIT", None)
    environment.pop("MOHAN_JIT_REEXEC", None)
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--expected-jit",
            mode,
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode:
        raise RuntimeError(
            f"PYTHON_JIT={mode} audit failed\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--expected-jit", choices=("0", "1"))
    arguments = parser.parse_args()
    if arguments.worker:
        if arguments.expected_jit is None:
            parser.error("--worker requires --expected-jit")
        print(json.dumps(_worker(arguments.expected_jit == "1")))
        return

    jit = getattr(sys, "_jit", None)
    if not jit or not jit.is_available():
        raise RuntimeError("this audit requires a JIT-capable Python 3.15 build")
    jit_off = _run_mode("0")
    jit_on = _run_mode("1")
    assert jit_off["jit_enabled"] is False
    assert jit_on["jit_enabled"] is True
    assert jit_off["checksum"] == jit_on["checksum"], (
        "JIT changed the deterministic post-speech motion result",
        jit_off["checksum"],
        jit_on["checksum"],
    )
    print(
        "POST_SPEECH_MOTION_PERFORMANCE_OK "
        + json.dumps(
            {
                "python": sys.version.split()[0],
                "jit_off": jit_off["timing"],
                "jit_on": jit_on["timing"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
