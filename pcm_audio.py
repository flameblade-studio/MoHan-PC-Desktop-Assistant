from __future__ import annotations

lazy import math
lazy import sys
lazy from array import array
lazy from dataclasses import dataclass


class PcmAudioError(ValueError):
    """Raised when a PCM16 buffer or conversion request is invalid."""


@dataclass(frozen=True)
class Pcm16RateState:
    """Small, serializable state used between streamed resampling chunks."""

    tail_frame: tuple[int, ...]
    phase: int


def _decode_pcm16(data: bytes, channels: int = 1) -> array[int]:
    if channels < 1:
        raise PcmAudioError("channels must be at least one")
    frame_width = channels * 2
    if len(data) % frame_width:
        raise PcmAudioError("PCM16 data must contain complete frames")
    samples = array("h")
    samples.frombytes(data)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def _encode_pcm16(samples: array[int]) -> bytes:
    if sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()


def _clip_pcm16(value: float) -> int:
    return max(-32768, min(32767, math.floor(value)))


def scale_pcm16(data: bytes, factor: float) -> bytes:
    """Scale little-endian signed PCM16 samples with saturation."""
    if not math.isfinite(factor):
        raise PcmAudioError("gain factor must be finite")
    samples = _decode_pcm16(data)
    adjusted = array("h", (_clip_pcm16(sample * factor) for sample in samples))
    return _encode_pcm16(adjusted)


def stereo_to_mono_pcm16(
    data: bytes,
    left_factor: float = 0.5,
    right_factor: float = 0.5,
) -> bytes:
    """Mix interleaved stereo PCM16 into mono PCM16."""
    if not math.isfinite(left_factor) or not math.isfinite(right_factor):
        raise PcmAudioError("mix factors must be finite")
    samples = _decode_pcm16(data, channels=2)
    mixed = array(
        "h",
        (
            _clip_pcm16(
                samples[index] * left_factor
                + samples[index + 1] * right_factor
            )
            for index in range(0, len(samples), 2)
        ),
    )
    return _encode_pcm16(mixed)


def rate_convert_pcm16(
    data: bytes,
    channels: int,
    input_rate: int,
    output_rate: int,
    state: Pcm16RateState | None = None,
) -> tuple[bytes, Pcm16RateState | None]:
    """Linearly resample streamed PCM16 while preserving chunk continuity."""
    if input_rate <= 0 or output_rate <= 0:
        raise PcmAudioError("sample rates must be positive")
    samples = _decode_pcm16(data, channels=channels)
    if input_rate == output_rate:
        return data, None
    if not samples:
        return b"", state

    frames = [
        tuple(samples[index : index + channels])
        for index in range(0, len(samples), channels)
    ]
    if state is None:
        phase = 0
    else:
        if len(state.tail_frame) != channels:
            raise PcmAudioError("resampling state channel count changed")
        frames.insert(0, state.tail_frame)
        phase = state.phase

    last_index = len(frames) - 1
    last_position = last_index * output_rate
    converted = array("h")
    while phase <= last_position:
        source_index, fraction = divmod(phase, output_rate)
        if source_index == last_index and fraction:
            break
        if fraction == 0:
            converted.extend(frames[source_index])
        else:
            next_frame = frames[source_index + 1]
            current_frame = frames[source_index]
            converted.extend(
                _clip_pcm16(
                    current_frame[channel]
                    + (
                        next_frame[channel] - current_frame[channel]
                    )
                    * fraction
                    / output_rate
                )
                for channel in range(channels)
            )
        phase += input_rate

    next_state = Pcm16RateState(
        tail_frame=frames[-1],
        phase=phase - last_position,
    )
    return _encode_pcm16(converted), next_state
