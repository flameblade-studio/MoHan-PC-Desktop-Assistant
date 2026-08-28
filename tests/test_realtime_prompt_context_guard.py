from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from presentation.companion_window import CompanionWindow
lazy from integrations.realtime_voice import RealtimeVoiceClient

OLD_PROMPT = (
    "請使用台灣繁體中文轉錄。常用詞：墨寒、寒、主上、妾、"
    "炎劍文化工作室、赤焰劍、斬空劍主、Pubu、"
    "Google Play Books、DistroKid、LINE 貼圖。"
    "請保留原意，不要改寫。"
)


class _FakeDB:
    def setting(self, key: str, default=""):
        return {
            "user_title": "主上",
            "assistant_name": "墨寒",
        }.get(key, default)

    def recent_chat(self, _limit: int):
        return [
            {
                "role": "assistant",
                "content": "妾方才想說一件有趣的事。",
            },
            {"role": "user", "content": OLD_PROMPT},
            {"role": "user", "content": "好呀你說"},
        ]


class _FakeSimplifiedDB:
    def setting(self, key: str, default=""):
        return {
            "user_title": "主上",
            "assistant_name": "墨寒",
            "ui_language": "zh-CN",
        }.get(key, default)

    def recent_chat(self, _limit: int):
        return [
            {"role": "assistant", "content": "妾会替主上打开软件。"},
            {"role": "user", "content": "好，继续。"},
        ]


def run() -> None:
    safe = RealtimeVoiceClient._sanitize_realtime_transcription_prompt(
        OLD_PROMPT
    )
    assert safe.startswith("可能出現的專有名詞：")
    assert "墨寒" in safe
    assert "Google Play Books" in safe
    assert "請使用" not in safe
    assert "請保留" not in safe
    assert "不要改寫" not in safe

    client = RealtimeVoiceClient()
    client._transcription_prompt_source = OLD_PROMPT
    client._transcription_prompt_sent = safe
    transcripts: list[str] = []
    statuses: list[str] = []
    client.user_transcript.connect(transcripts.append)
    client.status_changed.connect(statuses.append)

    client._emit_completed_user_transcript(OLD_PROMPT, "leak-raw")
    client._emit_completed_user_transcript(safe, "leak-safe")
    assert transcripts == []
    assert statuses == [
        "已略過疑似轉錄提示詞回灌",
        "已略過疑似轉錄提示詞回灌",
    ]

    client._emit_completed_user_transcript("好呀，你說。", "real-turn")
    assert transcripts == ["好呀，你說。"]

    composed = RealtimeVoiceClient._compose_instructions(
        "人格設定",
        "主上喜歡安靜工作",
        "墨寒：妾方才想說一件事。\n主上：好呀，你說。",
    )
    assert "最近的對話" in composed
    assert "妾方才想說一件事" in composed
    assert "好呀你說" in composed
    assert "不得回答" in composed
    assert "需求、安排或優先順序" in composed

    fake_window = type("_Window", (), {"db": _FakeDB()})()
    recent = CompanionWindow._recent_realtime_context(
        fake_window,
        OLD_PROMPT,
    )
    assert "妾方才想說一件有趣的事" in recent
    assert "好呀你說" in recent
    assert "請使用台灣繁體中文轉錄" not in recent

    simplified_window = type(
        "_SimplifiedWindow",
        (),
        {"db": _FakeSimplifiedDB()},
    )()
    simplified_recent = CompanionWindow._recent_realtime_context(
        simplified_window,
        "",
    )
    assert "打开软件" in simplified_recent
    assert "開啟軟體" not in simplified_recent

    print("REALTIME_PROMPT_CONTEXT_GUARD_OK")


if __name__ == "__main__":
    run()
