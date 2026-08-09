from __future__ import annotations

lazy import sys
lazy from array import array
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from pcm_audio import (
    PcmAudioError,
    rate_convert_pcm16,
    scale_pcm16,
    stereo_to_mono_pcm16,
)


def pcm(*samples: int) -> bytes:
    return array("h", samples).tobytes()


def unpack(data: bytes) -> tuple[int, ...]:
    samples = array("h")
    samples.frombytes(data)
    return tuple(samples)


def test_gain_clips_and_preserves_silence() -> None:
    assert unpack(scale_pcm16(pcm(-32768, -1001, 0, 1001, 32767), 0.5)) == (
        -16384,
        -501,
        0,
        500,
        16383,
    )
    assert unpack(scale_pcm16(pcm(-20000, 20000), 2.0)) == (-32768, 32767)
    assert scale_pcm16(pcm(100, -100), 0.0) == pcm(0, 0)


def test_stereo_mix_uses_complete_frames_and_saturates() -> None:
    assert unpack(
        stereo_to_mono_pcm16(pcm(1000, -1000, 1001, -1001, 32767, 32767))
    ) == (0, 0, 32767)
    try:
        stereo_to_mono_pcm16(b"\x00\x00")
    except PcmAudioError:
        pass
    else:
        raise AssertionError("incomplete stereo frame was accepted")


def test_streamed_resampling_is_continuous_across_chunk_boundaries() -> None:
    first, state = rate_convert_pcm16(pcm(0, 1000, 2000, 3000), 1, 4, 8)
    second, state = rate_convert_pcm16(pcm(4000, 5000), 1, 4, 8, state)
    assert unpack(first + second) == (
        0,
        500,
        1000,
        1500,
        2000,
        2500,
        3000,
        3500,
        4000,
        4500,
        5000,
    )
    assert state is not None


def test_downsampling_and_stereo_channels_remain_aligned() -> None:
    converted, _state = rate_convert_pcm16(
        pcm(0, 100, 1000, 1100, 2000, 2100, 3000, 3100),
        2,
        4,
        2,
    )
    assert unpack(converted) == (0, 100, 2000, 2100)


def main() -> None:
    test_gain_clips_and_preserves_silence()
    test_stereo_mix_uses_complete_frames_and_saturates()
    test_streamed_resampling_is_continuous_across_chunk_boundaries()
    test_downsampling_and_stereo_channels_remain_aligned()
    print("PCM_AUDIO_TESTS_OK")


if __name__ == "__main__":
    main()
