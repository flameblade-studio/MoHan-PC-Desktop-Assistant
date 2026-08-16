from __future__ import annotations

lazy from dataclasses import dataclass

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPixmap
lazy from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QFrame,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QWidget,
)

lazy from presentation.presentation_resources import resource_path

__all__ = (
    "FlagshipThemeResult",
    "apply_flagship_theme",
    "create_flagship_ornament",
    "mark_flagship_card",
)


@dataclass(frozen=True, slots=True)
class FlagshipThemeResult:
    """Observable result of applying the decorative control-centre theme."""

    high_contrast: bool
    scale: float
    themed_tabs: int
    themed_scroll_areas: int
    wrapped_labels: int


_MINIMUM_SCALE = 0.85
_MAXIMUM_SCALE = 2.0
_LONG_LABEL_THRESHOLD = 34
_LONG_LABEL_PIXEL_WIDTH = 320
_THEME_ASSET = resource_path("assets/ui/mohan-cloud.svg")
_LOBBY_BACKDROP = resource_path("assets/ui/mohan-strategist-lobby-v1.png")


def _scaled(value: int, scale: float) -> int:
    return max(1, round(value * scale))


def _theme_stylesheet(scale: float, *, high_contrast: bool) -> str:
    if high_contrast:
        colors = {
            "ink": "#071b2d",
            "muted": "#29485f",
            "surface": "#ffffff",
            "wash": "#e8f3fb",
            "line": "#315f7d",
            "silver": "#d8e8f2",
            "glow": "#0078b8",
            "focus": "#0078b8",
            "disabled": "#687985",
            "action": "#a63d00",
        }
    else:
        colors = {
            "ink": "#273047",
            "muted": "#596781",
            "surface": "#fffaf7",
            "wash": "#edf2ff",
            "line": "#9aaed0",
            "silver": "#dce6f5",
            "glow": "#7189c7",
            "focus": "#f0d58b",
            "disabled": "#667085",
            "action": "#6d67b7",
        }
    radius = _scaled(12, scale)
    padding_y = _scaled(8, scale)
    padding_x = _scaled(13, scale)
    tab_padding_y = _scaled(9, scale)
    tab_padding_x = _scaled(15, scale)
    scroll_width = _scaled(14, scale)
    focus_width = _scaled(2, scale)
    lobby_backdrop = _LOBBY_BACKDROP.as_posix()
    return f"""
QWidget[mohanFlagshipTheme="true"] {{
    color: #24375f;
    background: qradialgradient(
        cx:0.52, cy:0.35, radius:0.92,
        fx:0.52, fy:0.35,
        stop:0 #fff7fb, stop:0.30 #edf3ff,
        stop:0.68 #d8ddfa, stop:1 #aeb8e7
    );
}}
QWidget[mohanFlagshipTheme="true"] QLabel {{
    color: {colors['ink']};
    background: transparent;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="commandDeck"] {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(53, 67, 133, 248),
        stop:0.50 rgba(91, 94, 172, 246),
        stop:1 rgba(142, 91, 150, 246)
    );
    border: 1px solid #d8c4f2;
    border-radius: {_scaled(16, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="commandDeck"] QLabel {{
    color: #fff7fb;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="commandDeck"] QLabel[mohanRole="muted"] {{
    color: #ead8e2;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="commandDeck"] QLabel[mohanRole="headerStatus"] {{
    color: #f7dce9;
    font-size: {_scaled(16, scale)}px;
    font-weight: 600;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="commandFooter"] {{
    background: rgba(61, 72, 137, 236);
    border: 1px solid #d2c4ed;
    border-radius: {_scaled(14, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QWidget[mohanRole="featurePage"] {{
    background: transparent;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="gameLobby"] {{
    background: transparent;
    border-image: url("{lobby_backdrop}") 0 0 0 0 stretch stretch;
    border: 1px solid #c9bee8;
    border-radius: {_scaled(20, scale)}px;
    padding: {_scaled(7, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="gameNavigation"] {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(70, 81, 157, 246),
        stop:0.52 rgba(98, 93, 172, 244),
        stop:1 rgba(125, 91, 154, 244)
    );
    border: 1px solid #d7cdf4;
    border-radius: {_scaled(20, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="navigationTitle"] {{
    color: #fff9ff;
    font-family: "DFKai-SB", "KaiTi", "Microsoft JhengHei UI";
    font-size: {_scaled(18, scale)}px;
    font-weight: 700;
}}
QWidget[mohanFlagshipTheme="true"] QPushButton[mohanAction="navigation"] {{
    color: #f8f5ff;
    text-align: left;
    background: rgba(239, 242, 255, 36);
    border: 1px solid rgba(231, 225, 255, 104);
    border-radius: {_scaled(18, scale)}px;
    padding: {_scaled(9, scale)}px {_scaled(10, scale)}px;
    min-height: {_scaled(29, scale)}px;
    font-weight: 650;
}}
QWidget[mohanFlagshipTheme="true"] QPushButton[mohanAction="navigation"]:hover {{
    color: #ffffff;
    background: rgba(230, 220, 255, 72);
    border-color: #fff2c3;
}}
QWidget[mohanFlagshipTheme="true"] QPushButton[mohanAction="navigation"]:checked {{
    color: #56385d;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #fffdf7, stop:0.55 #f5e7fa, stop:1 #dceaff
    );
    border: 2px solid #f0d58b;
    font-weight: 750;
}}
QWidget[mohanFlagshipTheme="true"] QTabWidget[mohanRole="gameStage"]::pane {{
    background: transparent;
    border: 1px solid rgba(222, 211, 244, 118);
    border-radius: {_scaled(20, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="characterStage"] {{
    background: transparent;
    border: none;
}}
QWidget[mohanFlagshipTheme="true"] QLabel#dashboardCharacterStagePortrait {{
    background: qradialgradient(
        cx:0.50, cy:0.64, radius:0.60,
        fx:0.50, fy:0.64,
        stop:0 rgba(229, 221, 255, 72),
        stop:0.72 rgba(164, 156, 224, 24),
        stop:1 rgba(63, 69, 137, 0)
    );
    border: none;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="stageCaption"] {{
    background: rgba(31, 40, 89, 154);
    border: 1px solid rgba(240, 220, 255, 164);
    border-radius: {_scaled(15, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="stageTitle"] {{
    color: #fff8ff;
    font-family: "DFKai-SB", "KaiTi", "Microsoft JhengHei UI";
    font-size: {_scaled(20, scale)}px;
    font-weight: 750;
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="stageSubtitle"] {{
    color: #f1ddeb;
    font-size: {_scaled(12, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="featureDock"] {{
    background: rgba(244, 247, 255, 224);
    border: 1px solid rgba(211, 218, 241, 236);
    border-radius: {_scaled(20, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QWidget[mohanRole="featureContent"] {{
    background: transparent;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="pageBanner"] {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(58, 67, 137, 238),
        stop:0.55 rgba(94, 88, 165, 232),
        stop:1 rgba(135, 91, 151, 224)
    );
    border: 1px solid #ead9a2;
    border-radius: {_scaled(18, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="pageTitle"] {{
    color: #fff9f0;
    font-family: "DFKai-SB", "KaiTi", "Microsoft JhengHei UI";
    font-size: {_scaled(22, scale)}px;
    font-weight: 700;
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="pageSubtitle"] {{
    color: #eadff2;
    font-size: {_scaled(12, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="pageBody"] {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 253, 250, 188), stop:1 rgba(234, 240, 252, 172)
    );
    border: 1px solid #a9b9d6;
    border-radius: {_scaled(15, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="muted"] {{
    color: {colors['muted']};
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="ornament"] {{
    background: transparent;
    padding: 0;
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="brand"] {{
    color: #fff8fb;
    font-family: "DFKai-SB", "KaiTi", "Microsoft JhengHei UI";
    font-size: {_scaled(19, scale)}px;
    font-weight: 700;
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="sectionTitle"] {{
    color: #56334b;
    font-family: "DFKai-SB", "KaiTi", "Microsoft JhengHei UI";
    font-size: {_scaled(28, scale)}px;
    font-weight: 700;
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="cardTitle"] {{
    color: #4e3852;
    font-family: "DFKai-SB", "KaiTi", "Microsoft JhengHei UI";
    font-size: {_scaled(18, scale)}px;
    font-weight: 700;
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="formHeading"] {{
    color: #56384d;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(221, 229, 249, 238), stop:0.58 rgba(238, 241, 250, 180),
        stop:1 rgba(225, 234, 244, 80)
    );
    border-left: {_scaled(4, scale)}px solid #7189c7;
    border-radius: {_scaled(7, scale)}px;
    font-family: "DFKai-SB", "KaiTi", "Microsoft JhengHei UI";
    font-size: {_scaled(17, scale)}px;
    font-weight: 700;
    padding: {_scaled(8, scale)}px {_scaled(12, scale)}px;
    margin-top: {_scaled(5, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QLabel[mohanRole="statusPill"] {{
    color: {colors['ink']};
    background: {colors['wash']};
    border: 1px solid {colors['line']};
    border-radius: {_scaled(9, scale)}px;
    padding: {_scaled(8, scale)}px {_scaled(11, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="hero"] {{
    background: qradialgradient(
        cx:0.50, cy:0.24, radius:0.92,
        fx:0.50, fy:0.24,
        stop:0 rgba(255, 254, 248, 218), stop:0.38 rgba(245, 233, 250, 202),
        stop:0.72 rgba(230, 237, 255, 194), stop:1 rgba(212, 217, 244, 184)
    );
    border: 1px solid #c5b5e3;
    border-radius: {_scaled(18, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="portraitCard"] {{
    background: rgba(42, 51, 105, 72);
    border: 1px solid rgba(229, 215, 246, 164);
    border-radius: {_scaled(16, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QLabel#wardrobeCharacterPreview {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 80),
        stop:1 rgba(118, 158, 184, 54)
    );
    border: 1px solid rgba(126, 157, 178, 130);
    border-radius: {_scaled(14, scale)}px;
    padding: {_scaled(5, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QTabWidget::pane {{
    background: rgba(246, 247, 255, 184);
    border: 1px solid #c3b9e4;
    border-radius: {radius}px;
    top: -1px;
}}
QWidget[mohanFlagshipTheme="true"] QTabBar::tab {{
    color: #f5eaf0;
    background: rgba(34, 53, 78, 244);
    border: 1px solid #856b82;
    border-bottom-color: #856b82;
    border-radius: {_scaled(9, scale)}px;
    margin: {_scaled(2, scale)}px;
    padding: {tab_padding_y}px {tab_padding_x}px;
    min-height: {_scaled(20, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QTabBar::tab:selected {{
    color: #4b3045;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #fffaf8, stop:0.48 #f6e2eb, stop:1 #dfc2d2
    );
    border: 2px solid #b66d91;
    font-weight: 650;
}}
QWidget[mohanFlagshipTheme="true"] QTabBar::tab:hover:!selected {{
    color: #ffffff;
    background: #694b68;
}}
QWidget[mohanFlagshipTheme="true"] QScrollArea {{
    background: transparent;
    border: none;
}}
QWidget[mohanFlagshipTheme="true"] QScrollArea QWidget#qt_scrollarea_viewport {{
    background: transparent;
}}
QWidget[mohanFlagshipTheme="true"] QScrollBar:vertical {{
    background: {colors['wash']};
    width: {scroll_width}px;
    margin: 0;
}}
QWidget[mohanFlagshipTheme="true"] QScrollBar::handle:vertical {{
    background: {colors['line']};
    min-height: {_scaled(30, scale)}px;
    border-radius: {_scaled(6, scale)}px;
    margin: {_scaled(2, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QScrollBar::handle:vertical:hover {{
    background: {colors['glow']};
}}
QWidget[mohanFlagshipTheme="true"] QScrollBar::add-line:vertical,
QWidget[mohanFlagshipTheme="true"] QScrollBar::sub-line:vertical {{
    height: 0;
}}
QWidget[mohanFlagshipTheme="true"] QFrame[mohanRole="card"] {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 253, 249, 198), stop:0.58 rgba(239, 243, 253, 188),
        stop:1 rgba(224, 234, 250, 180)
    );
    border: 1px solid #9eafd0;
    border-radius: {radius}px;
}}
QWidget[mohanFlagshipTheme="true"] QLineEdit,
QWidget[mohanFlagshipTheme="true"] QTextEdit,
QWidget[mohanFlagshipTheme="true"] QComboBox,
QWidget[mohanFlagshipTheme="true"] QSpinBox {{
    color: {colors['ink']};
    background: rgba(255, 250, 247, 204);
    border: 1px solid {colors['line']};
    border-radius: {_scaled(8, scale)}px;
    padding: {padding_y}px {padding_x}px;
    selection-background-color: {colors['glow']};
    selection-color: #ffffff;
}}
QWidget[mohanFlagshipTheme="true"] QListWidget {{
    color: {colors['ink']};
    background: rgba(255, 255, 255, 184);
    border: 1px solid {colors['line']};
    border-radius: {_scaled(11, scale)}px;
    padding: {_scaled(7, scale)}px;
    outline: none;
}}
QWidget[mohanFlagshipTheme="true"] QListWidget::item {{
    background: rgba(235, 244, 249, 218);
    border: 1px solid transparent;
    border-radius: {_scaled(8, scale)}px;
    margin: {_scaled(3, scale)}px;
    padding: {_scaled(10, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QListWidget::item:selected {{
    color: #ffffff;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #245d7b, stop:1 #438ba9
    );
    border-color: #8fc5dc;
}}
QWidget[mohanFlagshipTheme="true"] QCheckBox {{
    spacing: {_scaled(9, scale)}px;
    padding: {_scaled(6, scale)}px {_scaled(3, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QCheckBox::indicator {{
    width: {_scaled(18, scale)}px;
    height: {_scaled(18, scale)}px;
    border: 1px solid {colors['line']};
    border-radius: {_scaled(5, scale)}px;
    background: {colors['surface']};
}}
QWidget[mohanFlagshipTheme="true"] QCheckBox::indicator:checked {{
    background: #347fa5;
    border: 4px solid #dcecf4;
}}
QWidget[mohanFlagshipTheme="true"] QGroupBox {{
    color: #4f3850;
    background: rgba(255, 251, 248, 224);
    border: 1px solid #9eafd0;
    border-radius: {_scaled(12, scale)}px;
    margin-top: {_scaled(18, scale)}px;
    padding-top: {_scaled(10, scale)}px;
    font-weight: 650;
}}
QWidget[mohanFlagshipTheme="true"] QGroupBox::title {{
    subcontrol-origin: margin;
    left: {_scaled(13, scale)}px;
    padding: 0 {_scaled(7, scale)}px;
    color: #4e5d7e;
    background: #edf2ff;
}}
QWidget[mohanFlagshipTheme="true"] QLineEdit:focus,
QWidget[mohanFlagshipTheme="true"] QTextEdit:focus,
QWidget[mohanFlagshipTheme="true"] QComboBox:focus,
QWidget[mohanFlagshipTheme="true"] QSpinBox:focus {{
    border: {focus_width}px solid {colors['focus']};
}}
QWidget[mohanFlagshipTheme="true"] QPushButton {{
    color: {colors['ink']};
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #fffafc, stop:0.48 #f3e2eb, stop:1 #dbc4d2
    );
    border: 1px solid {colors['line']};
    border-radius: {_scaled(14, scale)}px;
    padding: {padding_y}px {padding_x}px;
    min-height: {_scaled(20, scale)}px;
    font-weight: 600;
}}
QWidget[mohanFlagshipTheme="true"] QPushButton[mohanAction="primary"] {{
    color: #fffafb;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #74415f, stop:0.46 {colors['action']}, stop:1 #456f8b
    );
    border: 1px solid #e2b8cd;
    font-weight: 700;
    padding: {_scaled(10, scale)}px {_scaled(22, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QPushButton[mohanAction="secondary"] {{
    color: #f8eef3;
    background: rgba(255, 255, 255, 28);
    border: 1px solid #c7a8b7;
}}
QWidget[mohanFlagshipTheme="true"] QPushButton#globalCancelSettingsButton {{
    color: #273047;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #fffdf9, stop:1 #e8edf8
    );
    border: 1px solid #7c8eae;
    font-weight: 650;
    padding: {_scaled(10, scale)}px {_scaled(22, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QPushButton#globalSaveSettingsButton {{
    color: #ffffff;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #5a4f9f, stop:0.52 #6658ad, stop:1 #3f6288
    );
    border: 1px solid #f0d58b;
    font-weight: 750;
    padding: {_scaled(10, scale)}px {_scaled(24, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QPushButton[mohanAction="pose"] {{
    color: #5c4053;
    background: rgba(255, 250, 248, 226);
    border: 1px solid #caa8b8;
    min-width: {_scaled(42, scale)}px;
    padding: {_scaled(7, scale)}px {_scaled(9, scale)}px;
}}
QWidget[mohanFlagshipTheme="true"] QPushButton[mohanAction="pose"]:checked {{
    color: #fffafb;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #86506d, stop:1 #4f7890
    );
    border: 1px solid #e5c5d5;
}}
QWidget[mohanFlagshipTheme="true"] QPushButton:hover {{
    border-color: {colors['glow']};
    background: {colors['wash']};
}}
QWidget[mohanFlagshipTheme="true"] QPushButton:focus {{
    border: {focus_width}px solid {colors['focus']};
}}
QWidget[mohanFlagshipTheme="true"] QPushButton:pressed {{
    background: {colors['silver']};
}}
QWidget[mohanFlagshipTheme="true"] QPushButton:disabled {{
    color: {colors['disabled']};
    background: {colors['wash']};
}}
"""


