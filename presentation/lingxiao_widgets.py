"""凌霄的自繪元件與動效。QSS 做不到的一成在這裡：金線飾角、印章鈕、呼吸燈、
金塵粒子、頁面過場、主鈕光暈。

所有動效都經過 motion_enabled()：Windows 關掉「顯示動畫」時，元件照常存在、
外觀照舊，只是不動。測試可以用 set_motion_override() 強制開或關。
"""
from __future__ import annotations

lazy import math
lazy import random
lazy from dataclasses import dataclass

lazy from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QSize,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    Property,
)
lazy from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
lazy from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

lazy from presentation.lingxiao_tokens import (
    MOTION,
    LingxiaoPalette,
    font_stack,
    palette_for,
    reduced_motion_requested,
)

__all__ = (
    "CornerOrnaments",
    "GlowOnHover",
    "MotesLayer",
    "PageTransition",
    "PulseDot",
    "SealButton",
    "StateChip",
    "attach_corner_ornaments",
    "motion_enabled",
    "set_motion_override",
)

_MOTION_OVERRIDE: list[bool | None] = [None]


def set_motion_override(value: bool | None) -> None:
    """測試與偏好頁用：True 強制開、False 強制關、None 回到系統設定。"""

    _MOTION_OVERRIDE[0] = value


def motion_enabled() -> bool:
    if _MOTION_OVERRIDE[0] is not None:
        return _MOTION_OVERRIDE[0]
    return not reduced_motion_requested()


def _qcolor(hex_color: str, alpha: int = 255) -> QColor:
    color = QColor(hex_color)
    color.setAlpha(alpha)
    return color


# ---------------------------------------------------------------- 飾角


