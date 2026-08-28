from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from presentation.flagship_ui import FlagshipControlCenter
lazy from infrastructure.db import StudioDB
lazy from application.vision_runtime import VisionHealth, VisionReadiness


def assert_close_stops_every_owned_timer(
    application: QApplication,
    center: FlagshipControlCenter,
) -> None:
    extra_timer = QTimer(center)
    extra_timer.start(1)
    assert center.camera_restore_timer.isActive()
    assert any(timer.isActive() for timer in center.findChildren(QTimer))

    center.close_services()
    assert center._closed
    assert all(
        not timer.isActive()
        for timer in center.findChildren(QTimer)
    )
    center.close_services()  # idempotent shutdown
    application.processEvents()


def assert_late_callbacks_are_inert_after_close(
    application: QApplication,
    center: FlagshipControlCenter,
) -> None:
    with (
        patch.object(center.camera_presence, "start") as camera_start,
        patch.object(center.db, "set_setting") as set_setting,
        patch.object(center, "_refresh_face_profiles") as refresh_profiles,
    ):
        center._restore_camera_if_enabled()
        center._planner_timed_out()
        center._cloud_test_timed_out()
        center._cloud_test_done("google", {}, center._cloud_test_generation)
        center._cloud_connected("google", {})
        center._cloud_failed("google", "late failure")
        center._vision_health_changed(VisionHealth(VisionReadiness.READY))
        center._vision_scene_changed(object())
        center._enrollment_progress(1, 5)
        center._enrollment_completed("late identity")
        center._enrollment_failed("late failure")
        center._camera_status_changed("late status")
        center._presence_changed(True)
        center._drain_remote_commands()
        center._refresh_screen_cache()
        center.run_due_workflows()
        application.processEvents()
    camera_start.assert_not_called()
    set_setting.assert_not_called()
    refresh_profiles.assert_not_called()


def assert_delete_later_has_no_camera_restore_race(
    application: QApplication,
    root: Path,
) -> None:
    db = StudioDB(root / "delete-later.db")
    db.set_setting("camera_presence_enabled", True)
    center = FlagshipControlCenter(db, root)
    with patch.object(center.camera_presence, "start") as camera_start:
        center.close_services()
        db.close()
        center.deleteLater()
        application.processEvents()
        application.sendPostedEvents()
        application.processEvents()
    camera_start.assert_not_called()


def run() -> None:
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        db = StudioDB(root / "lifecycle.db")
        center = FlagshipControlCenter(db, root)
        assert_close_stops_every_owned_timer(application, center)
        assert_late_callbacks_are_inert_after_close(application, center)
        db.close()
        center.deleteLater()
        application.processEvents()
        assert_delete_later_has_no_camera_restore_race(application, root)
    print("FLAGSHIP_LIFECYCLE_OK")


if __name__ == "__main__":
    run()
