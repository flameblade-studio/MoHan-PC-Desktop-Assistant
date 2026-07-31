from __future__ import annotations

import argparse
import ctypes
import json
import os
import random
import sys
import time
from ctypes import wintypes
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import (
    CompanionWindow,
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_FRAMES,
)
from db import StudioDB


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
    ok = get_memory(
        process,
        ctypes.byref(counters),
        counters.cb,
    )
    return int(counters.WorkingSetSize) if ok else 0


def run(minutes: float, steps: int, seed: int) -> dict[str, object]:
    random.seed(seed)
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        db_path = (
            Path(temp_dir)
            / "YanJianStudio"
            / "MoHan"
            / "mohan.db"
        )
        db = StudioDB(db_path)
        db.set_setting("tts_enabled", False)
        db.close()

        app = QApplication.instance() or QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        for timer in window.findChildren(QTimer):
            timer.stop()

        expressions = tuple(EXPRESSION_POSES)
        started = time.monotonic()
        deadline = started + max(0.0, minutes) * 60.0
        iterations = 0
        accepted = 0
        rejected = 0
        baseline_memory = 0
        peak_memory = working_set_bytes()

        while (
            iterations < steps
            if steps > 0
            else time.monotonic() < deadline
        ):
            expression = random.choice(expressions)
            intensity = random.random()
            decision = window.expression_arbiter.request(
                expression,
                source=random.choice(
                    (
                        "ambient",
                        "fallback",
                        "ai_tag",
                        "conversation",
                        "user_direct",
                        "reminder",
                        "safety",
                    )
                ),
                intensity=intensity,
            )
            accepted += int(decision.accepted)
            rejected += int(not decision.accepted)
            if decision.accepted:
                window.set_state(
                    expression,
                    source="conversation",
                    intensity=intensity,
                    force=True,
                )

            pose = EXPRESSION_POSES[expression]
            suffix = window._pose_suffix(pose)
            frames = EXPRESSION_SPEECH_FRAMES[expression]
            window.state = "speaking"
            window.speech_closed_expression = expression
            window.speech_pose_suffix = suffix
            window.speech_gesture_expression = expression
            window.speech_mid_expression = frames["mid"]
            window.speech_open_expression = frames["open"]
            window._mouth_aperture_pixmap(
                random.choice(
                    (
                        frames["mid"],
                        frames["open"],
                        frames["round"],
                    )
                ),
                intensity,
            )
            window._blink_composite(
                window.expression_pixmaps[expression],
                expression,
            )
            window.gaze_target_x = random.uniform(-1.0, 1.0)
            window.gaze_target_y = random.uniform(-1.0, 1.0)
            window._attention_tick()
            window._physics_tick()
            if iterations % 997 == 0:
                window._apply_character_scale(
                    random.choice((75, 100, 125, 150, 180)),
                    preserve_anchor=False,
                )
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

            if iterations % 173 == 0:
                window._realtime_speaking(True)
                window._realtime_assistant_text(
                    "主上，妾在聽。"
                    "[[MOHAN_EMOTION:attentive:0.55]]"
                )
                window._audio_viseme_cue(
                    random.random(),
                    random.choice(("A", "I", "U", "E", "O")),
                )
                window._realtime_speaking(False)
                window._complete_realtime_speaking_stop()
            elif iterations % 211 == 0 and not window.speech_playing:
                window.speak(
                    "主上，這是壓力測試中的回覆。",
                    expression,
                )
                window._complete_speech_audio_finished()

            if iterations % 23 == 0:
                app.processEvents()
            if iterations == 500:
                baseline_memory = working_set_bytes()
            if iterations % 100 == 0:
                peak_memory = max(peak_memory, working_set_bytes())
            assert window.current_expression in window.expression_pixmaps
            iterations += 1

        app.processEvents()
        final_memory = working_set_bytes()
        if baseline_memory <= 0:
            baseline_memory = final_memory
        memory_growth = max(0, final_memory - baseline_memory)
        assert memory_growth < 128 * 1024 * 1024
        assert len(window.expression_anchor_profiles) >= len(
            EXPRESSION_POSES
        )
        assert len(window.expression_arbiter.audit) <= 256
        window.close()
        window.db.close()
        app.processEvents()
        return {
            "iterations": iterations,
            "accepted": accepted,
            "rejected": rejected,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "working_set_growth_mb": round(
                memory_growth / 1024 / 1024,
                2,
            ),
            "peak_working_set_mb": round(
                peak_memory / 1024 / 1024,
                2,
            ),
            "result": "PASS",
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--minutes",
        type=float,
        default=240.0,
        help="Real-time soak duration; default is four hours.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=0,
        help="Use an accelerated fixed iteration count instead of duration.",
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