class CornerOrnaments(QWidget):
    """貼在面板四角的金線括弧。透明、不吃滑鼠、跟著父面板縮放。"""

    def __init__(self, parent: QWidget, color: str, *, scale: float = 1.0) -> None:
        super().__init__(parent)
        self._color = color
        self._length = max(8, round(14 * scale))
        self._inset = max(1, round(2 * scale))
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAccessibleName("")
        parent.installEventFilter(self)
        self._fit()
        self.raise_()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        if event.type() in (QEvent.Resize, QEvent.Show):
            self._fit()
            self.raise_()
        return False

    def _fit(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(_qcolor(self._color, 190), 1.5)
        painter.setPen(pen)
        w, h, n, i = self.width(), self.height(), self._length, self._inset
        for (x, y, dx, dy) in ((i, i, 1, 1), (w - i, i, -1, 1), (i, h - i, 1, -1), (w - i, h - i, -1, -1)):
            painter.drawLine(QPointF(x, y + dy * 3), QPointF(x, y + dy * n))
            painter.drawLine(QPointF(x + dx * 3, y), QPointF(x + dx * n, y))
        painter.end()


def attach_corner_ornaments(frame: QWidget, color: str, *, scale: float = 1.0) -> CornerOrnaments:
    """冪等：同一個面板只掛一組飾角；主題重套時只換顏色。"""

    existing = frame.findChild(CornerOrnaments, "lingxiaoCornerOrnaments", Qt.FindDirectChildrenOnly)
    if existing is not None:
        existing._color = color
        existing.update()
        return existing
    ornaments = CornerOrnaments(frame, color, scale=scale)
    ornaments.setObjectName("lingxiaoCornerOrnaments")
    ornaments.show()
    return ornaments


# ---------------------------------------------------------------- 狀態晶片


class StateChip(QLabel):
    """有形狀的狀態：ok／warn／bad／gold／info／neutral，文字只是補充。"""

    def __init__(self, text: str = "", state: str = "neutral", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("mohanRole", "stateChip")
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.set_state(state)

    def set_state(self, state: str) -> None:
        self.setProperty("mohanState", state)
        self.style().unpolish(self)
        self.style().polish(self)


# ---------------------------------------------------------------- 呼吸燈


class PulseDot(QWidget):
    """狀態燈：顏色代表狀態，呼吸代表「活著」。動效關閉時是靜止的圓點。"""

    def __init__(self, color: str, parent: QWidget | None = None, *, diameter: int = 10) -> None:
        super().__init__(parent)
        self._color = color
        self._phase = 0.0
        self._diameter = diameter
        self.setFixedSize(diameter * 3, diameter * 3)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        if motion_enabled():
            self._timer.start(MOTION["motes_frame_ms"])

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + (MOTION["motes_frame_ms"] / MOTION["pulse_ms"])) % 1.0
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        breath = 0.5 + 0.5 * math.sin(self._phase * math.tau) if motion_enabled() else 0.5
        halo = self._diameter * (1.0 + 0.9 * breath)
        painter.setPen(Qt.NoPen)
        painter.setBrush(_qcolor(self._color, int(70 * (1 - breath) + 20)))
        painter.drawEllipse(center, halo, halo)
        painter.setBrush(_qcolor(self._color))
        painter.drawEllipse(center, self._diameter / 2, self._diameter / 2)
        painter.end()


# ---------------------------------------------------------------- 印章鈕


class SealButton(QPushButton):
    """緊急停止：圓形印章。整頁唯一的紅，按下有 240 ms 的壓印。"""

    def __init__(self, text: str, caption: str, parent: QWidget | None = None) -> None:
        super().__init__("", parent)
        self._seal_text = text
        self._caption = caption
        self._press = 0.0
        self._palette: LingxiaoPalette = palette_for(high_contrast=False)
        self.setProperty("mohanAction", "danger")
        self.setProperty("mohanRole", "sealButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedSize(132, 132)
        self.setAccessibleName(text)
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")
        self._animation = QPropertyAnimation(self, b"pressDepth", self)
        self._animation.setDuration(MOTION["seal_press_ms"])
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self.pressed.connect(lambda: self._animate(1.0))
        self.released.connect(lambda: self._animate(0.0))


    def sizeHint(self) -> QSize:  # QSS 的 min-height 會改寫 minimumSize，這裡把尺寸釘死
        return QSize(132, 132)

    def minimumSizeHint(self) -> QSize:
        return QSize(132, 132)

    def set_palette(self, palette: LingxiaoPalette) -> None:
        self._palette = palette
        self.update()

    def _animate(self, target: float) -> None:
        if not motion_enabled():
            self._press = target
            self.update()
            return
        self._animation.stop()
        self._animation.setStartValue(self._press)
        self._animation.setEndValue(target)
        self._animation.start()

    def _get_press(self) -> float:
        return self._press

    def _set_press(self, value: float) -> None:
        self._press = float(value)
        self.update()

    pressDepth = Property(float, _get_press, _set_press)  # noqa: N815 - Qt property

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt API
        p = self._palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(6, 6, -6, -6)
        shrink = 4 * self._press
        rect = rect.adjusted(shrink, shrink, -shrink, -shrink)
        halo_alpha = 34 if self.underMouse() else 18
        painter.setPen(Qt.NoPen)
        painter.setBrush(_qcolor(p.cinnabar, halo_alpha))
        painter.drawEllipse(QRectF(self.rect()).adjusted(1, 1, -1, -1))
        painter.setBrush(_qcolor("#3a140f" if not self.isDown() else "#521a12", 240))
        painter.setPen(QPen(_qcolor(p.cinnabar, 200), 2))
        painter.drawEllipse(rect)
        painter.setPen(QPen(_qcolor(p.cinnabar, 90), 1))
        painter.drawEllipse(rect.adjusted(8, 8, -8, -8))
        title = QFont()
        title.setFamilies(font_stack("display").replace('"', "").split(", "))
        title.setPixelSize(int(rect.height() * 0.24))
        title.setBold(True)
        title.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        painter.setFont(title)
        painter.setPen(_qcolor(p.cinnabar_text))
        painter.drawText(rect.adjusted(0, -8, 0, -8), Qt.AlignCenter, self._seal_text)
        caption = QFont()
        caption.setFamilies(font_stack("caps").replace('"', "").split(", "))
        caption.setPixelSize(max(8, int(rect.height() * 0.08)))
        caption.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        painter.setFont(caption)
        painter.setPen(_qcolor(p.cinnabar))
        painter.drawText(rect.adjusted(0, rect.height() * 0.30, 0, 0), Qt.AlignHCenter | Qt.AlignTop, self._caption)
        if self.hasFocus():
            painter.setPen(QPen(_qcolor(p.gold_2, 220), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(self.rect()).adjusted(2, 2, -2, -2))
        painter.end()


# ---------------------------------------------------------------- 主鈕光暈


class GlowOnHover(QObject):
    """滑鼠移上主動作／危險按鈕時，金（或硃砂）色外光暈淡入。

    用 QGraphicsDropShadowEffect 的 blurRadius 做動畫，不改按鈕幾何，不影響
    版面。同一顆按鈕只安裝一次（idempotent），主題重套時只更新顏色。
    """

    def __init__(self, button: QPushButton, palette: LingxiaoPalette) -> None:
        super().__init__(button)
        self._button = button
        self._effect = QGraphicsDropShadowEffect(button)
        self._effect.setOffset(0, 0)
        self._effect.setBlurRadius(0)
        self._animation = QPropertyAnimation(self._effect, b"blurRadius", self)
        self._animation.setDuration(MOTION["hover_glow_ms"])
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self.set_palette(palette)
        button.setGraphicsEffect(self._effect)
        button.installEventFilter(self)

    @classmethod
    def install(cls, button: QPushButton, palette: LingxiaoPalette) -> GlowOnHover:
        existing = button.findChild(GlowOnHover, "lingxiaoGlow", Qt.FindDirectChildrenOnly)
        if existing is not None:
            existing.set_palette(palette)
            return existing
        glow = cls(button, palette)
        glow.setObjectName("lingxiaoGlow")
        return glow

    def set_palette(self, palette: LingxiaoPalette) -> None:
        danger = self._button.property("mohanAction") == "danger"
        self._effect.setColor(_qcolor(palette.cinnabar if danger else palette.gold, 170))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        if event.type() == QEvent.Enter:
            self._to(22.0)
        elif event.type() == QEvent.Leave:
            self._to(0.0)
        return False

    def _to(self, radius: float) -> None:
        if not motion_enabled():
            self._effect.setBlurRadius(radius)
            return
        self._animation.stop()
        self._animation.setStartValue(self._effect.blurRadius())
        self._animation.setEndValue(radius)
        self._animation.start()


# ---------------------------------------------------------------- 頁面過場


class PageTransition(QObject):
    """切頁時新頁淡入。掛在 QTabWidget 的 currentChanged 上；動效關閉時什麼都不做。"""

    def __init__(self, tabs) -> None:
        super().__init__(tabs)
        self._tabs = tabs
        self._effect: QGraphicsOpacityEffect | None = None
        self._animation: QPropertyAnimation | None = None
        tabs.currentChanged.connect(self._on_changed)

    def _on_changed(self, index: int) -> None:
        page = self._tabs.widget(index)
        if page is None or not motion_enabled():
            return
        if self._animation is not None:
            self._animation.stop()
        self._release_effect()
        self._effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(self._effect)
        self._animation = QPropertyAnimation(self._effect, b"opacity", self)
        self._animation.setDuration(MOTION["page_transition_ms"])
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.finished.connect(self._release_effect)
        self._animation.start()

    def _release_effect(self) -> None:
        """卸下上一頁的透明效果。setGraphicsEffect(None) 會刪掉 C++ 物件，所以引用也要清。"""

        effect, self._effect = self._effect, None
        if effect is None:
            return
        try:
            owner = effect.parent()
        except RuntimeError:  # 頁面已先一步銷毀，效果跟著沒了
            return
        if isinstance(owner, QWidget):
            owner.setGraphicsEffect(None)


# ---------------------------------------------------------------- 金塵粒子與背景


_MOTE_TOP_EXIT = -0.02
_MOTE_BOTTOM_ENTRY = 1.02


@dataclass(slots=True)
class _Mote:
    x: float
    y: float
    radius: float
    speed: float
    drift: float
    phase: float


class MotesLayer(QWidget):
    """大廳底層：大廳圖降到 14% 不透明並加暗角，上面飄金塵。

    透明、不吃滑鼠、永遠在父容器最底層。動效關閉時只畫背景，不飄。
    """

    def __init__(self, parent: QWidget, backdrop: QPixmap | None, palette: LingxiaoPalette) -> None:
        super().__init__(parent)
        self._backdrop = backdrop if backdrop is not None and not backdrop.isNull() else None
        self._palette = palette
        self._random = random.Random(902)
        self._motes = [self._spawn() for _ in range(MOTION["motes_count"])]
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAccessibleName("")
        parent.installEventFilter(self)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        if motion_enabled():
            self._timer.start(MOTION["motes_frame_ms"])
        self._fit()
        self.lower()

    def set_palette(self, palette: LingxiaoPalette) -> None:
        self._palette = palette
        self.update()

    def _spawn(self) -> _Mote:
        r = self._random
        return _Mote(r.random(), r.random(), 0.8 + r.random() * 1.8, 0.02 + r.random() * 0.05, r.uniform(-0.01, 0.01), r.random())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        if event.type() in (QEvent.Resize, QEvent.Show):
            self._fit()
            self.lower()
        return False

    def _fit(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())

    def _tick(self) -> None:
        step = MOTION["motes_frame_ms"] / 1000.0
        for mote in self._motes:
            mote.y -= mote.speed * step
            mote.x += mote.drift * step
            mote.phase = (mote.phase + step * 0.35) % 1.0
            if mote.y < _MOTE_TOP_EXIT:
                mote.y = _MOTE_BOTTOM_ENTRY
                mote.x = self._random.random()
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), 16, 16)
        painter.setClipPath(path)
        if self._backdrop is not None:
            painter.setOpacity(0.14)
            scaled = self._backdrop.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap((w - scaled.width()) // 2, (h - scaled.height()) // 2, scaled)
            painter.setOpacity(1.0)
        # 底部暗角：讓立繪與面板從地面「浮」起來。
        vignette = QLinearGradient(0, h * 0.55, 0, h)
        vignette.setColorAt(0.0, _qcolor(self._palette.ink, 0))
        vignette.setColorAt(1.0, _qcolor(self._palette.ink, 170))
        painter.setPen(Qt.NoPen)
        painter.setBrush(vignette)
        painter.drawRect(0, 0, w, h)
        gold = QColor(self._palette.gold_2)
        for mote in self._motes:
            twinkle = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(mote.phase * math.tau))
            gold.setAlpha(int(150 * twinkle))
            painter.setBrush(gold)
            painter.drawEllipse(QPointF(mote.x * w, mote.y * h), mote.radius, mote.radius)
        painter.end()