def apply_flagship_theme(
    root: QWidget,
    *,
    high_contrast: bool = False,
    scale: float = 1.0,
) -> FlagshipThemeResult:
    """Apply MoHan's blue-silver flagship theme without changing UI content.

    The operation is idempotent. It does not read or persist settings, change
    translated strings, or replace widget ownership. The composition layer can
    call it again after adding a tab or when display scale changes.
    """

    normalized_scale = min(_MAXIMUM_SCALE, max(_MINIMUM_SCALE, float(scale)))
    root.setProperty("mohanFlagshipTheme", True)
    root.setStyleSheet(
        _theme_stylesheet(normalized_scale, high_contrast=high_contrast)
    )

    tabs = root.findChildren(QTabWidget)
    for tab_widget in tabs:
        tab_bar = tab_widget.tabBar()
        tab_bar.setElideMode(Qt.ElideRight)
        tab_bar.setUsesScrollButtons(True)
        tab_bar.setFocusPolicy(Qt.StrongFocus)
        tab_bar.setExpanding(False)

    scroll_areas = root.findChildren(QScrollArea)
    for scroll_area in scroll_areas:
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.viewport().setAutoFillBackground(False)

    wrapped_labels = 0
    for label in root.findChildren(QLabel):
        if (
            label.text().lstrip().startswith("<b>")
            and not label.property("mohanRole")
        ):
            label.setProperty("mohanRole", "formHeading")
            label.setStyleSheet("")
        plain_text = label.text().replace("<br>", " ")
        is_visually_long = (
            len(plain_text) >= _LONG_LABEL_THRESHOLD
            or label.fontMetrics().horizontalAdvance(plain_text)
            >= _LONG_LABEL_PIXEL_WIDTH
        )
        if not is_visually_long:
            continue
        label.setWordWrap(True)
        wrapped_labels += 1

    focusable_types = (
        QAbstractButton,
        QLineEdit,
        QTextEdit,
        QComboBox,
        QSpinBox,
    )
    for control_type in focusable_types:
        for control in root.findChildren(control_type):
            if control.focusPolicy() == Qt.NoFocus:
                control.setFocusPolicy(Qt.StrongFocus)

    root.style().unpolish(root)
    root.style().polish(root)
    root.update()
    return FlagshipThemeResult(
        high_contrast=high_contrast,
        scale=normalized_scale,
        themed_tabs=len(tabs),
        themed_scroll_areas=len(scroll_areas),
        wrapped_labels=wrapped_labels,
    )


def create_flagship_ornament(
    parent: QWidget | None = None,
    *,
    size: int = 88,
) -> QLabel:
    """Create a decorative, screen-reader-neutral ink-cloud ornament."""

    ornament = QLabel(parent)
    ornament.setProperty("mohanRole", "ornament")
    ornament.setAccessibleName("")
    ornament.setFocusPolicy(Qt.NoFocus)
    ornament.setAttribute(Qt.WA_TransparentForMouseEvents)
    pixmap = QPixmap(str(_THEME_ASSET))
    if not pixmap.isNull():
        edge = max(24, int(size))
        ornament.setPixmap(
            pixmap.scaled(
                edge,
                edge,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
    return ornament


def mark_flagship_card(frame: QFrame) -> None:
    """Opt a semantic section frame into card styling."""

    frame.setProperty("mohanRole", "card")
    frame.style().unpolish(frame)
    frame.style().polish(frame)
