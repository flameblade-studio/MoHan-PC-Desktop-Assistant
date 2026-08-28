from __future__ import annotations

lazy import io
lazy import os
lazy import wave
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

lazy from application import service_container
lazy from domain import pcm_audio
lazy from infrastructure.platform_contracts import PlatformCapabilities, PlatformPaths
lazy from integrations import azure_speech
lazy from integrations.realtime_voice import RealtimeVoiceClient
lazy from integrations.speech import (
    OpenAITTS,
    WindowsTTS,
    apply_wav_volume,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@dataclass
class RecordingPcmAcceleration:
    infer_calls: int = 0
    scale_calls: int = 0
    rate_calls: int = 0

    def analyze_pcm16(self, _pcm: bytes) -> tuple[float, float]:
        return 0.0, 0.0

    def infer_vowel_pcm16(
        self,
        _pcm: bytes,
        _sample_rate: int = 24_000,
    ) -> tuple[float, str]:
        self.infer_calls += 1
        return 0.25, "A"

    def scale_pcm16(self, data: bytes, factor: float) -> bytes:
        self.scale_calls += 1
        return pcm_audio.scale_pcm16(data, factor)

    def stereo_to_mono_pcm16(
        self,
        data: bytes,
        left_factor: float = 0.5,
        right_factor: float = 0.5,
    ) -> bytes:
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
        self.rate_calls += 1
        return pcm_audio.rate_convert_pcm16(
            data,
            channels,
            input_rate,
            output_rate,
            state,
        )


class _PlatformProbe:
    capabilities = PlatformCapabilities(
        platform_id="windows-native-wiring-test",
        display_name="Windows native wiring test",
        system_local_speech=True,
        verified_female_voice_catalog=True,
        offline_speech_recognition=True,
        secure_secret_storage=True,
        desktop_autostart=False,
        native_window_management=False,
        published_installers=(),
    )

    def __init__(self, root: Path) -> None:
        self.paths = PlatformPaths(root, root, root / "cache")

    def set_autostart(
        self,
        enabled: bool,
        *,
        application_id: str,
        command: str,
    ) -> None:
        del enabled, application_id, command

    def open_path(self, path: Path) -> None:
        del path


class _SecretStore:
    def __init__(self) -> None:
        self.value = ""

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


class _BackupManager:
    def __init__(self, _db: object, _backup_dir: Path) -> None:
        return None

    def automatic_if_due(self) -> None:
        return None


def _mono_wave() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(24_000)
        target.writeframes((1_000).to_bytes(2, "little", signed=True) * 480)
    return output.getvalue()


def test_speech_engines_accept_one_explicit_pcm_acceleration_port() -> None:
    accelerator = RecordingPcmAcceleration()
    local = WindowsTTS(pcm_acceleration=accelerator)
    cloud = OpenAITTS(pcm_acceleration=accelerator)
    realtime = RealtimeVoiceClient(pcm_acceleration=accelerator)
    azure = azure_speech.AzureSpeechTTS(pcm_acceleration=accelerator)

    assert local._pcm is accelerator
    assert cloud._pcm is accelerator
    assert realtime._pcm is accelerator
    assert azure._pcm is accelerator


def test_wav_volume_routes_through_the_injected_pcm_port() -> None:
    accelerator = RecordingPcmAcceleration()
    adjusted = apply_wav_volume(
        _mono_wave(),
        125,
        pcm_acceleration=accelerator,
    )

    assert adjusted.startswith(b"RIFF")
    assert accelerator.scale_calls == 1


def test_composition_root_builds_one_accelerator_for_every_pcm_engine() -> None:
    accelerator = RecordingPcmAcceleration()

    def secret_store_factory(
        _path: Path,
        _description: str = "MoHan protected secret",
    ) -> _SecretStore:
        return _SecretStore()

    with TemporaryDirectory(prefix="mohan-native-wiring-") as temp_dir:
        root = Path(temp_dir)
        with (
            patch(
                "application.service_container.NativeAcceleration",
                return_value=accelerator,
            ) as acceleration_factory,
            patch(
                "application.service_container.platform_secret_store_factory",
                return_value=secret_store_factory,
            ),
            patch(
                "application.service_container.BackupManager",
                _BackupManager,
            ),
        ):
            services = service_container.create_default_services(
                root / "data",
                root / "voice_listener.ps1",
                platform_services=_PlatformProbe(root),
            )

        try:
            realtime_output = services.realtime_speech_output
            assert realtime_output is not None
            engines = (
                services.local_tts,
                services.cloud_tts,
                services.realtime,
                services.azure_speech,
                services.azure_hd_speech,
                realtime_output._azure_speech,
                realtime_output._azure_hd_speech,
                realtime_output._local_speech,
            )
            assert acceleration_factory.call_count == 1
            assert all(engine is not None for engine in engines)
            assert all(engine._pcm is accelerator for engine in engines)
        finally:
            services.db.close()
