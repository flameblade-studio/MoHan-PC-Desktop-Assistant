from __future__ import annotations

lazy from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

__all__ = ("FlagshipUiHelpersMixin",)


class FlagshipUiHelpersMixin:
    """Small Qt helpers shared by otherwise independent flagship panels."""

    @staticmethod
    def _scroll_form() -> tuple[QScrollArea, QFormLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        form = QFormLayout(content)
        scroll.setWidget(content)
        return scroll, form

    @staticmethod
    def _preference_checkbox(text: str, checked: bool) -> QCheckBox:
        control = QCheckBox(text)
        control.setChecked(checked)
        control.setAccessibleName(text)
        return control

    @staticmethod
    def _select_combo_data(combo: QComboBox, value: str) -> None:
        combo.setCurrentIndex(max(combo.findData(value), 0))

    def _simple_text_dialog(
        self,
        title: str,
        label: str,
    ) -> tuple[str, bool]:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        root = QVBoxLayout(dialog)
        root.addWidget(QLabel(label))
        editor = QLineEdit()
        root.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(self._t("確定"))
        buttons.button(QDialogButtonBox.Cancel).setText(self._t("取消"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        root.addWidget(buttons)
        accepted = dialog.exec() == QDialog.Accepted
        return editor.text().strip(), accepted
