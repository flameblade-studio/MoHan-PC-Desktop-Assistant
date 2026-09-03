"""凌霄殼層與元件的行為契約。

守住的不是「長得像不像」，而是會壞掉的地方：
- 四領域版面不能吞掉任何分頁（未知功能落到「其他」）；
- 印章鈕在主題 QSS 的 min-height 下仍是 132×132 的圓；
- 切頁過場反覆觸發不得碰到已刪除的 C++ 效果物件；
- 動效關閉時過場什麼都不做；
- 所有文字／底色配對兩種調色盤都 ≥ 4.5:1。
"""
from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QEventLoop, QTimer
lazy from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

lazy from presentation.flagship_theme import apply_flagship_theme
lazy from presentation.lingxiao_shell import REALMS, realm_layout_order
lazy from presentation.lingxiao_tokens import (
    MOTION,
    TEXT_ON_SURFACE_PAIRS,
    contrast_ratio,
    palette_for,
)
lazy from presentation.lingxiao_widgets import (
    PageTransition,
    SealButton,
    StateChip,
    attach_corner_ornaments,
    set_motion_override,
)

WCAG_AA_NORMAL_TEXT = 4.5
SEAL_DIAMETER = 132


def _spin(milliseconds: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def _resolve(palette, value: str) -> str:
    return getattr(palette, value) if not value.startswith("#") else value


def assert_realm_layout_keeps_every_feature() -> None:
    known = tuple(feature for _key, _label, members in REALMS for feature in members)
    feature_ids = ("permissions", "chat", "brand_new_page", "wardrobe")
    layout = realm_layout_order(feature_ids)
    flattened = tuple(index for _realm, indexes in layout for index in indexes)
    assert sorted(flattened) == list(range(len(feature_ids))), layout
    assert layout[-1][0] == "other" and layout[-1][1] == (2,), layout
    assert layout[0][0] == "companion" and layout[0][1] == (1,), layout
    assert len(set(known)) == len(known), "一個功能不得同時屬於兩個領域"


def assert_contrast_pairs(palette) -> None:
    for pair in TEXT_ON_SURFACE_PAIRS:
        foreground, background = (_resolve(palette, str(value)) for value in pair[:2])
        ratio = contrast_ratio(foreground, background)
        assert ratio >= WCAG_AA_NORMAL_TEXT, (pair, foreground, background, round(ratio, 2))


def assert_seal_survives_theme(app: QApplication) -> None:
    root = QWidget()
    layout = QVBoxLayout(root)
    seal = SealButton("停手", "緊急停止")
    layout.addWidget(seal)
    apply_flagship_theme(root)
    root.show()
    app.processEvents()
    assert seal.size().toTuple() == (SEAL_DIAMETER, SEAL_DIAMETER), seal.size().toTuple()
    assert seal.property("mohanAction") == "danger"
    root.close()


def assert_page_transition_is_reentrant(app: QApplication) -> None:
    tabs = QTabWidget()
    for name in ("甲", "乙", "丙"):
        tabs.addTab(QLabel(name), name)
    tabs.show()
    set_motion_override(True)
    try:
        transition = PageTransition(tabs)
        for index in (1, 2, 0, 1):  # 動畫未完就切下一頁，過去會炸 RuntimeError
            tabs.setCurrentIndex(index)
            app.processEvents()
        _spin(MOTION["page_transition_ms"] + 80)
        app.processEvents()
        assert transition._effect is None, "過場結束後應釋放效果物件"
        assert tabs.currentWidget().graphicsEffect() is None
    finally:
        set_motion_override(None)
    tabs.close()


def assert_reduced_motion_skips_transition(app: QApplication) -> None:
    tabs = QTabWidget()
    tabs.addTab(QLabel("甲"), "甲")
    tabs.addTab(QLabel("乙"), "乙")
    tabs.show()
    set_motion_override(False)
    try:
        transition = PageTransition(tabs)
        tabs.setCurrentIndex(1)
        app.processEvents()
        assert transition._effect is None
        assert tabs.currentWidget().graphicsEffect() is None
    finally:
        set_motion_override(None)
    tabs.close()


def assert_chip_and_ornaments() -> None:
    chip = StateChip("草稿", "gold")
    assert chip.property("mohanState") == "gold"
    chip.set_state("ok")
    assert chip.property("mohanState") == "ok"
    frame = QFrame()
    first = attach_corner_ornaments(frame, palette_for(high_contrast=False).gold)
    second = attach_corner_ornaments(frame, palette_for(high_contrast=False).gold)
    assert first is second, "角飾重複掛載必須冪等"


def run() -> None:
    app = QApplication.instance() or QApplication([])
    assert_realm_layout_keeps_every_feature()
    assert_contrast_pairs(palette_for(high_contrast=False))
    assert_contrast_pairs(palette_for(high_contrast=True))
    assert_seal_survives_theme(app)
    assert_page_transition_is_reentrant(app)
    assert_reduced_motion_skips_transition(app)
    assert_chip_and_ornaments()
    print("LINGXIAO_THEME_OK")


if __name__ == "__main__":
    run()
