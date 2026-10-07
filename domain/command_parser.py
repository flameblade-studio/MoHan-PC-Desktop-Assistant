from __future__ import annotations

lazy import re

lazy from domain.character_pack.character_data import load_mohan_character_data

_COMMAND_PHRASES = load_mohan_character_data().identity


def _normalize_command(text: str) -> str:
    return re.sub(r"[\s，,。.!！?？、：:「」『』]+", "", text)


def is_start_work_command(text: str) -> bool:
    return _normalize_command(text) in _COMMAND_PHRASES.start_work_phrases


def is_stop_work_command(text: str) -> bool:
    return _normalize_command(text) in _COMMAND_PHRASES.stop_work_phrases
