from __future__ import annotations

lazy import os
lazy import re
lazy import subprocess
lazy import sys
lazy import webbrowser
lazy from contextlib import ExitStack, contextmanager
lazy from dataclasses import dataclass, replace
lazy from datetime import UTC, datetime
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QEvent, QModelIndex, QObject, Qt, QTimer, Signal
lazy from PySide6.QtGui import QAction
lazy from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListView,
    QMenu,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QWidget,
)

lazy from application.multisensory_interaction import (
    InteractionKind,
    ProactiveInteraction,
    interaction_text,
)
lazy from application.service_container import create_presentation_ports
lazy from infrastructure.db import StudioDB
lazy from infrastructure.platform_contracts import PlatformCapabilities, PlatformPaths
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.dashboard_dialogs import (
    ArchivedMemoryDialog,
    ChatHistoryDialog,
    MemoryEditorDialog,
)
lazy from presentation.dashboard_window import Dashboard

LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")

LANGUAGE_SELECTOR_NAMES = (
    "繁體中文（台灣）",
    "简体中文（中国大陆）",
    "English",
    "日本語",
)

# These are deliberately user-authored, mixed-script values. They are not
# translations and must survive every storage and rendering path byte for byte.
USER_SEEDS = {
    "todo_title": "Todo seed｜繁體原句｜简体原句｜English｜日本語",
    "idea_title": "Idea seed｜繁體標題｜简体标题｜English｜日本語",
    "idea_content": "Idea body｜繁體內文｜简体内容｜English｜日本語",
    "platform_name": "Platform seed｜繁體平台｜简体平台｜English｜日本語",
    "memory_title": "Memory seed｜繁體標題｜简体标题｜English｜日本語",
    "memory_content": "Memory body｜繁體內文｜简体内容｜English｜日本語",
    "chat_content": "Chat seed｜繁體對話｜简体对话｜English｜日本語",
}

EXPECTED_TABS = {
    "zh-TW": ("對話", "今日待辦", "工作平台", "長期記憶", "聲音", "電腦權限", "雲裳閣", "設定"),
    "zh-CN": ("对话", "今日待办", "工作平台", "长期记忆", "语音", "电脑权限", "云裳阁", "设置"),
    "en": (
        "Chat",
        "Today",
        "Work platforms",
        "Long-term memory",
        "Voice",
        "Computer permissions",
        "Wardrobe Pavilion",
        "Settings",
    ),
    "ja-JP": ("会話", "今日", "仕事プラットフォーム", "長期記憶", "音声", "パソコンの権限", "雲裳閣", "設定"),
}

EXPECTED_RUNTIME_PHRASES = {
    "zh-TW": (
        "今日卷冊尚空",
        "尚未建立工作平台",
        "這個分類目前沒有記憶",
        "編輯長期記憶",
        "已封存的長期記憶",
        "管理／清除對話",
    ),
    "zh-CN": (
        "今日待办尚空",
        "尚未建立工作平台",
        "这个分类目前没有记忆",
        "编辑长期记忆",
        "已封存的长期记忆",
        "管理／清除对话",
    ),
    "en": (
        "No tasks yet today",
        "No work platforms yet",
        "There are no memories in this category",
        "Edit long-term memory",
        "Archived long-term memories",
        "Manage / clear chats",
    ),
    "ja-JP": (
        "今日の予定はまだありません",
        "仕事プラットフォームはまだありません",
        "この分類には記憶がありません",
        "長期記憶を編集",
        "保管済みの長期記憶",
        "会話の管理／消去",
    ),
}

