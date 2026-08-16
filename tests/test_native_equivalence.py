from __future__ import annotations

lazy import importlib
lazy import math
lazy import random

lazy import pytest

lazy from application.native_acceleration import NativeAcceleration
lazy from domain import lip_sync, pcm_audio

try:
    NATIVE = importlib.import_module("_mohan_accel")
except ModuleNotFoundError:
    NATIVE = None

pytestmark = pytest.mark.skipif(
    NATIVE is None,
    reason="optional _mohan_accel extension is not built",
)


def _pcm(samples: list[int] | tuple[int, ...]) -> bytes:
    return b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples)


def _assert_float_pair_close(
    actual: tuple[float, float],
    expected: tuple[float, float],
) -> None:
    assert actual == pytest.approx(expected, rel=1e-12, abs=1e-12)


def _native_state(
    state: pcm_audio.Pcm16RateState | None,
) -> tuple[tuple[int, ...], int] | None:
    return None if state is None else (state.tail_frame, state.phase)


def test_native_analysis_matches_python_for_deterministic_audio() -> None:
    generator = random.Random(20260814)
    cases = [
        b"",
        b"\x01",
        bytes(1_920),
        _pcm([32_767, -32_768] * 480),
        _pcm([generator.randint(-32_768, 32_767) for _ in range(960)]),
    ]
    for pcm in cases:
        _assert_float_pair_close(NATIVE.analyze_pcm16(pcm), lip_sync.analyze_pcm16(pcm))


def test_native_analysis_matches_python_for_randomized_frames() -> None:
    generator = random.Random(2026081401)
    for sample_count in (1, 2, 31, 32, 479, 480, 960):
        for _case in range(12):
            pcm = _pcm([
                generator.randint(-32_768, 32_767) for _ in range(sample_count)
            ])
            _assert_float_pair_close(
                NATIVE.analyze_pcm16(pcm),
                lip_sync.analyze_pcm16(pcm),
            )


def test_native_vowel_inference_matches_all_reference_formants() -> None:
    for first, second in lip_sync.VOWEL_FORMANTS.values():
        samples = _pcm([
            int(
                7_000 * math.sin(2 * math.pi * first * index / 24_000)
                + 5_000 * math.sin(2 * math.pi * second * index / 24_000)
            )
            for index in range(960)
        ])
        native_level, native_vowel = NATIVE.infer_vowel_pcm16(samples, 24_000)
        python_level, python_vowel = lip_sync.infer_vowel_pcm16(samples, 24_000)
        assert native_level == pytest.approx(python_level, rel=1e-12, abs=1e-12)
        assert native_vowel == python_vowel


def test_native_vowel_inference_matches_randomized_20_ms_frames() -> None:
    generator = random.Random(2026081403)
    for _case in range(48):
        samples = _pcm([generator.randint(-12_000, 12_000) for _ in range(480)])
        native_level, native_vowel = NATIVE.infer_vowel_pcm16(samples, 24_000)
        python_level, python_vowel = lip_sync.infer_vowel_pcm16(samples, 24_000)
        assert native_level == pytest.approx(python_level, rel=1e-12, abs=1e-12)
        assert native_vowel == python_vowel


def test_native_vowel_inference_matches_python_at_i64_sample_rate_boundary() -> None:
    samples = _pcm([10_000] * 64)
    sample_rate = (1 << 63) - 1
    native_level, native_vowel = NATIVE.infer_vowel_pcm16(samples, sample_rate)
    python_level, python_vowel = lip_sync.infer_vowel_pcm16(samples, sample_rate)
    assert native_level == pytest.approx(python_level, rel=1e-12, abs=1e-12)
    assert native_vowel == python_vowel


@pytest.mark.parametrize("sample_rate", (24_000.0, 1 << 63))
def test_vowel_inference_rejects_sample_rates_outside_native_integer_contract(
    sample_rate: object,
) -> None:
    samples = _pcm([10_000] * 64)
    with pytest.raises((TypeError, ValueError, OverflowError)):
        lip_sync.infer_vowel_pcm16(samples, sample_rate)
    with pytest.raises((TypeError, OverflowError, ValueError)):
        NATIVE.infer_vowel_pcm16(samples, sample_rate)


