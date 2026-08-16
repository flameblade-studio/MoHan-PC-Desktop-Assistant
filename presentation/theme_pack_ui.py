from __future__ import annotations

lazy from collections.abc import Callable, Mapping
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Protocol, TypedDict, Unpack

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

lazy from domain.language_support import canonical_ui_language
lazy from presentation.ui_localization import ui_text

__all__ = (
    "BUILTIN_THEME_ID",
    "ThemeCatalogEntry",
    "ThemeCatalogPort",
    "ThemePackPanel",
    "ThemeSessionPort",
)

BUILTIN_THEME_ID = "builtin"


@dataclass(frozen=True, slots=True)
class ThemeCatalogEntry:
    """Display-only theme metadata supplied by an injected catalog."""

    theme_id: str
    display_names: Mapping[str, str]
    built_in: bool = False
    source_channel: str = "user-authored"

    def display_name(self, language: str) -> str:
        canonical = canonical_ui_language(language)
        return str(
            self.display_names.get(canonical)
            or self.display_names.get("en")
            or self.theme_id
        )


class ThemeCatalogPort(Protocol):
    """Minimal catalog boundary required by the embeddable widget."""

    def themes(self) -> tuple[ThemeCatalogEntry, ...]: ...


class ThemeSessionPort(Protocol):
    """Preview transaction boundary; persistence remains Dashboard-owned."""

    @property
    def persisted_theme_id(self) -> str: ...

    @property
    def preview_theme_id(self) -> str: ...

    def preview(self, theme_id: str) -> object: ...

    def cancel(self) -> object: ...

    def removal_block(self, theme_id: str) -> str | None: ...


ThemeInstaller = Callable[[Path], object]
ThemeRemover = Callable[[str], None]


class _ThemePackPanelOptions(TypedDict, total=False):
    language: str
    parent: QWidget | None