# Phrase-level rules avoid the invalid shortcut of banning all Han characters.
# Shared spellings such as ``新增`` are valid Simplified Chinese too; only
# orthographically or idiomatically Traditional residues belong in zh-CN.
FORBIDDEN_PHRASES = {
    "zh-TW": (
        "设置",
        "语音",
        "对话",
        "电脑权限",
        "今日待办",
        "长期记忆",
        "删除",
        "编辑",
        "选择",
        "用户",
        "文件夹",
    ),
    "zh-CN": (
        "設定",
        "聲音",
        "語音",
        "對話",
        "電腦權限",
        "今日待辦",
        "長期記憶",
        "刪除",
        "編輯",
        "選擇",
        "開啟",
        "關閉",
        "儲存",
        "資料夾",
        "使用者",
        "麥克風",
        "視窗",
        "顯示",
        "啟動",
        "連線",
        "還原",
        "靈感",
    ),
    "ja-JP": (
        "今日待辦",
        "工作平台",
        "電腦權限",
        "開始工作",
        "結束工作",
        "今日卷冊尚空",
        "尚未建立",
        "請先",
        "刪除勾選",
        "儲存",
        "開啟網站",
        "聲音風格",
        "語音狀態",
        "未計時",
        "分鐘",
        "使用者",
        "資料夾",
        "連線",
        "啟動",
        "關閉",
        "顯示",
        "選擇",
        "輸入",
    ),
}

REQUIRED_CANONICAL_COMBOS = (
    "mode_combo",
    "todo_category",
    "platform_filter",
    "memory_category",
    "memory_filter",
    "speech_recognition",
    "voice_engine",
    "azure_region",
    "azure_hd_region",
    "realtime_output_mode",
    "realtime_noise_reduction",
    "realtime_turn_detection",
    "profile_work_type",
    "profile_ui_language",
    "platform_status",
)

# Voice catalogs are intentionally language- and region-dependent. Their
# current display catalogs are tested elsewhere, so they are not cross-language
# itemData invariants in this gate.
DYNAMIC_VOICE_COMBOS = frozenset(
    {
        "windows_voice",
        "tts_voice",
        "realtime_voice",
        "azure_voice",
        "azure_hd_voice",
    }
)

WINDOWS_VOICES = (
    ("OneCore::Microsoft Yating", "zh-TW"),
    ("OneCore::Microsoft Xiaoxiao", "zh-CN"),
    ("OneCore::Microsoft Zira", "en-US"),
    ("OneCore::Microsoft Ayumi", "ja-JP"),
)


@dataclass(frozen=True, slots=True)
class CapturedText:
    source: str
    kind: str
    value: str


@dataclass(frozen=True, slots=True)
class GateIssue:
    language: str
    check: str
    source: str
    value: str


@dataclass(frozen=True, slots=True)
class LanguageEvidence:
    language: str
    tabs: tuple[str, ...]
    records: tuple[CapturedText, ...]
    database_values: dict[str, str]
    canonical_item_data: dict[str, tuple[str, ...]]


class FakeSecretStore:
    def load(self) -> str:
        return ""

    def save(self, _value: str) -> None:
        return None

    def clear(self) -> None:
        return None


class FakeListener(QObject):
    recognized = Signal(str)
    failed = Signal(str)
    listening_changed = Signal(bool)
    recording_changed = Signal(bool)
    status_changed = Signal(str)
    diagnostic_changed = Signal(str)

    def toggle_listening(self) -> None:
        return None


class StaticVoiceCatalog:
    def windows_voices(self) -> list[tuple[str, str]]:
        return list(WINDOWS_VOICES)


class OfflinePlatformServices:
    capabilities = PlatformCapabilities(
        platform_id="windows",
        display_name="Windows",
        system_local_speech=True,
        verified_female_voice_catalog=True,
        offline_speech_recognition=True,
        secure_secret_storage=True,
        desktop_autostart=True,
        native_window_management=True,
        published_installers=("portable-zip", "exe", "msi"),
    )

    def __init__(self, root: Path):
        self.paths = PlatformPaths(
            data=root / "data",
            config=root / "config",
            cache=root / "cache",
        )

    def set_autostart(
        self,
        _enabled: bool,
        *,
        application_id: str,
        command: str,
    ) -> None:
        raise AssertionError(
            f"Offline UI gate attempted autostart: {application_id} {command}"
        )

    def open_path(self, path: Path) -> None:
        raise AssertionError(f"Offline UI gate attempted external open: {path}")


def fake_secret_store_factory(
    _path: Path,
    _description: str = "MoHan protected secret",
) -> FakeSecretStore:
    return FakeSecretStore()


def deny_network(*args, **kwargs):
    del kwargs
    target = args[0] if args else "unknown target"
    raise AssertionError(f"Offline UI gate attempted network access: {target!r}")


