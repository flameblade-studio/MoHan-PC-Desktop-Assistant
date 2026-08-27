from __future__ import annotations

lazy import os
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from types import SimpleNamespace
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy from PySide6.QtCore import QCoreApplication

lazy from infrastructure.db import StudioDB
lazy from presentation.autonomous_outfit_generation_controller import (
    LAST_ATTEMPT_KEY,
    PENDING_JOB_KEY,
    AutonomousOutfitGenerationController,
)
lazy from application.self_generating_wardrobe import GeneratedOutfitResult
lazy from presentation.dashboard_shell import DashboardShellMixin


class _SecretStore:
    def load(self) -> str:
        return "test-api-key"


EXPECTED_STATUS_RELOADS = 2


class _Pool:
    def __init__(self) -> None:
        self.workers: list[object] = []

    def start(self, worker: object) -> None:
        self.workers.append(worker)


class _WidgetProbe:
    def __init__(self) -> None:
        self.enabled = True
        self.text = ""

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def setText(self, text: str) -> None:
        self.text = text


class _DashboardProbe:
    def __init__(self) -> None:
        self.wardrobe_status = _WidgetProbe()
        self.wardrobe_generate_button = _WidgetProbe()
        self.reloads = 0

    def _reload_wardrobe_packages(self) -> None:
        self.reloads += 1

    @staticmethod
    def _t(_key: str, fallback: str, **_values: object) -> str:
        return fallback


def test_trend_generation_keeps_chargeable_button_disabled() -> None:
    dashboard = _DashboardProbe()

    DashboardShellMixin.set_outfit_generation_status(
        dashboard,
        "generating-with-trend-search",
    )
    assert not dashboard.wardrobe_generate_button.enabled

    DashboardShellMixin.set_outfit_generation_status(dashboard, "installed")
    assert dashboard.wardrobe_generate_button.enabled
    assert dashboard.reloads == 1

    DashboardShellMixin.set_outfit_generation_status(
        dashboard,
        "installed-manual-lock",
    )
    assert dashboard.reloads == EXPECTED_STATUS_RELOADS


def test_explicit_generation_bypasses_only_the_unattended_backoff() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    del application
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        db = StudioDB(root / "mohan.db")
        db.set_setting("self_outfit_generation_enabled", True)
        db.set_setting(LAST_ATTEMPT_KEY, datetime.now(UTC).isoformat())
        controller = AutonomousOutfitGenerationController(
            db=db,
            secret_store=_SecretStore(),
            project_root=root,
        )
        controller._running = True
        statuses: list[str] = []
        controller.status_changed.connect(statuses.append)
        controller._create_wardrobe = lambda api_key: object()
        controller._pool = _Pool()

        controller.request_generation()
        assert statuses == ["cooldown-blocked"]
        assert controller._active_worker is None

        controller.request_generation(explicit=True)
        assert statuses[-1] == "generating"
        assert controller._active_worker is not None
        assert controller._active_worker.request.user_initiated is True
        assert len(controller._pool.workers) == 1

        cache_root = root / "outfit-generation-cache"
        completed = cache_root / "job-123"
        completed.mkdir(parents=True)
        (completed / "garment-front.png").write_bytes(b"checkpoint")
        controller._discard_completed_checkpoints("job-123")
        assert not completed.exists()

        cleanup_blocked = cache_root / "job-cleanup-blocked"
        cleanup_blocked.mkdir(parents=True)
        with patch(
            "presentation.autonomous_outfit_generation_controller.shutil.rmtree",
            side_effect=OSError("locked"),
        ):
            controller._discard_completed_checkpoints("job-cleanup-blocked")
        assert cleanup_blocked.is_dir()

        sibling = root / "must-not-delete"
        sibling.mkdir()
        controller._discard_completed_checkpoints("../must-not-delete")
        assert sibling.is_dir()

        db.set_setting(PENDING_JOB_KEY, "job-quarantined")
        resumable = cache_root / "job-quarantined"
        resumable.mkdir(parents=True)
        (resumable / "garment-front.png").write_bytes(b"checkpoint")
        quarantine = root / "outfit-quarantine" / "job-quarantined"
        quarantine.mkdir(parents=True)
        controller._completed(
            GeneratedOutfitResult(
                "quarantined",
                quarantine,
                None,
                None,
                ("garment:front:face-overlap",),
            )
        )
        assert db.setting(PENDING_JOB_KEY, "missing") == ""
        assert not resumable.exists()
        assert quarantine.is_dir()
        assert statuses[-1] == "quarantined"

        applied: list[str] = []
        controller._wardrobe_service = SimpleNamespace(apply=applied.append)
        controller._completed(
            GeneratedOutfitResult(
                "installed",
                quarantine,
                root / "outfits" / "packages" / "generated.mohan-outfit",
                SimpleNamespace(
                    pack_id="generated",
                    ensembles=(SimpleNamespace(ensemble_id="weather-look"),),
                ),
                (),
            )
        )
        assert applied == ["generated/weather-look"]
        assert statuses[-1] == "installed"

        applied.clear()
        db.set_setting(
            "wardrobe_manual_lock_until",
            (datetime.now(UTC).replace(microsecond=0) + timedelta(hours=2)).isoformat(),
        )
        controller._completed(
            GeneratedOutfitResult(
                "installed",
                quarantine,
                root / "outfits" / "packages" / "locked.mohan-outfit",
                SimpleNamespace(
                    pack_id="locked",
                    ensembles=(SimpleNamespace(ensemble_id="formal-look"),),
                ),
                (),
            )
        )
        assert applied == []
        assert statuses[-1] == "installed-manual-lock"
        db.close()


if __name__ == "__main__":
    test_explicit_generation_bypasses_only_the_unattended_backoff()
    print("OUTFIT_GENERATION_UI_BRIDGE_OK")
