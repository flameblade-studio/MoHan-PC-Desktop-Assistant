from __future__ import annotations

lazy import json
lazy import queue
lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from realtime_voice import RealtimeVoiceClient


class _Socket:
    connected = True


class _WebSocket:
    def __init__(self) -> None:
        self.sock = _Socket()
        self.sent: list[dict] = []

    def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))


def run() -> None:
    client = RealtimeVoiceClient()
    client.running = True
    client.echo_guard = True
    client.hybrid_transcription = False
    client.ws = _WebSocket()
    client._input_queue.put_nowait(b"queued-before-playback")

    transcripts: list[str] = []
    client.user_transcript.connect(transcripts.append)

    client._handle_server_event(
        {
            "type": (
                "conversation.item.input_audio_transcription.delta"
            ),
            "item_id": "turn-1",
            "delta": "你在",
        }
    )
    client._handle_server_event(
        {
            "type": "conversation.item.input_audio_transcription.done",
            "item_id": "turn-1",
            "transcript": "你在做什麼",
        }
    )
    assert transcripts == []

    completed = {
        "type": (
            "conversation.item.input_audio_transcription.completed"
        ),
        "item_id": "turn-1",
        "transcript": "你在做什麼？",
    }
    client._handle_server_event(completed)
    client._handle_server_event(completed)
    assert transcripts == ["你在做什麼？"]
    response_events = [
        event
        for event in client.ws.sent
        if event == {"type": "response.create"}
    ]
    assert len(response_events) == 1

    client._handle_server_event(
        {
            **completed,
            "item_id": "turn-2",
        }
    )
    assert transcripts == ["你在做什麼？", "你在做什麼？"]
    response_events = [
        event
        for event in client.ws.sent
        if event == {"type": "response.create"}
    ]
    assert len(response_events) == 2
    client._handle_server_event(
        {
            "type": (
                "conversation.item.input_audio_transcription.failed"
            ),
            "item_id": "noise-turn",
            "error": {
                "code": "audio_unintelligible",
                "message": "The audio could not be transcribed.",
            },
        }
    )
    response_events = [
        event
        for event in client.ws.sent
        if event == {"type": "response.create"}
    ]
    assert len(response_events) == 2
    assert {
        "type": "conversation.item.delete",
        "item_id": "noise-turn",
    } in client.ws.sent

    client._begin_assistant_audio()
    assert client._microphone_blocked()
    assert client._input_queue.empty()
    assert {
        "type": "input_audio_buffer.clear"
    } in client.ws.sent

    client._finish_assistant_audio()
    clear_events = [
        event
        for event in client.ws.sent
        if event == {"type": "input_audio_buffer.clear"}
    ]
    assert len(clear_events) >= 2

    # A packet that was dequeued before playback began must still be rejected
    # by the second guard immediately before WebSocket transmission.
    sender = RealtimeVoiceClient()
    sender.running = True
    sender.echo_guard = True
    sender.ws = _WebSocket()
    sender_queue: queue.Queue[bytes | None] = queue.Queue()
    sender_queue.put(b"\x00\x00" * 240)
    sender_queue.put(None)
    checks = iter((False, True))
    sender._microphone_blocked = lambda: next(checks)
    sender._input_sender_loop(sender_queue, 24000)
    assert sender.ws.sent == []

    print("REALTIME_ECHO_FINAL_TRANSCRIPT_OK")


if __name__ == "__main__":
    run()
