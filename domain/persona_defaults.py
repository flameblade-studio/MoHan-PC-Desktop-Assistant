"""Canonical four-language personality defaults for MoHan."""

from __future__ import annotations

lazy from domain.character_source import active_character_data

_PERSONAS = active_character_data().personas

PERSONA = _PERSONAS["zh-TW"].system_prompt
ENGLISH_PERSONA = _PERSONAS["en"].system_prompt
SIMPLIFIED_CHINESE_PERSONA = _PERSONAS["zh-CN"].system_prompt
JAPANESE_PERSONA = _PERSONAS["ja-JP"].system_prompt
__all__ = (
    "ENGLISH_PERSONA",
    "JAPANESE_PERSONA",
    "PERSONA",
    "SIMPLIFIED_CHINESE_PERSONA",
)
