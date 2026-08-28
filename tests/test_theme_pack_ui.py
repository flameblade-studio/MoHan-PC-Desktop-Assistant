from __future__ import annotations

lazy import os
lazy import re
lazy import sys
lazy from functools import partial
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import Mock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

lazy from theme_pack_ui import ThemeCatalogEntry, ThemePackPanel

LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
EXPECTED_THEME_COUNT = 2
EXPECTED_THEME_COUNT_AFTER_UPLOAD = 3
NAMES = frozendict({
    "zh-TW": "月色",
    "zh-CN": "月色",
    "en": "Moonlight",
    "ja-JP": "月明かり",
})
BUILTIN_NAMES = frozendict({
    "zh-TW": "內建主題",
    "zh-CN": "内置主题",
    "en": "Built-in theme",
    "ja-JP": "内蔵テーマ",
})


class FakeCatalog:
    def __init__(self) -> None:
        self.entries = [
            ThemeCatalogEntry(
                "builtin",
                BUILTIN_NAMES,
                built_in=True,
                source_channel="flameblade-official",
            ),
            ThemeCatalogEntry("moonlight", NAMES),
        ]

    def themes(self) -> tuple[ThemeCatalogEntry, ...]:
        return tuple(self.entries)


class FakeSession:
    def __init__(self, persisted: str = "builtin") -> None:
        self.persisted_theme_id = persisted
        self.preview_theme_id = persisted
        self.preview_calls: list[str] = []

    def preview(self, theme_id: str) -> object:
        self.preview_calls.append(theme_id)
        self.preview_theme_id = theme_id
        return object()

    def cancel(self) -> object:
        self.preview_theme_id = self.persisted_theme_id
        return object()

    def removal_block(self, theme_id: str) -> str | None:
        if theme_id == "builtin":
            return "builtin"
        if theme_id == self.persisted_theme_id:
            return "active"
        if theme_id == self.preview_theme_id:
            return "preview"
        return None


def list_text(panel: ThemePackPanel) -> tuple[str, ...]:
    return tuple(
        panel.theme_list.item(index).text()
        for index in range(panel.theme_list.count())
    )


def assert_four_language_visual_contract() -> None:
    expected = {
        "zh-TW": (
            "保存後生效",
            "取消並回復",
            "上傳單一檔案",
            "還原主題",
            "移除外掛包",
            "已安裝，尚未套用",
            "炎劍官方",
            "使用者自製",
        ),
        "zh-CN": (
            "保存后生效",
            "取消并恢复",
            "上传单个文件",
            "还原主题",
            "移除扩展包",
            "已安装，未启用",
            "炎剑官方",
            "用户自制",
        ),
        "en": (
            "Takes effect after saving",
            "Cancel to restore",
            "Upload one file",
            "Restore theme",
            "Remove add-on",
            "Installed, not active",
            "Flameblade official",
            "User-created",
        ),
        "ja-JP": (
            "保存後に反映",
            "取り消して元に戻す",
            "ファイルを1つアップロード",
            "テーマを元に戻す",
            "追加パッケージを削除",
            "インストール済み・未適用",
            "炎剣公式",
            "ユーザー制作",
        ),
    }
    for language in LANGUAGES:
        panel = ThemePackPanel(
            FakeCatalog(),
            FakeSession(),
            install=Mock(),
            remove=Mock(),
            language=language,
        )
        try:
            visible = "\n".join((
                panel.hint.text(),
                panel.upload_button.text(),
                panel.restore_button.text(),
                panel.remove_button.text(),
                *list_text(panel),
            ))
            assert all(text in visible for text in expected[language]), language
            assert panel.theme_list.count() == EXPECTED_THEME_COUNT
            assert not any(
                button.text() in {"保存設定", "保存设置", "Save settings", "設定を保存"}
                for button in panel.findChildren(QPushButton)
            )
            if language == "en":
                english_controls = (
                    f"{panel.hint.text()}\n{panel.upload_button.text()}\n"
                    f"{panel.restore_button.text()}\n{panel.remove_button.text()}\n"
                    f"{panel.status.text()}"
                )
                assert not CJK.search(english_controls)
        finally:
            panel.close()


