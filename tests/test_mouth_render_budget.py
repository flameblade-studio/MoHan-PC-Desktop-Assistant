from __future__ import annotations

lazy import os
lazy import statistics
lazy import sys
lazy import time
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from companion_animation_contract import EXPRESSION_SPEECH_FRAMES
lazy from companion_window import CompanionWindow


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * ratio))
    return ordered[index]


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        for timer in window.findChildren(QTimer):
            timer.stop()

        expression = "happy"
        frames = EXPRESSION_SPEECH_FRAMES[expression]
        window.state = "speaking"
        window.audio_driven_mouth = True
        window.speech_pose_suffix = ""
        window.speech_closed_expression = expression
        window.speech_mid_expression = frames["mid"]
        window.speech_open_expression = frames["open"]
        window.speech_gesture_expression = expression
        window.current_expression = frames["mid"]
        window.mouth_transition_from = window._mouth_aperture_pixmap(
            frames["mid"],
            0.48,
        )
        window.mouth_transition_to = window._mouth_aperture_pixmap(
            frames["open"],
            0.90,
        )
        window.mouth_transition_duration = 0.055
        window.mouth_visual_timer.start()

        timings_ms: list[float] = []
        for index in range(600):
            window.speech_blinking = index % 17 in {0, 1}
            window.mouth_transition_started = (
                time.perf_counter() - 0.0275
            )
            started = time.perf_counter()
            window._render_audio_mouth_transition()
            timings_ms.append(
                (time.perf_counter() - started) * 1000.0
            )

        mean_ms = statistics.fmean(timings_ms)
        p95_ms = percentile(timings_ms, 0.95)
        p99_ms = percentile(timings_ms, 0.99)
        assert mean_ms < 8.0, mean_ms
        assert p95_ms < 16.0, p95_ms
        assert p99_ms < 24.0, p99_ms
        assert not window.character.pixmap().isNull()

        window.close()
        window.db.close()
        app.processEvents()
    print(
        "MOUTH_RENDER_BUDGET_OK "
        f"mean_ms={mean_ms:.3f} "
        f"p95_ms={p95_ms:.3f} "
        f"p99_ms={p99_ms:.3f}"
    )


if __name__ == "__main__":
    run()
