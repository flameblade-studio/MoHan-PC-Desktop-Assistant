from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.behavior_director import SemanticEmotion
lazy from presentation.companion_speech_runtime import _semantic_emotion_for_state


def test_attentive_gentle_safety_are_mapped() -> None:
    assert _semantic_emotion_for_state("attentive_front") is SemanticEmotion.ATTENTIVE
    assert _semantic_emotion_for_state("gentle_smile_front") is SemanticEmotion.GENTLE
    assert _semantic_emotion_for_state("protective_front") is SemanticEmotion.SAFETY


def test_existing_emotions_still_map() -> None:
    assert _semantic_emotion_for_state("happy") is SemanticEmotion.HAPPY
    assert _semantic_emotion_for_state("worried_front") is SemanticEmotion.WORRIED
    assert _semantic_emotion_for_state("reminder") is SemanticEmotion.REMINDER
    assert _semantic_emotion_for_state("mock_scold") is SemanticEmotion.ANGRY


def test_unknown_state_falls_back_to_neutral() -> None:
    assert _semantic_emotion_for_state("idle") is SemanticEmotion.NEUTRAL
    assert _semantic_emotion_for_state("speaking") is SemanticEmotion.NEUTRAL
    assert _semantic_emotion_for_state("") is SemanticEmotion.NEUTRAL


def run() -> None:
    test_attentive_gentle_safety_are_mapped()
    test_existing_emotions_still_map()
    test_unknown_state_falls_back_to_neutral()
    print("EMOTION_SEMANTIC_MAPPING_OK")


if __name__ == "__main__":
    run()
