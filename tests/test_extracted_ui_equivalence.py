from __future__ import annotations

lazy import ast
lazy import importlib
lazy import os
lazy import sys
lazy from pathlib import Path

lazy from PySide6.QtGui import QIcon, QPixmap
lazy from PySide6.QtWidgets import QApplication, QWidget

lazy from presentation.dashboard_dialogs import (
    ArchivedMemoryDialog,
    ChatHistoryDialog,
    ClickableLabel,
    IdeaEditorDialog,
    MemoryEditorDialog,
    TodoRow,
    ZoomTextBrowser,
)
lazy from presentation.first_run_wizard import FirstRunWizard
lazy from ui_localization import (
    SIMPLIFIED_WORK_TYPE_LABELS,
    WORK_TYPE_LABELS,
    display_label,
    ui_text,
)
lazy from ui_localization_ja import JAPANESE_WORK_TYPE_LABELS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

APP_PATH = PROJECT_ROOT / "app.py"
APP_PROFILE_PATH = PROJECT_ROOT / "domain" / "app_profile.py"
DASHBOARD_DIALOGS_PATH = PROJECT_ROOT / "presentation" / "dashboard_dialogs.py"
FIRST_RUN_WIZARD_PATH = PROJECT_ROOT / "presentation" / "first_run_wizard.py"

DASHBOARD_DIALOG_CLASSES = (
    "ClickableLabel",
    "ZoomTextBrowser",
    "TodoRow",
    "IdeaEditorDialog",
    "MemoryEditorDialog",
    "ArchivedMemoryDialog",
    "ChatHistoryDialog",
)
EXTRACTED_UI_CLASSES = (*DASHBOARD_DIALOG_CLASSES, "FirstRunWizard")
ADD_ITEM_ARG_COUNT = 2

DEFAULT_PROFILE = {
    "assistant_name": "墨寒",
    "user_title": "主上",
    "organization_name": "",
    "window_title": "",
    "work_type": "一般辦公／行政",
    "ui_language": "zh-TW",
    "wake_word": "墨寒",
}

WORK_TYPES = (
    "一般辦公／行政",
    "專案管理",
    "自由工作者／接案",
    "創作／內容工作",
    "軟體開發／技術",
    "教育／研究",
    "銷售／客戶服務",
    "其他（可自行輸入）",
)

CORE_TEXT = {
    "zh-TW": ("首次啟動設定", "助理名稱", "尚缺必要資料"),
    "zh-CN": ("首次启动设置", "助手名称", "缺少必要信息"),
    "en": (
        "First-run setup",
        "Assistant name",
        "Required information missing",
    ),
    "ja-JP": (
        "初回セットアップ",
        "アシスタント名",
        "必須情報がありません",
    ),
}

WORK_TYPE_TEXT = {
    "zh-TW": WORK_TYPES,
    "zh-CN": (
        "一般办公／行政",
        "项目管理",
        "自由职业／承接项目",
        "创作／内容工作",
        "软件开发／技术",
        "教育／研究",
        "销售／客户服务",
        "其他（可自行输入）",
    ),
    "en": (
        "General office / administration",
        "Project management",
        "Freelance / contract work",
        "Creative / content work",
        "Software development / technology",
        "Education / research",
        "Sales / customer service",
        "Other (enter your own)",
    ),
    "ja-JP": (
        "一般事務／管理",
        "プロジェクト管理",
        "フリーランス／受託",
        "創作／コンテンツ制作",
        "ソフトウェア開発／技術",
        "教育／研究",
        "営業／カスタマーサービス",
        "その他（自由入力）",
    ),
}

LANGUAGE_CHOICES = (
    ("繁體中文（台灣）", "zh-TW"),
    ("简体中文（中国大陆）", "zh-CN"),
    ("English", "en"),
    ("日本語", "ja-JP"),
)


def _module_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assignment_value(
    tree: ast.Module | ast.ClassDef,
    name: str,
) -> object:
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        if not any(
            isinstance(target, ast.Name) and target.id == name
            for target in targets
        ):
            continue
        value = node.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "frozendict"
            and len(value.args) == 1
            and not value.keywords
        ):
            value = value.args[0]
        return ast.literal_eval(value)
    raise AssertionError(f"Missing literal assignment: {name}")


def _class_node(tree: ast.Module, name: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"Missing class: {name}")


def _method_node(class_node: ast.ClassDef, name: str) -> ast.FunctionDef:
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Missing method: {class_node.name}.{name}")


