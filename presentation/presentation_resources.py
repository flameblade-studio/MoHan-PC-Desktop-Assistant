from __future__ import annotations

"""Qt-owned resource helpers shared by desktop presentation modules."""

lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QFont, QIcon, QPixmap
lazy from PySide6.QtWidgets import QApplication

APP_ICON_PATH = "assets/mohan-halfbody.ico"

# Window-local fallback used by direct widget tests.  The application
# composition root installs the complete theme on QApplication in production.
STYLE = """
QWidget { color: #24364a; font-size: 13px; }
QDialog, QMainWindow { background: #eef3f8; }
QTabWidget::pane { border: 1px solid #b9c9d8; border-radius: 12px; background: #ffffff; }
QTabBar::tab { background: #e4ebf3; color: #48647a; padding: 10px 18px; margin: 2px; border-radius: 9px; }
QTabBar::tab:selected { background: #cfe0ee; color: #17344f; font-weight: 600; }
QTabBar::tab:hover { background: #d9e6f0; color: #17344f; }
QLineEdit, QTextBrowser, QTextEdit, QListWidget, QComboBox, QTimeEdit, QSpinBox {
    background: #ffffff; color: #20364a; border: 1px solid #b8c8d6; border-radius: 9px; padding: 7px;
    selection-background-color: #9fc4dc; selection-color: #102a3d;
}
QComboBox QAbstractItemView {
    background: #ffffff; color: #20364a; border: 1px solid #b8c8d6;
    selection-background-color: #cfe0ee; selection-color: #17344f;
    outline: 0;
}
QComboBox QAbstractItemView::item { min-height: 30px; padding: 5px 10px; }
QComboBox QAbstractItemView::item:hover { background: #d9e6f0; color: #17344f; }
QComboBox QAbstractItemView::item:selected { background: #cfe0ee; color: #17344f; }
QComboBox QAbstractItemView::item:disabled { color: #7890a3; background: #f3f6f9; }
QScrollArea#todoScroll { background: #ffffff; border: 1px solid #c3d0dc; border-radius: 10px; }
QScrollArea#formScrollPage { background: #ffffff; border: none; }
QScrollArea#formScrollPage QWidget#qt_scrollarea_viewport { background: #ffffff; }
QWidget#formScrollContent { background: #ffffff; }
QScrollArea#formScrollPage QScrollBar:vertical { background: #edf2f6; width: 14px; margin: 0; }
QScrollArea#formScrollPage QScrollBar::handle:vertical { background: #9eb5c7; min-height: 28px; border-radius: 6px; margin: 2px; }
QScrollArea#formScrollPage QScrollBar::handle:vertical:hover { background: #789bb2; }
QScrollArea#formScrollPage QScrollBar::add-line:vertical,
QScrollArea#formScrollPage QScrollBar::sub-line:vertical { height: 0; background: transparent; }
QScrollArea#formScrollPage QScrollBar::add-page:vertical,
QScrollArea#formScrollPage QScrollBar::sub-page:vertical { background: transparent; }
QWidget#todoViewport, QWidget#todoContainer { background: #ffffff; }
QFrame#todoCard { background: #f5f8fb; border: 1px solid #c3d0dc; border-radius: 10px; }
QLabel#todoTitle { color: #1e3549; font-size: 14px; font-weight: 600; }
QLabel#todoCategory { color: #356d88; font-size: 11px; }
QLabel#sectionCount { color: #356d88; }
QLabel#emptyState { color: #64788a; padding: 24px; }
QLabel#entryFeedback { color: #3f7752; padding-left: 4px; }
QListWidget#ideaList { background: #ffffff; color: #24364a; border: 1px solid #c3d0dc; border-radius: 10px; padding: 6px; }
QListWidget#ideaList::item { background: #f3f7fa; border: 1px solid #c8d4df; border-radius: 7px; margin: 3px; padding: 9px; }
QListWidget#ideaList::item:selected { background: #cfe0ee; color: #17344f; }
QSplitter#todaySplitter::handle { background: #b3c4d1; height: 6px; margin: 2px 0; border-radius: 3px; }
QSplitter#todaySplitter::handle:hover { background: #789bb2; }
QPushButton { background: #dce9f3; color: #17344f; border: 1px solid #8eabc0; border-radius: 10px; padding: 8px 13px; font-weight: 600; }
QPushButton:hover { background: #c9dfed; border-color: #6f96ae; }
QPushButton:pressed { background: #aecbdc; }
QPushButton:disabled { background: #e8edf1; color: #8997a3; border-color: #ccd5dc; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator { width: 20px; height: 20px; background: #ffffff; border: 2px solid #58758a; border-radius: 5px; }
QCheckBox::indicator:hover { border-color: #245f80; background: #f1f7fb; }
QCheckBox::indicator:checked { background: #245f80; border-color: #245f80; image: url(assets/ui/checkmark.svg); }
QCheckBox::indicator:disabled { background: #e7edf2; border-color: #aab7c1; }
QToolTip { background: #ffffff; color: #24364a; border: 1px solid #9eb5c7; padding: 5px; }
QFrame#onboardingHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #dce9f4, stop:0.55 #edf2f7, stop:1 #f6eee7); border: 1px solid #b6c8d6; border-radius: 20px; }
QFrame#onboardingContent { background: #ffffff; border: 1px solid #c4d1dc; border-radius: 20px; }
QLabel#onboardingBrand { color: #17344f; font-size: 30px; font-weight: 700; }
QLabel#onboardingTagline { color: #435f73; font-size: 15px; line-height: 1.35; }
QLabel#onboardingTitle { color: #17344f; font-size: 28px; font-weight: 700; }
QFrame#onboardingContent QLabel { color: #263d50; font-size: 15px; }
QFrame#onboardingContent QLabel#onboardingTitle { color: #17344f; font-size: 28px; font-weight: 700; }
QFrame#onboardingContent QLabel#onboardingNote { color: #355d74; font-size: 14px; }
QFrame#onboardingContent QLineEdit,
QFrame#onboardingContent QComboBox { min-height: 34px; padding: 7px 10px; font-size: 15px; }
QFrame#onboardingContent QPushButton { min-height: 38px; padding: 8px 20px; font-size: 16px; }
QMenu { background: #ffffff; color: #000000; border: 1px solid #aeb6bd; border-radius: 8px; padding: 5px; }
QMenu::item { color: #000000; background: transparent; padding: 7px 18px; border-radius: 6px; }
QMenu::item:selected { color: #000000; background: #dce8ef; }
QMenu::separator { height: 1px; background: #c9ced3; margin: 4px 8px; }
"""

