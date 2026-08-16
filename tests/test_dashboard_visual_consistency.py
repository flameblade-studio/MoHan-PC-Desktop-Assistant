from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QFrame,
    QLabel,
    QPushButton,
    QSplitter,
    QWidget,
)
lazy from presentation.presentation_resources import resource_path
lazy from test_global_settings_actions import close_dashboard
lazy from test_wardrobe_ui import build_language_dashboard


def _frames(page, role: str) -> tuple[QFrame, ...]:
    return tuple(
        frame
        for frame in page.findChildren(QFrame)
        if frame.property("mohanRole") == role
    )


def run() -> None:
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        db, dashboard = build_language_dashboard(Path(temporary), "zh-TW")
        try:
            dashboard.resize(1320, 860)
            dashboard.show()
            application.processEvents()
            assert resource_path(
                "assets/ui/mohan-strategist-lobby-v1.png"
            ).is_file()
            assert dashboard.tabs.count() == 8
            assert dashboard.tabs.tabBar().isHidden()
            brand_line = dashboard._t(
                "dashboard_brand_line",
                "墨色為骨・寒光為心",
            )
            assert sum(
                label.text() == brand_line
                for label in dashboard.findChildren(QLabel)
            ) == 1
            assert len(dashboard.game_navigation_buttons) == 8
            assert all(
                isinstance(button, QPushButton)
                and button.property("mohanAction") == "navigation"
                and button.accessibleName()
                for button in dashboard.game_navigation_buttons
            )
            for index, button in enumerate(dashboard.game_navigation_buttons):
                button.click()
                assert dashboard.tabs.currentIndex() == index
                assert button.isChecked()
                assert sum(
                    candidate.isChecked()
                    for candidate in dashboard.game_navigation_buttons
                ) == 1
            for index in range(dashboard.tabs.count()):
                page = dashboard.tabs.widget(index)
                title = dashboard.tabs.tabText(index)
                if title == "雲裳閣":
                    assert _frames(page, "hero")
                    assert _frames(page, "portraitCard")
                    continue
                assert _frames(page, "pageBanner"), title
                assert _frames(page, "characterStage"), title
                assert _frames(page, "featureDock"), title
                splitter = page.findChild(QSplitter, "featurePageSplitter")
                assert splitter is not None, title
                assert splitter.count() == 2, title
                assert splitter.widget(0).minimumWidth() >= 400, title
                assert splitter.widget(1).minimumWidth() >= 500, title
                assert splitter.widget(1).width() >= 500, title
                portrait = page.findChild(
                    QLabel,
                    "dashboardCharacterStagePortrait",
                )
                assert portrait is not None, title
                assert portrait.pixmap() is not None, title
                assert not portrait.pixmap().isNull(), title
                assert page.property("mohanRole") == "featurePage", title
            settings_index = next(
                index
                for index in range(dashboard.tabs.count())
                if dashboard.tabs.tabText(index) == "設定"
            )
            settings_page = dashboard.tabs.widget(settings_index)
            settings_content = settings_page.findChild(
                QWidget,
                "formScrollContent",
            )
            assert settings_content is not None
            settings_form = settings_content.layout()
            assert isinstance(settings_form, QFormLayout)
            assert settings_form.labelAlignment() & Qt.AlignVCenter
            assert settings_form.labelAlignment() & Qt.AlignRight
        finally:
            close_dashboard(dashboard, db)
    print("DASHBOARD_VISUAL_CONSISTENCY_OK")


if __name__ == "__main__":
    run()
