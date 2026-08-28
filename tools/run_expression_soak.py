from __future__ import annotations

lazy import argparse
lazy import ctypes
lazy import json
lazy import os
lazy import random
lazy import sys
lazy import time
lazy from ctypes import wintypes
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import (
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_FRAMES,
)
lazy from presentation.companion_window import CompanionWindow
lazy from infrastructure.db import StudioDB

ARBITER_SOURCES = (
    "ambient",
    "fallback",
    "ai_tag",
    "conversation",
    "user_direct",
    "reminder",
    "safety",
)
VISEMES = ("A", "I", "U", "E", "O")
CHARACTER_SCALES = (75, 100, 125, 150, 180)
BASELINE_ITERATION = 500
MAX_AUDIT_ENTRIES = 256


class ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


@dataclass(slots=True)
class SoakState:
    app: QApplication
    window: CompanionWindow
    expressions: tuple[str, ...]
    started: float
    deadline: float
    iterations: int = 0
    accepted: int = 0
    rejected: int = 0
    baseline_memory: int = 0
    peak_memory: int = 0


def working_set_bytes() -> int:
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    get_memory = kernel32.K32GetProcessMemoryInfo
    get_memory.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    )
    get_memory.restype = wintypes.BOOL
    process = kernel32.GetCurrentProcess()
    ok = get_memory(process, ctypes.byref(counters), counters.cb)
    return int(counters.WorkingSetSize) if ok else 0


def _prepare_database(temp_dir: str) -> None:
    db_path = Path(temp_dir) / "YanJianStudio" / "MoHan" / "mohan.db"
    db = StudioDB(db_path)
    db.set_setting("tts_enabled", False)
    db.close()


def _prepare_window(app: QApplication) -> CompanionWindow:
    window = CompanionWindow(startup_speech=False)
    window.show()
    app.processEvents()
    for timer in window.findChildren(QTimer):
        timer.stop()
    return window


def _new_state(
    app: QApplication,
    window: CompanionWindow,
    minutes: float,
) -> SoakState:
    started = time.monotonic()
    state = SoakState(
        app=app,
        window=window,
        expressions=tuple(EXPRESSION_POSES),
        started=started,
        deadline=started + max(0.0, minutes) * 60.0,
    )
    state.peak_memory = working_set_bytes()
    return state


def _request_expression(state: SoakState) -> tuple[str, float]:
    expression = random.choice(state.expressions)
    intensity = random.random()
    decision = state.window.expression_arbiter.request(
        expression,
        source=random.choice(ARBITER_SOURCES),
        intensity=intensity,
    )
    state.accepted += int(decision.accepted)
    state.rejected += int(not decision.accepted)
    if decision.accepted:
        state.window.set_state(
            expression,
            source="conversation",
            intensity=intensity,
            force=True,
        )
    return expression, intensity


def _exercise_expression_rendering(
    window: CompanionWindow,
    expression: str,
    intensity: float,
) -> None:
    pose = EXPRESSION_POSES[expression]
    frames = EXPRESSION_SPEECH_FRAMES[expression]
    window.state = "speaking"
    window.speech_closed_expression = expression
    window.speech_pose_suffix = window._pose_suffix(pose)
    window.speech_gesture_expression = expression
    window.speech_mid_expression = frames["mid"]
    window.speech_open_expression = frames["open"]
    window._mouth_aperture_pixmap(
        random.choice((frames["mid"], frames["open"], frames["round"])),
        intensity,
    )
    window._blink_composite(window.expression_pixmaps[expression], expression)
    window.gaze_target_x = random.uniform(-1.0, 1.0)
    window.gaze_target_y = random.uniform(-1.0, 1.0)
    window._attention_tick()
    window._physics_tick()


def _assert_overlay_geometry(window: CompanionWindow) -> None:
    assert all(
        layer.geometry() == window.character.geometry()
        for layer in (
            window.expression_overlay,
            window.sleeve_left_overlay,
            window.sleeve_right_overlay,
            window.hair_left_overlay,
            window.hair_right_overlay,
            window.physics_overlay,
            window.face_overlay,
            window.eye_overlay,
        )
    )


def _exercise_character_scale(window: CompanionWindow, iteration: int) -> None:
    if iteration % 997 != 0:
        return
    window._apply_character_scale(
        random.choice(CHARACTER_SCALES),
        preserve_anchor=False,
    )
    _assert_overlay_geometry(window)


def _exercise_realtime_speech(window: CompanionWindow) -> None:
    window._realtime_speaking(True)
    window._realtime_assistant_text(
        "主上，妾在聽。[[MOHAN_EMOTION:attentive:0.55]]"
    )
    window._audio_viseme_cue(random.random(), random.choice(VISEMES))
    window._realtime_speaking(False)
    window._complete_realtime_speaking_stop()


def _exercise_speech(
    window: CompanionWindow,
    iteration: int,
    expression: str,
) -> None:
    if iteration % 173 == 0:
        _exercise_realtime_speech(window)
    elif iteration % 211 == 0 and not window.speech_playing:
        window.speak("主上，這是壓力測試中的回覆。", expression)
        window._complete_speech_audio_finished()


def _sample_runtime(state: SoakState) -> None:
    if state.iterations % 23 == 0:
        state.app.processEvents()
    if state.iterations == BASELINE_ITERATION:
        state.baseline_memory = working_set_bytes()
    if state.iterations % 100 == 0:
        state.peak_memory = max(state.peak_memory, working_set_bytes())


def _run_iteration(state: SoakState) -> None:
    expression, intensity = _request_expression(state)
    _exercise_expression_rendering(state.window, expression, intensity)
    _exercise_character_scale(state.window, state.iterations)
    _exercise_speech(state.window, state.iterations, expression)
    _sample_runtime(state)
    assert state.window.current_expression in state.window.expression_pixmaps
    state.iterations += 1


def _should_continue(state: SoakState, steps: int) -> bool:
    if steps > 0:
        return state.iterations < steps
    return time.monotonic() < state.deadline


def _result(state: SoakState) -> dict[str, object]:
    state.app.processEvents()
    final_memory = working_set_bytes()
    if state.baseline_memory <= 0:
        state.baseline_memory = final_memory
    memory_growth = max(0, final_memory - state.baseline_memory)
    assert memory_growth < 128 * 1024 * 1024
    assert len(state.window.expression_anchor_profiles) >= len(
        EXPRESSION_POSES
    )
    assert len(state.window.expression_arbiter.audit) <= MAX_AUDIT_ENTRIES
    state.window.close()
    state.window.db.close()
    state.app.processEvents()
    return {
        "iterations": state.iterations,
        "accepted": state.accepted,
        "rejected": state.rejected,
        "elapsed_seconds": round(time.monotonic() - state.started, 3),
        "working_set_growth_mb": round(memory_growth / 1024 / 1024, 2),
        "peak_working_set_mb": round(state.peak_memory / 1024 / 1024, 2),
        "result": "PASS",
    }


def run(minutes: float, steps: int, seed: int) -> dict[str, object]:
    random.seed(seed)
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        _prepare_database(temp_dir)
        app = QApplication.instance() or QApplication([])
        state = _new_state(app, _prepare_window(app), minutes)
        while _should_continue(state, steps):
            _run_iteration(state)
        return _result(state)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--minutes",
        type=float,
        default=0.0,
        help="Optional real-time duration; use --steps for deterministic release validation.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=20000,
        help="Deterministic accelerated iteration count used by default.",
    )
    parser.add_argument("--seed", type=int, default=20260730)
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.minutes, args.steps, args.seed),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
