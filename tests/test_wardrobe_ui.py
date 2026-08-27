from __future__ import annotations

lazy import os
lazy import sys
lazy from datetime import datetime
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QWidget,
)
lazy from test_global_settings_actions import close_dashboard, dependencies

TAB_COUNT = 8
POSE_BUTTON_COUNT = 4
TWO_HOURS_SECONDS = 2 * 60 * 60

lazy from infrastructure.db import StudioDB
lazy from presentation.dashboard_window import Dashboard

LANGUAGE_CONTRACTS = {
    "zh-TW": {
        "tab": "雲裳閣",
        "import": ("匯入",),
        "apply": ("套用",),
        "restore": ("還原內建",),
        "packages": ("套件清單",),
        "compatibility": ("相容狀態",),
    },
    "zh-CN": {
        "tab": "云裳阁",
        "import": ("导入",),
        "apply": ("应用",),
        "restore": ("恢复内置", "还原内置"),
        "packages": ("套件列表", "套件清单"),
        "compatibility": ("兼容状态",),
    },
    "en": {
        "tab": "Wardrobe Pavilion",
        "import": ("Import",),
        "apply": ("Apply",),
        "restore": ("Restore Built-in", "Restore Built-In"),
        "packages": ("Package List",),
        "compatibility": ("Compatibility Status",),
    },
    "ja-JP": {
        "tab": "雲裳閣",
        "import": ("インポート",),
        "apply": ("適用",),
        "restore": ("内蔵に戻す", "内蔵へ戻す", "内蔵を復元", "内蔵衣装に戻す"),
        "packages": ("パッケージ一覧",),
        "compatibility": ("互換性状態", "互換状態"),
    },
}

FORBIDDEN_SUBPAGE_ACTIONS = frozenset({
    "保存設定",
    "保存工具權限",
    "保存安全權限",
    "保存連線設定",
    "保存设置",
    "保存工具权限",
    "保存安全权限",
    "保存连接设置",
    "Save Settings",
    "Save Tool Permissions",
    "Save Security Permissions",
    "Save Connection Settings",
    "設定を保存",
    "ツール権限を保存",
    "セキュリティ権限を保存",
    "接続設定を保存",
})


def build_language_dashboard(
    root: Path,
    language: str,
) -> tuple[StudioDB, Dashboard]:
    db = StudioDB(root / f"mohan-{language}.db")
    for key, value in (
        ("onboarding_complete", True),
        ("assistant_name", "MoHan"),
        ("user_title", "User"),
        ("organization_name", ""),
        ("window_title", "MoHan"),
        ("work_type", "一般辦公／行政"),
        ("ui_language", language),
        ("wake_word", "MoHan"),
    ):
        db.set_setting(key, value)
    with patch.object(QTimer, "start", return_value=None):
        dashboard = Dashboard(db, dependencies(root))
    dashboard.show()
    QApplication.processEvents()
    return db, dashboard


def visible_texts(root: QWidget) -> tuple[str, ...]:
    texts: list[str] = []
    for widget in (root, *root.findChildren(QWidget)):
        if widget is not root and not widget.isVisibleTo(root):
            continue
        if isinstance(widget, (QLabel, QPushButton, QCheckBox, QGroupBox)):
            texts.append(widget.text())
        if isinstance(widget, (QLineEdit, QTextEdit)):
            texts.append(widget.placeholderText())
        if isinstance(widget, QComboBox):
            texts.extend(widget.itemText(index) for index in range(widget.count()))
        if isinstance(widget, QListWidget):
            texts.extend(widget.item(index).text() for index in range(widget.count()))
        if isinstance(widget, QTabWidget):
            texts.extend(widget.tabText(index) for index in range(widget.count()))
    return tuple(text.strip() for text in texts if text and text.strip())


def assert_any_text_contains(
    texts: tuple[str, ...],
    alternatives: tuple[str, ...],
    capability: str,
) -> None:
    assert any(
        alternative.casefold() in text.casefold()
        for text in texts
        for alternative in alternatives
    ), f"Wardrobe Pavilion is missing {capability}: {alternatives!r}"