# Light menu/tooltip palette shared by system-level popups (e.g. the tray menu)
# that do not inherit the dashboard's flagship theme.  Keeps items readable on
# the light control-centre palette instead of the OS dark theme.
LIGHT_MENU_STYLE = """
QMenu { background: #ffffff; color: #24364a; border: 1px solid #9eb5c7; border-radius: 8px; padding: 5px; }
QMenu::item { color: #24364a; background: transparent; padding: 7px 18px; border-radius: 6px; }
QMenu::item:selected { color: #17344f; background: #dce8ef; }
QMenu::item:disabled { color: #8997a3; }
QMenu::separator { height: 1px; background: #c9ced3; margin: 4px 8px; }
QToolTip { background: #ffffff; color: #24364a; border: 1px solid #9eb5c7; padding: 5px; }
"""


def application_ui_font() -> QFont:
    font = QFont()
    font.setFamilies(
        [
            "Microsoft JhengHei UI",
            "Microsoft YaHei UI",
            "Yu Gothic UI",
            "Segoe UI",
        ]
    )
    font.setPointSize(10)
    return font


RESOURCE_BASE = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])
)


def resource_path(relative: str) -> Path:
    return RESOURCE_BASE / relative


def application_icon() -> QIcon:
    application = QApplication.instance()
    if application is not None and not application.windowIcon().isNull():
        return application.windowIcon()
    icon_path = resource_path(APP_ICON_PATH)
    icon = QIcon(str(icon_path))
    if icon.isNull():
        raise RuntimeError(f"MoHan application icon could not be loaded: {icon_path}")
    return icon


@dataclass(frozen=True, slots=True)
class FaceRenderLayers:
    """Qt image layers passed through the injected face-renderer port."""

    mouth_source: QPixmap
    mouth_mask: QPixmap
    mouth_rect: QRect
    blink_source: QPixmap | None = None
    blink_mask: QPixmap | None = None
    blush_source: QPixmap | None = None
    blush_mask: QPixmap | None = None


__all__ = (
    "STYLE",
    "FaceRenderLayers",
    "application_icon",
    "application_ui_font",
    "resource_path",
)
