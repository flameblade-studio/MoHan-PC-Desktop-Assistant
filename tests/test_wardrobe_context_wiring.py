from __future__ import annotations

lazy import os
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy from PySide6.QtCore import QCoreApplication

lazy from infrastructure.db import StudioDB
lazy from presentation.autonomous_outfit_generation_controller import (
    AutonomousOutfitGenerationController,
)
lazy from presentation.companion_speech_emotion import wardrobe_mood_for_state


class _SecretStore:
    def load(self) -> str:
        return "test-api-key"


class _Pool:
    def __init__(self) -> None:
        self.workers: list[object] = []

    def start(self, worker: object) -> None:
        self.workers.append(worker)


class _Scout:
    def discover(self, request):
        del request
        return ()


def test_real_expression_states_feed_stable_wardrobe_moods() -> None:
    assert wardrobe_mood_for_state("happy") == "cheerful"
    assert wardrobe_mood_for_state("gentle_smile_front") == "affectionate"
    assert wardrobe_mood_for_state("worried_front") == "upset"
    assert wardrobe_mood_for_state("reminder") == "focused"
    assert wardrobe_mood_for_state("speaking") is None


def test_saved_trend_switch_injects_factory_and_live_context(tmp_path: Path) -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    del application
    db = StudioDB(tmp_path / "mohan.db")
    db.set_setting("self_outfit_generation_enabled", True)
    db.set_setting("fashion_trend_search_enabled", True)
    db.set_setting("current_mood", "cheerful")
    db.set_setting("mode", "工作")
    calls: list[tuple[str, str]] = []
    scout = _Scout()

    def factory(api_key: str, model: str):
        calls.append((api_key, model))
        return scout

    controller = AutonomousOutfitGenerationController(
        db=db,
        secret_store=_SecretStore(),
        project_root=tmp_path,
        trend_scout_factory=factory,
    )
    controller._running = True
    controller._pool = _Pool()
    statuses: list[str] = []
    controller.status_changed.connect(statuses.append)

    controller.request_generation(explicit=True)

    assert calls and calls[0][0] == "test-api-key"
    assert controller._active_worker is not None
    assert controller._active_worker.wardrobe.trend_scout is scout
    assert controller._active_worker.wardrobe.policy.trend_search_enabled is True
    assert controller._active_worker.request.mood == "cheerful"
    assert controller._active_worker.request.occasion == "work"
    assert statuses[-1] == "generating-with-trend-search"
    db.close()


def test_trend_switch_without_injected_factory_fails_closed(tmp_path: Path) -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    del application
    db = StudioDB(tmp_path / "mohan.db")
    db.set_setting("self_outfit_generation_enabled", True)
    db.set_setting("fashion_trend_search_enabled", True)
    controller = AutonomousOutfitGenerationController(
        db=db,
        secret_store=_SecretStore(),
        project_root=tmp_path,
    )
    controller._running = True
    controller._pool = _Pool()
    statuses: list[str] = []
    controller.status_changed.connect(statuses.append)

    controller.request_generation(explicit=True)

    assert controller._active_worker is not None
    assert controller._active_worker.wardrobe.policy.trend_search_enabled is False
    assert statuses[-1] == "generating"
    db.close()
