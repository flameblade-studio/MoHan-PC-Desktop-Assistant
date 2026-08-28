from __future__ import annotations

"""Wardrobe intuition (穿搭直覺), inspired by "A・I ga Tomaranai!".

A real girl does not blindly wear whatever the user picks.  When the weather is
hot she suggests lighter clothes; if the user forces her into summer wear during
a cold snap, her affection dips a little and she complains — a playful extension
of the jealousy logic.

This is pure domain logic with no Qt dependency.  It maps a temperature to a
comfort verdict and a suggested outfit weight, so the presentation layer can
surface a suggestion or a complaint without blocking the UI.
"""

lazy from enum import StrEnum

# Temperature thresholds (Celsius) for comfort verdicts.
HOT_THRESHOLD_C = 28.0
COLD_THRESHOLD_C = 12.0


class OutfitWeight(StrEnum):
    LIGHT = "light"
    MODERATE = "moderate"
    WARM = "warm"


class ComfortVerdict(StrEnum):
    COMFORTABLE = "comfortable"
    TOO_HOT = "too_hot"
    TOO_COLD = "too_cold"


def weight_for_thermal_bands(thermal_bands: frozenset[str]) -> OutfitWeight:
    """Derive a worn-outfit weight from an autonomous profile's thermal bands.

    An outfit tailored for the hot band is light clothing; one tailored for the
    cool/cold bands is warm clothing; anything that spans both extremes (or
    neither) is a versatile moderate outfit.  This lets the wardrobe runtime
    persist ``wardrobe_current_weight`` so the comfort-complaint intuition can
    judge what MoHan is actually wearing.
    """
    covers_hot = "hot" in thermal_bands
    covers_cold = bool(thermal_bands & {"cool", "cold"})
    if covers_hot and not covers_cold:
        return OutfitWeight.LIGHT
    if covers_cold and not covers_hot:
        return OutfitWeight.WARM
    return OutfitWeight.MODERATE


def suggested_weight(temperature_c: float) -> OutfitWeight:
    """Return the outfit weight that suits the current temperature."""
    if temperature_c >= HOT_THRESHOLD_C:
        return OutfitWeight.LIGHT
    if temperature_c <= COLD_THRESHOLD_C:
        return OutfitWeight.WARM
    return OutfitWeight.MODERATE


def comfort_verdict(
    temperature_c: float,
    current_weight: OutfitWeight,
) -> ComfortVerdict:
    """Judge whether the current outfit weight suits the temperature."""
    suggested = suggested_weight(temperature_c)
    if current_weight is suggested:
        return ComfortVerdict.COMFORTABLE
    if suggested is OutfitWeight.LIGHT and current_weight is not OutfitWeight.LIGHT:
        return ComfortVerdict.TOO_HOT
    if suggested is OutfitWeight.WARM and current_weight is not OutfitWeight.WARM:
        return ComfortVerdict.TOO_COLD
    return ComfortVerdict.COMFORTABLE


def complaint_line(language: str, verdict: ComfortVerdict) -> str:
    """Return a four-language complaint for an uncomfortable outfit."""
    if verdict is ComfortVerdict.TOO_COLD:
        return {
            "zh-TW": "主上……你是想把妾身凍壞，好找新策士嗎？",
            "zh-CN": "主上……你是想把妾身冻坏，好找新策士吗？",
            "en": "My lord… are you trying to freeze me so you can find a new strategist?",
            "ja-JP": "主上……妾を凍えさせて、新しい策士を探すおつもりですか？",
        }.get(language, "主上……你是想把妾身凍壞，好找新策士嗎？")
    if verdict is ComfortVerdict.TOO_HOT:
        return {
            "zh-TW": "好熱……主上，妾想換件輕便些的衣裳。",
            "zh-CN": "好热……主上，妾想换件轻便些的衣裳。",
            "en": "It is so warm… my lord, may I change into something lighter?",
            "ja-JP": "暑いです……主上、もっと軽い衣装に着替えたいです。",
        }.get(language, "好熱……主上，妾想換件輕便些的衣裳。")
    return ""