def assert_click_and_keyboard_preview() -> None:
    session = FakeSession()
    panel = ThemePackPanel(
        FakeCatalog(),
        session,
        install=Mock(),
        remove=Mock(),
    )
    try:
        moonlight = panel.theme_list.item(1)
        panel.theme_list.setCurrentItem(moonlight)
        assert session.preview_calls[-1] == "moonlight"
        assert not panel.remove_button.isEnabled()
        panel.theme_list.itemActivated.emit(moonlight)
        assert session.preview_calls[-1] == "moonlight"
        assert panel.theme_list.focusPolicy() != Qt.NoFocus
        for button in (
            panel.upload_button,
            panel.restore_button,
            panel.remove_button,
        ):
            assert button.focusPolicy() == Qt.StrongFocus
    finally:
        panel.close()


def assert_install_refreshes_without_preview() -> None:
    catalog = FakeCatalog()
    session = FakeSession()

    def install(source: Path) -> object:
        assert source == Path("C:/Downloads/dawn.mohan-theme")
        catalog.entries.append(
            ThemeCatalogEntry(
                "dawn",
                frozendict(dict.fromkeys(LANGUAGES, "Dawn")),
            )
        )
        return object()

    panel = ThemePackPanel(catalog, session, install=install, remove=Mock())
    try:
        previous_calls = tuple(session.preview_calls)
        with patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("C:/Downloads/dawn.mohan-theme", ""),
        ):
            panel._upload_one_file()
        assert panel.theme_list.count() == EXPECTED_THEME_COUNT_AFTER_UPLOAD
        assert tuple(session.preview_calls) == previous_calls
        assert panel.theme_list.currentItem().data(Qt.UserRole) == "builtin"
    finally:
        panel.close()


def remove_theme(
    catalog: FakeCatalog,
    removed: list[str],
    theme_id: str,
) -> None:
    removed.append(theme_id)
    catalog.entries[:] = [
        entry for entry in catalog.entries if entry.theme_id != theme_id
    ]


def assert_delete_guards_and_localized_confirmation() -> None:
    for language in LANGUAGES:
        catalog = FakeCatalog()
        session = FakeSession()
        removed: list[str] = []

        panel = ThemePackPanel(
            catalog,
            session,
            install=Mock(),
            remove=partial(remove_theme, catalog, removed),
            language=language,
        )
        try:
            builtin = panel.theme_list.item(0)
            panel.theme_list.setCurrentItem(builtin)
            assert not panel.remove_button.isEnabled()
            with patch("PySide6.QtWidgets.QMessageBox.warning") as warning:
                panel._remove_selected()
            assert warning.called
            assert not removed

            moonlight = panel.theme_list.item(1)
            panel.theme_list.setCurrentItem(moonlight)
            assert not panel.remove_button.isEnabled()
            panel._restore_builtin_preview()
            assert panel.remove_button.isEnabled()
            with patch(
                "PySide6.QtWidgets.QMessageBox.question",
                return_value=QMessageBox.Yes,
            ) as question:
                panel._remove_selected()
            confirmation = question.call_args.args[2]
            assert NAMES[language] in confirmation
            assert "{package}" not in confirmation
            assert removed == ["moonlight"]
            assert panel.theme_list.count() == 1
        finally:
            panel.close()


def assert_active_theme_cannot_be_removed() -> None:
    session = FakeSession(persisted="moonlight")
    remove = Mock()
    panel = ThemePackPanel(FakeCatalog(), session, install=Mock(), remove=remove)
    try:
        moonlight = panel.theme_list.item(1)
        panel.theme_list.setCurrentItem(moonlight)
        assert not panel.remove_button.isEnabled()
        with patch("PySide6.QtWidgets.QMessageBox.warning"):
            panel._remove_selected()
        remove.assert_not_called()
    finally:
        panel.close()


def assert_rejected_install_does_not_mutate_ui() -> None:
    catalog = FakeCatalog()

    def reject(_source: Path) -> object:
        raise ValueError("unsafe")

    panel = ThemePackPanel(catalog, FakeSession(), install=reject, remove=Mock())
    try:
        before = list_text(panel)
        with (
            patch(
                "PySide6.QtWidgets.QFileDialog.getOpenFileName",
                return_value=("C:/Downloads/unsafe.zip", ""),
            ),
            patch("PySide6.QtWidgets.QMessageBox.warning") as warning,
        ):
            panel._upload_one_file()
        assert list_text(panel) == before
        assert warning.called
    finally:
        panel.close()


def run() -> None:
    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True):
        assert_four_language_visual_contract()
        assert_click_and_keyboard_preview()
        assert_install_refreshes_without_preview()
        assert_delete_guards_and_localized_confirmation()
        assert_active_theme_cannot_be_removed()
        assert_rejected_install_does_not_mutate_ui()
    app.processEvents()
    print("THEME_PACK_UI_OK")


if __name__ == "__main__":
    run()
