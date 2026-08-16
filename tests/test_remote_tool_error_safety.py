from __future__ import annotations

lazy import json
lazy import sys
lazy from dataclasses import asdict
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch
lazy from urllib.error import HTTPError
lazy from urllib.parse import urlencode
lazy from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application import flagship_action_runtime
lazy from application.flagship_action_runtime import ActionExecutor
lazy from domain.flagship_action_models import ActionPlan, ActionRequest
lazy from domain.flagship_action_policy import PolicyEngine
lazy from infrastructure.db import StudioDB
lazy from integrations.remote_control import (
    REMOTE_FILE_UNAVAILABLE,
    REMOTE_FILE_UNAVAILABLE_MESSAGES,
    RemoteControlServer,
    RemoteRequestHandler,
    RemoteServerConfig,
    RemoteServerServices,
    TokenRegistry,
    remote_file_unavailable,
)
lazy from safe_error import sanitize_error as canonical_sanitize_error

_BAIT_MARKER = "NOT" + "-A-REAL-SECRET-42"
_PRIVATE_PATH = "C:" + "\\Users\\private-user\\AppData\\secret.txt"
_FORBIDDEN = (_BAIT_MARKER, _PRIVATE_PATH, "private-user", "api_key=")


class _UnavailableRemoteFile:
    name = "unavailable.txt"
    suffix = ".txt"

    def open(self, _mode: str) -> None:
        try:
            raise OSError(_PRIVATE_PATH)
        except OSError as source:
            raise PermissionError("api_key=" + _BAIT_MARKER) from source


def _authorized_request(url: str, token: str) -> Request:
    return Request(url, headers={"Authorization": f"Bearer {token}"})


def _read_fixed_file_error(request: Request) -> dict[str, str]:
    try:
        urlopen(request, timeout=3)
    except HTTPError as exc:
        assert exc.code == 403
        payload = json.load(exc)
    else:
        raise AssertionError("unavailable remote files must fail closed")
    assert payload == {"error": REMOTE_FILE_UNAVAILABLE}
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in _FORBIDDEN:
        assert forbidden.casefold() not in serialized.casefold()
    return payload


def _assert_remote_file_boundary(root: Path) -> None:
    database = StudioDB(root / "remote-safety.db")
    shared_file = root / "shared.txt"
    shared_content = b"safe remote content"
    shared_file.write_bytes(shared_content)
    registry = TokenRegistry(database)
    token = registry.pair("安全測試裝置", ["files"])
    server = RemoteControlServer(
        RemoteServerConfig(
            host="127.0.0.1",
            port=0,
            enabled=True,
            allow_commands=False,
            allow_files=True,
        ),
        registry,
        RemoteServerServices(
            status_provider=lambda: {"ok": True},
            command_handler=lambda _text, _device: {"accepted": False},
            allowed_folders=(str(root),),
        ),
    )
    server.start()
    try:
        port = server._server.server_port
        endpoint = f"http://127.0.0.1:{port}/api/v1/file"
        query = urlencode({"path": str(shared_file)})
        with urlopen(
            _authorized_request(f"{endpoint}?{query}", token),
            timeout=3,
        ) as response:
            assert response.status == 200
            assert response.read() == shared_content
            disposition = response.headers["Content-Disposition"]
        assert shared_file.name not in disposition
        assert "mohan-" in disposition

        outside_path = root.parent / "private-user" / "secret.txt"
        outside_query = urlencode({"path": str(outside_path)})
        _read_fixed_file_error(
            _authorized_request(f"{endpoint}?{outside_query}", token)
        )

        original_json = RemoteRequestHandler._json

        def checked_json(
            handler: RemoteRequestHandler,
            status: int,
            payload: dict[str, object],
        ) -> None:
            if payload == {"error": REMOTE_FILE_UNAVAILABLE}:
                assert sys.exception() is None
            original_json(handler, status, payload)

        with (
            patch.object(
                server,
                "_allowed_file",
                return_value=_UnavailableRemoteFile(),
            ),
            patch.object(RemoteRequestHandler, "_json", checked_json),
        ):
            _read_fixed_file_error(
                _authorized_request(f"{endpoint}?{query}", token)
            )
    finally:
        server.stop()
        database.close()


def _assert_tool_error_boundary() -> None:
    audit: list[tuple[str, dict[str, object]]] = []
    executor = ActionExecutor(
        PolicyEngine({"read_status": "允許"}),
        audit=lambda event, payload: audit.append((event, payload)),
    )

    def failing_handler(_request: ActionRequest):
        try:
            raise OSError(_PRIVATE_PATH)
        except OSError as source:
            raise RuntimeError("api_key=" + _BAIT_MARKER) from source

    def checked_sanitizer(error: BaseException):
        assert sys.exception() is None
        assert error.__cause__ is not None
        assert error.__context__ is not None
        return canonical_sanitize_error(error)

    executor.register("read_status", failing_handler)
    request = ActionRequest("read_status", "讀取安全測試狀態")
    with patch.object(
        flagship_action_runtime,
        "sanitize_error",
        side_effect=checked_sanitizer,
    ):
        result, = executor.execute(ActionPlan("安全錯誤測試", [request]))

    assert not result.success
    assert "type=runtime_error" in result.message
    assert "diagnostic=internal_failure" in result.message
    surface = json.dumps(
        {"result": asdict(result), "audit": audit},
        ensure_ascii=False,
        default=str,
    )
    for forbidden in _FORBIDDEN:
        assert forbidden.casefold() not in surface.casefold()
    assert any(event == "action_result" for event, _payload in audit)


def run() -> None:
    assert tuple(REMOTE_FILE_UNAVAILABLE_MESSAGES) == (
        "zh-TW",
        "zh-CN",
        "en-US",
        "ja-JP",
    )
    assert remote_file_unavailable("zh-TW") == "檔案目前無法提供"
    assert remote_file_unavailable("zh-CN") == "文件目前无法提供"
    assert remote_file_unavailable("en") == "The file is currently unavailable."
    assert remote_file_unavailable("ja-JP") == "現在このファイルを提供できません。"
    with TemporaryDirectory(dir=Path.cwd()) as temporary:
        _assert_remote_file_boundary(Path(temporary).resolve())
    _assert_tool_error_boundary()
    print("REMOTE_TOOL_ERROR_SAFETY_OK")


if __name__ == "__main__":
    run()
