from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from speech_boundary import SpeechTimingCollector, SpeechTimingKind


def run() -> None:
    collector = SpeechTimingCollector(7)
    source = SimpleNamespace(
        audio_offset=5_000_000,
        duration=2_000_000,
        boundary_type=SimpleNamespace(name="Word"),
        text="private text must not be retained",
    )
    word = collector.word_boundary(source)
    assert word is not None
    assert word.operation_id == 7
    assert word.audio_offset_seconds == 0.5
    assert word.duration_seconds == 0.2
    assert word.kind is SpeechTimingKind.WORD
    assert not word.estimated
    assert "private" not in repr(word)
    assert collector.word_boundary(source) is None

    fallback = collector.word_boundary(
        SimpleNamespace(audio_offset=8_000_000, boundary_type="Sentence")
    )
    assert fallback is not None
    assert fallback.kind is SpeechTimingKind.SENTENCE
    assert fallback.duration_seconds == 0.0
    assert fallback.estimated

    viseme = collector.viseme(SimpleNamespace(audio_offset=9_000_000, viseme_id=12))
    assert viseme is not None
    assert viseme.kind is SpeechTimingKind.VISEME
    assert viseme.cue_id == 12
    assert viseme.estimated
    assert collector.viseme(SimpleNamespace(audio_offset=9_000_000, viseme_id=12)) is None
    assert collector.word_boundary(SimpleNamespace(duration=10)) is None
    assert collector.viseme(SimpleNamespace(audio_offset=10)) is None
    print("SPEECH_BOUNDARY_OK")


if __name__ == "__main__":
    run()
