from __future__ import annotations

lazy import math
lazy import sys
lazy from array import array
lazy from dataclasses import dataclass

# Re-exported from the centralized constants module for a single source of truth.
lazy from domain.constants import PCM16_MAX_SAMPLE as MAX_PCM16_SAMPLE, PCM16_MIN_SAMPLE as MIN_PCM16_SAMPLE


class PcmAudioError(ValueError):
    """Raised when a PCM16 buffer or conversion request is invalid."""


type Pcm16Buffer = bytes | bytearray

MAX_RATE_CONVERSION_OUTPUT_SAMPLES = 4_194_304
_MAX_SAMPLE_RATE = (1 << 32) - 1
_MAX_RATE_STATE_PHASE = (1 << 64) - 1


@dataclass(frozen=True)
class Pcm16RateState:
    """Small, serializable state used between streamed resampling chunks."""

    tail_frame: tuple[int, ...]
    phase: int


def validate_pcm16_buffer(data: object) -> Pcm16Buffer:
    """Return a supported PCM buffer without copying its bytes."""
    if not isinstance(data, (bytes, bytearray)):
        raise PcmAudioError("PCM16 data must be bytes or bytearray")
    return data


def _validate_integer_range(
    value: object,
    *,
    name: str,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise PcmAudioError(
            f"{name} must be an integer from {minimum} through {maximum}"
        )
    return value


def _validate_finite_factor(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PcmAudioError(f"{name} must be a real number")
    try:
        normalized = float(value)
    except OverflowError as error:
        raise PcmAudioError(f"{name} must fit a finite 64-bit float") from error
    if not math.isfinite(normalized):
        raise PcmAudioError(f"{name} must be finite")
    return normalized


def _validate_pcm16_frames(
    data: object,
    *,
    channels: int,
) -> Pcm16Buffer:
    validated = validate_pcm16_buffer(data)
    frame_width = channels * 2
    if len(validated) % frame_width:
        raise PcmAudioError("PCM16 data must contain complete frames")
    return validated


def validate_scale_pcm16_request(
    data: object,
    factor: object,
) -> tuple[Pcm16Buffer, float]:
    """Validate and normalize one mono PCM16 gain request."""
    validated = _validate_pcm16_frames(data, channels=1)
    return validated, _validate_finite_factor(factor, name="gain factor")


def validate_stereo_to_mono_pcm16_request(
    data: object,
    left_factor: object,
    right_factor: object,
) -> tuple[Pcm16Buffer, float, float]:
    """Validate and normalize one interleaved stereo-mix request."""
    validated = _validate_pcm16_frames(data, channels=2)
    left = _validate_finite_factor(left_factor, name="left mix factor")
    right = _validate_finite_factor(right_factor, name="right mix factor")
    return validated, left, right


def validate_pcm16_rate_state(
    state: object,
    *,
    channels: int,
) -> Pcm16RateState | None:
    """Validate immutable streamed-resampling state without transforming it."""
    if state is None:
        return None
    if not isinstance(state, Pcm16RateState):
        raise PcmAudioError("resampling state has an invalid type")
    if not isinstance(state.tail_frame, tuple):
        raise PcmAudioError("resampling state tail frame must be a tuple")
    if len(state.tail_frame) != channels:
        raise PcmAudioError("resampling state channel count changed")
    _validate_integer_range(
        state.phase,
        name="resampling state phase",
        minimum=0,
        maximum=_MAX_RATE_STATE_PHASE,
    )
    if any(
        isinstance(sample, bool)
        or not isinstance(sample, int)
        or not MIN_PCM16_SAMPLE <= sample <= MAX_PCM16_SAMPLE
        for sample in state.tail_frame
    ):
        raise PcmAudioError("resampling state is outside the PCM16 contract")
    return state


def validate_rate_conversion_request_size(
    data_size: int,
    channels: int,
    input_rate: int,
    output_rate: int,
    state: Pcm16RateState | None = None,
) -> None:
    """Reject malformed or amplifying requests before allocating output."""
    data_size = _validate_integer_range(
        data_size,
        name="PCM16 data size",
        minimum=0,
        maximum=sys.maxsize,
    )
    channels = _validate_integer_range(
        channels,
        name="channel count",
        minimum=1,
        maximum=sys.maxsize,
    )
    input_rate = _validate_integer_range(
        input_rate,
        name="input sample rate",
        minimum=1,
        maximum=_MAX_SAMPLE_RATE,
    )
    output_rate = _validate_integer_range(
        output_rate,
        name="output sample rate",
        minimum=1,
        maximum=_MAX_SAMPLE_RATE,
    )
    frame_width = channels * 2
    if data_size % frame_width:
        raise PcmAudioError("PCM16 data must contain complete frames")
    state = validate_pcm16_rate_state(state, channels=channels)
    if input_rate == output_rate or data_size == 0:
        return

    frame_count = data_size // frame_width
    phase = 0
    if state is not None:
        frame_count += 1
        phase = state.phase

    last_position = (frame_count - 1) * output_rate
    output_frames = (
        0
        if phase > last_position
        else (last_position - phase) // input_rate + 1
    )
    if output_frames * channels > MAX_RATE_CONVERSION_OUTPUT_SAMPLES:
        raise PcmAudioError("resampling output size exceeds the supported limit")


def validate_rate_conversion_request(
    data: object,
    channels: int,
    input_rate: int,
    output_rate: int,
    state: Pcm16RateState | None = None,
) -> Pcm16Buffer:
    """Validate one streamed conversion request without decoding its audio."""
    validated = validate_pcm16_buffer(data)
    validate_rate_conversion_request_size(
        len(validated),
        channels,
        input_rate,
        output_rate,
        state,
    )
    return validated


def _decode_pcm16(data: Pcm16Buffer) -> array[int]:
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


def scale_pcm16(data: Pcm16Buffer, factor: float) -> bytes:
    """Scale little-endian signed PCM16 samples with saturation."""
    data, factor = validate_scale_pcm16_request(data, factor)
    samples = _decode_pcm16(data)
    adjusted = array("h", (_clip_pcm16(sample * factor) for sample in samples))
    return _encode_pcm16(adjusted)


def stereo_to_mono_pcm16(
    data: Pcm16Buffer,
    left_factor: float = 0.5,
    right_factor: float = 0.5,
) -> bytes:
    """Mix interleaved stereo PCM16 into mono PCM16."""
    data, left_factor, right_factor = validate_stereo_to_mono_pcm16_request(
        data,
        left_factor,
        right_factor,
    )
    samples = _decode_pcm16(data)
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
    data: Pcm16Buffer,
    channels: int,
    input_rate: int,
    output_rate: int,
    state: Pcm16RateState | None = None,
) -> tuple[bytes, Pcm16RateState | None]:
    """Linearly resample streamed PCM16 while preserving chunk continuity."""
    data = validate_rate_conversion_request(
        data,
        channels,
        input_rate,
        output_rate,
        state,
    )
    samples = _decode_pcm16(data)
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
