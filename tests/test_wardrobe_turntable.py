"""Full-circle pointer gestures and accessible keyboard rotation."""
from __future__ import annotations

lazy import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import pytest
lazy from PySide6.QtCore import QEvent, QPointF, QRect, Qt
lazy from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPixmap
lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication, QFrame
lazy from presentation.dashboard_artwork import SCENE_GROUND_RATIO
lazy from presentation.wardrobe_turntable import TURN_TABLE_VIEWS, WardrobeTurntableLabel


def _surface() -> WardrobeTurntableLabel:
    QApplication.instance() or QApplication([])
    label = WardrobeTurntableLabel()
    label.resize(480, 640)
    label.show()
    return label


def _mouse(label, kind, x, button, buttons):
    event = QMouseEvent(kind, QPointF(x, 120), QPointF(x, 120), button, buttons, Qt.NoModifier)
    QApplication.sendEvent(label, event)


def _source_pixmap(
    size: tuple[int, int], visible_rect: tuple[int, int, int, int],
) -> QPixmap:
    image = QImage(*size, QImage.Format_RGBA8888)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.fillRect(QRect(*visible_rect), QColor(220, 180, 120, 255))
    painter.end()
    return QPixmap.fromImage(image)


def _visible_bottom(pixmap: QPixmap) -> int:
    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    rows = [
        y
        for y in range(image.height())
        if any(image.pixelColor(x, y).alpha() > 0 for x in range(image.width()))
    ]
    assert rows
    return rows[-1]


def _assert_ground_alignment(label: WardrobeTurntableLabel) -> None:
    ground = label.height() * SCENE_GROUND_RATIO
    visible_bottom_edge = _visible_bottom(label.pixmap()) + 1
    assert abs(visible_bottom_edge - ground) <= 1


@pytest.mark.parametrize(
    ("view_id", "source_size", "visible_rect"),
    [
        ("yaw+000-pitch+00", (120, 180), (24, 15, 72, 73)),
        ("yaw+090-pitch+00", (180, 240), (38, 29, 108, 123)),
        ("yaw-180-pitch+00", (96, 144), (17, 9, 62, 97)),
    ],
)
@pytest.mark.parametrize("scene_size", [(320, 240), (640, 480), (511, 377)])
def test_scene_attachment_aligns_alpha_feet_after_resize(
    view_id, source_size, visible_rect, scene_size,
):
    QApplication.instance() or QApplication([])
    scene = QFrame()
    label = WardrobeTurntableLabel(scene)
    label.attach_to_scene(SCENE_GROUND_RATIO)
    label.set_view(view_id)
    label.set_rendered_pixmap(_source_pixmap(source_size, visible_rect))
    scene.resize(*scene_size)
    scene.show()
    QApplication.processEvents()
    try:
        _assert_ground_alignment(label)
        baseline = label.pixmap().toImage().copy()
        intermediate_sizes = (
            (max(120, scene_size[0] - 37), max(120, scene_size[1] - 23)),
            (scene_size[0] + 83, scene_size[1] + 67),
            scene_size,
            (scene_size[0] + 41, scene_size[1] + 29),
            scene_size,
        )
        for width, height in intermediate_sizes:
            scene.resize(width, height)
            QApplication.processEvents()
            _assert_ground_alignment(label)
        assert label.pixmap().toImage() == baseline
        assert label.view_id == view_id
    finally:
        scene.close()


def test_keyboard_full_turn_visits_every_view_and_preserves_anatomical_sides():
    label = _surface()
    visited = []
    label.view_changed.connect(visited.append)
    try:
        for _ in range(6):
            QTest.keyClick(label, Qt.Key_Right)
        assert label.view_id == "yaw+090-pitch+00"  # MoHan's anatomical left.
        for _ in range(12):
            QTest.keyClick(label, Qt.Key_Right)
        assert label.view_id == "yaw-090-pitch+00"  # MoHan's anatomical right.
        for _ in range(6):
            QTest.keyClick(label, Qt.Key_Right)
        assert label.view_id == "yaw+000-pitch+00"
        assert len(visited) == len(set(visited)) == len(TURN_TABLE_VIEWS)
        QTest.keyClick(label, Qt.Key_Left)
        assert label.view_id == "yaw-015-pitch+00"
        QTest.keyClick(label, Qt.Key_Home)
        assert label.view_id == "yaw+000-pitch+00"
    finally:
        label.close()


def test_taller_headwear_does_not_rescale_the_body():
    QApplication.instance() or QApplication([])
    scene = QFrame()
    scene.resize(320, 240)
    label = WardrobeTurntableLabel(scene)
    label.attach_to_scene(SCENE_GROUND_RATIO)
    source = _source_pixmap((120, 180), (24, 15, 72, 73))
    scene.show()
    label.set_rendered_pixmap(source)
    QApplication.processEvents()
    try:
        body_region = QRect(0, 150, 320, 90)
        before = label.pixmap().toImage().copy(body_region)
        with_headwear = source.copy()
        painter = QPainter(with_headwear)
        painter.fillRect(QRect(48, 0, 24, 15), QColor("red"))
        painter.end()
        label.set_rendered_pixmap(with_headwear)
        QApplication.processEvents()
        assert label.pixmap().toImage().copy(body_region) == before
        _assert_ground_alignment(label)
    finally:
        scene.close()


def test_drag_wraps_at_back_and_ignores_hover_after_release():
    label = _surface()
    try:
        label.set_view("yaw+165-pitch+00")
        _mouse(label, QEvent.MouseButtonPress, 200, Qt.LeftButton, Qt.LeftButton)
        _mouse(label, QEvent.MouseMove, 220, Qt.NoButton, Qt.LeftButton)
        assert label.view_id == "yaw-180-pitch+00"
        _mouse(label, QEvent.MouseMove, 240, Qt.NoButton, Qt.LeftButton)
        assert label.view_id == "yaw-165-pitch+00"
        _mouse(label, QEvent.MouseMove, 200, Qt.NoButton, Qt.LeftButton)
        assert label.view_id == "yaw+165-pitch+00"
        _mouse(label, QEvent.MouseButtonRelease, 200, Qt.LeftButton, Qt.NoButton)
        _mouse(label, QEvent.MouseMove, 420, Qt.NoButton, Qt.NoButton)
        assert label.view_id == "yaw+165-pitch+00"
        assert label.cursor().shape() == Qt.OpenHandCursor
    finally:
        label.close()


def test_unknown_or_intermediate_pose_cannot_replace_a_real_view():
    label = _surface()
    try:
        with pytest.raises(ValueError):
            label.set_view("yaw+010-pitch+00")
        assert label.view_id == "yaw+000-pitch+00"
    finally:
        label.close()
