lazy import sys
lazy import wave
lazy from array import array
lazy from pathlib import Path
lazy from types import SimpleNamespace
lazy from typing import ClassVar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from speech import SpeechListener


def pcm_block(level: int) -> bytes:
    samples = int(16000 * SpeechListener.RECORD_BLOCK_SECONDS)
    return array("h", [level] * samples).tobytes()


class FakeInputStream:
    levels: ClassVar[list[int]] = []
    stop_after_reads: int | None = None
    listener: SpeechListener | None = None

    def __init__(self, **_kwargs):
        self.index = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _block_size):
        level = (
            self.levels[self.index]
            if self.index < len(self.levels)
            else 0
        )
        self.index += 1
        if (
            self.stop_after_reads is not None
            and self.index >= self.stop_after_reads
            and self.listener is not None
        ):
            self.listener._stop_recording.set()
        return pcm_block(level), False


def run() -> None:
    # The 0.7-second natural pause in the middle must not truncate the second
    # phrase. The final 0.9-second silence should still end promptly.
    FakeInputStream.levels = (
        [20] * 3
        + [900] * 5
        + [25] * 7
        + [650] * 5
        + [20] * 9
    )
    fake_sounddevice = SimpleNamespace(RawInputStream=FakeInputStream)
    previous = sys.modules.get("sounddevice")
    sys.modules["sounddevice"] = fake_sounddevice
    listener = SpeechListener(Path("voice_listener.ps1"))
    FakeInputStream.listener = listener
    path = None
    try:
        path = listener._record_wav()
        with wave.open(str(path), "rb") as recording:
            duration = recording.getnframes() / recording.getframerate()
        assert duration >= 2.8, duration
        assert duration < 3.1, duration
        path.unlink(missing_ok=True)
        path = None

        # A second click requests an immediate send without waiting for the
        # automatic endpoint or the ten-second safety ceiling.
        listener._stop_recording.clear()
        FakeInputStream.levels = [20] * 3 + [900] * 30
        FakeInputStream.stop_after_reads = 10
        path = listener._record_wav()
        with wave.open(str(path), "rb") as recording:
            manual_duration = (
                recording.getnframes() / recording.getframerate()
            )
        assert 0.9 <= manual_duration <= 1.1, manual_duration
    finally:
        if previous is None:
            sys.modules.pop("sounddevice", None)
        else:
            sys.modules["sounddevice"] = previous
        if path is not None:
            path.unlink(missing_ok=True)
    print("SPEECH_CAPTURE_ENDPOINT_OK")


if __name__ == "__main__":
    run()
