"""The Wardrobe Pavilion preview shows the composed look through the runtime path.

The preview composes each of its four views with the same full-body renderer
and active-outfit overlay the desktop companion uses, honouring the selected
outfit, makeup choice and intensity; composites are cached per appearance
signature and built on a short timer once the tab is visible.  Without a
compositor (offline dashboards) it falls back to the bare base and says so.
"""

from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtGui import QColor, QImage
lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.db import StudioDB
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.dashboard_wardrobe_preview import STATE_COMPOSITED, STATE_FALLBACK
lazy from presentation.dashboard_window import Dashboard
lazy from test_gesture_app_wiring import offline_presentation_ports
lazy from test_global_settings_actions import (
    FakeListener,
    FakeSecretStore,
    OfflinePlatformServices,
    close_dashboard,
    dependencies,
    fake_secret_store_factory,
)

WARDROBE_TAB = "雲裳閣"
POSE_ATLAS = ROOT / "assets" / "pose-atlas" / "v5-base"
FULL_BODY_SIZE = (1024, 1536)
FRONT_BUTTON, BACK_BUTTON = 0, 3
# Probe pixels recorded by tools/assemble_official_default_pack.py for yaw+000: a robe
# pixel over the grey base and the strongest lip pixel of the built-in classic makeup.
TORSO = (488, 585)
LIPS = (552, 292)
# Back view: the robe covers the lower back below the loose hair.
BACK_BAND = (380, 700, 260, 200)
MIN_BACK_ROBE_PIXELS = 500
BLUE_MARGIN = 40
GREY_TOLERANCE = 12
COMPOSE_TIMEOUT_MS = 60_000
POLL_MS = 50
CLASSIC_MAKEUP = "builtin/classic"
BARE_MAKEUP = "none"


def _dependencies(root: Path) -> DashboardDependencies:
    """Offline dashboard services plus the real overlay and full-body compositor."""
    store = root / "outfits"  # the dashboard uses ``db.path.parent / "outfits"``
    ports = replace(
        offline_presentation_ports(),
        outfit_overlay_factory=lambda **options: ActiveOutfitOverlay(store, ROOT, **options),
        full_body_renderer_factory=lambda outfit_overlay=None: LayeredFullBodyRenderer(
            outfit_overlay=outfit_overlay
        ),
    )
    secret_store = FakeSecretStore()
    return DashboardDependencies(
        listener=FakeListener(),
        secret_store=secret_store,
        azure_secret_store=secret_store,
        azure_hd_secret_store=secret_store,
        secret_store_factory=fake_secret_store_factory,
        platform_services=OfflinePlatformServices(root),
        presentation_ports=ports,
    )


def _build(root: Path, services: DashboardDependencies) -> tuple[StudioDB, Dashboard]:
    db = StudioDB(root / "mohan-preview.db")
    db.set_setting("onboarding_complete", True)
    db.set_setting("ui_language", "zh-TW")
    with patch.object(QTimer, "start", return_value=None):
        dashboard = Dashboard(db, services)
    dashboard.show()
    QApplication.processEvents()
    return db, dashboard


def _open_wardrobe(dashboard: Dashboard) -> None:
    tabs = dashboard.tabs
    names = [tabs.tabText(index) for index in range(tabs.count())]
    tabs.setCurrentIndex(names.index(WARDROBE_TAB))
    QApplication.processEvents()


def _wait_composited(dashboard: Dashboard) -> None:
    waited = 0
    while dashboard._wardrobe_preview_state != STATE_COMPOSITED and waited < COMPOSE_TIMEOUT_MS:
        QTest.qWait(POLL_MS)
        waited += POLL_MS
    assert dashboard._wardrobe_preview_state == STATE_COMPOSITED, dashboard._wardrobe_preview_state


def _is_grey(color: QColor) -> bool:
    red, green, blue, _alpha = color.getRgb()
    return abs(red - green) <= GREY_TOLERANCE and abs(green - blue) <= GREY_TOLERANCE


