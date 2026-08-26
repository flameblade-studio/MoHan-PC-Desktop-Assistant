from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.proactive_companion_runtime import _memory_check_in_text
lazy from presentation.companion_speech_emotion import _emotion_rate_adjustment


def test_emotion_rate_adjustment_slows_shy_and_speeds_happy() -> None:
    assert _emotion_rate_adjustment("shy") == -1
    assert _emotion_rate_adjustment("shy_cute_front") == -1
    assert _emotion_rate_adjustment("gentle_smile_front") == -1
    assert _emotion_rate_adjustment("worried") == -1
    assert _emotion_rate_adjustment("happy") == 1
    assert _emotion_rate_adjustment("proud_front") == 1
    assert _emotion_rate_adjustment("eureka_front") == 1


def test_emotion_rate_adjustment_is_neutral_for_plain_speech() -> None:
    assert _emotion_rate_adjustment("speaking") == 0
    assert _emotion_rate_adjustment("idle") == 0
    assert _emotion_rate_adjustment("") == 0


def test_memory_check_in_text_weaves_topic_per_language() -> None:
    zh = _memory_check_in_text("zh-TW", "主上", "寫報告")
    assert "寫報告" in zh and "主上" in zh
    en = _memory_check_in_text("en", "Master", "the report")
    assert "the report" in en and "Master" in en
    ja = _memory_check_in_text("ja-JP", "主上", "レポート")
    assert "レポート" in ja


def test_memory_check_in_text_rejects_empty_topic() -> None:
    assert _memory_check_in_text("zh-TW", "主上", "") == ""
    assert _memory_check_in_text("zh-TW", "主上", "   ") == ""


def run() -> None:
    test_emotion_rate_adjustment_slows_shy_and_speeds_happy()
    test_emotion_rate_adjustment_is_neutral_for_plain_speech()
    test_memory_check_in_text_weaves_topic_per_language()
    test_memory_check_in_text_rejects_empty_topic()
    print("AFFECTIVE_PROSODY_AND_TOPICS_OK")


if __name__ == "__main__":
    run()
