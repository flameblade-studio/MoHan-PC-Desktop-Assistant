from __future__ import annotations

lazy import json
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from db import PlatformProgressUpdate, StudioDB

UI_LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")


@dataclass(frozen=True, slots=True)
class StoredCase:
    todo_id: int
    idea_id: int
    memory_id: int
    platform_name: str
    workflow_id: int
    connector_id: str
    allowed_target_id: int
    paired_device_id: int


def user_text(language: str, field: str) -> str:
    return (
        f"{language}｜{field}｜简体剑魂不转换｜繁體墨寒不改寫｜"
        "English e\u0301 stays EXACT｜日本語かなカナ｜emoji 👩🏻‍💻🗡️"
    )


def row_with_id(rows: list, row_id: int):
    return next(row for row in rows if int(row["id"]) == row_id)


def write_case(db: StudioDB, language: str) -> StoredCase:
    db.set_setting("ui_language", language)

    todo_id = db.add_todo(user_text(language, "todo-title"), "其他")

    idea_id = db.add_idea(
        user_text(language, "idea-add-title"),
        user_text(language, "idea-add-content"),
    )
    added_idea = db.idea(idea_id)
    assert added_idea is not None
    assert added_idea["title"] == user_text(language, "idea-add-title")
    assert added_idea["content"] == user_text(language, "idea-add-content")
    db.update_idea(
        idea_id,
        user_text(language, "idea-update-title"),
        user_text(language, "idea-update-content"),
    )

    memory_id = db.add_memory(
        user_text(language, "memory-add-content"),
        "偏好",
        "manual",
        3,
        user_text(language, "memory-add-title"),
    )
    added_memory = db.memory(memory_id)
    assert added_memory is not None
    assert added_memory["title"] == user_text(language, "memory-add-title")
    assert added_memory["content"] == user_text(language, "memory-add-content")
    assert db.update_memory(
        memory_id,
        user_text(language, "memory-update-title"),
        user_text(language, "memory-update-content"),
        "偏好",
        4,
    )

    db.log_chat("user", user_text(language, "chat-content"))

    platform_name = user_text(language, "custom-platform-name")
    platform_url = f"https://example.invalid/{language}/preservation"
    assert db.add_platform(platform_name, platform_url)
    db.update_platform(
        PlatformProgressUpdate(
            platform=platform_name,
            status="進行中",
            missing=user_text(language, "platform-missing"),
            item_name=user_text(language, "platform-item-name"),
            next_action=user_text(language, "platform-next-action"),
            notes=user_text(language, "platform-notes"),
            url=platform_url,
        )
    )

    workflow_definition = json.dumps(
        {"description": user_text(language, "workflow-definition")},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    workflow_id = db.save_workflow(
        user_text(language, "workflow-name"),
        workflow_definition,
    )

    connector_id = f"preservation-{language.lower()}"
    db.save_connector(
        connector_id,
        user_text(language, "connector-display-name"),
        True,
        {"note": user_text(language, "connector-configuration")},
    )

    allowed_target_id = db.add_allowed_target(
        "folder",
        user_text(language, "allowed-target-display-name"),
        f"virtual://preservation/{language}",
        "read",
    )
    paired_device_id = db.add_paired_device(
        user_text(language, "paired-device-name"),
        f"test-only-token-hash-{language}",
        ["status"],
    )
    return StoredCase(
        todo_id=todo_id,
        idea_id=idea_id,
        memory_id=memory_id,
        platform_name=platform_name,
        workflow_id=workflow_id,
        connector_id=connector_id,
        allowed_target_id=allowed_target_id,
        paired_device_id=paired_device_id,
    )


def assert_reopened_case(db: StudioDB, language: str, stored: StoredCase) -> None:
    assert db.setting("ui_language") == language

    todo = row_with_id(db.list_todos(include_done=True), stored.todo_id)
    assert todo["title"] == user_text(language, "todo-title")
    assert todo["category"] == "其他"
    assert todo["status"] == "待辦"

    idea = db.idea(stored.idea_id)
    assert idea is not None
    assert idea["text"] == user_text(language, "idea-update-title")
    assert idea["title"] == user_text(language, "idea-update-title")
    assert idea["content"] == user_text(language, "idea-update-content")

    memory = db.memory(stored.memory_id)
    assert memory is not None
    assert memory["title"] == user_text(language, "memory-update-title")
    assert memory["content"] == user_text(language, "memory-update-content")
    assert memory["category"] == "偏好"

    chat = db.recent_chat(1)[0]
    assert chat["role"] == "user"
    assert chat["content"] == user_text(language, "chat-content")

    platform = next(
        row
        for row in db.platform_rows()
        if row["platform"] == stored.platform_name
    )
    assert platform["status"] == "進行中"
    assert platform["missing"] == user_text(language, "platform-missing")
    assert platform["item_name"] == user_text(language, "platform-item-name")
    assert platform["next_action"] == user_text(language, "platform-next-action")
    assert platform["notes"] == user_text(language, "platform-notes")
    assert platform["url"] == f"https://example.invalid/{language}/preservation"

    workflow = db.workflow(stored.workflow_id)
    assert workflow is not None
    assert workflow["name"] == user_text(language, "workflow-name")
    assert json.loads(workflow["definition"]) == {
        "description": user_text(language, "workflow-definition")
    }

    connector = db.connector(stored.connector_id)
    assert connector is not None
    assert connector["display_name"] == user_text(
        language,
        "connector-display-name",
    )
    assert json.loads(connector["configuration"]) == {
        "note": user_text(language, "connector-configuration")
    }

    allowed_target = row_with_id(db.allowed_targets(), stored.allowed_target_id)
    assert allowed_target["display_name"] == user_text(
        language,
        "allowed-target-display-name",
    )

    paired_device = row_with_id(db.paired_devices(), stored.paired_device_id)
    assert paired_device["device_name"] == user_text(
        language,
        "paired-device-name",
    )


def test_studio_db_preserves_user_content() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        for language in UI_LANGUAGES:
            database_path = root / f"user-content-{language}.db"
            database = StudioDB(database_path)
            try:
                stored = write_case(database, language)
            finally:
                database.close()

            reopened_database = StudioDB(database_path)
            try:
                assert_reopened_case(reopened_database, language, stored)
            finally:
                reopened_database.close()


def main() -> None:
    test_studio_db_preserves_user_content()
    print("USER_CONTENT_PRESERVATION_OK")


if __name__ == "__main__":
    main()