def deny_process(*args, **kwargs):
    del kwargs
    target = args[0] if args else "unknown command"
    raise AssertionError(f"Offline UI gate attempted a process: {target!r}")


@contextmanager
def offline_runtime():
    """Make accidental I/O fail closed while runtime widgets are constructed."""
    with ExitStack() as stack:
        for target in (
            "integrations.ai_client.urlopen",
            "integrations.cloud_connectors.urlopen",
            "integrations.home_assistant.urlopen",
            "integrations.speech.urlopen",
            "infrastructure.updater.urlopen",
            "socket.create_connection",
            "websocket.WebSocketApp",
        ):
            stack.enter_context(patch(target, side_effect=deny_network))
        stack.enter_context(patch.object(subprocess, "Popen", side_effect=deny_process))
        stack.enter_context(patch.object(webbrowser, "open", side_effect=deny_process))
        # Every UI timer is irrelevant to a static localization traversal. This
        # also prevents screen capture, scheduled workflows, and polling.
        stack.enter_context(patch.object(QTimer, "start", return_value=None))
        yield


def clean_text(value: object) -> str:
    return str(value or "").strip()


def object_path(root: QWidget, obj: QObject) -> str:
    parts: list[str] = []
    current: QObject | None = obj
    while current is not None:
        class_name = current.metaObject().className()
        name = clean_text(current.objectName())
        segment = f"{class_name}#{name}" if name else class_name
        parent = current.parent()
        if not name and parent is not None:
            siblings = [
                child
                for child in parent.children()
                if child.metaObject().className() == class_name
            ]
            if len(siblings) > 1:
                segment += f"[{siblings.index(current)}]"
        parts.append(segment)
        if current is root:
            break
        current = parent
    return "/".join(reversed(parts))


def object_aliases(root: QWidget) -> dict[int, str]:
    aliases: dict[int, str] = {}

    def bind(owner: object, prefix: str = "") -> None:
        for name, value in vars(owner).items():
            alias = f"{prefix}{name}"
            if isinstance(value, QObject):
                aliases.setdefault(id(value), alias)
            elif isinstance(value, dict):
                for key, item in value.items():
                    if isinstance(item, QObject):
                        aliases.setdefault(id(item), f"{alias}[{key}]")

    bind(root)
    flagship = getattr(root, "flagship_center", None)
    if flagship is not None:
        bind(flagship, "flagship_center.")
    return aliases


def add_record(
    records: set[CapturedText],
    source: str,
    kind: str,
    value: object,
) -> None:
    text = clean_text(value)
    if text:
        records.add(CapturedText(source, kind, text))


def widget_content_records(
    widget: QWidget,
    source: str,
) -> set[CapturedText]:
    records: set[CapturedText] = set()
    if isinstance(widget, QLabel):
        add_record(records, source, "text", widget.text())
    if isinstance(widget, (QPushButton, QCheckBox)):
        add_record(records, source, "text", widget.text())
    if isinstance(widget, QGroupBox):
        add_record(records, source, "title", widget.title())
    records.update(widget_editor_records(widget, source))
    records.update(widget_container_records(widget, source))
    return records


def widget_editor_records(
    widget: QWidget,
    source: str,
) -> set[CapturedText]:
    records: set[CapturedText] = set()
    if isinstance(widget, QLineEdit):
        # Secret fields are intentionally never copied into diagnostics.
        if widget.echoMode() == QLineEdit.Normal:
            add_record(records, source, "text", widget.text())
        add_record(records, source, "placeholder", widget.placeholderText())
    if isinstance(widget, QTextEdit):
        add_record(records, source, "text", widget.toPlainText())
        add_record(records, source, "placeholder", widget.placeholderText())
    if isinstance(widget, QComboBox):
        add_record(records, source, "text", widget.currentText())
        for index in range(widget.count()):
            add_record(records, source, f"combo-item[{index}]", widget.itemText(index))
            for kind, role in (
                ("tooltip", Qt.ItemDataRole.ToolTipRole),
                ("accessibleText", Qt.ItemDataRole.AccessibleTextRole),
                (
                    "accessibleDescription",
                    Qt.ItemDataRole.AccessibleDescriptionRole,
                ),
            ):
                add_record(
                    records,
                    source,
                    f"combo-item-{kind}[{index}]",
                    widget.itemData(index, role),
                )
    return records


