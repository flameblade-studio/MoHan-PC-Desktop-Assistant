from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from types import SimpleNamespace
lazy from typing import ClassVar
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from integrations.speech import play_pcm16_stream_with_visemes
lazy from integrations.speech_audio import preferred_output_device

EXPECTED_CUE_COUNT = 4
WASAPI_DEVICE_ID = 18


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


class FakeDeviceSelection:
    def __init__(self, *, compatible: bool) -> None:
        self.compatible = compatible
        self.checked: list[dict[str, object]] = []

    @staticmethod
    def query_hostapis() -> list[dict[str, object]]:
        return [
            {
                "name": "Windows WASAPI",
                "default_output_device": WASAPI_DEVICE_ID,
            }
        ]

    def check_output_settings(self, **settings: object) -> None:
        self.checked.append(settings)
        if not self.compatible:
            raise OSError("Invalid sample rate")


def assert_output_device_fallback() -> None:
    with patch("integrations.speech_audio.sys.platform", "win32"):
        incompatible = FakeDeviceSelection(compatible=False)
        assert preferred_output_device(
            incompatible,
            sample_rate=24_000,
            channels=1,
        ) is None
        assert incompatible.checked == [
            {
                "device": WASAPI_DEVICE_ID,
                "samplerate": 24_000,
                "channels": 1,
                "dtype": "int16",
            }
        ]

        compatible = FakeDeviceSelection(compatible=True)
        assert preferred_output_device(
            compatible,
            sample_rate=48_000,
            channels=2,
        ) == WASAPI_DEVICE_ID


def run() -> None:
    assert_output_device_fallback()
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
