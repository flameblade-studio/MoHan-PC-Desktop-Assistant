from __future__ import annotations

lazy import inspect
lazy import io
lazy import json
lazy import sys
lazy import wave
lazy from pathlib import Path
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.speech_configuration import VOICE_GENERATION_PROMPT
lazy from integrations.speech import OpenAITTS


def silent_wav() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(24000)
        target.writeframes(b"")
    return buffer.getvalue()


def captured_tts_payload(instructions: str) -> dict:
    response = io.BytesIO(silent_wav())
    tts = OpenAITTS()
    with (
        patch(
            "integrations.speech.urlopen",
            return_value=response,
        ) as mocked_urlopen,
        patch.object(tts, "_emit_wave_cues"),
        patch("winsound.PlaySound"),
    ):
        tts._run("主上，妾在。", "sk-test", "coral", instructions)
    request = mocked_urlopen.call_args.args[0]
    return json.loads(request.data.decode("utf-8"))


def run() -> None:
    root = Path(__file__).resolve().parents[1]
    runtime_sources = "\n".join(
        (root / name).read_text(encoding="utf-8")
        for name in (
            "integrations/speech.py",
            "domain/speech_configuration.py",
            "integrations/realtime_voice.py",
            "integrations/ai_client.py",
        )
    )
    assert runtime_sources.count(
        "請使用台灣繁體中文，以自然的台灣中文口音說話。"
    ) == 1
    for obsolete_fragment in (
        "成熟沉靜、清晰自然的繁體中文女聲",
        "以成熟、沉靜、清晰的繁體中文女聲朗讀",
        "使用自然、輕微而穩定的台灣華語口音",
        "REALTIME_VOICE_GUIDANCE",
    ):
        assert obsolete_fragment not in runtime_sources

    voice_default = inspect.signature(OpenAITTS.speak).parameters[
        "voice"
    ].default
    assert voice_default == "coral"

    payload = captured_tts_payload(VOICE_GENERATION_PROMPT)
    assert payload["voice"] == "coral"
    assert payload["instructions"] == VOICE_GENERATION_PROMPT

    payload_without_prompt = captured_tts_payload("")
    assert "instructions" not in payload_without_prompt
    print("VOICE_PROMPT_INTEGRITY_OK")


if __name__ == "__main__":
    run()
