lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from realtime_voice import (
    RealtimeSessionConfig,
    RealtimeVoiceClient,
)


def run() -> None:
    event = RealtimeVoiceClient._session_update_event(
        RealtimeSessionConfig(
            transcription_prompt="常用詞：墨寒、主上、炎劍文化工作室。",
        ),
        "請使用台灣繁體中文",
    )
    session = event["session"]
    audio_input = session["audio"]["input"]
    transcription = audio_input["transcription"]
    turn = audio_input["turn_detection"]
    assert event["type"] == "session.update"
    assert session["model"] == "gpt-realtime-2.1-mini"
    assert "include" not in session
    assert transcription is None
    assert audio_input["noise_reduction"] == {"type": "near_field"}
    assert turn == {
        "type": "server_vad",
        "threshold": 0.45,
        "prefix_padding_ms": 500,
        "silence_duration_ms": 850,
        "create_response": False,
        "interrupt_response": True,
    }

    semantic = RealtimeVoiceClient._session_update_event(
        RealtimeSessionConfig(
            model="gpt-realtime-2.1",
            transcription_model="gpt-4o-transcribe",
            transcription_language="",
            noise_reduction="off",
            turn_detection="semantic_vad",
        ),
        "test",
    )
    semantic_input = semantic["session"]["audio"]["input"]
    assert "noise_reduction" not in semantic_input
    assert semantic_input["transcription"] is None
    assert semantic_input["turn_detection"] == {
        "type": "semantic_vad",
        "eagerness": "medium",
        "create_response": False,
        "interrupt_response": True,
    }

    legacy = RealtimeVoiceClient._session_update_event(
        RealtimeSessionConfig(
            transcription_prompt="常用詞：墨寒、主上。",
            external_transcription=False,
        ),
        "test",
    )
    assert legacy["session"]["include"] == [
        "item.input_audio_transcription.logprobs"
    ]
    assert legacy["session"]["audio"]["input"]["transcription"] == {
        "model": "gpt-4o-mini-transcribe",
        "language": "zh",
        "prompt": "常用詞：墨寒、主上。",
    }

    source = Path("realtime_voice.py").read_text(encoding="utf-8")
    assert "gpt-realtime-whisper" not in source
    print("REALTIME_TRANSCRIPTION_CONFIG_OK")


if __name__ == "__main__":
    run()
