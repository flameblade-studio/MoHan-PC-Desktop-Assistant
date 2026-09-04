"""墨寒・凌霄：控制中心的視覺層。

樣式表的每一個顏色都來自 lingxiao_tokens；這裡只決定「哪個角色用哪個材質」。
apply_flagship_theme() 仍是唯一入口，介面與 2026-09-02 之前完全相同——
組合層、主題包重染、測試都不需要改呼叫方式。新增的三件事：

- 面板飾角：帶 mohanRole 的面板在四角掛上金線（lingxiao_widgets.attach_corner_ornaments）。
- 主鈕光暈：滑鼠移上主動作按鈕時金色外光暈淡入（lingxiao_widgets.GlowOnHover）。
- 全部動效尊重 Windows「顯示動畫」設定；關掉時樣式不變、動效靜止。
"""
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
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QWidget,
)

lazy from presentation.lingxiao_tokens import (
    TYPE_SCALE,
    LingxiaoPalette,
    font_stack,
)
lazy from presentation.lingxiao_themes import (
    DEFAULT_THEME_ID,
    canonical_theme_id,
    palette_for_theme,
)
lazy from presentation.lingxiao_widgets import (
    GlowOnHover,
    MotesLayer,
    SealButton,
    attach_corner_ornaments,
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
    theme: str = DEFAULT_THEME_ID


_MINIMUM_SCALE = 0.85
_MAXIMUM_SCALE = 2.0
_LONG_LABEL_THRESHOLD = 34
_LONG_LABEL_PIXEL_WIDTH = 320
_THEME_ASSET = resource_path("assets/ui/mohan-cloud.svg")
# 面板角落要掛金線飾角的角色。gameLobby 與 featurePage 是容器，不掛。
_ORNAMENTED_ROLES = frozenset(
    {
        "card",
        "portraitCard",
        "featureDock",
        "pageBody",
        "hero",
        "desktopCompanionStatusCard",
        "commandFooter",
    }
)


def _scaled(value: int, scale: float) -> int:
    return max(1, round(value * scale))


def _rgba(hex_color: str, alpha: int) -> str:
    red, green, blue = (int(hex_color[index:index + 2], 16) for index in (1, 3, 5))
    return f"rgba({red}, {green}, {blue}, {alpha})"


def _theme_stylesheet(
    scale: float,
    *,
    high_contrast: bool,
    theme: str = DEFAULT_THEME_ID,
) -> str:
    p: LingxiaoPalette = palette_for_theme(theme, high_contrast=high_contrast)
    s = lambda value: _scaled(value, scale)  # noqa: E731 - 樣式表裡到處要用
    fs = {name: s(size) for name, size in TYPE_SCALE.items()}
    display, caps, body = font_stack("display"), font_stack("caps"), font_stack("body")
    R = 'QWidget[mohanFlagshipTheme="true"]'  # noqa: N806 - 選擇器前綴
    glass = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {_rgba(p.lacquer_2, 214)}, stop:1 {_rgba(p.lacquer, 206)})"
    gold_fill = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {p.gold_2}, stop:1 {p.gold})"
    gold_fill_hover = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffe9b8, stop:1 {p.gold_2})"
    gold_wash = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {_rgba(p.gold_2, 34)}, stop:1 {_rgba(p.gold, 8)})"
    arrow = f"border-left: {s(5)}px solid transparent; border-right: {s(5)}px solid transparent;"
    return f"""
{R} {{
    color: {p.moon};
    font-family: {body};
    font-size: {fs['body']}px;
    background: qradialgradient(cx:0.68, cy:0.0, radius:1.2, fx:0.68, fy:0.0,
        stop:0 {p.lacquer_2}, stop:0.45 {p.lacquer}, stop:1 {p.ink});
}}
{R} QLabel {{ color: {p.moon}; background: transparent; }}
{R} QLabel[mohanRole="muted"] {{ color: {p.mist}; }}
{R} QLabel[mohanRole="ornament"] {{ background: transparent; padding: 0; }}

/* ---- 頂部狀態緞帶 ---- */
{R} QFrame[mohanRole="commandDeck"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {_rgba(p.lacquer_2, 236)}, stop:1 {_rgba(p.ink_deep, 230)});
    border: 1px solid {p.line};
    border-bottom: 1px solid {p.gold_dim};
    border-radius: {s(12)}px;
}}
{R} QFrame[mohanRole="commandDeck"] QLabel {{ color: {p.moon}; }}
{R} QFrame[mohanRole="commandDeck"] QLabel[mohanRole="muted"] {{
    color: {p.dim};
    font-family: {caps};
    font-size: {fs['label']}px;
    letter-spacing: {s(2)}px;
}}
{R} QFrame[mohanRole="commandDeck"] QLabel[mohanRole="headerStatus"] {{
    color: {p.gold_2};
    font-family: {caps};
    font-size: {fs['numeral']}px;
    font-weight: 600;
    letter-spacing: 1px;
}}
{R} QLabel[mohanRole="brand"] {{
    color: {p.gold_2};
    font-family: {display};
    font-size: {fs['brand']}px;
    font-weight: 700;
    letter-spacing: {s(3)}px;
}}

/* ---- 草稿動作列（原全域取消／保存）---- */
{R} QFrame[mohanRole="commandFooter"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {_rgba(p.lacquer_2, 244)}, stop:1 {_rgba(p.ink_deep, 244)});
    border: 1px solid {p.gold_dim};
    border-radius: {s(10)}px;
}}
{R} QFrame[mohanRole="commandFooter"] QLabel {{ color: {p.mist}; }}

/* ---- 大廳、導覽軌、舞台 ---- */
{R} QWidget[mohanRole="featurePage"] {{ background: transparent; }}
{R} QFrame[mohanRole="gameLobby"] {{
    background: transparent;
    border: 1px solid {p.line};
    border-radius: {s(16)}px;
}}
{R} QFrame[mohanRole="gameNavigation"] {{
    background: {_rgba(p.ink_deep, 196)};
    border: none;
    border-right: 1px solid {p.line};
    border-top-left-radius: {s(16)}px;
    border-bottom-left-radius: {s(16)}px;
}}
{R} QLabel[mohanRole="navigationTitle"] {{
    color: {p.gold_2};
    font-family: {display};
    font-size: {fs['card_title']}px;
    font-weight: 700;
    letter-spacing: {s(2)}px;
}}
{R} QLabel[mohanRole="navRealm"] {{
    color: {p.dim};
    font-family: {caps};
    font-size: {s(10)}px;
    font-weight: 600;
    letter-spacing: {s(3)}px;
    padding: 0 0 0 {s(6)}px;
    background: transparent;
    border: none;
}}
{R} QPushButton[mohanAction="navigation"] {{
    color: {p.moon};
    text-align: left;
    background: {_rgba(p.lacquer, 235)};
    border: 1px solid {p.line};
    border-left: {s(3)}px solid {p.line};
    border-radius: {s(10)}px;
    padding: {s(7)}px {s(10)}px;
    min-height: {s(32)}px;
    font-size: {fs['body']}px;
    font-weight: 600;
}}
{R} QPushButton[mohanAction="navigation"]:hover {{
    color: {p.gold_2};
    background: {p.lacquer_2};
    border-color: {p.gold_dim};
}}
{R} QPushButton[mohanAction="navigation"]:checked {{
    color: {p.gold_2};
    background: {gold_wash};
    border: 1px solid {p.gold_dim};
    border-left: {s(3)}px solid {p.gold};
    font-weight: 700;
}}
{R} QTabWidget[mohanRole="gameStage"]::pane {{ background: transparent; border: none; }}
{R} QFrame[mohanRole="characterStage"], {R} QFrame[mohanRole="desktopCompanionStage"] {{
    background: transparent; border: none;
}}
{R} QFrame[mohanRole="desktopCompanionStatusCard"] {{
    background: {glass};
    border: 1px solid {p.line};
    border-radius: {s(16)}px;
}}
{R} QLabel[mohanRole="desktopCompanionStatusTitle"] {{
    color: {p.gold_2};
    font-family: {display};
    font-size: {fs['card_title']}px;
    font-weight: 700;
}}
{R} QLabel[mohanRole="desktopCompanionStatusNote"] {{ color: {p.mist}; font-size: {fs['label']}px; }}
{R} QFrame[mohanRole="desktopCompanionStatusRow"] {{
    background: {_rgba(p.ink_deep, 150)};
    border: 1px solid {p.line};
    border-radius: {s(10)}px;
}}
{R} QLabel[mohanRole="desktopCompanionStatusName"] {{ color: {p.mist}; font-size: {fs['label']}px; }}
{R} QLabel[mohanRole="desktopCompanionStatusValue"] {{ color: {p.moon}; font-size: {fs['body']}px; font-weight: 600; }}
{R} QLabel#dashboardCharacterStagePortrait, {R} QLabel#wardrobeCharacterPreview {{
    background: qradialgradient(cx:0.5, cy:0.66, radius:0.62, fx:0.5, fy:0.66,
        stop:0 {_rgba(p.gold, 46)}, stop:0.55 {_rgba(p.gold, 12)}, stop:1 {_rgba(p.ink, 0)});
    border: none;
}}
{R} QFrame[mohanRole="stageCaption"] {{
    background: {_rgba(p.lacquer, 210)};
    border: 1px solid {p.gold_dim};
    border-radius: {s(12)}px;
}}
{R} QLabel[mohanRole="stageTitle"] {{
    color: {p.gold_2}; font-family: {display}; font-size: {fs['card_title']}px; font-weight: 700;
}}
{R} QLabel[mohanRole="stageSubtitle"] {{ color: {p.mist}; font-size: {fs['label']}px; }}

/* ---- 功能區與頁面 ---- */
{R} QFrame[mohanRole="featureDock"] {{
    background: {_rgba(p.lacquer, 196)};
    border: 1px solid {p.line};
    border-radius: {s(16)}px;
}}
{R} QWidget[mohanRole="featureContent"] {{ background: transparent; }}
{R} QFrame[mohanRole="pageBanner"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {_rgba(p.lacquer_2, 236)}, stop:1 {_rgba(p.lacquer, 120)});
    border: 1px solid {p.line};
    border-left: {s(3)}px solid {p.gold};
    border-radius: {s(12)}px;
}}
{R} QLabel[mohanRole="pageTitle"] {{
    color: {p.gold_2};
    font-family: {display};
    font-size: {fs['page_title']}px;
    font-weight: 700;
    letter-spacing: {s(2)}px;
}}
{R} QLabel[mohanRole="pageSubtitle"] {{ color: {p.mist}; font-size: {fs['label']}px; }}
{R} QFrame[mohanRole="pageBody"] {{
    background: {_rgba(p.ink_deep, 150)};
    border: 1px solid {p.line};
    border-radius: {s(12)}px;
}}
{R} QLabel[mohanRole="sectionTitle"] {{
    color: {p.gold_2};
    font-family: {display};
    font-size: {fs['section_title']}px;
    font-weight: 700;
    letter-spacing: {s(3)}px;
}}
{R} QLabel[mohanRole="cardTitle"] {{
    color: {p.moon};
    font-family: {display};
    font-size: {fs['card_title']}px;
    font-weight: 700;
    letter-spacing: 1px;
}}
{R} QLabel[mohanRole="formHeading"] {{
    color: {p.gold};
    background: {_rgba(p.gold, 18)};
    border-left: {s(3)}px solid {p.gold_dim};
    border-radius: {s(6)}px;
    font-family: {display};
    font-size: {fs['body_strong']}px;
    font-weight: 700;
    padding: {s(7)}px {s(12)}px;
    margin-top: {s(6)}px;
}}
{R} QLabel[mohanRole="statusPill"] {{
    color: {p.moon};
    background: {p.lacquer_2};
    border: 1px solid {p.line};
    border-radius: {s(9)}px;
    padding: {s(7)}px {s(11)}px;
}}
{R} QLabel[mohanRole="stateChip"] {{
    color: {p.mist};
    background: {_rgba(p.ink_deep, 170)};
    border: 1px solid {p.line};
    border-radius: {s(11)}px;
    padding: {s(2)}px {s(10)}px;
    font-size: {fs['label']}px;
}}
{R} QLabel[mohanRole="stateChip"][mohanState="ok"] {{ color: {p.jade}; border-color: {_rgba(p.jade, 140)}; }}
{R} QLabel[mohanRole="stateChip"][mohanState="warn"] {{ color: {p.amber}; border-color: {_rgba(p.amber, 140)}; }}
{R} QLabel[mohanRole="stateChip"][mohanState="bad"] {{ color: {p.cinnabar_text}; border-color: {_rgba(p.cinnabar, 170)}; background: {_rgba(p.cinnabar, 30)}; }}
{R} QLabel[mohanRole="stateChip"][mohanState="gold"] {{ color: {p.gold_2}; border-color: {p.gold_dim}; }}
{R} QLabel[mohanRole="stateChip"][mohanState="info"] {{ color: {p.sky}; border-color: {_rgba(p.sky, 140)}; }}
{R} QFrame[mohanRole="hero"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {_rgba(p.lacquer_2, 220)}, stop:1 {_rgba(p.gold, 14)});
    border: 1px solid {p.gold_dim};
    border-radius: {s(16)}px;
}}
{R} QFrame[mohanRole="portraitCard"] {{
    background: {_rgba(p.lacquer, 176)};
    border: 1px solid {p.line};
    border-radius: {s(16)}px;
}}
{R} QFrame[mohanRole="card"] {{
    background: {glass};
    border: 1px solid {p.line};
    border-radius: {s(12)}px;
}}

/* ---- 內頁分頁、捲軸、分割線 ---- */
{R} QTabWidget::pane {{
    background: {_rgba(p.ink_deep, 120)};
    border: 1px solid {p.line};
    border-radius: {s(12)}px;
    top: -1px;
}}
{R} QTabBar::tab {{
    color: {p.mist};
    background: {p.lacquer};
    border: 1px solid {p.line};
    border-radius: {s(8)}px;
    margin: {s(2)}px;
    padding: {s(8)}px {s(14)}px;
    min-height: {s(18)}px;
}}
{R} QTabBar::tab:selected {{
    color: {p.gold_2};
    background: {p.lacquer_2};
    border: 1px solid {p.gold_dim};
    font-weight: 700;
}}
{R} QTabBar::tab:hover:!selected {{ color: {p.moon}; background: {p.lacquer_2}; }}
{R} QScrollArea {{ background: transparent; border: none; }}
{R} QScrollArea > QWidget, {R} QScrollArea > QWidget > QWidget {{ background: transparent; }}
{R} QScrollBar:vertical {{ background: transparent; width: {s(10)}px; margin: 0; }}
{R} QScrollBar::handle:vertical {{
    background: {p.line};
    min-height: {s(30)}px;
    border-radius: {s(5)}px;
    margin: {s(2)}px;
}}
{R} QScrollBar::handle:vertical:hover {{ background: {p.gold_dim}; }}
{R} QScrollBar::add-line:vertical, {R} QScrollBar::sub-line:vertical {{ height: 0; }}
{R} QScrollBar:horizontal {{ background: transparent; height: {s(10)}px; margin: 0; }}
{R} QScrollBar::handle:horizontal {{ background: {p.line}; min-width: {s(30)}px; border-radius: {s(5)}px; margin: {s(2)}px; }}
{R} QScrollBar::add-line:horizontal, {R} QScrollBar::sub-line:horizontal {{ width: 0; }}
{R} QSplitter::handle {{ background: transparent; image: none; border: none; }}
{R} QSplitter::handle:hover {{ background: {p.line}; }}
{R} QSplitter::handle:pressed {{ background: {p.gold_dim}; }}

/* ---- 輸入控制項：把 Windows 原生箭頭全部換掉 ---- */
{R} QLineEdit, {R} QTextEdit, {R} QComboBox, {R} QSpinBox {{
    color: {p.moon};
    background: {p.ink_deep};
    border: 1px solid {p.line};
    border-radius: {s(6)}px;
    padding: {s(7)}px {s(11)}px;
    selection-background-color: {p.selection};
    selection-color: #ffffff;
}}
{R} QLineEdit:focus, {R} QTextEdit:focus, {R} QComboBox:focus, {R} QSpinBox:focus {{
    border: {s(2)}px solid {p.gold_2};
}}
{R} QLineEdit:hover, {R} QComboBox:hover, {R} QSpinBox:hover {{ border-color: {p.gold_dim}; }}
{R} QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: {s(26)}px;
    border: none;
    border-left: 1px solid {p.line};
}}
{R} QComboBox::down-arrow {{
    width: 0; height: 0;
    {arrow}
    border-top: {s(6)}px solid {p.gold};
    margin-right: {s(2)}px;
}}
{R} QComboBox::down-arrow:on {{ border-top: none; border-bottom: {s(6)}px solid {p.gold_2}; }}
{R} QComboBox QAbstractItemView {{
    color: {p.moon};
    background: {p.lacquer_2};
    border: 1px solid {p.gold_dim};
    border-radius: {s(8)}px;
    selection-background-color: {p.selection};
    selection-color: #ffffff;
    outline: 0;
}}
{R} QComboBox QAbstractItemView::item {{ min-height: {s(30)}px; padding: {s(5)}px {s(10)}px; }}
{R} QComboBox QAbstractItemView::item:hover {{ color: {p.moon}; background: {p.lacquer}; }}
{R} QComboBox QAbstractItemView::item:selected {{ color: {p.on_gold}; background: {p.gold_2}; }}
{R} QSpinBox::up-button, {R} QSpinBox::down-button {{
    subcontrol-origin: border;
    width: {s(20)}px;
    border-left: 1px solid {p.line};
    background: {p.lacquer};
}}
{R} QSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: {s(6)}px; }}
{R} QSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: {s(6)}px; }}
{R} QSpinBox::up-button:hover, {R} QSpinBox::down-button:hover {{ background: {p.lacquer_2}; }}
{R} QSpinBox::up-arrow {{ width: 0; height: 0; {arrow} border-bottom: {s(5)}px solid {p.gold}; }}
{R} QSpinBox::down-arrow {{ width: 0; height: 0; {arrow} border-top: {s(5)}px solid {p.gold}; }}
{R} QListWidget {{
    color: {p.moon};
    background: {p.ink_deep};
    border: 1px solid {p.line};
    border-radius: {s(12)}px;
    padding: {s(6)}px;
    outline: none;
}}
{R} QListWidget::item {{
    background: {_rgba(p.lacquer, 200)};
    border: 1px solid transparent;
    border-radius: {s(10)}px;
    margin: {s(3)}px;
    padding: {s(10)}px {s(12)}px;
}}
{R} QListWidget::item:hover {{ background: {_rgba(p.lacquer_2, 230)}; border-color: {p.line}; }}
{R} QListWidget::item:selected {{
    color: {p.gold_2};
    background: {gold_wash};
    border-color: {p.gold_dim};
}}
{R} QCheckBox {{ color: {p.moon}; spacing: {s(9)}px; padding: {s(5)}px {s(3)}px; }}
{R} QCheckBox::indicator {{
    width: {s(18)}px; height: {s(18)}px;
    border: 1px solid {p.line};
    border-radius: {s(4)}px;
    background: {p.ink_deep};
}}
{R} QCheckBox::indicator:hover {{ border-color: {p.gold_dim}; }}
{R} QCheckBox::indicator:checked {{ background: {p.gold}; border: {s(4)}px solid {p.lacquer_2}; }}
{R} QGroupBox {{
    color: {p.mist};
    background: {_rgba(p.lacquer, 150)};
    border: 1px solid {p.line};
    border-radius: {s(12)}px;
    margin-top: {s(18)}px;
    padding-top: {s(10)}px;
    font-weight: 600;
}}
{R} QGroupBox::title {{
    subcontrol-origin: margin;
    left: {s(13)}px;
    padding: 0 {s(7)}px;
    color: {p.gold_2};
    background: {p.lacquer};
    font-family: {display};
}}

/* ---- 按鈕 ---- */
{R} QPushButton {{
    color: {p.moon};
    background: {p.lacquer_2};
    border: 1px solid {p.line};
    border-radius: {s(8)}px;
    padding: {s(7)}px {s(14)}px;
    min-height: {s(20)}px;
    font-weight: 600;
}}
{R} QPushButton:hover {{ border-color: {p.gold}; background: {p.lacquer_2}; color: {p.gold_2}; }}
{R} QPushButton:pressed {{ background: {p.ink_deep}; color: {p.moon}; }}
{R} QPushButton:focus {{ border: {s(2)}px solid {p.gold_2}; }}
{R} QPushButton:disabled {{ color: {p.dim}; background: {p.lacquer}; border-color: {p.line}; }}
{R} QPushButton[mohanAction="primary"], {R} QPushButton#globalSaveSettingsButton {{
    color: {p.on_gold};
    background: {gold_fill};
    border: 1px solid {p.gold_dim};
    font-weight: 700;
    padding: {s(8)}px {s(20)}px;
}}
{R} QPushButton[mohanAction="primary"]:hover, {R} QPushButton#globalSaveSettingsButton:hover {{
    color: {p.on_gold};
    background: {gold_fill_hover};
    border-color: {p.gold_2};
}}
{R} QPushButton[mohanAction="primary"]:pressed, {R} QPushButton#globalSaveSettingsButton:pressed {{
    color: {p.on_gold};
    background: {p.gold};
}}
{R} QPushButton[mohanAction="secondary"], {R} QPushButton#globalCancelSettingsButton {{
    color: {p.moon};
    background: transparent;
    border: 1px solid {p.line};
}}
{R} QPushButton[mohanAction="danger"] {{
    color: {p.cinnabar_text};
    background: {_rgba(p.cinnabar, 44)};
    border: 1px solid {p.cinnabar};
    font-weight: 700;
}}
{R} QPushButton[mohanRole="sealButton"] {{
    min-width: 132px; max-width: 132px; min-height: 132px; max-height: 132px;
    padding: 0; border: none; background: transparent;
}}
{R} QPushButton[mohanAction="danger"]:hover {{ color: {p.cinnabar_text}; background: {_rgba(p.cinnabar, 90)}; border-color: {p.cinnabar}; }}
{R} QPushButton[mohanAction="pose"] {{
    color: {p.mist};
    background: {p.lacquer};
    border: 1px solid {p.line};
    min-width: {s(42)}px;
    padding: {s(6)}px {s(10)}px;
}}
{R} QPushButton[mohanAction="pose"]:checked {{ color: {p.on_gold}; background: {p.gold}; border-color: {p.gold_2}; }}

/* ---- 選單與提示 ---- */
QMenu {{
    background: {p.lacquer_2};
    color: {p.moon};
    border: 1px solid {p.gold_dim};
    border-radius: {s(8)}px;
    padding: {s(5)}px;
}}
QMenu::item {{ color: {p.moon}; background: transparent; padding: {s(7)}px {s(18)}px; border-radius: {s(6)}px; }}
QMenu::item:selected {{ color: {p.on_gold}; background: {p.gold_2}; }}
QMenu::item:disabled {{ color: {p.dim}; }}
QMenu::separator {{ height: 1px; background: {p.line}; margin: {s(4)}px {s(8)}px; }}
QToolTip {{
    background: {p.lacquer_2};
    color: {p.moon};
    border: 1px solid {p.gold_dim};
    padding: {s(5)}px {s(8)}px;
}}
"""