def _robe_over_grey(bare: QImage, composed: QImage, band: tuple[int, int, int, int]) -> int:
    x0, y0, width, height = band
    count = 0
    for y in range(y0, y0 + height):
        for x in range(x0, x0 + width):
            after = composed.pixelColor(x, y)
            if _is_grey(bare.pixelColor(x, y)) and after.blue() - after.red() >= BLUE_MARGIN:
                count += 1
    return count


def test_preview_composites_the_active_look_through_the_runtime() -> None:
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        db, dashboard = _build(root, _dependencies(root))
        try:
            _open_wardrobe(dashboard)
            _wait_composited(dashboard)
            front = dashboard._wardrobe_pose_source
            assert front.size().toTuple() == FULL_BODY_SIZE
            bare_front = QImage(str(POSE_ATLAS / "yaw+000-pitch+00.png"))
            assert _is_grey(bare_front.pixelColor(*TORSO))
            torso = front.toImage().pixelColor(*TORSO)
            assert torso.blue() - torso.red() >= BLUE_MARGIN
            shown = dashboard.wardrobe_character_preview.pixmap()
            assert shown is not None and not shown.isNull()
            assert dashboard.wardrobe_preview_state_label.text() == ""
            # A cached view is re-shown at once, without scheduling another composite.
            dashboard.wardrobe_pose_buttons[FRONT_BUTTON].click()
            application.processEvents()
            assert not dashboard._wardrobe_preview_pending
            assert dashboard._wardrobe_preview_state == STATE_COMPOSITED
            # The back view is not the bare base either.
            dashboard.wardrobe_pose_buttons[BACK_BUTTON].click()
            application.processEvents()
            _wait_composited(dashboard)
            back = dashboard._wardrobe_pose_source.toImage()
            bare_back = QImage(str(POSE_ATLAS / "yaw-180-pitch+00.png"))
            assert back != bare_back
            assert _robe_over_grey(bare_back, back, BACK_BAND) >= MIN_BACK_ROBE_PIXELS
            # Makeup "none" versus "classic" changes the lip region of the composed preview.
            dashboard.wardrobe_pose_buttons[FRONT_BUTTON].click()
            application.processEvents()
            _wait_composited(dashboard)
            classic_lips = dashboard._wardrobe_pose_source.toImage().pixelColor(*LIPS)
            selector = dashboard.wardrobe_makeup_selector
            assert selector.currentData() == CLASSIC_MAKEUP
            selector.setCurrentIndex(selector.findData(BARE_MAKEUP))
            application.processEvents()
            _wait_composited(dashboard)
            bare_lips = dashboard._wardrobe_pose_source.toImage().pixelColor(*LIPS)
            assert bare_lips != classic_lips
            selector.setCurrentIndex(selector.findData(CLASSIC_MAKEUP))
            application.processEvents()
            _wait_composited(dashboard)
            assert dashboard._wardrobe_pose_source.toImage().pixelColor(*LIPS) == classic_lips
        finally:
            close_dashboard(dashboard, db)


def test_offline_dashboard_without_compositor_flags_the_bare_preview() -> None:
    """No compositor injected: the bare base is shown synchronously and the status says so."""
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        db, dashboard = _build(root, dependencies(root))
        try:
            _open_wardrobe(dashboard)
            assert dashboard._wardrobe_full_body_renderer is None
            assert dashboard._wardrobe_preview_state == STATE_FALLBACK
            assert not dashboard._wardrobe_preview_pending
            assert dashboard.wardrobe_service.appearance_active()
            assert dashboard.wardrobe_status.text() == dashboard._t(
                "wardrobe_preview_fallback",
                "造型預覽暫時無法合成，目前顯示素體；桌面伴侶不受影響。",
            )
            shown = dashboard.wardrobe_character_preview.pixmap()
            assert shown is not None and not shown.isNull()
        finally:
            close_dashboard(dashboard, db)
