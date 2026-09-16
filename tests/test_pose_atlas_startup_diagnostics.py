"""Startup reports rejected assets while preserving the legacy UI."""

from __future__ import annotations

lazy import logging
lazy import os
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import pytest
lazy from PySide6.QtWidgets import QApplication

lazy from application.adaptive_character_composition import (
    AdaptiveCharacterComposition,
)
lazy from domain.safe_error import SafeDiagnostic, SafeError, SafeErrorType
lazy from presentation import companion_core
lazy from presentation.companion_window import CompanionWindow


LOGGER_NAME = "presentation.companion_core"
STARTUP_FAILURE_EVENT = "adaptive_character_startup_failed"
BAIT_SECRET = "NOT-A-REAL-STARTUP-SECRET-42"


@dataclass(frozen=True, slots=True)
class _HealthyDecision:
    should_publish: bool
    used_legacy: bool
    frame: object
    framing: object | None = None


class _HealthyRuntime:
    def __init__(self) -> None:
        self.generation = 0

    def begin_operation(self) -> int:
        self.generation += 1
        return self.generation

    def cancel(self, _generation: int) -> None:
        return None

    def dispatch(self, request: object) -> _HealthyDecision:
        return _HealthyDecision(False, True, request.atomic_frame.body)


class _HealthyFactory:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, _stage_frame) -> AdaptiveCharacterComposition:
        self.calls += 1
        return AdaptiveCharacterComposition(_HealthyRuntime(), SimpleNamespace(enabled=True))


def _startup_event_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if record.name == LOGGER_NAME
        and STARTUP_FAILURE_EVENT in record.getMessage()
    ]


def _window_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOHAN_DATA_DIR", str(tmp_path / "mohan-data"))


def test_hash_rejection_is_safely_logged_and_legacy_ui_survives(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A rejected source disables only adaptive v4 and keeps the character visible."""

    _window_data_dir(tmp_path, monkeypatch)
    application = QApplication.instance() or QApplication([])

    def reject_pose_atlas(*_args: object, **_kwargs: object) -> object:
        raise ValueError(
            "PoseAtlas source hash mismatch for yaw+000-pitch+00; "
            f"token={BAIT_SECRET}; path={tmp_path / 'private-source.png'}"
        )

    monkeypatch.setattr(companion_core, "PoseAtlasAssets", reject_pose_atlas)
    window = None
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        try:
            window = CompanionWindow(
                startup_speech=False,
                defer_visual_startup=True,
                adaptive_character_enabled=True,
            )
        finally:
            if window is not None:
                window.close()
            application.processEvents()

    assert window is not None
    assert window._adaptive_character_enabled is False
    assert window._adaptive_character_composition is None
    assert window._performance_app_bridge is None
    assert window._adaptive_character_startup_error == SafeError(
        SafeErrorType.VALIDATION_ERROR,
        SafeDiagnostic.INVALID_INPUT,
    )
    pixmap = window.character.pixmap()
    assert pixmap is not None and not pixmap.isNull()

    events = _startup_event_records(caplog)
    assert len(events) == 1
    message = events[0].getMessage()
    assert "type=validation_error" in message
    assert "diagnostic=invalid_input" in message
    assert BAIT_SECRET not in message
    assert str(tmp_path) not in message
    assert "PoseAtlas source hash mismatch" not in message


def test_healthy_startup_keeps_empty_safe_error_state_and_no_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _window_data_dir(tmp_path, monkeypatch)
    application = QApplication.instance() or QApplication([])
    factory = _HealthyFactory()
    window = None
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        try:
            window = CompanionWindow(
                startup_speech=False,
                defer_visual_startup=True,
                adaptive_character_factory=factory,
                adaptive_character_enabled=True,
            )
        finally:
            if window is not None:
                window.close()
            application.processEvents()

    assert window is not None
    assert factory.calls == 1
    assert window._adaptive_character_enabled is True
    assert window._adaptive_character_startup_error is None
    assert not _startup_event_records(caplog)


def test_explicitly_disabled_startup_keeps_empty_safe_error_state_and_no_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _window_data_dir(tmp_path, monkeypatch)
    application = QApplication.instance() or QApplication([])
    window = None
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        try:
            window = CompanionWindow(
                startup_speech=False,
                defer_visual_startup=True,
                adaptive_character_enabled=False,
            )
        finally:
            if window is not None:
                window.close()
            application.processEvents()

    assert window is not None
    assert window._adaptive_character_enabled is False
    assert window._adaptive_character_startup_error is None
    assert window._adaptive_character_composition is None
    assert not _startup_event_records(caplog)
