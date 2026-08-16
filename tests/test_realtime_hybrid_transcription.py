from __future__ import annotations

lazy import io
lazy import json
lazy import sys
lazy import wave
lazy from pathlib import Path
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from integrations.realtime_voice import RealtimeVoiceClient
lazy from integrations.speech import transcribe_wav_bytes


class _Socket:
    connected = True


class _WebSocket:
    def __init__(self) -> None:
        self.sock = _Socket()
        self.sent: list[dict] = []

    def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))


class _CapturedThread:
    target = None
    args = ()

    def __init__(self, target, args, daemon):
        assert daemon
        _CapturedThread.target = target
        _CapturedThread.args = args

    def start(self):
        return None


class _Response:
    def __enter__(self):
        return io.BytesIO(
            '{"text":"主上，這是高精度文字。"}'.encode()
        )

    def __exit__(self, *_args):
        return False


def run() -> None:
    client = RealtimeVoiceClient()
    client.running = True
    client.echo_guard = False
    client.hybrid_transcription = True
    client._session_generation = 7
    client.ws = _WebSocket()
    client._input_resume_at = 0.0
    client._handle_server_event(
        {
            "type": "input_audio_buffer.speech_started",
            "item_id": "ordinary-speech",
            "audio_start_ms": 0,
        }
    )
    assert client._input_resume_at == 0.0
    assert not client._microphone_blocked()

    # Three seconds of the exact 24 kHz PCM sent to Realtime are retained.
    packet = b"\x10\x00" * 2400
    for _ in range(30):
        client._remember_sent_audio(packet)
    assert 2999 <= client._current_input_offset_ms() <= 3001

    transcripts: list[str] = []
    client.user_transcript.connect(transcripts.append)
    client._handle_server_event(
        {
            "type": "input_audio_buffer.speech_started",
            "item_id": "utterance-1",
            "audio_start_ms": 500,
        }
    )
    with patch(
        "integrations.realtime_voice.threading.Thread",
        _CapturedThread,
    ):
        client._handle_server_event(
            {
                "type": "input_audio_buffer.speech_stopped",
                "item_id": "utterance-1",
                "audio_end_ms": 2500,
            }
        )
    assert client._hybrid_transcription_active.is_set()
    assert _CapturedThread.target == client._run_hybrid_transcription
    item_id, wav_audio, generation = _CapturedThread.args
    assert item_id == "utterance-1"
    assert generation == 7
    with wave.open(io.BytesIO(wav_audio), "rb") as recording:
        assert recording.getframerate() == 24000
        assert recording.getnchannels() == 1
        assert 1.99 <= (
            recording.getnframes() / recording.getframerate()
        ) <= 2.01

    client._finish_hybrid_transcription(
        "utterance-1",
        "主上，這是高精度文字。",
        "",
        7,
    )
    assert transcripts == ["主上，這是高精度文字。"]
    assert {"type": "response.create"} in client.ws.sent
    assert client._response_pending.is_set()
    assert not client._hybrid_transcription_active.is_set()
    assert client._microphone_blocked()

    before = len(
        [
            event
            for event in client.ws.sent
            if event == {"type": "response.create"}
        ]
    )
    client._hybrid_transcription_active.set()
    client._finish_hybrid_transcription(
        "noise-1",
        "",
        "無法辨識這段語音",
        7,
    )
    after = len(
        [
            event
            for event in client.ws.sent
            if event == {"type": "response.create"}
        ]
    )
    assert before == after
    assert {
        "type": "conversation.item.delete",
        "item_id": "noise-1",
    } in client.ws.sent

    with patch(
        "integrations.speech.urlopen",
        return_value=_Response(),
    ) as mocked:
        text = transcribe_wav_bytes(
            wav_audio,
            "sk-test",
            "gpt-4o-mini-transcribe",
            "zh",
            "墨寒、主上",
        )
    assert text == "主上，這是高精度文字。"
    request = mocked.call_args.args[0]
    body = request.data
    assert b"gpt-4o-mini-transcribe" in body
    assert "墨寒、主上".encode() in body
    assert wav_audio in body

    print("REALTIME_HYBRID_TRANSCRIPTION_OK")


if __name__ == "__main__":
    run()
