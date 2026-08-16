from __future__ import annotations

lazy import io
lazy import json
lazy import sys
lazy import traceback
lazy from pathlib import Path
lazy from typing import Self
lazy from unittest.mock import patch
lazy from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from integrations.cloud_connectors import (
    PROVIDERS,
    GoogleDriveConnector,
    JsonApiClient,
    OAuthError,
    OAuthPKCEFlow,
    _authorization_code,
    refresh_oauth_token,
)
lazy from integrations.home_assistant import (
    HomeAssistantClient,
    HomeAssistantConfig,
    HomeAssistantError,
)


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _size: int = -1) -> bytes:
        return self.payload


def _sensitive_values() -> tuple[str, ...]:
    marker = "SENSITIVE" + "-VALUE-42"
    return (
        marker,
        "api" + f"_key={marker}",
        "tok" + f"en={marker}",
        "pass" + f"word={marker}",
        "Coo" + f"kie=session-{marker}",
        "owner" + "@example.invalid",
        "C:" + "\\Users\\private-user\\AppData\\secret.json",
        "/home/" + "private-user/.config/secret.json",
    )


def _external_body() -> bytes:
    return json.dumps({
        "error": "provider rejected request",
        "detail": " | ".join(_sensitive_values()),
    }).encode("utf-8")


def _http_error(status: int) -> HTTPError:
    marker = _sensitive_values()[0]
    return HTTPError(
        "https://provider.invalid/private?tok" + f"en={marker}",
        status,
        "Bearer " + marker,
        None,
        io.BytesIO(_external_body()),
    )


def _error_surface(error: BaseException) -> str:
    return "\n".join((
        str(error),
        repr(error),
        "".join(traceback.format_exception_only(type(error), error)),
    ))


def _assert_sanitized(
    action,
    error_type: type[Exception],
    *,
    expected: tuple[str, ...],
) -> None:
    try:
        action()
    except error_type as exc:
        surface = _error_surface(exc)
        assert exc.__cause__ is None
        assert exc.__context__ is None
    else:
        raise AssertionError(f"{error_type.__name__} was not raised")

    for fragment in expected:
        assert fragment in surface
    for sensitive in _sensitive_values():
        assert sensitive not in surface
    for forbidden in (
        "provider.invalid",
        "private-user",
        "Bearer",
        "session-",
        "response body",
    ):
        assert forbidden not in surface


def _assert_oauth_callback_is_sanitized() -> None:
    detail = " ".join(_sensitive_values())
    _assert_sanitized(
        lambda: _authorization_code(
            {
                "state": "expected",
                "error": "access_denied",
                "error_description": detail,
            },
            "expected",
        ),
        OAuthError,
        expected=("type=unknown_error", "diagnostic=unknown_failure"),
    )


def _assert_oauth_exchange_is_sanitized() -> None:
    flow = OAuthPKCEFlow(PROVIDERS["google"], "public-client")
    with patch("integrations.cloud_connectors.urlopen", side_effect=_http_error(401)):
        _assert_sanitized(
            lambda: flow._exchange(
                "authorization-code",
                "pkce-verifier",
                "http://127.0.0.1/callback",
            ),
            OAuthError,
            expected=(
                "type=http_error",
                "diagnostic=authentication_required",
                "http_status=401",
            ),
        )


def _assert_oauth_refresh_is_sanitized() -> None:
    with patch("integrations.cloud_connectors.urlopen", side_effect=_http_error(429)):
        _assert_sanitized(
            lambda: refresh_oauth_token(
                PROVIDERS["google"],
                {
                    "refresh_token": "opaque-refresh-value",
                    "client_id": "public-client",
                },
            ),
            OAuthError,
            expected=(
                "type=http_error",
                "diagnostic=rate_limited",
                "http_status=429",
            ),
        )


def _assert_json_api_errors_are_sanitized() -> None:
    client = JsonApiClient("opaque-access-value", "https://api.example.invalid")
    with patch("integrations.cloud_connectors.urlopen", side_effect=_http_error(503)):
        _assert_sanitized(
            lambda: client.request("GET", "/private"),
            OAuthError,
            expected=(
                "type=http_error",
                "diagnostic=remote_service_failure",
                "http_status=503",
            ),
        )

    with patch(
        "integrations.cloud_connectors.urlopen",
        return_value=_Response(_external_body() + b" invalid-json"),
    ):
        _assert_sanitized(
            lambda: client.request("GET", "/malformed"),
            OAuthError,
            expected=("type=decoding_error", "diagnostic=invalid_response"),
        )

    connection_detail = " | ".join(_sensitive_values())
    with patch(
        "integrations.cloud_connectors.urlopen",
        side_effect=URLError(connection_detail),
    ):
        _assert_sanitized(
            lambda: client.request_bytes(
                "POST",
                "/bytes",
                b"content",
                "application/octet-stream",
            ),
            OAuthError,
            expected=(
                "type=connection_error",
                "diagnostic=network_unavailable",
            ),
        )


def _assert_drive_upload_error_is_sanitized() -> None:
    connector = GoogleDriveConnector("opaque-access-value")
    with patch("integrations.cloud_connectors.urlopen", side_effect=_http_error(403)):
        _assert_sanitized(
            lambda: connector.upload_small("safe.txt", b"content"),
            OAuthError,
            expected=(
                "type=http_error",
                "diagnostic=access_denied",
                "http_status=403",
            ),
        )


def _assert_home_assistant_errors_are_sanitized() -> None:
    client = HomeAssistantClient(
        HomeAssistantConfig(
            "https://home-assistant.example.invalid",
            "opaque-home-token",
        )
    )
    with patch("integrations.home_assistant.urlopen", side_effect=_http_error(404)):
        _assert_sanitized(
            lambda: client._request("GET", "/api/states/private"),
            HomeAssistantError,
            expected=(
                "type=http_error",
                "diagnostic=resource_not_found",
                "http_status=404",
            ),
        )

    with patch(
        "integrations.home_assistant.urlopen",
        side_effect=URLError(" | ".join(_sensitive_values())),
    ):
        _assert_sanitized(
            lambda: client._request("GET", "/api/"),
            HomeAssistantError,
            expected=(
                "type=connection_error",
                "diagnostic=network_unavailable",
            ),
        )

    with patch(
        "integrations.home_assistant.urlopen",
        return_value=_Response(_external_body() + b" malformed"),
    ):
        _assert_sanitized(
            lambda: client._request("GET", "/api/"),
            HomeAssistantError,
            expected=("type=decoding_error", "diagnostic=invalid_response"),
        )


def _assert_success_paths_are_unchanged() -> None:
    api = JsonApiClient("opaque-access-value", "https://api.example.invalid")
    with patch(
        "integrations.cloud_connectors.urlopen",
        return_value=_Response(b'{"ok": true}'),
    ):
        assert api.request("GET", "/health") == {"ok": True}

    home = HomeAssistantClient(
        HomeAssistantConfig(
            "https://home-assistant.example.invalid",
            "opaque-home-token",
        )
    )
    with patch(
        "integrations.home_assistant.urlopen",
        return_value=_Response(b'{"message": "API running."}'),
    ):
        assert home.health() is True


def run() -> None:
    _assert_oauth_callback_is_sanitized()
    _assert_oauth_exchange_is_sanitized()
    _assert_oauth_refresh_is_sanitized()
    _assert_json_api_errors_are_sanitized()
    _assert_drive_upload_error_is_sanitized()
    _assert_home_assistant_errors_are_sanitized()
    _assert_success_paths_are_unchanged()
    print("CLOUD_ERROR_SANITIZATION_OK")


if __name__ == "__main__":
    run()