class ThemePackPanel(QWidget):
    """Dashboard-embeddable theme browser with no archive or DB knowledge."""

    def __init__(
        self,
        catalog: ThemeCatalogPort,
        session: ThemeSessionPort,
        *,
        install: ThemeInstaller,
        remove: ThemeRemover,
        **options: Unpack[_ThemePackPanelOptions],
    ) -> None:
        unknown = set(options) - {"language", "parent"}
        if unknown:
            name = min(unknown)
            raise TypeError(
                "ThemePackPanel.__init__() got an unexpected keyword "
                f"argument {name!r}"
            )
        language = options.get("language", "zh-TW")
        parent = options.get("parent")
        super().__init__(parent)
        self.catalog = catalog
        self.session = session
        self.install_callback = install
        self.remove_callback = remove
        self.language = language
        self._refreshing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.hint = QLabel(
            self._t("wardrobe_changes_after_save", "保存後生效")
            + " · "
            + self._t("wardrobe_cancel_restores", "取消並回復")
        )
        self.hint.setWordWrap(True)
        self.theme_list = QListWidget()
        self.theme_list.setAccessibleName(
            self._t("theme_preview", "主題預覽")
        )
        self.status = QLabel(self._t("theme_preview", "主題預覽"))
        self.status.setWordWrap(True)

        actions = QHBoxLayout()
        self.upload_button = QPushButton(
            self._t("wardrobe_upload_single_file", "上傳單一檔案")
        )
        self.restore_button = QPushButton(
            self._t("theme_restore", "還原主題")
        )
        self.remove_button = QPushButton(
            self._t("wardrobe_remove_package", "移除外掛包")
        )
        for button in (
            self.upload_button,
            self.restore_button,
            self.remove_button,
        ):
            button.setFocusPolicy(Qt.StrongFocus)
            actions.addWidget(button)
        actions.addStretch()

        layout.addWidget(self.hint)
        layout.addWidget(self.theme_list, 1)
        layout.addWidget(self.status)
        layout.addLayout(actions)

        self.theme_list.currentItemChanged.connect(self._preview_current)
        self.theme_list.itemActivated.connect(self._preview_item)
        self.upload_button.clicked.connect(self._upload_one_file)
        self.restore_button.clicked.connect(self._restore_builtin_preview)
        self.remove_button.clicked.connect(self._remove_selected)
        self.refresh()

    def _t(self, key: str, chinese: str, **values: object) -> str:
        return ui_text(self.language, key, chinese, **values)

    @staticmethod
    def _theme_id(item: QListWidgetItem | None) -> str | None:
        return None if item is None else str(item.data(Qt.UserRole))

    def refresh(self) -> None:
        """Reload display metadata without changing the current preview."""

        selected_id = self._theme_id(self.theme_list.currentItem())
        self._refreshing = True
        try:
            self.theme_list.clear()
            selected_item: QListWidgetItem | None = None
            preview_item: QListWidgetItem | None = None
            for theme in self.catalog.themes():
                label = theme.display_name(self.language)
                source_key = (
                    "theme_source_official"
                    if theme.source_channel == "flameblade-official"
                    else "theme_source_user"
                )
                source_fallback = (
                    "炎劍官方" if source_key == "theme_source_official" else "使用者自製"
                )
                label += " · " + self._t(source_key, source_fallback)
                if theme.theme_id not in {
                    self.session.persisted_theme_id,
                    self.session.preview_theme_id,
                }:
                    label += " · " + self._t(
                        "wardrobe_installed_inactive",
                        "已安裝，未啟用",
                    )
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, theme.theme_id)
                item.setData(Qt.UserRole + 1, theme.display_name(self.language))
                item.setData(Qt.UserRole + 2, theme.built_in)
                self.theme_list.addItem(item)
                if theme.theme_id == selected_id:
                    selected_item = item
                if theme.theme_id == self.session.preview_theme_id:
                    preview_item = item
            self.theme_list.setCurrentItem(selected_item or preview_item)
        finally:
            self._refreshing = False
        self._update_remove_state()

    def _preview_current(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if not self._refreshing and current is not None:
            self._preview_item(current)

    def _preview_item(self, item: QListWidgetItem) -> None:
        theme_id = self._theme_id(item)
        if theme_id is None:
            return
        try:
            self.session.preview(theme_id)
        except (OSError, RuntimeError, ValueError):
            self._show_rejected()
            return
        name = str(item.data(Qt.UserRole + 1))
        self.status.setText(
            self._t("theme_preview", "主題預覽") + "：" + name
        )
        self._update_remove_state()

    def _upload_one_file(self) -> None:
        source, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self._t("wardrobe_upload_single_file", "上傳單一檔案"),
            str(Path.home() / "Downloads"),
            "MoHan theme package (*.mohan-theme *.zip)",
        )
        if not source:
            return
        try:
            self.install_callback(Path(source))
        except (OSError, RuntimeError, ValueError):
            self._show_rejected()
            return
        self.refresh()

    def _restore_builtin_preview(self) -> None:
        try:
            self.session.preview(BUILTIN_THEME_ID)
        except (OSError, RuntimeError, ValueError):
            self._show_rejected()
            return
        self.status.setText(self._t("theme_restore", "還原主題"))
        self._update_remove_state()

    def _update_remove_state(self) -> None:
        theme_id = self._theme_id(self.theme_list.currentItem())
        blocked = theme_id is None or self.session.removal_block(theme_id) is not None
        self.remove_button.setEnabled(not blocked)

    def _remove_selected(self) -> None:
        item = self.theme_list.currentItem()
        theme_id = self._theme_id(item)
        if theme_id is None:
            return
        block = self.session.removal_block(theme_id)
        if block is not None:
            message = (
                self._t(
                    "wardrobe_builtin_not_removable",
                    "內建包不可刪除",
                )
                if block == "builtin"
                else self._t(
                    "wardrobe_switch_before_remove",
                    "請先切換，再移除使用中的包",
                )
            )
            QMessageBox.warning(self, self.remove_button.text(), message)
            self._update_remove_state()
            return
        package_name = str(item.data(Qt.UserRole + 1))
        answer = QMessageBox.question(
            self,
            self.remove_button.text(),
            self._t(
                "wardrobe_delete_confirm",
                "確定移除「{package}」嗎？",
                package=package_name,
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self.remove_callback(theme_id)
        except (OSError, RuntimeError, ValueError):
            self._show_rejected()
            return
        self.refresh()

    def _show_rejected(self) -> None:
        QMessageBox.warning(
            self,
            self._t("theme_preview", "主題預覽"),
            self._t(
                "package_rejected_unsafe_or_missing",
                "套件含危險內容或缺少檔案，已整包拒絕",
            ),
        )
