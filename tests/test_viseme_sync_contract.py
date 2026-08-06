from __future__ import annotations

import os
import random
import struct
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import CompanionWindow, EXPRESSION_SPEECH_FRAMES
from lip_sync import (
    VISEME_CUES_PER_SECOND,
    VISEME_CHANGE_TRANSITION_SECONDS,
    VISEME_CLOSE_TRANSITION_SECONDS,
    VISEME_OPEN_TRANSITION_SECONDS,
    infer_vowel_pcm16,
)


def run() -> None:
    project_root = Path(__file__).resolve().parents[1]
    runtime_sources = {
        name: (project_root / name).read_text(encoding="utf-8")
        for name in ("app.py", "speech.py", "realtime_voice.py")
    }
    combined_runtime = "\n".join(runtime_sources.values())
    assert "_audio_mouth_cue" not in combined_runtime
    assert "mouth_cue = Signal" not in combined_runtime
    assert ".mouth_cue.emit" not in combined_runtime
    assert "rate // 25" not in combined_runtime
    assert "24000 // 25" not in combined_runtime
    assert ".start(140)" not in combined_runtime

    # A high zero-crossing unvoiced segment is a consonant transition, not a
    # fabricated vowel. Silence must remain an explicit closed-mouth state.
    noisy = b"".join(
        struct.pack("<h", 12000 if index % 2 else -12000)
        for index in range(960)
    )
    assert infer_vowel_pcm16(noisy, 24000)[1] == "CONSONANT"
    assert infer_vowel_pcm16(bytes(1920), 24000)[1] == "CLOSED"

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
        window.speech_pose_suffix = ""
        window.speech_closed_expression = expression
        window.speech_mid_expression = frames["mid"]
        window.speech_open_expression = frames["open"]
        window.speech_gesture_expression = expression

        clock = [0.0]
        with patch("app.time.perf_counter", side_effect=lambda: clock[0]):
            window._start_mouth_animation(audio_driven=True)

            def cue(vowel: str, level: float = 0.60) -> None:
                window._audio_viseme_cue(level, vowel)
                clock[0] += 1.0 / VISEME_CUES_PER_SECOND

            cue("A")
            assert window.current_viseme == "E"
            assert (
                window.mouth_transition_duration
                == VISEME_OPEN_TRANSITION_SECONDS
            )
            cue("A")
            assert window.current_viseme == "E"
            cue("A")
            assert window.current_viseme == "E"
            cue("A")
            assert window.current_viseme == "E"
            cue("A")
            assert window.current_viseme == "A"
            assert clock[0] <= 0.101
            assert (
                window.mouth_transition_duration
                == VISEME_CHANGE_TRANSITION_SECONDS
            )

            # Sustaining A must not restart the interpolation every 20 ms.
            started_at = window.mouth_transition_started
            for _ in range(4):
                cue("A")
            assert window.current_viseme == "A"
            assert window.mouth_transition_started == started_at

            vowel_change_started = clock[0]
            cue("O")
            cue("O")
            assert window.current_viseme == "O"
            assert clock[0] - vowel_change_started <= 0.041

            # A consonant can react within one 20 ms cue after the current
            # vowel's minimum hold, then sustained silence closes the mouth.
            cue("O")
            cue("O")
            cue("O")
            cue("O")
            consonant_started = clock[0]
            cue("CONSONANT", 0.35)
            assert window.current_viseme == "CONSONANT"
            assert clock[0] - consonant_started <= 0.021
            cue("CLOSED", 0.0)
            assert window.current_viseme == "CONSONANT"
            cue("CLOSED", 0.0)
            assert window.current_viseme == "CLOSED"
            assert (
                window.mouth_transition_duration
                == VISEME_CLOSE_TRANSITION_SECONDS
            )

            # Long mixed phoneme stream with overlapping blinks. This catches
            # stale-state restoration, invalid transitions and physics layers
            # disappearing only after many rapid changes.
            generator = random.Random(20260731)
            valid_states = {
                "A",
                "I",
                "U",
                "E",
                "O",
                "CONSONANT",
                "CLOSED",
            }
            for index in range(2_000):
                vowel = generator.choices(
                    tuple(valid_states),
                    weights=(16, 13, 10, 18, 12, 7, 8),
                    k=1,
                )[0]
                level = (
                    0.0
                    if vowel == "CLOSED"
                    else 0.34
                    if vowel == "CONSONANT"
                    else generator.uniform(0.16, 0.72)
                )
                cue(vowel, level)
                if index % 113 == 0 and not window.speech_blinking:
                    window._blink()
                if window.speech_blinking and index % 113 == 4:
                    window._finish_speaking_blink(
                        window.speech_current_expression,
                        window.blink_generation,
                    )
                assert window.current_viseme in valid_states
                assert not window.speech_visual_pixmap.isNull()
                assert window.active_physics_pose == "cheek"
                assert not window.hair_left_overlay.isHidden()
                assert not window.sleeve_left_overlay.isHidden()

        window.close()
        window.db.close()
        app.processEvents()
    print("VISEME_SYNC_CONTRACT_OK")


if __name__ == "__main__":
    run()
