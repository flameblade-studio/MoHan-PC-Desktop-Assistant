from __future__ import annotations

import math
import sys
from array import array


VOWEL_FORMANTS = {
    "A": (800.0, 1200.0),
    "I": (300.0, 2400.0),
    "U": (350.0, 850.0),
    "E": (500.0, 2000.0),
    "O": (500.0, 950.0),
}

# One timing contract is shared by Windows TTS, OpenAI TTS and Realtime.
# Audio is sampled every 40 ms; two matching samples confirm a vowel in
# roughly 80 ms without the 120 ms lag of the former three-sample rule.
VISEME_CUES_PER_SECOND = 25
VISEME_CONFIRM_FRAMES = {
    "A": 2,
    "I": 2,
    "U": 2,
    "E": 2,
    "O": 2,
    "CONSONANT": 1,
}
VISEME_SILENCE_CONFIRM_FRAMES = 2
VISEME_MIN_HOLD_SECONDS = {
    "CLOSED": 0.040,
    "A": 0.075,
    "I": 0.065,
    "U": 0.075,
    "E": 0.065,
    "O": 0.075,
    "CONSONANT": 0.040,
}
VISEME_OPEN_TRANSITION_SECONDS = 0.085
VISEME_CLOSE_TRANSITION_SECONDS = 0.075
VISEME_CHANGE_TRANSITION_SECONDS = 0.055


def _pcm16_samples(pcm: bytes) -> array:
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) - (len(pcm) % 2)])
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def analyze_pcm16(pcm: bytes) -> tuple[float, float]:
    """Return normalized loudness and a rough articulation/brightness cue."""
    if len(pcm) < 4:
        return 0.0, 0.0
    samples = _pcm16_samples(pcm)
    if not samples:
        return 0.0, 0.0
    sum_squares = sum(sample * sample for sample in samples)
    rms = math.sqrt(sum_squares / len(samples))
    loudness = max(0.0, min(1.0, (rms - 90.0) / 6200.0))
    crossings = sum(
        1
        for previous, current in zip(samples, samples[1:])
        if (previous < 0 <= current) or (previous >= 0 > current)
    )
    crossing_rate = crossings / max(1, len(samples) - 1)
    articulation = max(0.0, min(1.0, crossing_rate / 0.24))
    return loudness, articulation


def _goertzel_power(
    samples: list[float],
    sample_rate: int,
    frequency: float,
) -> float:
    coefficient = 2.0 * math.cos(2.0 * math.pi * frequency / sample_rate)
    previous = 0.0
    previous_two = 0.0
    for sample in samples:
        current = sample + coefficient * previous - previous_two
        previous_two = previous
        previous = current
    return max(
        0.0,
        previous_two * previous_two
        + previous * previous
        - coefficient * previous * previous_two,
    )


def infer_vowel_pcm16(
    pcm: bytes,
    sample_rate: int = 24000,
) -> tuple[float, str]:
    """Estimate loudness and an A/I/U/E/O viseme from short mono PCM16."""
    level, articulation = analyze_pcm16(pcm)
    if level < 0.025:
        return level, "CLOSED"
    # Unvoiced consonants and short fricative/plosive attacks have far more
    # zero crossings than sustained vowels. Treat them as a brief neutral
    # consonant pose instead of forcing a false A/I/U/E/O classification.
    if articulation >= 0.48:
        return level, "CONSONANT"
    raw = _pcm16_samples(pcm)
    if len(raw) < 32 or sample_rate <= 0:
        return level, "E"
    mean = sum(raw) / len(raw)
    scale = max(1.0, max(abs(sample - mean) for sample in raw))
    count = len(raw)
    windowed = [
        ((sample - mean) / scale)
        * (0.54 - 0.46 * math.cos(2.0 * math.pi * index / (count - 1)))
        for index, sample in enumerate(raw)
    ]
    candidates = {
        250.0,
        300.0,
        350.0,
        450.0,
        500.0,
        600.0,
        700.0,
        800.0,
        850.0,
        950.0,
        1200.0,
        1600.0,
        2000.0,
        2400.0,
        3000.0,
    }
    powers = {
        frequency: _goertzel_power(windowed, sample_rate, frequency)
        for frequency in candidates
        if frequency < sample_rate / 2
    }
    low_frequencies = [
        frequency for frequency in powers if 250.0 <= frequency <= 850.0
    ]
    high_frequencies = [
        frequency for frequency in powers if 800.0 <= frequency <= 3000.0
    ]
    if not low_frequencies or not high_frequencies:
        return level, "E"
    first_formant = max(low_frequencies, key=powers.get)
    second_formant = max(high_frequencies, key=powers.get)

    def distance(formants: tuple[float, float]) -> float:
        first, second = formants
        return (
            abs(math.log(max(first_formant, 1.0) / first))
            + 0.8 * abs(math.log(max(second_formant, 1.0) / second))
        )

    vowel = min(VOWEL_FORMANTS, key=lambda name: distance(VOWEL_FORMANTS[name]))
    return level, vowel
