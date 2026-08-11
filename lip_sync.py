from __future__ import annotations

lazy import math
lazy import sys
lazy from array import array
lazy from dataclasses import dataclass
lazy from itertools import pairwise

VOWEL_FORMANTS = frozendict({
    "A": (800.0, 1200.0),
    "I": (300.0, 2400.0),
    "U": (350.0, 850.0),
    "E": (500.0, 2000.0),
    "O": (500.0, 950.0),
})

# One timing contract is shared by Windows TTS, OpenAI TTS, Azure Speech and
# Realtime. A 20 ms cue matches the Realtime device block and keeps buffered
# WAV providers on the same clock instead of making their lips react at half
# the live-audio rate.
VISEME_CUES_PER_SECOND = 50
VISEME_CONFIRM_FRAMES = frozendict({
    "A": 3,
    "I": 3,
    "U": 3,
    "E": 3,
    "O": 3,
    "CONSONANT": 1,
})
VISEME_SILENCE_CONFIRM_FRAMES = 2
VISEME_MIN_HOLD_SECONDS = frozendict({
    "CLOSED": 0.040,
    "A": 0.075,
    "I": 0.065,
    "U": 0.075,
    "E": 0.065,
    "O": 0.075,
    "CONSONANT": 0.040,
})
VISEME_OPEN_TRANSITION_SECONDS = 0.055
VISEME_CLOSE_TRANSITION_SECONDS = 0.050
VISEME_CHANGE_TRANSITION_SECONDS = 0.050
VALID_VISEMES = frozenset({
    "A",
    "I",
    "U",
    "E",
    "O",
    "CONSONANT",
    "CLOSED",
})
WIDE_VISEMES = frozenset({"A", "I", "O"})
STRONG_JAW_VISEMES = frozenset({"A", "O"})


@dataclass(frozen=True, slots=True)
class VisemeFrame:
    """One UI-independent result from the 50 Hz mouth state machine."""

    previous: str
    selected: str
    jaw_aperture: float
    frame_index: int
    mouth_open: bool
    jaw_weight: float


@dataclass(slots=True)
class VisemeDynamics:
    """Mutable acoustic state with no Qt or speech-provider dependency."""

    smoothed_level: float = 0.0
    candidate: str = "CLOSED"
    candidate_frames: int = 0
    silence_frames: int = 0
    hold_frames: int = 0
    current: str = "CLOSED"
    jaw_aperture: float = 0.0

    def reset(self) -> None:
        self.smoothed_level = 0.0
        self.candidate = "CLOSED"
        self.candidate_frames = 0
        self.silence_frames = 0
        self.hold_frames = 0
        self.current = "CLOSED"
        self.jaw_aperture = 0.0

    def _select_silence(self, held_for: float, minimum_hold: float) -> str:
        self.silence_frames += 1
        self.candidate = "CLOSED"
        self.candidate_frames = 0
        confirmed = (
            self.silence_frames >= VISEME_SILENCE_CONFIRM_FRAMES
            and held_for >= minimum_hold
        )
        return (
            "CLOSED"
            if confirmed or self.smoothed_level < 0.012
            else self.current
        )

    def _select_voiced(
        self,
        vowel: str,
        held_for: float,
        minimum_hold: float,
    ) -> str:
        self.silence_frames = 0
        if vowel == self.candidate:
            self.candidate_frames += 1
        else:
            self.candidate = vowel
            self.candidate_frames = 1
        stable = (
            self.candidate_frames >= VISEME_CONFIRM_FRAMES.get(vowel, 2)
            and held_for >= minimum_hold
        )
        if stable:
            return vowel
        if self.current == "CLOSED":
            return "CONSONANT" if vowel == "CONSONANT" else "E"
        return self.current

    def advance(self, level: float, vowel: str) -> VisemeFrame:
        """Advance one cue while preserving the established timing contract."""
        self.smoothed_level = self.smoothed_level * 0.38 + float(level) * 0.62
        normalized_vowel = str(vowel).upper()
        if normalized_vowel not in VALID_VISEMES:
            normalized_vowel = "E"

        previous = self.current
        self.hold_frames += 1
        held_for = self.hold_frames / VISEME_CUES_PER_SECOND
        minimum_hold = VISEME_MIN_HOLD_SECONDS.get(self.current, 0.065)
        is_silence = (
            self.smoothed_level < 0.035 or normalized_vowel == "CLOSED"
        )
        selected = (
            self._select_silence(held_for, minimum_hold)
            if is_silence
            else self._select_voiced(
                normalized_vowel,
                held_for,
                minimum_hold,
            )
        )

        target_aperture = _target_aperture(selected, self.smoothed_level)
        response = 0.48 if target_aperture > self.jaw_aperture else 0.24
        self.jaw_aperture += (
            target_aperture - self.jaw_aperture
        ) * response
        if selected != "CLOSED":
            self.jaw_aperture = max(0.08, self.jaw_aperture)
        if selected != previous:
            self.hold_frames = 0
        self.current = selected
        return VisemeFrame(
            previous=previous,
            selected=selected,
            jaw_aperture=self.jaw_aperture,
            frame_index=(
                2 if selected in WIDE_VISEMES else int(selected != "CLOSED")
            ),
            mouth_open=selected != "CLOSED",
            jaw_weight=1.0 if selected in STRONG_JAW_VISEMES else 0.55,
        )


def _target_aperture(viseme: str, smoothed_level: float) -> float:
    raw_aperture = max(0.0, min(1.0, (smoothed_level - 0.02) / 0.35))
    if viseme == "CLOSED":
        return 0.0
    if viseme == "CONSONANT":
        return min(0.14, 0.05 + raw_aperture * 0.12)
    return min(0.92, 0.08 + raw_aperture * 0.84)


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
        for previous, current in pairwise(samples)
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
