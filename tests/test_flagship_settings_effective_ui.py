from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from PySide6.QtWidgets import QApplication

lazy from domain.performance_preferences import PerformancePreferences
lazy from presentation.flagship_ui import ControlCenterDependencies, FlagshipControlCenter
lazy from infrastructure.db import StudioDB, StudioDBSettingsPort
lazy from infrastructure.performance_preferences_store import (
    PerformancePreferencesStore,
)

TOUCHED_AWAY_MINUTES = 7
EXTERNAL_WELCOME_SECONDS = 300
EXTERNAL_SILENCE_SECONDS = 50 * 60
TOUCHED_SILENCE_MINUTES = 31
TOUCHED_INTENSITY = 80
SELECTED_SCALE = 1.3


@pytest.fixture
def center_env(tmp_path):
    QApplication.instance() or QApplication([])
    db = StudioDB(tmp_path / "mohan.db")
    center = FlagshipControlCenter(
        db,
        tmp_path,
        dependencies=ControlCenterDependencies(),
    )
    try:
        yield db, center
    finally:
        center.close_services()
        center.deleteLater()
        QApplication.processEvents()
        db.close()


def test_proactive_controls_live_inside_the_control_center(center_env) -> None:
    """The three former invisible widgets must be real children of the UI."""

    _db, center = center_env
    for control in (
        center.proactive_mode,
        center.minimum_away_minutes,
        center.conversation_silence_minutes,
        center.performance_view_360,
        center.performance_full_back,
        center.performance_emotional_back,
        center.performance_camera_context,
        center.performance_intensity,
        center.flagship_high_contrast,
        center.flagship_ui_scale,
    ):
        assert center.isAncestorOf(control)
    # The dead remote-tab duplicate of the proactivity master switch is gone;
    # ``companion_enabled`` (the typed store) is the only writer.
    assert not hasattr(center, "proactive_enabled")


def test_untouched_proactive_controls_never_overwrite_saved_values(
    center_env,
) -> None:
    """A save must not clobber values another settings page wrote meanwhile."""

    db, center = center_env
    db.set_setting("proactive_interaction_mode", "quiet")
    db.set_setting(
        "multisensory_welcome_minimum_seconds", EXTERNAL_WELCOME_SECONDS
    )
    db.set_setting(
        "multisensory_conversation_silence_seconds", EXTERNAL_SILENCE_SECONDS
    )
    assert center.save_draft_settings() is True
    assert db.setting("proactive_interaction_mode") == "quiet"
    assert db.setting("multisensory_welcome_minimum_seconds") == (
        EXTERNAL_WELCOME_SECONDS
    )
    assert db.setting("multisensory_conversation_silence_seconds") == (
        EXTERNAL_SILENCE_SECONDS
    )


def test_touched_proactive_controls_persist_and_reset_after_save(
    center_env,
) -> None:
    db, center = center_env
    mode_index = center.proactive_mode.findData("active")
    center.proactive_mode.setCurrentIndex(mode_index)
    center.minimum_away_minutes.setValue(TOUCHED_AWAY_MINUTES)
    center.conversation_silence_minutes.setValue(TOUCHED_SILENCE_MINUTES)
    assert center.save_draft_settings() is True
    assert db.setting("proactive_interaction_mode") == "active"
    assert db.setting("multisensory_welcome_minimum_seconds") == (
        TOUCHED_AWAY_MINUTES * 60
    )
    assert db.setting("multisensory_conversation_silence_seconds") == (
        TOUCHED_SILENCE_MINUTES * 60
    )
    # After the save the controls are untouched again: a later external write
    # survives the next flagship save.
    db.set_setting("proactive_interaction_mode", "balanced")
    assert center.save_draft_settings() is True
    assert db.setting("proactive_interaction_mode") == "balanced"


def test_cancel_restores_proactive_controls_from_persistence(center_env) -> None:
    db, center = center_env
    db.set_setting("proactive_interaction_mode", "active")
    center.minimum_away_minutes.setValue(TOUCHED_AWAY_MINUTES)
    center.cancel_draft_settings()
    assert center.proactive_mode.currentData() == "active"
    assert center.minimum_away_minutes.value() == 1
    assert not center._proactive_interaction_touched


def test_performance_card_saves_through_the_typed_store(center_env) -> None:
    db, center = center_env
    store = PerformancePreferencesStore(StudioDBSettingsPort(db))
    # Conservative domain defaults: every back/360/camera flag starts False.
    defaults = store.load()
    assert defaults == PerformancePreferences()
    assert defaults.view_360_enabled is False
    assert center.performance_view_360.isChecked() is False
    center.performance_view_360.setChecked(True)
    center.performance_emotional_back.setChecked(True)
    center.performance_intensity.setValue(TOUCHED_INTENSITY)
    assert center.save_draft_settings() is True
    saved = store.load()
    assert saved.view_360_enabled is True
    assert saved.emotional_back_view_enabled is True
    assert saved.intensity_percent == TOUCHED_INTENSITY
    assert saved.full_back_view_enabled is False
    assert saved.camera_context_enabled is False


def test_accessibility_controls_write_contrast_and_scale(center_env) -> None:
    db, center = center_env
    assert db.setting("flagship_high_contrast", None) is None
    center.flagship_high_contrast.setChecked(True)
    scale_index = center.flagship_ui_scale.findData(SELECTED_SCALE)
    assert scale_index >= 0
    center.flagship_ui_scale.setCurrentIndex(scale_index)
    assert center.save_draft_settings() is True
    assert db.setting("flagship_high_contrast") is True
    assert float(db.setting("flagship_ui_scale")) == SELECTED_SCALE