@pytest.mark.parametrize(
    ("data", "input_rate", "output_rate"),
    ((b"", 1, 2), (_pcm([0]), 1, 1)),
)
def test_invalid_rate_state_is_not_accepted_by_shortcut_paths(
    data: bytes,
    input_rate: int,
    output_rate: int,
) -> None:
    python_state = pcm_audio.Pcm16RateState((0, 1), 0)
    with pytest.raises(pcm_audio.PcmAudioError):
        pcm_audio.rate_convert_pcm16(
            data,
            1,
            input_rate,
            output_rate,
            python_state,
        )
    with pytest.raises(ValueError):
        NATIVE.rate_convert_pcm16(
            data,
            1,
            input_rate,
            output_rate,
            ((0, 1), 0),
        )


def test_native_pcm_operations_match_python_exactly() -> None:
    data = _pcm((-32_768, -20_001, -1_001, 0, 1_001, 20_001, 32_767))
    for factor in (-2.0, -0.5, 0.0, 0.5, 2.0):
        assert NATIVE.scale_pcm16(data, factor) == pcm_audio.scale_pcm16(data, factor)

    stereo = _pcm((1_000, -1_000, 1_001, -1_001, 32_767, 32_767))
    for left, right in ((0.5, 0.5), (1.0, 0.0), (-0.25, 1.25)):
        assert NATIVE.stereo_to_mono_pcm16(stereo, left, right) == (
            pcm_audio.stereo_to_mono_pcm16(stereo, left, right)
        )


def test_native_pcm_operations_are_byte_exact_for_randomized_frames() -> None:
    generator = random.Random(2026081402)
    mono_samples = [generator.randint(-32_768, 32_767) for _ in range(480)]
    mono = _pcm(mono_samples)
    for factor in (-1.75, -0.125, 0.125, 0.73, 1.75):
        assert NATIVE.scale_pcm16(mono, factor) == pcm_audio.scale_pcm16(
            mono,
            factor,
        )

    stereo = _pcm([generator.randint(-32_768, 32_767) for _ in range(480 * 2)])
    for left, right in ((0.2, 0.8), (0.73, -0.31), (-1.0, 1.0)):
        assert NATIVE.stereo_to_mono_pcm16(stereo, left, right) == (
            pcm_audio.stereo_to_mono_pcm16(stereo, left, right)
        )


def test_native_accepts_mutable_buffers_without_reinterpreting_samples() -> None:
    data = _pcm((-32_768, -1, 0, 1, 32_767))
    mutable_data = bytearray(data)
    assert NATIVE.scale_pcm16(mutable_data, 0.5) == pcm_audio.scale_pcm16(
        data,
        0.5,
    )
    _assert_float_pair_close(
        NATIVE.analyze_pcm16(mutable_data),
        lip_sync.analyze_pcm16(data),
    )


def test_native_streamed_rate_conversion_matches_python_exactly() -> None:
    chunks = [_pcm((0, 1_000, 2_000, 3_000)), _pcm((4_000, 5_000))]
    python_state = None
    native_state = None
    for chunk in chunks:
        expected, python_state = pcm_audio.rate_convert_pcm16(
            chunk,
            1,
            4,
            8,
            python_state,
        )
        actual, native_state = NATIVE.rate_convert_pcm16(
            chunk,
            1,
            4,
            8,
            native_state,
        )
        assert actual == expected
        assert native_state == _native_state(python_state)


@pytest.mark.parametrize(
    ("channels", "input_rate", "output_rate"),
    (
        (1, 8_000, 24_000),
        (1, 24_000, 16_000),
        (1, 24_000, 48_000),
        (2, 44_100, 48_000),
        (2, 48_000, 24_000),
    ),
)
def test_native_rate_conversion_is_exact_for_common_stream_rates(
    channels: int,
    input_rate: int,
    output_rate: int,
) -> None:
    generator = random.Random(channels * input_rate + output_rate)
    python_state = None
    native_state = None
    for frame_count in (1, 7, 31, 480):
        chunk = _pcm([
            generator.randint(-32_768, 32_767) for _ in range(frame_count * channels)
        ])
        expected, python_state = pcm_audio.rate_convert_pcm16(
            chunk,
            channels,
            input_rate,
            output_rate,
            python_state,
        )
        actual, native_state = NATIVE.rate_convert_pcm16(
            chunk,
            channels,
            input_rate,
            output_rate,
            native_state,
        )
        assert actual == expected
        assert native_state == _native_state(python_state)


def test_adapter_uses_the_built_native_module_without_failures() -> None:
    accelerator = NativeAcceleration()
    data = _pcm([500, -500] * 240)
    assert accelerator.scale_pcm16(data, 0.75) == pcm_audio.scale_pcm16(data, 0.75)
    status = accelerator.status()
    assert status.available
    assert status.operation_failures == ()
