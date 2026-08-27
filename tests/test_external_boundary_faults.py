from __future__ import annotations

lazy import json
lazy from pathlib import Path

lazy import pytest
lazy from PySide6.QtCore import QCoreApplication

lazy from integrations import speech as speech_module
lazy from application.self_generating_wardrobe import GeneratedOutfitDraft, _write_draft
lazy from domain.outfit_pack import OutfitPackError
lazy from integrations.speech import MAX_TTS_RESPONSE_BYTES, OpenAITTS
lazy from integrations.speech_recognition import (
    MAX_TRANSCRIPTION_RESPONSE_BYTES,
    TranscriptionHttpBoundary,
    TranscriptionRequest,
    transcribe_wav_bytes_impl,
)


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self, limit: int = -1) -> bytes:
        return self.payload if limit < 0 else self.payload[:limit]


def _app() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


def test_tts_rejects_oversized_audio_without_playback(monkeypatch) -> None:
    _app()
    response = _Response(b"x" * (MAX_TTS_RESPONSE_BYTES + 1))
    monkeypatch.setattr(speech_module, "urlopen", lambda *_a, **_k: response)
    tts = OpenAITTS()
    failures: list[str] = []
    finished: list[bool] = []
    tts.failed.connect(failures.append)
    tts.finished.connect(lambda: finished.append(True))
    generation = tts._begin_generation()

    tts._run("hello", "secret-key", "coral", "", generation)

    assert failures
    assert not finished
    assert "secret-key" not in failures[0]


@pytest.mark.parametrize(
    "payload",
    (
        b"{" + b"x" * MAX_TRANSCRIPTION_RESPONSE_BYTES,
        b"not-json",
        json.dumps({"text": ""}).encode("utf-8"),
    ),
    ids=("oversized", "malformed-json", "empty-transcript"),
)
def test_transcription_rejects_oversized_or_malformed_response(payload: bytes) -> None:
    boundary = TranscriptionHttpBoundary(open_request=lambda *_a, **_k: _Response(payload))

    with pytest.raises(RuntimeError) as caught:
        transcribe_wav_bytes_impl(
            b"RIFF-test",
            "secret-key",
            TranscriptionRequest("gpt-test", "zh"),
            boundary,
        )

    assert "secret-key" not in str(caught.value)


def test_partial_quarantine_write_is_removed_but_existing_job_is_preserved(
    tmp_path: Path,
) -> None:
    broken = GeneratedOutfitDraft(
        {},
        frozendict({"assets/not-a-png.png": b"broken"}),
        frozendict({}),
    )
    partial = tmp_path / "partial-job"
    with pytest.raises(OutfitPackError):
        _write_draft(partial, broken)
    assert not partial.exists()

    existing = tmp_path / "existing-job"
    existing.mkdir()
    marker = existing / "owner-evidence.txt"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError):
        _write_draft(existing, broken)
    assert marker.read_text(encoding="utf-8") == "preserve"
