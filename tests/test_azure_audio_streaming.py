from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from types import SimpleNamespace
lazy from typing import ClassVar
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from integrations.speech import play_pcm16_stream_with_visemes

EXPECTED_CUE_COUNT = 4


class FakeOutputStream:
    writes: ClassVar[list[bytes]] = []

    def __init__(self, **settings: object) -> None:
        assert settings == {
            "samplerate": 24_000,
            "channels": 1,
            "dtype": "int16",
            "blocksize": 480,
            "device": None,
        }

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def write(self, chunk: bytes) -> None:
        self.writes.append(bytes(chunk))


def run() -> None:
    FakeOutputStream.writes = []
    source = bytearray(b"\x01\x00" * 1_200)
    first_audio: list[bool] = []
    cues: list[tuple[float, str]] = []

    def read_chunk(buffer: bytearray) -> int:
        if not source:
            return 0
        size = min(len(buffer), 730, len(source))
        buffer[:size] = source[:size]
        del source[:size]
        return size

    with patch(
        "integrations.speech.sd",
        SimpleNamespace(RawOutputStream=FakeOutputStream),
    ):
        play_pcm16_stream_with_visemes(
            read_chunk,
            volume_percent=100,
            muted=False,
            emit_cue=lambda level, vowel: cues.append((level, vowel)),
            on_first_audio=lambda: first_audio.append(True),
        )

    assert first_audio == [True]
    assert [len(chunk) for chunk in FakeOutputStream.writes] == [960, 960, 480]
    assert cues[-1] == (0.0, "CLOSED")
    assert len(cues) == EXPECTED_CUE_COUNT
    print("AZURE_AUDIO_STREAMING_OK")


if __name__ == "__main__":
    run()
