from __future__ import annotations

lazy import hashlib
lazy import io
lazy import os
lazy import sys
lazy import tempfile
lazy import traceback
lazy from collections.abc import Callable
lazy from email.message import Message
lazy from pathlib import Path
lazy from typing import Self
lazy from unittest.mock import patch
lazy from urllib.error import HTTPError
lazy from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools import sync_wordpress_download_page as wordpress_sync
lazy from updater import InstallerAsset, UpdateError, UpdateManager

_FAKE_TOKEN = "NOT-A-REAL-TOKEN-EXTERNAL-BOUNDARY"
_PRIVATE_PATH = "C:" + "\\Users\\private-user\\AppData\\MoHan\\secret.json"
_RESPONSE_BODY = (
    '{"token":"'
    + _FAKE_TOKEN
    + '","private_path":"'
    + _PRIVATE_PATH.replace("\\", "\\\\")
    + '"} trailing-data'
)
_API_URL = "https://api.github.com/repos/example/project/releases"
_INSTALLER_URL = "https://github.com/example/project/releases/download/v1/app.exe"
_FORBIDDEN = (
    _FAKE_TOKEN,
    _PRIVATE_PATH,
    _RESPONSE_BODY,
    "private-user",
    "response_body=",
)


def _untrusted_detail() -> str:
    return (
        "response_body="
        + _RESPONSE_BODY
        + "; token="
        + _FAKE_TOKEN
        + "; path="
        + _PRIVATE_PATH
    )


def _http_error() -> HTTPError:
    detail = _untrusted_detail()
    return HTTPError(
        _API_URL + "?token=" + _FAKE_TOKEN,
        503,
        detail,
        Message(),
        io.BytesIO(detail.encode("utf-8")),
    )


def _assert_safe_error(
    action: Callable[[], object],
    error_type: type[BaseException],
    expected_message: str,
) -> None:
    try:
        action()
    except error_type as error:
        assert str(error) == expected_message
        assert error.__cause__ is None
        assert error.__context__ is None
        rendered = "\n".join(
            (
                str(error),
                repr(error),
                "".join(traceback.format_exception(error)),
            )
        )
        lowered = rendered.casefold()
        for forbidden in _FORBIDDEN:
            assert forbidden.casefold() not in lowered, forbidden
        return
    raise AssertionError(f"expected {error_type.__name__}")


class _Response:
    def __init__(self, url: str, payload: bytes):
        self._url = url
        self._payload = payload
        self._offset = 0
        self.headers = Message()
        self.headers["Content-Length"] = str(len(payload))

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def geturl(self) -> str:
        return self._url

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._payload) - self._offset
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


class _UnreadableManifest:
    def read_text(self, *, encoding: str) -> str:
        assert encoding == "utf-8"
        raise OSError(_untrusted_detail())


def _raise_http_error(_request: object, **_kwargs: object) -> object:
    raise _http_error()


def _raise_os_error(_request: object, **_kwargs: object) -> object:
    raise OSError(_untrusted_detail())


def _response_opener(payload: bytes) -> Callable[..., _Response]:
    def opener(request: Request, **_kwargs: object) -> _Response:
        return _Response(request.full_url, payload)

    return opener


def _raise_progress_error(_received: int, _total: int) -> None:
    raise RuntimeError(_untrusted_detail())


def _wordpress_environment() -> dict[str, str]:
    return {
        "WORDPRESS_BASE_URL": "https://wordpress.example.test",
        "WORDPRESS_USERNAME": _FAKE_TOKEN,
        "WORDPRESS_APP_PASSWORD": _PRIVATE_PATH,
    }


def test_wordpress_external_errors_are_sanitized() -> None:
    endpoint = "https://wordpress.example.test/wp-json/wp/v2/pages"
    with (
        patch.dict(os.environ, _wordpress_environment(), clear=True),
        patch.object(wordpress_sync, "urlopen", side_effect=_http_error()),
    ):
        _assert_safe_error(
            lambda: wordpress_sync.request_json(endpoint),
            RuntimeError,
            "WordPress API request was rejected",
        )

    with (
        patch.dict(os.environ, _wordpress_environment(), clear=True),
        patch.object(
            wordpress_sync,
            "urlopen",
            side_effect=OSError(_untrusted_detail()),
        ),
    ):
        _assert_safe_error(
            lambda: wordpress_sync.request_json(endpoint),
            RuntimeError,
            "WordPress API is unavailable",
        )

    with (
        patch.dict(os.environ, _wordpress_environment(), clear=True),
        patch.object(
            wordpress_sync,
            "urlopen",
            return_value=_Response(endpoint, _RESPONSE_BODY.encode("utf-8")),
        ),
    ):
        _assert_safe_error(
            lambda: wordpress_sync.request_json(endpoint),
            RuntimeError,
            "WordPress API returned invalid JSON",
        )

    _assert_safe_error(
        lambda: wordpress_sync.load_manifest(_UnreadableManifest()),
        RuntimeError,
        "Release manifest could not be loaded",
    )


def _manager(
    download_dir: Path,
    opener: Callable[..., object],
) -> UpdateManager:
    return UpdateManager(
        "example/project",
        "1.0.0",
        download_dir,
        opener,
    )


def _asset(payload: bytes) -> InstallerAsset:
    return InstallerAsset(
        "exe",
        "app.exe",
        _INSTALLER_URL,
        hashlib.sha256(payload).hexdigest(),
        len(payload),
    )


def test_updater_external_errors_are_sanitized() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        manager = _manager(root, _raise_http_error)
        _assert_safe_error(
            lambda: manager._request_bytes(_API_URL, 1024),
            UpdateError,
            "GitHub 更新服務回應錯誤。",
        )

        manager = _manager(root, _raise_os_error)
        _assert_safe_error(
            lambda: manager._request_bytes(_API_URL, 1024),
            UpdateError,
            "無法連線至 GitHub 更新服務。",
        )

        manager = _manager(
            root,
            _response_opener(_RESPONSE_BODY.encode("utf-8")),
        )
        _assert_safe_error(
            lambda: manager._request_json(_API_URL),
            UpdateError,
            "GitHub 更新資料格式不正確。",
        )

        malformed_url = "https://[" + _FAKE_TOKEN + "/" + _PRIVATE_PATH
        _assert_safe_error(
            lambda: UpdateManager._validate_url(malformed_url),
            UpdateError,
            "更新網址不是受信任的 GitHub HTTPS 來源。",
        )

        payload = b"verified-installer"
        manager = _manager(root, _response_opener(payload))
        _assert_safe_error(
            lambda: manager.download(_asset(payload), _raise_progress_error),
            UpdateError,
            "安裝程式下載失敗。",
        )

        blocked = root / ("private-user-" + _FAKE_TOKEN)
        blocked.write_text(_RESPONSE_BODY, encoding="utf-8")
        manager = _manager(blocked, _response_opener(payload))
        _assert_safe_error(
            lambda: manager.download(_asset(payload)),
            UpdateError,
            "安裝程式下載失敗。",
        )


def main() -> None:
    test_wordpress_external_errors_are_sanitized()
    test_updater_external_errors_are_sanitized()
    print("EXTERNAL_ERROR_BOUNDARIES_OK")


if __name__ == "__main__":
    main()
