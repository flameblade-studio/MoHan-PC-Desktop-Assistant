from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.wardrobe_intuition import (
    ComfortVerdict,
    OutfitWeight,
    comfort_verdict,
    complaint_line,
    suggested_weight,
)


def test_suggested_weight_by_temperature() -> None:
    assert suggested_weight(30.0) is OutfitWeight.LIGHT
    assert suggested_weight(20.0) is OutfitWeight.MODERATE
    assert suggested_weight(5.0) is OutfitWeight.WARM


def test_comfortable_when_weight_matches() -> None:
    assert (
        comfort_verdict(30.0, OutfitWeight.LIGHT)
        is ComfortVerdict.COMFORTABLE
    )
    assert (
        comfort_verdict(5.0, OutfitWeight.WARM)
        is ComfortVerdict.COMFORTABLE
    )


def test_too_cold_when_warm_needed() -> None:
    assert (
        comfort_verdict(5.0, OutfitWeight.LIGHT)
        is ComfortVerdict.TOO_COLD
    )


def test_too_hot_when_light_needed() -> None:
    assert (
        comfort_verdict(30.0, OutfitWeight.WARM)
        is ComfortVerdict.TOO_HOT
    )


def test_complaint_lines_are_four_language() -> None:
    cold = complaint_line("zh-TW", ComfortVerdict.TOO_COLD)
    assert "凍壞" in cold
    assert complaint_line("en", ComfortVerdict.TOO_COLD)
    assert complaint_line("ja-JP", ComfortVerdict.TOO_COLD)
    assert complaint_line("zh-TW", ComfortVerdict.COMFORTABLE) == ""


def run() -> None:
    test_suggested_weight_by_temperature()
    test_comfortable_when_weight_matches()
    test_too_cold_when_warm_needed()
    test_too_hot_when_light_needed()
    test_complaint_lines_are_four_language()
    print("WARDROBE_INTUITION_OK")


if __name__ == "__main__":
    run()
