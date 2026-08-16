"""Provider-neutral contract for optional PCM and lip-sync acceleration."""

from __future__ import annotations

lazy from typing import Protocol

lazy from domain import lip_sync, pcm_audio


class PcmAccelerationPort(Protocol):
    """Pure numeric operations that may be supplied by Python or Rust."""

    def analyze_pcm16(self, pcm: bytes) -> tuple[float, float]: ...

    def infer_vowel_pcm16(
        self,
        pcm: bytes,
        sample_rate: int = 24_000,
    ) -> tuple[float, str]: ...

    def scale_pcm16(self, data: bytes, factor: float) -> bytes: ...

    def stereo_to_mono_pcm16(
        self,
        data: bytes,
        left_factor: float = 0.5,
        right_factor: float = 0.5,
    ) -> bytes: ...

    def rate_convert_pcm16(
        self,
        data: bytes,
        channels: int,
        input_rate: int,
        output_rate: int,
        state: pcm_audio.Pcm16RateState | None = None,
    ) -> tuple[bytes, pcm_audio.Pcm16RateState | None]: ...


class PythonPcmAcceleration:
    """Reference implementation and mandatory native-failure fallback."""

    __slots__ = ()

    @staticmethod
    def analyze_pcm16(pcm: bytes) -> tuple[float, float]:
        return lip_sync.analyze_pcm16(pcm)

    @staticmethod
    def infer_vowel_pcm16(
        pcm: bytes,
        sample_rate: int = 24_000,
    ) -> tuple[float, str]:
        return lip_sync.infer_vowel_pcm16(pcm, sample_rate)

    @staticmethod
    def scale_pcm16(data: bytes, factor: float) -> bytes:
        return pcm_audio.scale_pcm16(data, factor)

    @staticmethod
    def stereo_to_mono_pcm16(
        data: bytes,
        left_factor: float = 0.5,
        right_factor: float = 0.5,
    ) -> bytes:
        return pcm_audio.stereo_to_mono_pcm16(
            data,
            left_factor,
            right_factor,
        )

    @staticmethod
    def rate_convert_pcm16(
        data: bytes,
        channels: int,
        input_rate: int,
        output_rate: int,
        state: pcm_audio.Pcm16RateState | None = None,
    ) -> tuple[bytes, pcm_audio.Pcm16RateState | None]:
        return pcm_audio.rate_convert_pcm16(
            data,
            channels,
            input_rate,
            output_rate,
            state,
        )


PYTHON_PCM_ACCELERATION: PcmAccelerationPort = PythonPcmAcceleration()

__all__ = (
    "PYTHON_PCM_ACCELERATION",
    "PcmAccelerationPort",
    "PythonPcmAcceleration",
)