def _language_choices(wizard_class: ast.ClassDef) -> tuple[tuple[str, str], ...]:
    method = _method_node(wizard_class, "_initialize_language")
    choices: list[tuple[str, str]] = []
    for statement in method.body:
        if not isinstance(statement, ast.Expr) or not isinstance(
            statement.value,
            ast.Call,
        ):
            continue
        call = statement.value
        if (
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "addItem"
            and isinstance(call.func.value, ast.Attribute)
            and call.func.value.attr == "ui_language"
            and len(call.args) == ADD_ITEM_ARG_COUNT
        ):
            choices.append(
                (
                    ast.literal_eval(call.args[0]),
                    ast.literal_eval(call.args[1]),
                )
            )
    return tuple(choices)


def _require_runtime_modules() -> tuple[object, object]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        importlib.import_module("PySide6")
    except ModuleNotFoundError as exc:
        raise AssertionError(
            "PySide6 is required for the extracted UI equivalence gate; "
            "the gate must not be skipped."
        ) from exc
    return (
        importlib.import_module("presentation.dashboard_dialogs"),
        importlib.import_module("presentation.first_run_wizard"),
    )


def _resolved_owner_classes() -> dict[str, object]:
    return {
        "ArchivedMemoryDialog": ArchivedMemoryDialog,
        "ChatHistoryDialog": ChatHistoryDialog,
        "ClickableLabel": ClickableLabel,
        "FirstRunWizard": FirstRunWizard,
        "IdeaEditorDialog": IdeaEditorDialog,
        "MemoryEditorDialog": MemoryEditorDialog,
        "TodoRow": TodoRow,
        "ZoomTextBrowser": ZoomTextBrowser,
    }


def _resolve_export(value: object) -> object:
    resolver = getattr(value, "resolve", None)
    return resolver() if callable(resolver) else value


def test_extracted_ui_classes_have_one_true_owner() -> None:
    app_tree = _module_tree(APP_PATH)
    dialogs_tree = _module_tree(DASHBOARD_DIALOGS_PATH)
    wizard_tree = _module_tree(FIRST_RUN_WIZARD_PATH)
    locally_defined = {
        node.name
        for node in app_tree.body
        if isinstance(node, ast.ClassDef)
    }
    duplicates = sorted(locally_defined.intersection(EXTRACTED_UI_CLASSES))
    assert duplicates == [], (
        "app.py must not define extracted UI classes: "
        f"{duplicates!r}"
    )
    for name in DASHBOARD_DIALOG_CLASSES:
        assert _class_node(dialogs_tree, name).name == name
    assert _class_node(wizard_tree, "FirstRunWizard").name == "FirstRunWizard"

    app_exports = set(_assignment_value(app_tree, "__all__"))
    assert not app_exports.intersection(EXTRACTED_UI_CLASSES)


def test_owner_modules_resolve_exact_extracted_classes() -> None:
    dialogs_module, wizard_module = _require_runtime_modules()
    exports = _resolved_owner_classes()
    for name in DASHBOARD_DIALOG_CLASSES:
        assert name in vars(dialogs_module), name
        export = _resolve_export(exports[name])
        assert export.__module__ == "presentation.dashboard_dialogs", name
        assert export.__name__ == name
        exports[name] = export

    assert "FirstRunWizard" in vars(wizard_module)
    wizard_export = _resolve_export(exports["FirstRunWizard"])
    assert wizard_export.__module__ == "presentation.first_run_wizard"
    assert wizard_export.__name__ == "FirstRunWizard"


def test_first_run_wizard_pure_defaults_and_four_language_values() -> None:
    wizard_tree = _module_tree(FIRST_RUN_WIZARD_PATH)
    profile_tree = _module_tree(APP_PROFILE_PATH)
    assert _assignment_value(wizard_tree, "__all__") == ("FirstRunWizard",)
    assert _assignment_value(profile_tree, "DEFAULT_PROFILE") == DEFAULT_PROFILE
    wizard_class = _class_node(wizard_tree, "FirstRunWizard")
    assert _assignment_value(wizard_class, "WORK_TYPES") == WORK_TYPES
    assert _language_choices(wizard_class) == LANGUAGE_CHOICES

    fallback_text = ("首次啟動設定", "助理名稱", "尚缺必要資料")
    keys = ("first_run_title", "assistant_name", "required_title")
    for language, expected in CORE_TEXT.items():
        actual = tuple(
            ui_text(language, key, fallback)
            for key, fallback in zip(keys, fallback_text, strict=True)
        )
        assert actual == expected, language
        work_type_labels = tuple(
            display_label(
                language,
                value,
                WORK_TYPE_LABELS,
                SIMPLIFIED_WORK_TYPE_LABELS,
                JAPANESE_WORK_TYPE_LABELS,
            )
            for value in WORK_TYPES
        )
        assert work_type_labels == WORK_TYPE_TEXT[language], language