def widget_container_records(
    widget: QWidget,
    source: str,
) -> set[CapturedText]:
    records: set[CapturedText] = set()
    if isinstance(widget, QTabWidget):
        for index in range(widget.count()):
            add_record(records, source, f"tabText[{index}]", widget.tabText(index))
            add_record(
                records,
                source,
                f"tabToolTip[{index}]",
                widget.tabToolTip(index),
            )
            add_record(
                records,
                source,
                f"tabWhatsThis[{index}]",
                widget.tabWhatsThis(index),
            )
            add_record(
                records,
                source,
                f"tabAccessibleName[{index}]",
                widget.tabBar().accessibleTabName(index),
            )
    if isinstance(widget, QMenu):
        add_record(records, source, "menu-title", widget.title())
    return records


def widget_records(
    root: QWidget,
    widget: QWidget,
    scope: str,
    aliases: dict[int, str],
) -> set[CapturedText]:
    records: set[CapturedText] = set()
    identity = aliases.get(id(widget), object_path(root, widget))
    source = f"{scope}/{identity}"
    for kind, value in (
        ("windowTitle", widget.windowTitle()),
        ("tooltip", widget.toolTip()),
        ("statusTip", widget.statusTip()),
        ("whatsThis", widget.whatsThis()),
        ("accessibleName", widget.accessibleName()),
        ("accessibleDescription", widget.accessibleDescription()),
    ):
        add_record(records, source, kind, value)
    records.update(widget_content_records(widget, source))
    return records


def action_records(
    root: QWidget,
    action: QAction,
    scope: str,
    aliases: dict[int, str],
) -> set[CapturedText]:
    identity = aliases.get(id(action), object_path(root, action))
    source = f"{scope}/{identity}"
    records: set[CapturedText] = set()
    for kind, value in (
        ("action-text", action.text()),
        ("action-iconText", action.iconText()),
        ("action-tooltip", action.toolTip()),
        ("action-statusTip", action.statusTip()),
        ("action-whatsThis", action.whatsThis()),
    ):
        add_record(records, source, kind, value)
    return records


def has_combo_ancestor(widget: QWidget) -> bool:
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QComboBox):
            return True
        parent = parent.parentWidget()
    return False


def model_records(
    root: QWidget,
    view: QAbstractItemView,
    scope: str,
    aliases: dict[int, str],
) -> set[CapturedText]:
    model = view.model()
    combo_views = {
        id(combo.view())
        for combo in root.findChildren(QComboBox)
    }
    combo_models = {
        id(combo.model())
        for combo in root.findChildren(QComboBox)
    }
    if (
        has_combo_ancestor(view)
        or view.metaObject().className() == "QComboBoxListView"
        or id(view) in combo_views
        or (model is not None and id(model) in combo_models)
    ):
        return set()
    identity = aliases.get(id(view), object_path(root, view))
    source = f"{scope}/{identity}"
    if model is None:
        return set()
    records: set[CapturedText] = set()
    is_list_view = isinstance(view, QListView)
    roles = (
        ("item-text", Qt.ItemDataRole.DisplayRole),
        ("item-tooltip", Qt.ItemDataRole.ToolTipRole),
        ("item-accessibleText", Qt.ItemDataRole.AccessibleTextRole),
        ("item-accessibleDescription", Qt.ItemDataRole.AccessibleDescriptionRole),
    )

    def visit(parent: QModelIndex | None = None) -> None:
        parent = QModelIndex() if parent is None else parent
        for row in range(model.rowCount(parent)):
            column_count = 1 if is_list_view else model.columnCount(parent)
            for column in range(column_count):
                index = model.index(row, column, parent)
                item_source = f"{source}[{row},{column}]"
                for kind, role in roles:
                    add_record(records, item_source, kind, model.data(index, role))
                if not is_list_view and model.hasChildren(index):
                    visit(index)

    visit()
    return records


