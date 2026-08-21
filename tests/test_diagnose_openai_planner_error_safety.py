from __future__ import annotations

lazy import io
lazy import json
lazy import sys
lazy from contextlib import redirect_stdout
lazy from email.message import Message
lazy from pathlib import Path
lazy from unittest.mock import patch
lazy from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools import diagnose_openai_planner as diagnostic

EXIT_CODE_HTTP_ERROR = 3
EXIT_CODE_OS_ERROR = 4
EXIT_CODE_PLANNER_FAILED = 5

_FAKE_TOKEN = "NOT-A-REAL-TOKEN-DIAGNOSTIC-BOUNDARY"
_PRIVATE_PATH = "C:" + "\\Users\\private-user\\AppData\\MoHan\\secret.json"
_RESPONSE_BODY = json.dumps(
    {
        "error": "raw provider failure",
        "token": _FAKE_TOKEN,
        "private_path": _PRIVATE_PATH,
    }
)
_UNTRUSTED_DETAIL = (
    f"response_body={_RESPONSE_BODY}; token={_FAKE_TOKEN}; path={_PRIVATE_PATH}"
)
_FORBIDDEN = (
    _FAKE_TOKEN,
    _PRIVATE_PATH,
    _RESPONSE_BODY,
    "private-user",
    "raw provider failure",
    "response_body=",
)


class _SecretStore:
    def __init__(self, _path: Path) -> None:
        pass

    def load(self) -> str:
        return _FAKE_TOKEN


class _Cursor:
    @staticmethod
    def fetchone() -> tuple[str]:
        return (json.dumps("gpt-safe-model"),)


class _Connection:
    @staticmethod
    def execute(_query: str) -> _Cursor:
        return _Cursor()

    @staticmethod
    def close() -> None:
        pass


class _Signal:
    def __init__(self) -> None:
        self._callback = None

    def connect(self, callback) -> None:
        self._callback = callback

    def emit(self, value: object) -> None:
        assert self._callback is not None
        self._callback(value)


class _Signals:
    def __init__(self) -> None:
        self.done = _Signal()
        self.failed = _Signal()


class _FailedPlanner:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.signals = _Signals()

    def run(self) -> None:
        self.signals.failed.emit(_UNTRUSTED_DETAIL)


class _UnreadableBody(io.BytesIO):
    def read(self, *_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("HTTP response body must not be read")


def _http_error() -> HTTPError:
    return HTTPError(
        "https://api.openai.com/private?token=" + _FAKE_TOKEN,
        503,
        _UNTRUSTED_DETAIL,
        Message(),
        _UnreadableBody(_RESPONSE_BODY.encode("utf-8")),
    )


def _raise(error: BaseException):
    def raiser(*_args: object, **_kwargs: object) -> object:
        raise error

    return raiser


def _run(urlopen_replacement, *, planner=_FailedPlanner) -> tuple[int, str]:
    output = io.StringIO()
    with (
        patch.object(diagnostic, "SecretStore", _SecretStore),
        patch("sqlite3.connect", return_value=_Connection()),
        patch.object(diagnostic, "urlopen", urlopen_replacement),
        patch.object(diagnostic, "ActionPlannerWorker", planner),
        redirect_stdout(output),
    ):
        result = diagnostic.main(_PRIVATE_PATH)
    return result, output.getvalue()


def _assert_private_details_absent(output: str) -> None:
    lowered = output.casefold()
    for forbidden in _FORBIDDEN:
        assert forbidden.casefold() not in lowered, forbidden


def test_http_error_exposes_only_finite_metadata() -> None:
    error = _http_error()
    result, output = _run(_raise(error))

    assert result == EXIT_CODE_HTTP_ERROR
    assert "MODEL_CHECK=failed" in output
    assert "type=http_error" in output
    assert "diagnostic=remote_service_failure" in output
    assert "http_status=503" in output
    assert error.__cause__ is None
    assert error.__context__ is None
    _assert_private_details_absent(output)


def test_raw_exception_and_planner_failure_are_sanitized() -> None:
    error = OSError(_UNTRUSTED_DETAIL)
    result, output = _run(_raise(error))

    assert result == EXIT_CODE_OS_ERROR
    assert "type=operating_system_error" in output
    assert "diagnostic=local_io_failure" in output
    assert error.__cause__ is None
    assert error.__context__ is None
    _assert_private_details_absent(output)

    response = io.BytesIO(b'{"id":"gpt-safe-model"}')
    result, output = _run(lambda *_args, **_kwargs: response)

    assert result == EXIT_CODE_PLANNER_FAILED
    assert "PLANNER=failed" in output
    assert "type=unknown_error" in output
    assert "diagnostic=unknown_failure" in output
    _assert_private_details_absent(output)


def main() -> None:
    test_http_error_exposes_only_finite_metadata()
    test_raw_exception_and_planner_failure_are_sanitized()
    print("DIAGNOSE_OPENAI_PLANNER_ERROR_SAFETY_OK")


if __name__ == "__main__":
    main()
