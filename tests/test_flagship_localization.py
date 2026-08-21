from __future__ import annotations

lazy import os
lazy import re
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QWidget,
)

lazy from flagship_ui import FlagshipControlCenter, WorkflowEditor
lazy from flagship_ui_localization import (
    FLAGSHIP_TRANSLATIONS,
    FlagshipTranslator,
    validate_flagship_translations,
)
lazy from infrastructure.db import StudioDB

HAN_CHARACTER = re.compile(r"[\u3400-\u9fff]")
FLAGSHIP_TAB_COUNT = 8
TRANSLATION_LANGUAGE_COUNT = 3
ENGLISH_ALLOWED_HAN = frozenset({
    # User-owned profile data and the character's proper name are content,
    # not system UI. They are allowed to remain verbatim.
    "墨寒",
})


def _visible_texts(root: QWidget) -> list[str]:
    values: list[str] = []
    if root.windowTitle():
        values.append(root.windowTitle())
    for widget in [root, *root.findChildren(QWidget)]:
        if widget.toolTip():
            values.append(widget.toolTip())
        if isinstance(widget, (QLabel, QPushButton, QCheckBox)):
            values.append(widget.text())
        if isinstance(widget, (QLineEdit, QTextEdit)):
            values.append(widget.placeholderText())
        if isinstance(widget, QComboBox):
            values.extend(widget.itemText(index) for index in range(widget.count()))
        if isinstance(widget, QListWidget):
            values.extend(widget.item(index).text() for index in range(widget.count()))
        if isinstance(widget, QTextBrowser):
            values.append(widget.toPlainText())
        if isinstance(widget, QTabWidget):
            values.extend(widget.tabText(index) for index in range(widget.count()))
    return [value for value in values if value]


def _unapproved_han(values: list[str]) -> list[str]:
    offenders: list[str] = []
    for value in values:
        cleaned = value
        for allowed in ENGLISH_ALLOWED_HAN:
            cleaned = cleaned.replace(allowed, "")
        if HAN_CHARACTER.search(cleaned):
            offenders.append(value)
    return offenders


def _assert_canonical_values(center: FlagshipControlCenter) -> None:
    assert center.remote_host.itemData(0) == "127.0.0.1"
    assert center.remote_host.itemData(1) == "0.0.0.0"
    assert center._permission_controls["delete_file"].currentData() == "禁止"
    assert center._permission_controls["email_send"].currentData() == "每次詢問"

    editor = WorkflowEditor(center, language=center.language)
    assert [editor.trigger.itemData(index) for index in range(3)] == [
        "manual",
        "schedule",
        "work_start",
    ]
    return editor


def _assert_english_center(center: FlagshipControlCenter) -> None:
    assert center.language == "en"
    assert center.tabs.count() == FLAGSHIP_TAB_COUNT
    assert [center.tabs.tabText(index) for index in range(FLAGSHIP_TAB_COUNT)] == [
        "Task Center",
        "Workflows",
        "Cloud Connectors",
        "Smart Home",
        "Remote & Privacy",
        "Companion Care",
        "Security Permissions",
        "Audit Log",
    ]
    for index in range(center.tabs.count()):
        center.tabs.setCurrentIndex(index)
        assert center.tabs.currentWidget() is not None

    editor = _assert_canonical_values(center)
    try:
        assert editor.windowTitle() == "Add a Safe Workflow"
        assert [editor.trigger.itemText(index) for index in range(3)] == [
            "Run manually",
            "Daily at a set time",
            "When work starts",
        ]
        assert not _unapproved_han(_visible_texts(center) + _visible_texts(editor))
    finally:
        editor.close()


def _assert_japanese_center(center: FlagshipControlCenter) -> None:
    assert center.language == "ja-JP"
    assert center.tabs.count() == FLAGSHIP_TAB_COUNT
    assert [center.tabs.tabText(index) for index in range(FLAGSHIP_TAB_COUNT)] == [
        "タスクセンター",
        "ワークフロー",
        "クラウド接続",
        "スマートホーム",
        "リモートとプライバシー",
        "寄り添いと気遣い",
        "セキュリティ権限",
        "監査ログ",
    ]
    for index in range(center.tabs.count()):
        center.tabs.setCurrentIndex(index)
        assert center.tabs.currentWidget() is not None

    editor = _assert_canonical_values(center)
    try:
        assert editor.windowTitle() == "安全なワークフローを追加"
        assert [editor.trigger.itemText(index) for index in range(3)] == [
            "手動で実行",
            "毎日指定時刻",
            "作業開始時",
        ]
    finally:
        editor.close()


def _assert_user_data_is_preserved(center: FlagshipControlCenter) -> None:
    user_text = "不要翻譯這段文字 C:\\墨寒\\設定.json"
    user_url = "https://example.com/繁體路徑"
    assert (
        center._t(
            "[遠端裝置：{device}] {text}",
            device="我的手機",
            text=user_text,
        )
        == f"[Remote device: 我的手機] {user_text}"
    )
    assert center._t("已上傳：{name}", name=user_url) == f"Uploaded: {user_url}"
    detail = "UnicodeDecodeError: 無法解碼 C:\\舊資料.txt"
    assert detail in center._t("測試失敗：{error}", error=detail)


def run() -> None:
    validate_flagship_translations()
    assert all(len(row) == TRANSLATION_LANGUAGE_COUNT for row in FLAGSHIP_TRANSLATIONS.values())
    assert FlagshipTranslator("zh-CN").text("任務中心") == "任务中心"

    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        english_db = StudioDB(root / "english.db")
        japanese_db = StudioDB(root / "japanese.db")
        english = FlagshipControlCenter(english_db, root, language="en")
        japanese = FlagshipControlCenter(japanese_db, root, language="ja-JP")
        try:
            _assert_english_center(english)
            _assert_japanese_center(japanese)
            _assert_user_data_is_preserved(english)
        finally:
            english.close_services()
            japanese.close_services()
            english_db.close()
            japanese_db.close()
            english.deleteLater()
            japanese.deleteLater()
            app.processEvents()
    print("FLAGSHIP_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
