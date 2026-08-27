"""Native popup styling shared by every Dashboard feature page."""

from __future__ import annotations

lazy from PySide6.QtGui import QColor, QPalette
lazy from PySide6.QtWidgets import QComboBox, QWidget

POPUP_STYLE = (
    "QAbstractItemView { background-color: #ffffff; color: #20364a;"
    " selection-background-color: #cfe0ee; selection-color: #17344f;"
    " border: 1px solid #9bb8d5; outline: 0; }"
)


def enforce_readable_combo_popups(root: QWidget) -> None:
    """Apply a light real palette to native Windows combo popup views."""

    for combo in root.findChildren(QComboBox):
        view = combo.view()
        if view is None:
            continue
        palette = view.palette()
        for role, color in (
            (QPalette.Base, "#ffffff"),
            (QPalette.Text, "#20364a"),
            (QPalette.Highlight, "#cfe0ee"),
            (QPalette.HighlightedText, "#17344f"),
        ):
            palette.setColor(role, QColor(color))
        view.setPalette(palette)
        view.setStyleSheet(POPUP_STYLE)
        view.viewport().setPalette(palette)
        view.viewport().setAutoFillBackground(True)
