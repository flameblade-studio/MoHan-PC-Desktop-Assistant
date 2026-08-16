from __future__ import annotations

lazy import io
lazy import logging
lazy import queue
lazy import wave
lazy from collections import Counter
lazy from collections.abc import Callable
lazy from types import ModuleType, SimpleNamespace
lazy from typing import ClassVar, Self
lazy from unittest.mock import patch

lazy from PySide6.QtCore import QCoreApplication

lazy from application.native_acceleration import NativeAcceleration
lazy from domain import lip_sync, pcm_audio
lazy from integrations.azure_speech import AzureSpeechTTS, _SynthesisRequest
lazy from integrations.realtime_voice import RealtimeVoiceClient
lazy from integrations.speech import OpenAITTS, WindowsTTS


def _wave(*, channels: int = 1, frames: int = 480) -> bytes:
    samples = (1_000, -700) if channels == 2 else (1_000,)
    frame = b"".join(
        sample.to_bytes(2, "little", signed=True) for sample in samples
    )
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(channels)
        target.setsampwidth(2)
        target.setframerate(24_000)
        target.writeframes(frame * frames)
    return output.getvalue()


class _RecordingAcceleration:
    """Record operation names and lengths without retaining user audio."""

    def __init__(
        self,
        *,
        failures: frozenset[str] = frozenset(),
    ) -> None:
        self.calls: Counter[str] = Counter()
        self.byte_lengths: list[tuple[str, int]] = []
        self._failures = failures

    def _record(self, operation: str, data: bytes) -> None:
        self.calls[operation] += 1
        self.byte_lengths.append((operation, len(data)))
        if operation in self._failures:
            raise RuntimeError(f"{operation} fault")

    def analyze_pcm16(self, pcm: bytes) -> tuple[float, float]:
        self._record("analyze_pcm16", pcm)
        return lip_sync.analyze_pcm16(pcm)

    def infer_vowel_pcm16(
        self,
        pcm: bytes,
        sample_rate: int = 24_000,
    ) -> tuple[float, str]:
        self._record("infer_vowel_pcm16", pcm)
        return lip_sync.infer_vowel_pcm16(pcm, sample_rate)

    def scale_pcm16(self, data: bytes, factor: float) -> bytes:
        self._record("scale_pcm16", data)
        return pcm_audio.scale_pcm16(data, factor)

    def stereo_to_mono_pcm16(
        self,
        data: bytes,
        left_factor: float = 0.5,
        right_factor: float = 0.5,
    ) -> bytes:
        self._record("stereo_to_mono_pcm16", data)
        return pcm_audio.stereo_to_mono_pcm16(
            data,
            left_factor,
            right_factor,
        )

    def rate_convert_pcm16(
        self,
        data: bytes,
        channels: int,
        input_rate: int,
        output_rate: int,
        state: pcm_audio.Pcm16RateState | None = None,
    ) -> tuple[bytes, pcm_audio.Pcm16RateState | None]:
        self._record("rate_convert_pcm16", data)
        return pcm_audio.rate_convert_pcm16(
            data,
            channels,
            input_rate,
            output_rate,
            state,
        )