def collect_visible_state(
    root: QWidget,
    scope: str,
    aliases: dict[int, str],
) -> set[CapturedText]:
    records: set[CapturedText] = set()
    widgets = (root, *root.findChildren(QWidget))
    for widget in widgets:
        if widget is not root and not widget.isVisibleTo(root):
            continue
        records.update(widget_records(root, widget, scope, aliases))
        if isinstance(widget, QAbstractItemView):
            records.update(model_records(root, widget, scope, aliases))
    return records


def collect_runtime_text(
    application: QApplication,
    root: QWidget,
    scope: str,
) -> tuple[CapturedText, ...]:
    root.show()
    application.processEvents()
    aliases = object_aliases(root)
    records: set[CapturedText] = set()
    explored: set[tuple[int, int]] = set()

    def visit(container: QWidget) -> None:
        records.update(collect_visible_state(root, scope, aliases))
        visible_tabs = [
            tab
            for tab in container.findChildren(QTabWidget)
            if tab.isVisibleTo(root)
        ]
        for tab in visible_tabs:
            original_index = tab.currentIndex()
            for index in range(tab.count()):
                marker = (id(tab), index)
                if marker in explored:
                    continue
                explored.add(marker)
                tab.setCurrentIndex(index)
                application.processEvents()
                records.update(collect_visible_state(root, scope, aliases))
                page = tab.widget(index)
                if page is not None:
                    visit(page)
            tab.setCurrentIndex(original_index)
            application.processEvents()

    visit(root)
    # Menus may not be open during a traversal, but already-created menu titles
    # and actions are runtime UI and must still pass the release gate.
    for menu in root.findChildren(QMenu):
        records.update(widget_records(root, menu, scope, aliases))
    for action in root.findChildren(QAction):
        records.update(action_records(root, action, scope, aliases))
    return tuple(sorted(records, key=lambda item: (item.source, item.kind, item.value)))


def combo_item_data(combo: QComboBox) -> tuple[str, ...]:
    return tuple(repr(combo.itemData(index)) for index in range(combo.count()))


def canonical_combo_snapshot(dashboard: Dashboard) -> dict[str, tuple[str, ...]]:
    aliases = object_aliases(dashboard)
    snapshot: dict[str, tuple[str, ...]] = {}
    for combo in dashboard.findChildren(QComboBox):
        identity = aliases.get(id(combo), object_path(dashboard, combo))
        if identity in DYNAMIC_VOICE_COMBOS:
            continue
        values = combo_item_data(combo)
        if values and any(value != "None" for value in values):
            snapshot[identity] = values
    if dashboard.platform_controls:
        first_controls = next(iter(dashboard.platform_controls.values()))
        snapshot["platform_status"] = combo_item_data(first_controls.status)
    return snapshot


def stop_and_close(application: QApplication, widget: QWidget) -> None:
    flagship = getattr(widget, "flagship_center", None)
    if flagship is not None:
        flagship.close_services()
    for timer in widget.findChildren(QTimer):
        timer.stop()
    widget.close()
    widget.deleteLater()
    application.sendPostedEvents(None, QEvent.DeferredDelete)
    application.processEvents()


def configure_language(db: StudioDB, language: str) -> None:
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


def seed_database(db: StudioDB) -> tuple[int, dict[str, str]]:
    todo_id = db.add_todo(USER_SEEDS["todo_title"])
    idea_id = db.add_idea(USER_SEEDS["idea_title"], USER_SEEDS["idea_content"])
    assert db.add_platform(USER_SEEDS["platform_name"])
    memory_id = db.add_memory(
        USER_SEEDS["memory_content"],
        title=USER_SEEDS["memory_title"],
    )
    db.log_chat("user", USER_SEEDS["chat_content"])

    todo = next(row for row in db.list_todos(True) if int(row["id"]) == todo_id)
    idea = db.idea(idea_id)
    memory = db.memory(memory_id)
    platform = db.platform_rows()[0]
    chat = db.chat_history(1)[0]
    assert idea is not None
    assert memory is not None
    return memory_id, {
        "todo_title": str(todo["title"]),
        "idea_title": str(idea["title"]),
        "idea_content": str(idea["content"]),
        "platform_name": str(platform["platform"]),
        "memory_title": str(memory["title"]),
        "memory_content": str(memory["content"]),
        "chat_content": str(chat["content"]),
    }


