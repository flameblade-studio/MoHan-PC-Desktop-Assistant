from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QPoint, Qt
lazy from PySide6.QtWidgets import (
    QApplication,
    QGraphicsColorizeEffect,
    QLabel,
    QWidget,
)

lazy from domain.theme_pack import ThemePack
lazy from presentation.dashboard_artwork import (
    CelestialFrame,
    apply_dashboard_artwork,
)
lazy from presentation.dashboard_theme_materials import resolve_material_palette
lazy from presentation.lingxiao_tokens import PALETTE
lazy from presentation.presentation_resources import resource_path

ARTWORK_PATH = "assets/ui/mohan-celestial-palace-v1.png"
CHARACTER_COLOR = "#123456"
TEST_SCALE = 1.75


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _theme() -> ThemePack:
    return ThemePack(
        theme_id="flameblade.sponsor.test",
        display_names=frozendict(
            {
                "zh-TW": "測試赤焰",
                "zh-CN": "测试赤焰",
                "en": "Test Flame",
                "ja-JP": "テスト赤焔",
            }
        ),
        tokens=frozendict(
            {
                "window": "#1A1214",
                "background": "#1A1214",
                "card": "#241A1C",
                "surface": "#241A1C",
                "text": "#F2E6E0",
                "title": "#FFD9C9",
                "muted": "#C4A99D",
                "border": "#5C4038",
                "primary": "#D9481C",
            }
        ),
        font_family="Microsoft JhengHei UI",
        radius=12,
        background="assets/background.png",
        source_channel="flameblade-official",
        source_kind="original",
        author="CHOU MING HUA",
        license_name="MoHan Sponsor DLC - All Rights Reserved (ASSETS-LICENSE.md)",
    )


def _frame(kind: str = "scene") -> tuple[QWidget, CelestialFrame]:
    root = QWidget()
    root.setProperty("celestialScale", 1.0)
    frame = CelestialFrame(root, kind=kind)
    frame.setGeometry(0, 0, 420, 300)
    root.resize(420, 300)
    root.show()
    _application().processEvents()
    return root, frame


def test_scene_and_frame_follow_resize_and_runtime_scale() -> None:
    application = _application()
    root = QWidget()
    root.setProperty("celestialScale", TEST_SCALE)
    scene = CelestialFrame(root, kind="scene")
    panel = CelestialFrame(root, kind="panel")
    scene.setGeometry(0, 0, 420, 220)
    panel.setGeometry(0, 220, 420, 160)
    root.resize(420, 380)
    root.show()
    try:
        apply_dashboard_artwork(root, PALETTE)
        application.processEvents()
        assert scene._art.scale == TEST_SCALE
        assert panel._art.scale == TEST_SCALE
        assert scene._art.geometry() == scene.rect()
        assert panel._art.geometry() == panel.rect()
        assert scene.grab().size() == scene.size()
        assert panel.grab().size() == panel.size()

        scene.resize(640, 280)
        panel.resize(640, 180)
        application.processEvents()
        assert scene._art.geometry() == scene.rect()
        assert panel._art.geometry() == panel.rect()
        assert scene.grab().size() == scene.size()
        assert panel.grab().size() == panel.size()
    finally:
        root.close()


def test_decorative_canvas_is_mouse_transparent() -> None:
    root, frame = _frame()
    try:
        canvas = frame._art
        assert canvas.testAttribute(Qt.WA_TransparentForMouseEvents)
        assert canvas.focusPolicy() == Qt.NoFocus
        point = canvas.mapToGlobal(QPoint(20, 20))
        hit = QApplication.widgetAt(point)
        assert hit is not canvas
    finally:
        root.close()


def test_dlc_tint_changes_decorative_pixels_but_not_character_pixels() -> None:
    application = _application()
    root, frame = _frame()
    character = QLabel(frame)
    character.setGeometry(150, 90, 120, 100)
    character.setStyleSheet(f"background-color: {CHARACTER_COLOR}; border: none;")
    character.show()
    try:
        apply_dashboard_artwork(root, PALETTE)
        application.processEvents()
        before = frame.grab().toImage()
        character_point = QPoint(210, 140)
        before_character = before.pixelColor(character_point)

        apply_dashboard_artwork(root, PALETTE, _theme())
        application.processEvents()
        after = frame.grab().toImage()
        after_character = after.pixelColor(character_point)

        assert before_character.name().lower() == CHARACTER_COLOR
        assert after_character.name().lower() == CHARACTER_COLOR
        assert isinstance(frame._art.graphicsEffect(), QGraphicsColorizeEffect)
        decorative_changes = sum(
            before.pixelColor(x, y) != after.pixelColor(x, y)
            for y in range(after.height())
            for x in range(after.width())
            if not character.geometry().contains(x, y)
        )
        assert decorative_changes > 0
    finally:
        root.close()


def test_external_background_is_usable_and_builtin_switch_clears_it() -> None:
    application = _application()
    root, frame = _frame()
    background = resource_path(ARTWORK_PATH)
    assert background.is_file()
    try:
        apply_dashboard_artwork(root, PALETTE, _theme(), background)
        application.processEvents()
        assert frame._art.background is not None
        assert not frame._art.background.isNull()
        assert isinstance(frame._art.graphicsEffect(), QGraphicsColorizeEffect)
        assert not frame.grab().toImage().isNull()

        apply_dashboard_artwork(root, PALETTE)
        application.processEvents()
        assert frame._art.background is None
        assert frame._art.graphicsEffect() is None
        assert frame._materials == resolve_material_palette(PALETTE)
        assert not frame.grab().toImage().isNull()
    finally:
        root.close()


def test_high_contrast_removes_background_detail_and_restores_decoration() -> None:
    application = _application()
    root, frame = _frame()
    label = QLabel("Readable controls", frame)
    label.setGeometry(80, 80, 160, 40)
    label.show()
    try:
        apply_dashboard_artwork(root, PALETTE, high_contrast=True)
        application.processEvents()
        assert frame._art.isHidden()
        assert label.isVisibleTo(root)
        background_point = QPoint(10, 10)
        assert frame.grab().toImage().pixelColor(background_point).name() == frame._materials.panel.lower()
        apply_dashboard_artwork(root, PALETTE)
        application.processEvents()
        assert frame._art.isVisibleTo(root)
        assert label.isVisibleTo(root)
    finally:
        root.close()
