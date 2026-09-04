from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import presentation.lingxiao_shell as lingxiao_shell
lazy from presentation.lingxiao_shell import update_draft_bar


class _Chip:
    def __init__(self) -> None:
        self.text = "舊狀態"
        self.state = "ok"

    def setText(self, value: str) -> None:
        self.text = value

    def set_state(self, value: str) -> None:
        self.state = value


class _Message:
    def __init__(self) -> None:
        self.text = "舊提示"

    def setText(self, value: str) -> None:
        self.text = value


class _FailingDB:
    def settings_snapshot(self) -> object:
        raise OSError("simulated database read failure")


def assert_draft_read_failure_is_visible() -> None:
    chip = _Chip()
    message = _Message()
    shell = SimpleNamespace(
        draft_chip=chip,
        draft_message=message,
        _settings_draft_snapshot={"mode": "工作"},
        db=_FailingDB(),
        _t=lambda _key, fallback, **values: fallback.format(**values),
    )
    result = update_draft_bar(shell)
    expected = getattr(lingxiao_shell, "DRAFT_BAR_READ_ERROR", "error")
    assert result == expected == "error"
    assert chip.text == "讀取失敗"
    assert chip.state == "bad"
    assert message.text == "設定無法讀取，請稍後再試"


def run() -> None:
    checks = (assert_draft_read_failure_is_visible,)
    failures: list[str] = []
    for check in checks:
        try:
            check()
        except Exception as error:
            failures.append(f"{check.__name__}: {type(error).__name__}: {error}")
    if failures:
        raise AssertionError("\n".join(failures))
    print("D06_DRAFT_BAR_OK")


if __name__ == "__main__":
    run()
