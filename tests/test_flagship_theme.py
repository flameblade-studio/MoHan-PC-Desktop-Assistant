from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

lazy from presentation.flagship_theme import (
    apply_flagship_theme,
    create_flagship_ornament,
    mark_flagship_card,
)

SRGB_LINEARIZATION_THRESHOLD = 0.04045
MIN_CONTRAST_RATIO = 4.5
EXPECTED_SCALE = 1.35
THEMED_SCROLL_AREA_COUNT = 4
WRAPPED_LABEL_COUNT = 4
MAX_SCALE = 2.0
MIN_SCALE = 0.85
TAB_COUNT = 4


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92
        if value <= SRGB_LINEARIZATION_THRESHOLD
        else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground: str, background: str) -> float:
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def assert_control_text_contrast() -> None:
    pairs = (
        ("#273047", "#fffdf9"),
        ("#273047", "#e8edf8"),
        ("#ffffff", "#5a4f9f"),
        ("#ffffff", "#6658ad"),
        ("#ffffff", "#3f6288"),
        ("#fff9f0", "#3a4389"),
        ("#f8f5ff", "#46519d"),
    )
    for foreground, background in pairs:
        assert _contrast_ratio(foreground, background) >= MIN_CONTRAST_RATIO


def _fixture() -> tuple[QWidget, QTabWidget, QScrollArea, QLabel, QLineEdit]:
    root = QWidget()
    layout = QVBoxLayout(root)
    tabs = QTabWidget()
    for title in (
        "繁體中文設定頁面標籤",
        "简体中文设置页面标签",
        "English settings page with a deliberately long label",
        "日本語の非常に長い設定ページラベル",
    ):
        scroll = QScrollArea()
        content = QWidget()
        form = QFormLayout(content)
        long_label = QLabel(
            "這是一段足以驗證四語長文換行、不截斷內容與鍵盤選取能力的說明文字。"
        )
        editor = QLineEdit()
        form.addRow(long_label, editor)
        scroll.setWidget(content)
        tabs.addTab(scroll, title)
    layout.addWidget(tabs)
    button = QPushButton("Apply")
    layout.addWidget(button)
    first_scroll = tabs.widget(0)
    first_label = first_scroll.widget().findChild(QLabel)
    first_editor = first_scroll.widget().findChild(QLineEdit)
    return root, tabs, first_scroll, first_label, first_editor


def assert_theme_contract(app: QApplication) -> None:
    root, tabs, scroll, long_label, editor = _fixture()
    result = apply_flagship_theme(root, scale=1.35)
    root.show()
    app.processEvents()

    assert root.property("mohanFlagshipTheme") is True
    assert result.scale == EXPECTED_SCALE
    assert result.themed_tabs == 1
    assert result.themed_scroll_areas == THEMED_SCROLL_AREA_COUNT
    assert result.wrapped_labels == WRAPPED_LABEL_COUNT
    assert tabs.tabBar().usesScrollButtons()
    assert tabs.tabBar().elideMode() == Qt.ElideRight
    assert tabs.tabBar().focusPolicy() == Qt.StrongFocus
    assert scroll.widgetResizable()
    assert scroll.frameShape() == QFrame.NoFrame
    assert long_label.wordWrap()
    assert editor.focusPolicy() == Qt.StrongFocus
    assert "#347fa5" in root.styleSheet().lower()

    repeated = apply_flagship_theme(root, scale=9.0)
    assert repeated.scale == MAX_SCALE
    assert tabs.count() == TAB_COUNT
    root.close()


def assert_high_contrast_and_ornament(app: QApplication) -> None:
    root, *_ = _fixture()
    result = apply_flagship_theme(root, high_contrast=True, scale=0.1)
    assert result.high_contrast
    assert result.scale == MIN_SCALE
    stylesheet = root.styleSheet().lower()
    assert "#071b2d" in stylesheet
    assert "#a63d00" in stylesheet

    card = QFrame(root)
    mark_flagship_card(card)
    assert card.property("mohanRole") == "card"

    ornament = create_flagship_ornament(root, size=96)
    assert ornament.property("mohanRole") == "ornament"
    assert ornament.focusPolicy() == Qt.NoFocus
    assert ornament.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert not ornament.pixmap().isNull()
    root.close()
    app.processEvents()


def run() -> None:
    app = QApplication.instance() or QApplication([])
    assert_theme_contract(app)
    assert_high_contrast_and_ornament(app)
    assert_control_text_contrast()
    print("FLAGSHIP_THEME_OK")


if __name__ == "__main__":
    run()
