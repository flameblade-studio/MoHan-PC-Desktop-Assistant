from __future__ import annotations

lazy import os
lazy import random
lazy import struct
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from companion_animation_contract import EXPRESSION_SPEECH_FRAMES
lazy from companion_window import CompanionWindow
lazy from lip_sync import (
    VISEME_CHANGE_TRANSITION_SECONDS,
    VISEME_CLOSE_TRANSITION_SECONDS,
    VISEME_CUES_PER_SECOND,
    VISEME_OPEN_TRANSITION_SECONDS,
    infer_vowel_pcm16,
)

EXPECTED_VOWEL_CHANGE_LATENCY = 0.101
EXPECTED_SUSTAIN_CHANGE_LATENCY = 0.061
EXPECTED_CONSONANT_LATENCY = 0.021
BLINK_REMAINDER = 4


class CueDriver:
    def __init__(self, window: CompanionWindow, clock: list[float]) -> None:
        self.window = window
        self.clock = clock

    def __call__(self, vowel: str, level: float = 0.60) -> None:
        self.window._audio_viseme_cue(level, vowel)
        self.clock[0] += 1.0 / VISEME_CUES_PER_SECOND


def _assert_runtime_source_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    runtime_sources = {
        name: (project_root / name).read_text(encoding="utf-8")
        for name in (
            "app.py",
            "integrations/speech.py",
            "integrations/realtime_voice.py",
        )
    }
    combined_runtime = "\n".join(runtime_sources.values())
    assert "_audio_mouth_cue" not in combined_runtime
    assert "mouth_cue = Signal" not in combined_runtime
    assert ".mouth_cue.emit" not in combined_runtime
    assert "rate // 25" not in combined_runtime
    assert "24000 // 25" not in combined_runtime
    assert ".start(140)" not in combined_runtime


def _assert_pcm_inference_contract() -> None:
    # A high zero-crossing unvoiced segment is a consonant transition, not a
    # fabricated vowel. Silence must remain an explicit closed-mouth state.
    noisy = b"".join(
        struct.pack("<h", 12000 if index % 2 else -12000)
        for index in range(960)
    )
    assert infer_vowel_pcm16(noisy, 24000)[1] == "CONSONANT"
    assert infer_vowel_pcm16(bytes(1920), 24000)[1] == "CLOSED"


def _configure_expression_speech(window: CompanionWindow) -> None:
    expression = "happy"
    frames = EXPRESSION_SPEECH_FRAMES[expression]
    window.state = "speaking"
    window.speech_pose_suffix = ""
    window.speech_closed_expression = expression
    window.speech_mid_expression = frames["mid"]
    window.speech_open_expression = frames["open"]
    window.speech_gesture_expression = expression


def _assert_initial_open(window: CompanionWindow, cue: CueDriver) -> None:
    cue("A")
    assert window.viseme_dynamics.current == "E"
    assert window.mouth_transition_duration == VISEME_OPEN_TRANSITION_SECONDS
    for _ in range(3):
        cue("A")
        assert window.viseme_dynamics.current == "E"
    cue("A")
    assert window.viseme_dynamics.current == "A"
    assert cue.clock[0] <= EXPECTED_VOWEL_CHANGE_LATENCY
    assert window.mouth_transition_duration == VISEME_CHANGE_TRANSITION_SECONDS


def _assert_sustain_and_vowel_change(
    window: CompanionWindow,
    cue: CueDriver,
) -> None:
    # Sustaining A must not restart the interpolation every 20 ms.
    started_at = window.mouth_transition_started
    for _ in range(4):
        cue("A")
    assert window.viseme_dynamics.current == "A"
    assert window.mouth_transition_started == started_at
    vowel_change_started = cue.clock[0]
    cue("O")
    cue("O")
    assert window.viseme_dynamics.current == "A"
    cue("O")
    assert window.viseme_dynamics.current == "O"
    assert cue.clock[0] - vowel_change_started <= EXPECTED_SUSTAIN_CHANGE_LATENCY


def _assert_consonant_and_close(
    window: CompanionWindow,
    cue: CueDriver,
) -> None:
    # A consonant reacts after the current vowel hold; silence closes naturally.
    for _ in range(4):
        cue("O")
    consonant_started = cue.clock[0]
    cue("CONSONANT", 0.35)
    assert window.viseme_dynamics.current == "CONSONANT"
    assert cue.clock[0] - consonant_started <= EXPECTED_CONSONANT_LATENCY
    cue("CLOSED", 0.0)
    assert window.viseme_dynamics.current == "CONSONANT"
    cue("CLOSED", 0.0)
    assert window.viseme_dynamics.current == "CLOSED"
    assert window.mouth_transition_duration == VISEME_CLOSE_TRANSITION_SECONDS


def _random_level(vowel: str, generator: random.Random) -> float:
    if vowel == "CLOSED":
        return 0.0
    if vowel == "CONSONANT":
        return 0.34
    return generator.uniform(0.16, 0.72)


def _assert_long_mixed_stream(
    window: CompanionWindow,
    cue: CueDriver,
) -> None:
    # Overlapping blinks catch stale state and physics loss after rapid changes.
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
        cue(vowel, _random_level(vowel, generator))
        if index % 113 == 0 and not window.speech_blinking:
            window._blink()
        if window.speech_blinking and index % 113 == BLINK_REMAINDER:
            window._finish_speaking_blink(window.blink_generation)
        assert window.viseme_dynamics.current in valid_states
        assert not window.speech_visual_pixmap.isNull()
        assert window.active_physics_pose == "cheek"
        assert not window.hair_left_overlay.isHidden()
        assert not window.sleeve_left_overlay.isHidden()


def _assert_viseme_timing(window: CompanionWindow) -> None:
    clock = [0.0]
    with patch("time.perf_counter", side_effect=lambda: clock[0]):
        window._start_mouth_animation(audio_driven=True)
        cue = CueDriver(window, clock)
        _assert_initial_open(window, cue)
        _assert_sustain_and_vowel_change(window, cue)
        _assert_consonant_and_close(window, cue)
        _assert_long_mixed_stream(window, cue)


def _assert_window_visemes(temp_dir: str) -> None:
    os.environ["LOCALAPPDATA"] = temp_dir
    app = QApplication([])
    window = CompanionWindow(startup_speech=False)
    window.show()
    app.processEvents()
    for timer in window.findChildren(QTimer):
        timer.stop()
    _configure_expression_speech(window)
    _assert_viseme_timing(window)
    window.close()
    window.db.close()
    app.processEvents()


def run() -> None:
    _assert_runtime_source_contract()
    _assert_pcm_inference_contract()
    with TemporaryDirectory() as temp_dir:
        _assert_window_visemes(temp_dir)
    print("VISEME_SYNC_CONTRACT_OK")


if __name__ == "__main__":
    run()