def dashboard_dependencies(root: Path) -> DashboardDependencies:
    presentation_ports = replace(
        create_presentation_ports(),
        voice_catalog=StaticVoiceCatalog(),
        autostart_configurator=lambda _enabled, _platform: None,
    )
    return DashboardDependencies(
        listener=FakeListener(),
        secret_store=FakeSecretStore(),
        azure_secret_store=FakeSecretStore(),
        azure_hd_secret_store=FakeSecretStore(),
        secret_store_factory=fake_secret_store_factory,
        platform_services=OfflinePlatformServices(root),
        presentation_ports=presentation_ports,
    )


def build_language_evidence(
    application: QApplication,
    language: str,
) -> LanguageEvidence:
    records: list[CapturedText] = []
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        db = StudioDB(root / f"mohan-{language}.db")
        try:
            configure_language(db, language)
            with offline_runtime():
                empty_dashboard = Dashboard(db, dashboard_dependencies(root))
                empty_tabs = tuple(
                    empty_dashboard.tabs.tabText(index)
                    for index in range(empty_dashboard.tabs.count())
                )
                records.extend(
                    collect_runtime_text(
                        application,
                        empty_dashboard,
                        "empty-dashboard",
                    )
                )
                stop_and_close(application, empty_dashboard)

                memory_id, database_values = seed_database(db)
                seeded_dashboard = Dashboard(db, dashboard_dependencies(root))
                records.extend(
                    collect_runtime_text(
                        application,
                        seeded_dashboard,
                        "seeded-dashboard",
                    )
                )
                canonical = canonical_combo_snapshot(seeded_dashboard)

                memory = db.memory(memory_id)
                assert memory is not None
                dialogs = (
                    (
                        "memory-editor",
                        MemoryEditorDialog(memory, language=language),
                    ),
                    (
                        "archived-memory",
                        ArchivedMemoryDialog(db, language=language),
                    ),
                    (
                        "chat-history",
                        ChatHistoryDialog(db, language=language),
                    ),
                )
                for scope, dialog in dialogs:
                    records.extend(
                        collect_runtime_text(application, dialog, scope)
                    )
                    stop_and_close(application, dialog)
                stop_and_close(application, seeded_dashboard)
        finally:
            db.close()
    return LanguageEvidence(
        language=language,
        tabs=empty_tabs,
        records=tuple(
            sorted(
                set(records),
                key=lambda item: (item.source, item.kind, item.value),
            )
        ),
        database_values=database_values,
        canonical_item_data=canonical,
    )


def scrub_approved_content(record: CapturedText) -> str:
    value = record.value
    # User content is an explicit data exception, never a system-translation
    # exception. A changed seed no longer matches and is therefore reported.
    for seed in USER_SEEDS.values():
        value = value.replace(seed, "")
    # MoHan's source-language character name is an intentional brand spelling.
    value = value.replace("墨寒", "")
    # Language names are allowed only as self-names inside the language combo.
    if "profile_ui_language" in record.source and record.kind.startswith(
        "combo-item"
    ):
        for self_name in LANGUAGE_SELECTOR_NAMES:
            value = value.replace(self_name, "")
    return value


def issue(
    issues: set[GateIssue],
    language: str,
    check: str,
    source: str,
    value: object,
) -> None:
    issues.add(GateIssue(language, check, source, clean_text(value)))


def validate_expected_ui(
    evidence: LanguageEvidence,
    issues: set[GateIssue],
) -> None:
    language = evidence.language
    expected_tabs = EXPECTED_TABS[language]
    if evidence.tabs != expected_tabs:
        issue(
            issues,
            language,
            "dashboard tab labels",
            "Dashboard.tabs",
            f"expected={expected_tabs!r}; actual={evidence.tabs!r}",
        )

    visible_values = tuple(record.value for record in evidence.records)
    for phrase in EXPECTED_RUNTIME_PHRASES[language]:
        if not any(phrase in value for value in visible_values):
            issue(
                issues,
                language,
                "missing expected runtime phrase",
                "runtime traversal",
                phrase,
            )

