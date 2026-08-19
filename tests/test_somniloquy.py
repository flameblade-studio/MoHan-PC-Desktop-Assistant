from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.somniloquy import (
    SOMNILOQUY_TRIGGER_PROBABILITY,
    is_anachronistic,
    random_somniloquy,
    should_murmur,
    somniloquy_lines,
    validate_library,
)


def test_all_languages_have_dream_fragments() -> None:
    for language in ("zh-TW", "zh-CN", "en", "ja-JP"):
        lines = somniloquy_lines(language)
        assert len(lines) >= 5, language
        assert all(line.strip() for line in lines), language


def test_no_anachronistic_vocabulary_in_any_language() -> None:
    for language in ("zh-TW", "zh-CN", "en", "ja-JP"):
        offenders = validate_library(language)
        assert not offenders, (language, offenders)


def test_modern_markers_are_rejected() -> None:
    assert is_anachronistic("哈囉，主人")
    assert is_anachronistic("hello master")
    assert is_anachronistic("你好，主人")
    assert not is_anachronistic("汴京的煙雨……主上，赤焰劍冷……")


def test_random_somniloquy_stays_in_library() -> None:
    lines = somniloquy_lines("zh-TW")
    for _ in range(20):
        assert random_somniloquy("zh-TW") in lines


def test_murmur_probability_is_very_low() -> None:
    # The trigger probability must stay tiny so the companion never chatters
    # constantly during idle.
    assert SOMNILOQUY_TRIGGER_PROBABILITY < 0.01
    # A deterministic RNG below the threshold always murmurs; above never does.
    import random as _random
    always = _random.Random(0)
    always.random = lambda: 0.0  # type: ignore[method-assign]
    assert should_murmur(always)
    never = _random.Random(0)
    never.random = lambda: 0.5  # type: ignore[method-assign]
    assert not should_murmur(never)


def run() -> None:
    test_all_languages_have_dream_fragments()
    test_no_anachronistic_vocabulary_in_any_language()
    test_modern_markers_are_rejected()
    test_random_somniloquy_stays_in_library()
    test_murmur_probability_is_very_low()
    print("SOMNILOQUY_OK")


if __name__ == "__main__":
    run()