def apply_flagship_theme(
    root: QWidget,
    *,
    high_contrast: bool = False,
    scale: float = 1.0,
    theme: str = DEFAULT_THEME_ID,
) -> FlagshipThemeResult:
    """Apply the Lingxiao theme without changing UI content.

    The operation is idempotent. It does not read or persist settings, change
    translated strings, or replace widget ownership. The composition layer can
    call it again after adding a tab or when display scale changes.
    """

    normalized_scale = min(_MAXIMUM_SCALE, max(_MINIMUM_SCALE, float(scale)))
    normalized_theme = canonical_theme_id(theme)
    root.setProperty("mohanFlagshipTheme", True)
    root.setStyleSheet(
        _theme_stylesheet(
            normalized_scale,
            high_contrast=high_contrast,
            theme=normalized_theme,
        )
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

    palette = palette_for_theme(normalized_theme, high_contrast=high_contrast)
    for seal in root.findChildren(SealButton):
        seal.set_palette(palette)
    for motes in root.findChildren(MotesLayer):
        motes.set_palette(palette)
    for frame in root.findChildren(QFrame):
        if frame.property("mohanRole") in _ORNAMENTED_ROLES:
            attach_corner_ornaments(frame, palette.gold, scale=normalized_scale)
    for button in root.findChildren(QPushButton):
        if button.property("mohanAction") in {"primary", "danger"} or (
            button.objectName() == "globalSaveSettingsButton"
        ):
            GlowOnHover.install(button, palette)

    root.style().unpolish(root)
    root.style().polish(root)
    root.update()
    return FlagshipThemeResult(
        high_contrast=high_contrast,
        scale=normalized_scale,
        themed_tabs=len(tabs),
        themed_scroll_areas=len(scroll_areas),
        wrapped_labels=wrapped_labels,
        theme=normalized_theme,
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
