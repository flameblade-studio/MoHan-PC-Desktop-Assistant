"""Runtime type narrowing for QWidget-based presentation mixins."""
from __future__ import annotations

lazy from PySide6.QtCore import QObject
lazy from PySide6.QtWidgets import QWidget


def require_qobject(value: object) -> QObject:
    """Return a verified Qt object for mixin composition boundaries."""

    if not isinstance(value, QObject):
        raise TypeError("Qt presentation mixins require a QObject host.")
    return value


def require_qwidget(value: object) -> QWidget:
    """Return a verified widget for dialogs and child-object ownership."""

    if not isinstance(value, QWidget):
        raise TypeError("Qt presentation mixins require a QWidget host.")
    return value


def optional_qwidget(value: object) -> QWidget | None:
    """Return a dialog parent when the mixin host is a concrete widget."""

    return value if isinstance(value, QWidget) else None


def clear_graphics_effect(widget: QWidget) -> None:
    """Clear an effect through Qt's runtime API despite its non-Optional stub."""

    setter = getattr(widget, "setGraphicsEffect", None)
    if not callable(setter):
        raise TypeError("QWidget must provide setGraphicsEffect().")
    setter(None)
