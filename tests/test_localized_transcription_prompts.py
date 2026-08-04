from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import StudioDB
from language_support import (
    LEGACY_TRANSCRIPTION_PROMPT,
    is_builtin_transcription_prompt,
    localized_transcription_prompt,
)
from realtime_voice import RealtimeVoiceClient


def _create_existing_profile(path: Path, prompt: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    values = {
        "ui_language": "zh-CN",
        "assistant_name": "墨寒",
        "user_title": "主上",
        "organization_name": "測試工作室",
        "wake_word": "小寒",
        "transcription_prompt": prompt,
    }
    conn.executemany(
        "INSERT INTO settings(key, value) VALUES(?, ?)",
        [
            (key, json.dumps(value, ensure_ascii=False))
            for key, value in values.items()
        ],
    )
    conn.commit()
    conn.close()


def run() -> None:
    profiles = {
        "zh-TW": "請使用台灣繁體中文準確轉錄",
        "zh-CN": "请使用中国简体中文准确转录",
        "en": "Please transcribe accurately in English",
        "ja-JP": "日本語で正確に文字起こししてください",
    }
    prompts: dict[str, str] = {}
    for language, expected in profiles.items():
        prompt = localized_transcription_prompt(
            language,
            assistant_name="墨寒",
            user_title="主上",
            organization_name="測試工作室",
            wake_word="墨寒",
        )
        prompts[language] = prompt
        assert expected in prompt
        assert prompt.count("墨寒") == 1
        assert "測試工作室" in prompt
        assert "炎劍文化工作室" not in prompt
        assert "DistroKid" not in prompt
        safe = RealtimeVoiceClient._sanitize_realtime_transcription_prompt(
            prompt
        )
        assert "墨寒" in safe
        assert "測試工作室" in safe
        assert expected not in safe

    assert is_builtin_transcription_prompt(
        prompts["en"],
        "en",
        assistant_name="墨寒",
        user_title="主上",
        organization_name="測試工作室",
        wake_word="墨寒",
    )
    assert not is_builtin_transcription_prompt(
        "My private custom vocabulary",
        "en",
        assistant_name="墨寒",
        user_title="主上",
        organization_name="測試工作室",
        wake_word="墨寒",
    )

    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        legacy_path = Path(temp) / "legacy.db"
        _create_existing_profile(legacy_path, LEGACY_TRANSCRIPTION_PROMPT)
        legacy = StudioDB(legacy_path)
        migrated = str(legacy.setting("transcription_prompt"))
        assert "请使用中国简体中文准确转录" in migrated
        assert "小寒" in migrated
        assert "測試工作室" in migrated
        assert "Pubu" not in migrated
        legacy.close()

        custom_path = Path(temp) / "custom.db"
        custom_prompt = "请准确转录。我的专有词：海风计划。"
        _create_existing_profile(custom_path, custom_prompt)
        custom = StudioDB(custom_path)
        assert custom.setting("transcription_prompt") == custom_prompt
        custom.close()

    print("LOCALIZED_TRANSCRIPTION_PROMPTS_OK")


if __name__ == "__main__":
    run()
