from __future__ import annotations

lazy import json
lazy import sys
lazy from datetime import datetime
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import application.workflow_engine as workflow_engine
lazy import domain.outfit_pack_makeup as makeup_module
lazy import domain.version_info as version_info
lazy from application.workflow_engine import Workflow, schedule_due
lazy from domain.outfit_pack_makeup import (
    read_makeup_intensity,
    write_makeup_intensity,
)

VALID_INTENSITY = 0.35


def assert_makeup_bad_value_preserves_last_valid_and_notifies_once() -> None:
    with TemporaryDirectory() as temporary:
        store = Path(temporary)
        write_makeup_intensity(store, VALID_INTENSITY)
        assert read_makeup_intensity(store) == VALID_INTENSITY
        (store / "makeup.json").write_text(
            json.dumps({"intensity": "not-a-number"}),
            encoding="utf-8",
        )
        notices: list[str] = []
        assert read_makeup_intensity(store, notify=notices.append) == VALID_INTENSITY
        assert read_makeup_intensity(store, notify=notices.append) == VALID_INTENSITY
        assert notices == ["妝容設定無法讀取，已保留上一個有效值。"]


def assert_bad_schedule_value_notifies() -> None:
    notices: list[str] = []
    workflow = Workflow(
        None,
        "壞排程",
        True,
        {"type": "schedule", "time": "99:99"},
        [],
    )
    assert not schedule_due(
        workflow,
        datetime(2026, 9, 4, 9, 0),
        None,
        notify=notices.append,
    )
    assert notices == ["排程設定無法讀取"]


def assert_bad_version_value_is_unknown() -> None:
    with TemporaryDirectory() as temporary:
        path = Path(temporary) / "build-info.json"
        path.write_text("{broken-json", encoding="utf-8")
        original = version_info._build_info_path
        version_info._build_info_path = lambda: path
        try:
            assert version_info.build_info()["version"] == "未知版本"
        finally:
            version_info._build_info_path = original


def run() -> None:
    # Keep the module references explicit: these are the exact public paths
    # whose swallowed-error behavior is being audited.
    assert workflow_engine.schedule_due is schedule_due
    assert makeup_module.read_makeup_intensity is read_makeup_intensity
    checks = (
        assert_makeup_bad_value_preserves_last_valid_and_notifies_once,
        assert_bad_schedule_value_notifies,
        assert_bad_version_value_is_unknown,
    )
    failures: list[str] = []
    for check in checks:
        try:
            check()
        except Exception as error:
            failures.append(f"{check.__name__}: {type(error).__name__}: {error}")
    if failures:
        raise AssertionError("\n".join(failures))
    print("D04_SETTINGS_OK")


if __name__ == "__main__":
    run()
