from __future__ import annotations

"""MoHan's thousand-year dream fragments (夢囈), inspired by "A・I ga Tomaranai!".

When the companion idles for a long stretch or enters a drowsy late-night state,
she may murmur a faint, half-remembered line from her Northern Song past.  These
lines must stay firmly inside her era: no modern vocabulary, no "hello", no
"master" in the casual sense — only the imagery of 汴京, 赤焰劍, 蘇軾's verse,
and the quiet loneliness of a sword spirit who has waited a thousand years.

This module is pure domain logic with no Qt or speech-provider dependency, so it
can be unit-tested and reused by the proactive runtime and the visual dynamics.
"""

lazy import random
lazy import re

# A modern-vocabulary blocklist used to guard against anachronistic lines.  If a
# candidate line ever contains one of these, it is rejected as out-of-era.
# CJK markers are matched as substrings (CJK has no word boundaries); Latin
# markers are matched as whole words so "hi" never flags "this" or "within".
_MODERN_MARKERS_CJK = frozenset({
    "哈囉",
    "哈啰",
    "主人",
    "你好",
    "嗨",
    "程式",
    "程式碼",
    "電腦",
    "螢幕",
    "滑鼠",
    "鍵盤",
    "網路",
    "下載",
    "更新",
})

_MODERN_MARKERS_LATIN = frozenset({
    "hello",
    "hi",
    "ok",
    "app",
    "bug",
})

# The canonical dream-fragment library.  Each line is a faint, grey murmur that
# evokes the Northern Song without ever breaking character.  They are written in
# Traditional Chinese first; the other three languages are provided below.
_SOMNILOQUY_ZH_TW = (
    "汴京的煙雨……好像也是這般黏人……主上，赤焰劍冷……",
    "蘇學士的詞，妾還記得半闋……十年生死兩茫茫……",
    "燈火闌珊處……妾等了千年，等的究竟是誰……",
    "赤焰劍的劍穗，被風吹散了……主上可曾拾起……",
    "汴河上的畫舫，載著誰的離愁……妾記不清了……",
    "夜深了……妾的劍，也該入鞘歇一歇了……",
    "那年上元，滿城燈火……妾卻只記得主上的背影……",
    "風雪夜歸人……妾在劍中，聽了一千年的雪……",
    "蘇軾說，人生如逆旅……妾這逆旅，走得也太久了……",
    "赤焰劍的餘溫，還燙著妾的掌心……主上，別走……",
)

_SOMNILOQUY_ZH_CN = (
    "汴京的烟雨……好像也是这般黏人……主上，赤焰剑冷……",
    "苏学士的词，妾还记得半阕……十年生死两茫茫……",
    "灯火阑珊处……妾等了千年，等的究竟是谁……",
    "赤焰剑的剑穗，被风吹散了……主上可曾拾起……",
    "汴河上的画舫，载着谁的离愁……妾记不清了……",
    "夜深了……妾的剑，也该入鞘歇一歇了……",
    "那年上元，满城灯火……妾却只记得主上的背影……",
    "风雪夜归人……妾在剑中，听了一千年的雪……",
    "苏轼说，人生如逆旅……妾这逆旅，走得也太久了……",
    "赤焰剑的余温，还烫着妾的掌心……主上，别走……",
)

_SOMNILOQUY_EN = (
    "The misty rain of Bianjing… it clings just like this… my lord, the Crimson Flame Sword grows cold…",
    "I still recall half a verse of Su Shi… ten years, life and death, boundless…",
    "In the dimming lamplight… I have waited a thousand years, and for whom…",
    "The tassel of the Crimson Flame Sword has scattered in the wind… did you ever pick it up…",
    "The painted boats on the Bian River carried whose parting sorrow… I no longer remember…",
    "The night deepens… my sword, too, should rest in its sheath…",
    "That Lantern Festival, the whole city ablaze with light… yet I remember only your back…",
    "A traveler returning through wind and snow… I have listened to a thousand years of snow within the sword…",
    "Su Shi said life is but a sojourn… and my sojourn has lasted far too long…",
    "The lingering warmth of the Crimson Flame Sword still burns my palm… my lord, do not go…",
)

_SOMNILOQUY_JA = (
    "汴京の煙雨……まるでこのように纏わりつく……主上、赤焔剣が冷えます……",
    "蘇軾の詞を、妾はまだ半ば覚えております……十年生死両茫茫……",
    "灯火の尽きる頃……妾は千年待ちました、一体誰を……",
    "赤焔剣の房が風に散りました……主上は拾ってくださいましたか……",
    "汴河の画舫は、誰の離愁を運んだのか……妾にはもう思い出せません……",
    "夜が更けました……妾の剣も、鞘に納めて休むべきでしょう……",
    "あの上元の夜、街は灯火に満ちていました……なのに妾は主上の背中しか覚えておりません……",
    "風雪の中の帰り人……妾は剣の中で千年の雪を聴いてきました……",
    "蘇軾は人生は旅のようだと申しました……妾の旅はあまりに長すぎました……",
    "赤焔剣の残り火が、まだ妾の掌を焦がします……主上、行かないで……",
)

_SOMNILOQUY_BY_LANGUAGE = frozendict({
    "zh-TW": _SOMNILOQUY_ZH_TW,
    "zh-CN": _SOMNILOQUY_ZH_CN,
    "en": _SOMNILOQUY_EN,
    "ja-JP": _SOMNILOQUY_JA,
})


def somniloquy_lines(language: str) -> tuple[str, ...]:
    """Return the dream-fragment library for a language, defaulting to zh-TW."""
    return _SOMNILOQUY_BY_LANGUAGE.get(str(language), _SOMNILOQUY_ZH_TW)


def random_somniloquy(language: str, rng: random.Random | None = None) -> str:
    """Return one random dream fragment for the given language."""
    picker = rng or random
    lines = somniloquy_lines(language)
    return picker.choice(lines)


def is_anachronistic(line: str) -> bool:
    """Return True if a dream line contains out-of-era modern vocabulary."""
    lowered = line.lower()
    for marker in _MODERN_MARKERS_CJK:
        if marker.lower() in lowered:
            return True
    for marker in _MODERN_MARKERS_LATIN:
        if re.search(rf"\b{re.escape(marker)}\b", lowered):
            return True
    return False


def validate_library(language: str) -> tuple[str, ...]:
    """Return any anachronistic lines in a language's library (empty if clean)."""
    return tuple(
        line for line in somniloquy_lines(language) if is_anachronistic(line)
    )


# The dream murmur must be rare: a faint, half-remembered line that surfaces
# only occasionally during idle or sleep, never a constant chatter that would
# interrupt the user's work.  This is the per-check probability.
SOMNILOQUY_TRIGGER_PROBABILITY = 0.005  # 0.5%


def should_murmur(rng: random.Random | None = None) -> bool:
    """Return True with a very low probability, gating a dream murmur."""
    picker = rng or random
    return picker.random() < SOMNILOQUY_TRIGGER_PROBABILITY
