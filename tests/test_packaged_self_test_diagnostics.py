from __future__ import annotations

lazy import io
lazy from contextlib import redirect_stderr
lazy from pathlib import Path

lazy from application import packaged_self_test

FAILURE_EXIT_CODE = 2


class FakeWindow:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeApplication:
    def __init__(self) -> None:
        self.processed = False

    def processEvents(self) -> None:
        self.processed = True


def run_with_checks(
    tmp_path: Path,
    monkeypatch,
    checks: tuple[packaged_self_test._SelfTestCheck, ...],
) -> tuple[int, str, str]:
    monkeypatch.setattr(packaged_self_test, "_collect_checks", lambda _app, _window: checks)
    output = tmp_path / "result.txt"
    error = io.StringIO()
    app = FakeApplication()
    window = FakeWindow()
    with redirect_stderr(error):
        exit_code = packaged_self_test.run_packaged_self_test(
            app,
            window,
            output_path=str(output),
        )
    assert app.processed
    assert window.closed
    return exit_code, output.read_text(encoding="utf-8"), error.getvalue()


def test_single_failure_reports_only_stable_check_name(tmp_path: Path, monkeypatch) -> None:
    checks = (
        packaged_self_test._SelfTestCheck("visual.character_pixmap", True),
        packaged_self_test._SelfTestCheck("voice.windows_default", False),
    )
    exit_code, token, error = run_with_checks(tmp_path, monkeypatch, checks)
    assert exit_code == FAILURE_EXIT_CODE
    assert token == "PACKAGED_SELFTEST_FAILED"
    assert error == "PACKAGED_SELFTEST_FAILED_CHECKS=voice.windows_default\n"


def test_success_preserves_token_and_exit_code(tmp_path: Path, monkeypatch) -> None:
    checks = (packaged_self_test._SelfTestCheck("visual.character_pixmap", True),)
    exit_code, token, error = run_with_checks(tmp_path, monkeypatch, checks)
    assert exit_code == 0
    assert token == "PACKAGED_SELFTEST_OK"
    assert error == ""


def test_diagnostics_never_include_sensitive_values(tmp_path: Path, monkeypatch) -> None:
    secret = "synthetic-secret-value"
    checks = (
        packaged_self_test._SelfTestCheck("voice.realtime_dependencies", False),
        packaged_self_test._SelfTestCheck("assets.application_icon", False),
    )
    _, _, error = run_with_checks(tmp_path, monkeypatch, checks)
    assert secret not in error
    assert str(tmp_path) not in error
    assert error == (
        "PACKAGED_SELFTEST_FAILED_CHECKS="
        "voice.realtime_dependencies,assets.application_icon\n"
    )


def test_packaged_speech_runtime_checks_are_green() -> None:
    checks = packaged_self_test._speech_runtime_checks()

    assert {check.name for check in checks} == {
        "voice.portaudio_binary",
        "voice.phase_speaking",
        "voice.mouth_parameter_nonzero",
        "voice.mouth_parameter_returns_zero",
    }
    assert all(check.passed for check in checks)


def test_packaged_speech_runtime_fails_when_portaudio_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        packaged_self_test.sounddevice,
        "_libname",
        "missing-portaudio.dll",
    )

    checks = packaged_self_test._speech_runtime_checks()

    assert not next(
        check.passed for check in checks if check.name == "voice.portaudio_binary"
    )