def validate_user_seeds(
    evidence: LanguageEvidence,
    issues: set[GateIssue],
) -> None:
    language = evidence.language
    visible_values = tuple(record.value for record in evidence.records)
    for key, expected in USER_SEEDS.items():
        actual = evidence.database_values.get(key, "<missing>")
        if actual != expected:
            issue(
                issues,
                language,
                "user seed changed in database",
                f"database.{key}",
                f"expected={expected!r}; actual={actual!r}",
            )
        if not any(expected in value for value in visible_values):
            issue(
                issues,
                language,
                "user seed missing or changed in UI",
                f"runtime.{key}",
                expected,
            )


def validate_script_policy(
    evidence: LanguageEvidence,
    issues: set[GateIssue],
) -> None:
    language = evidence.language
    if language == "en":
        for record in evidence.records:
            residue = scrub_approved_content(record)
            match = CJK.search(residue)
            if match is not None:
                issue(
                    issues,
                    language,
                    f"unapproved CJK starts with {match.group(0)!r}",
                    f"{record.source}::{record.kind}",
                    record.value,
                )
        return

    forbidden = FORBIDDEN_PHRASES.get(language, ())
    for record in evidence.records:
        residue = scrub_approved_content(record)
        for phrase in forbidden:
            if phrase in residue:
                issue(
                    issues,
                    language,
                    f"forbidden phrase {phrase!r}",
                    f"{record.source}::{record.kind}",
                    record.value,
                )


def validate_language(
    evidence: LanguageEvidence,
    issues: set[GateIssue],
) -> None:
    validate_expected_ui(evidence, issues)
    validate_user_seeds(evidence, issues)
    validate_script_policy(evidence, issues)


def validate_canonical_item_data(
    evidence_by_language: dict[str, LanguageEvidence],
    issues: set[GateIssue],
) -> None:
    baseline = evidence_by_language["zh-TW"].canonical_item_data
    for name in REQUIRED_CANONICAL_COMBOS:
        values = baseline.get(name)
        if values is None or not any(value != "None" for value in values):
            issue(
                issues,
                "zh-TW",
                "missing canonical itemData",
                name,
                values,
            )

    all_names = set().union(
        *(
            set(evidence.canonical_item_data)
            for evidence in evidence_by_language.values()
        )
    )
    for name in sorted(all_names):
        if name in DYNAMIC_VOICE_COMBOS:
            continue
        expected = baseline.get(name)
        for language in LANGUAGES[1:]:
            actual = evidence_by_language[language].canonical_item_data.get(name)
            if actual != expected:
                issue(
                    issues,
                    language,
                    "canonical itemData changed with UI language",
                    name,
                    f"zh-TW={expected!r}; {language}={actual!r}",
                )


def validate_morning_welcome_localization() -> None:
    interaction = ProactiveInteraction(InteractionKind.WELCOME_BACK, "happy")
    morning = datetime(2026, 8, 13, 8, 0, tzinfo=UTC)
    lines = {
        language: interaction_text(
            language,
            interaction,
            user_title="Owner",
            wall_time=morning,
        )
        for language in LANGUAGES
    }
    assert lines == {
        "zh-TW": "早安，Owner。",
        "zh-CN": "早上好，Owner。",
        "en": "Good morning, Owner.",
        "ja-JP": "おはようございます、Owner。",
    }
    assert len(set(lines.values())) == len(LANGUAGES)


def format_issues(issues: set[GateIssue]) -> str:
    ordered = sorted(
        issues,
        key=lambda item: (item.language, item.check, item.source, item.value),
    )
    lines = [f"Full UI localization gate found {len(ordered)} issue(s):"]
    lines.extend(
        f"- [{item.language}] {item.check} | {item.source} -> {item.value!r}"
        for item in ordered
    )
    return "\n".join(lines)


def run() -> None:
    validate_morning_welcome_localization()
    application = QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    evidence_by_language = {
        language: build_language_evidence(application, language)
        for language in LANGUAGES
    }
    issues: set[GateIssue] = set()
    for evidence in evidence_by_language.values():
        validate_language(evidence, issues)
    validate_canonical_item_data(evidence_by_language, issues)
    assert not issues, format_issues(issues)
    print("FULL_UI_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