class _MemoryDB:
    def __init__(self, settings: dict[str, object] | None = None) -> None:
        self.settings = dict(settings or {})
        self.todo_updates: list[tuple[int, bool]] = []
        self.deleted_todos: list[int] = []

    def setting(self, key: str, default: object = None) -> object:
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: object) -> None:
        self.settings[key] = value

    def set_todo_done(self, todo_id: int, checked: bool) -> None:
        self.todo_updates.append((todo_id, checked))

    def delete_todo(self, todo_id: int) -> None:
        self.deleted_todos.append(todo_id)

    def list_archived_memories(self, _limit: int) -> list[object]:
        return []

    def restore_archived_memory(self, _archive_id: int) -> int:
        return 0

    def chat_history(self, _limit: int) -> list[object]:
        return []

    def chat_count(self) -> int:
        return 0


class _Capabilities:
    system_local_speech = True


class _PlatformServices:
    capabilities = _Capabilities()


def test_extracted_ui_constructs_minimally_offscreen() -> None:
    dialogs_module, wizard_module = _require_runtime_modules()
    exports = {
        name: _resolve_export(value)
        for name, value in _resolved_owner_classes().items()
    }
    application = QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    application.setWindowIcon(QIcon(QPixmap(1, 1)))
    widgets: list[QWidget] = []
    todo = {
        "id": 1,
        "status": "待辦",
        "title": "整理今日工作",
        "category": "其他",
    }
    memory = {
        "title": "偏好",
        "content": "使用繁體中文",
        "category": "偏好",
        "importance": 3,
        "source": "manual",
        "created_at": "2026-08-13 09:00:00",
        "updated_at": "2026-08-13 09:00:00",
    }
    try:
        dialog_db = _MemoryDB()
        constructed = (
            (exports["ClickableLabel"](), dialogs_module.ClickableLabel),
            (exports["ZoomTextBrowser"](), dialogs_module.ZoomTextBrowser),
            (
                exports["TodoRow"](dialog_db, todo, "zh-TW"),
                dialogs_module.TodoRow,
            ),
            (
                exports["IdeaEditorDialog"](
                    "標題",
                    "內容",
                    language="zh-TW",
                ),
                dialogs_module.IdeaEditorDialog,
            ),
            (
                exports["MemoryEditorDialog"](
                    memory,
                    language="zh-TW",
                ),
                dialogs_module.MemoryEditorDialog,
            ),
            (
                exports["ArchivedMemoryDialog"](
                    dialog_db,
                    language="zh-TW",
                ),
                dialogs_module.ArchivedMemoryDialog,
            ),
            (
                exports["ChatHistoryDialog"](
                    dialog_db,
                    language="zh-TW",
                ),
                dialogs_module.ChatHistoryDialog,
            ),
        )
        for widget, extracted_class in constructed:
            widgets.append(widget)
            assert isinstance(widget, QWidget)
            assert type(widget) is extracted_class

        wizard_db = _MemoryDB({"ui_language": "zh-TW"})
        wizard = exports["FirstRunWizard"](
            wizard_db,
            platform_services=_PlatformServices(),
        )
        widgets.append(wizard)
        assert isinstance(wizard, QWidget)
        assert type(wizard) is wizard_module.FirstRunWizard
        assert wizard.windowTitle() == CORE_TEXT["zh-TW"][0]
        assert wizard.form_labels["assistant_name"].text() == (
            CORE_TEXT["zh-TW"][1]
        )
        assert wizard.assistant_name.text() == DEFAULT_PROFILE["assistant_name"]
        assert wizard.user_title.text() == DEFAULT_PROFILE["user_title"]
        assert wizard.organization_name.text() == ""
        assert wizard.window_title.text() == ""
        assert wizard.work_type.currentData() == DEFAULT_PROFILE["work_type"]
        assert wizard.ui_language.currentData() == "zh-TW"
        assert wizard.wake_word.text() == DEFAULT_PROFILE["wake_word"]
        application.processEvents()
    finally:
        for widget in reversed(widgets):
            widget.close()
            widget.deleteLater()
        application.processEvents()


def run() -> None:
    test_extracted_ui_classes_have_one_true_owner()
    test_owner_modules_resolve_exact_extracted_classes()
    test_first_run_wizard_pure_defaults_and_four_language_values()
    test_extracted_ui_constructs_minimally_offscreen()
    print("EXTRACTED_UI_EQUIVALENCE_OK")


if __name__ == "__main__":
    run()