class _OutputStream:
    instances: ClassVar[list[_OutputStream]] = []

    def __init__(self, **_settings: object) -> None:
        self.writes: list[bytes] = []
        self.stopped = False
        self.closed = False
        self.__class__.instances.append(self)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def start(self) -> None:
        return None

    def write(self, chunk: bytes) -> None:
        self.writes.append(bytes(chunk))

    def stop(self) -> None:
        self.stopped = True

    def abort(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class _Response:
    def __init__(self, audio: bytes) -> None:
        self._audio = audio

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._audio


class _OneChunkQueue:
    def __init__(self, client: RealtimeVoiceClient, chunk: bytes) -> None:
        self._client = client
        self._chunk = chunk

    def get(self) -> bytes:
        self._client.running = False
        return self._chunk

    @staticmethod
    def empty() -> bool:
        return True


def _sounddevice_probe() -> SimpleNamespace:
    return SimpleNamespace(
        RawOutputStream=_OutputStream,
        PortAudioError=OSError,
    )


def _read_once(payload: bytes) -> Callable[[bytearray], int]:
    pending = bytearray(payload)

    def read(buffer: bytearray) -> int:
        if not pending:
            return 0
        size = min(len(buffer), len(pending))
        buffer[:size] = pending[:size]
        del pending[:size]
        return size

    return read


def test_windows_and_openai_wave_paths_use_the_injected_port() -> None:
    QCoreApplication.instance() or QCoreApplication([])
    accelerator = _RecordingAcceleration()
    cues: list[tuple[float, str]] = []
    audio = _wave(channels=2)
    windows = WindowsTTS(pcm_acceleration=accelerator)
    openai = OpenAITTS(pcm_acceleration=accelerator)
    windows.viseme_cue.connect(lambda level, vowel: cues.append((level, vowel)))
    openai.viseme_cue.connect(lambda level, vowel: cues.append((level, vowel)))

    _OutputStream.instances.clear()
    with patch("integrations.speech.sd", _sounddevice_probe()):
        windows._play_wave_bytes(audio, windows._begin_generation())
        openai._play_wave_bytes(audio, openai._begin_generation())

    assert accelerator.calls["scale_pcm16"] == 2
    assert accelerator.calls["stereo_to_mono_pcm16"] == 2
    assert accelerator.calls["infer_vowel_pcm16"] == 2
    assert cues[-1] == (0.0, "CLOSED")
    assert len(_OutputStream.instances) == 2
    assert all(stream.stopped and stream.closed for stream in _OutputStream.instances)


def test_realtime_input_and_output_use_resample_scale_and_50_hz_port() -> None:
    QCoreApplication.instance() or QCoreApplication([])
    accelerator = _RecordingAcceleration()
    client = RealtimeVoiceClient(pcm_acceleration=accelerator)
    sent: list[str] = []
    client.ws = SimpleNamespace(
        sock=SimpleNamespace(connected=True),
        send=sent.append,
    )
    client.running = True
    microphone = queue.Queue()
    microphone.put(b"\x10\x00" * 960)
    microphone.put(None)
    client._input_sender_loop(microphone, 48_000)

    cues: list[tuple[float, str]] = []
    client.viseme_cue.connect(lambda level, vowel: cues.append((level, vowel)))
    client.running = True
    client.volume_percent = 125
    client._server_audio_done = True
    client._begin_assistant_audio()
    output = _OutputStream()
    client._playback_loop(
        _OneChunkQueue(client, b"\x20\x00" * 480),
        output,
        48_000,
    )

    assert sent
    assert accelerator.calls["rate_convert_pcm16"] == 2
    assert accelerator.calls["infer_vowel_pcm16"] == 1
    assert accelerator.calls["scale_pcm16"] == 1
    assert output.writes
    assert cues[-1] == (0.0, "CLOSED")


def test_stream_playback_closes_after_an_injected_pcm_fault() -> None:
    from integrations.speech import play_pcm16_stream_with_visemes

    accelerator = _RecordingAcceleration(
        failures=frozenset({"infer_vowel_pcm16"}),
    )
    cues: list[tuple[float, str]] = []

    _OutputStream.instances.clear()
    with patch("integrations.speech.sd", _sounddevice_probe()):
        try:
            play_pcm16_stream_with_visemes(
                _read_once(b"\x20\x00" * 480),
                volume_percent=125,
                muted=False,
                emit_cue=lambda level, vowel: cues.append((level, vowel)),
                pcm_acceleration=accelerator,
            )
        except RuntimeError as error:
            assert str(error) == "infer_vowel_pcm16 fault"
        else:
            raise AssertionError("the injected PCM fault was not surfaced")

    assert accelerator.calls["infer_vowel_pcm16"] == 1
    assert cues == [(0.0, "CLOSED")]


def test_azure_engine_forwards_the_injected_port_to_stream_playback() -> None:
    accelerator = _RecordingAcceleration()
    engine = AzureSpeechTTS(pcm_acceleration=accelerator)
    operation_id = engine._begin_operation()
    forwarded: list[object] = []

    class _Reader:
        @staticmethod
        def read(_buffer: bytearray) -> int:
            return 0

        def close(self) -> None:
            return None

    class _Future:
        @staticmethod
        def get() -> object:
            return SimpleNamespace(reason="completed")

    class _Synthesizer:
        @staticmethod
        def speak_ssml_async(_ssml: str) -> _Future:
            return _Future()

    def playback(
        _read_chunk: object,
        *,
        pcm_acceleration: object,
        emit_cue: object,
        on_first_audio: object,
        **_settings: object,
    ) -> None:
        del emit_cue, on_first_audio
        forwarded.append(pcm_acceleration)

    with (
        patch(
            "integrations.azure_speech._streaming_synthesizer",
            return_value=(_Reader(), _Synthesizer()),
        ),
        patch(
            "integrations.azure_speech.play_pcm16_stream_with_visemes",
            side_effect=playback,
        ),
        patch(
            "integrations.azure_speech.speechsdk",
            SimpleNamespace(
                ResultReason=SimpleNamespace(Canceled="canceled"),
            ),
        ),
    ):
        engine._run(
            _SynthesisRequest(
                text="主上，妾在。",
                api_key="test-key",
                region="eastasia",
                voice="zh-TW-HsiaoChenNeural",
                locale="zh-TW",
            ),
            operation_id,
        )

    assert forwarded == [accelerator]


def test_one_native_fault_falls_back_and_openai_still_closes(
    caplog,
) -> None:
    QCoreApplication.instance() or QCoreApplication([])
    audio = _wave()
    pcm_body = audio[44:]
    module = ModuleType("_mohan_accel")
    module.__version__ = "fault-test"

    def fail_inference(_pcm: bytes, _sample_rate: int) -> tuple[float, str]:
        raise RuntimeError("simulated native inference failure")

    module.infer_vowel_pcm16 = fail_inference
    module.scale_pcm16 = pcm_audio.scale_pcm16
    accelerator = NativeAcceleration(module_loader=lambda _name: module)
    tts = OpenAITTS(pcm_acceleration=accelerator)
    events: list[tuple[str, object]] = []
    tts.viseme_cue.connect(
        lambda level, vowel: events.append(("viseme", (level, vowel)))
    )
    tts.finished.connect(lambda: events.append(("finished", None)))
    tts.failed.connect(lambda message: events.append(("failed", message)))

    _OutputStream.instances.clear()
    with (
        caplog.at_level(logging.WARNING),
        patch("integrations.speech.urlopen", return_value=_Response(audio)),
        patch("integrations.speech.sd", _sounddevice_probe()),
    ):
        tts._run("皜祈岫", "test-key", "coral", "", generation=None)

    assert accelerator.status().operation_failures == (
        ("infer_vowel_pcm16", 1),
    )
    assert events[-2:] == [
        ("viseme", (0.0, "CLOSED")),
        ("finished", None),
    ]
    assert all(name != "failed" for name, _value in events)
    assert pcm_body.hex() not in caplog.text
    assert "RuntimeError" in caplog.text
    assert "simulated native inference failure" not in caplog.text