def test_wardrobe_tab_and_controls_have_four_language_contract() -> None:
    application = QApplication.instance() or QApplication([])
    failures: list[str] = []
    for language, contract in LANGUAGE_CONTRACTS.items():
        with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            db, dashboard = build_language_dashboard(Path(temp), language)
            try:
                tabs = dashboard.tabs
                tab_names = tuple(
                    tabs.tabText(index) for index in range(tabs.count())
                )
                try:
                    assert tabs.count() == TAB_COUNT, (
                        f"{language}: Dashboard must have 8 tabs; found "
                        f"{tabs.count()} ({tab_names!r})"
                    )
                    wardrobe_index = tab_names.index(contract["tab"])
                    page = tabs.widget(wardrobe_index)
                    assert page is not None
                    tabs.setCurrentIndex(wardrobe_index)
                    application.processEvents()
                    texts = visible_texts(page)
                    for capability in (
                        "import",
                        "apply",
                        "restore",
                        "packages",
                        "compatibility",
                    ):
                        assert_any_text_contains(
                            texts,
                            contract[capability],
                            capability,
                        )
                    pose_keys: list[int] = []
                    assert len(dashboard.wardrobe_pose_buttons) == POSE_BUTTON_COUNT
                    for button in dashboard.wardrobe_pose_buttons:
                        button.click()
                        application.processEvents()
                        assert button.isChecked()
                        pixmap = dashboard.wardrobe_character_preview.pixmap()
                        assert pixmap is not None and not pixmap.isNull()
                        pose_keys.append(pixmap.cacheKey())
                    assert len(set(pose_keys)) == POSE_BUTTON_COUNT
                    dashboard._restore_builtin_outfit()
                    lock_until = datetime.fromisoformat(
                        str(db.setting("wardrobe_manual_lock_until", ""))
                    )
                    changed_at = datetime.fromisoformat(
                        str(db.setting("wardrobe_last_changed_at", ""))
                    )
                    assert lock_until > changed_at
                    assert db.setting("active_outfit_id", "") == (
                        "mohan.default.blue-silver"
                    )
                    dashboard.manual_wardrobe_lock_hours.setValue(2)
                    application.processEvents()
                    revised_lock = datetime.fromisoformat(
                        str(db.setting("wardrobe_manual_lock_until", ""))
                    )
                    assert int(
                        (revised_lock - changed_at).total_seconds()
                    ) == TWO_HOURS_SECONDS
                    dashboard.manual_wardrobe_lock_hours.setValue(0)
                    application.processEvents()
                    assert db.setting("wardrobe_manual_lock_until", "missing") == ""
                    spin = dashboard.manual_wardrobe_lock_hours
                    assert spin.buttonSymbols() == QAbstractSpinBox.NoButtons
                    assert dashboard.manual_wardrobe_lock_hours_up.isEnabled()
                    assert dashboard.manual_wardrobe_lock_hours_down.isEnabled()
                    spin.setValue(spin.maximum())
                    assert spin.stepEnabled() & QAbstractSpinBox.StepUpEnabled
                    assert spin.stepEnabled() & QAbstractSpinBox.StepDownEnabled
                    dashboard.manual_wardrobe_lock_hours_up.click()
                    assert spin.value() == spin.minimum()
                    dashboard.manual_wardrobe_lock_hours_down.click()
                    assert spin.value() == spin.maximum()
                    forbidden = sorted(
                        text for text in texts if text in FORBIDDEN_SUBPAGE_ACTIONS
                    )
                    assert forbidden == [], (
                        f"{language}: Wardrobe subpage exposes save actions: {forbidden!r}"
                    )
                except (AssertionError, ValueError) as exc:
                    failures.append(str(exc))
            finally:
                close_dashboard(dashboard, db)
    assert not failures, "Wardrobe UI contract gaps:\n- " + "\n- ".join(failures)


if __name__ == "__main__":
    test_wardrobe_tab_and_controls_have_four_language_contract()
    print("WARDROBE_UI_OK")
