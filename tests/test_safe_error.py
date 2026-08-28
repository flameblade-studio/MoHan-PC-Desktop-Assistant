from __future__ import annotations

lazy import io
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.safe_error import (
    SafeDiagnostic,
    SafeErrorType,
    sanitize_error,
)

HTTP_BAD_GATEWAY = 502
HTTP_TOO_MANY_REQUESTS = 429
HTTP_GATEWAY_TIMEOUT = 504
HTTP_SERVICE_UNAVAILABLE = 503


@dataclass(frozen=True)
class _Response:
    status_code: int


class _ResponseError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.response = _Response(status_code)


class _BrokenStatusError(Exception):
    @property
    def status(self) -> int:
        raise RuntimeError("property contains a secret")

    def __str__(self) -> str:
        raise RuntimeError("string conversion contains a secret")


class _IntSubclass(int):
    pass


def _bait_details() -> tuple[str, ...]:
    marker = "NOT" + "-A-REAL-SECRET-42"
    return (
        "api" + f"_key={marker}",
        "tok" + f"en={marker}",
        "pass" + f"word={marker}",
        "Author" + "ization: " + "Bearer " + marker,
        "Coo" + "kie: session=" + marker,
        "Server=db.example.test;User Id=user;Pass" + "word=" + marker,
        "maintainer" + "@example.test",
        "C:" + "\\Users\\private-user\\AppData\\secret.txt",
        "/home/" + "private-user/.config/secret.json",
        "/Users/" + "private-user/Library/secret.json",
        "\\\\server\\Users\\private-user\\secret.txt",
        "密" + "碼＝" + marker,
        "トー" + "クン＝" + marker,
        "🔐 " + marker,
    )


def _surfaces(error) -> str:
    return "\n".join((str(error), repr(error)))


def _assert_bait_secrets_are_discarded() -> None:
    baits = _bait_details()
    combined = " | ".join(baits)
    errors = (
        RuntimeError(combined),
        _ResponseError(combined, 503),
        HTTPError(
            "https://example.test/private",
            401,
            combined,
            None,
            io.BytesIO(combined.encode("utf-8")),
        ),
        _BrokenStatusError(combined),
        combined,
    )

    for error in errors:
        surface = _surfaces(sanitize_error(error))
        for bait in baits:
            assert bait not in surface
        for private_fragment in (
            "NOT-A-REAL-SECRET",
            "private-user",
            "example.test",
            "Bearer",
            "session=",
        ):
            assert private_fragment not in surface


def _assert_http_status_is_preserved_safely() -> None:
    cases = {
        401: SafeDiagnostic.AUTHENTICATION_REQUIRED,
        403: SafeDiagnostic.ACCESS_DENIED,
        404: SafeDiagnostic.RESOURCE_NOT_FOUND,
        408: SafeDiagnostic.REQUEST_TIMEOUT,
        409: SafeDiagnostic.CONFLICT,
        429: SafeDiagnostic.RATE_LIMITED,
        503: SafeDiagnostic.REMOTE_SERVICE_FAILURE,
    }
    for status, diagnostic in cases.items():
        safe = sanitize_error(RuntimeError("opaque"), http_status=status)
        assert safe.error_type is SafeErrorType.HTTP_ERROR
        assert safe.diagnostic is diagnostic
        assert safe.http_status == status
        assert str(status) in str(safe)

    response_error = sanitize_error(_ResponseError("opaque", 502))
    assert response_error.http_status == HTTP_BAD_GATEWAY
    assert response_error.diagnostic is SafeDiagnostic.REMOTE_SERVICE_FAILURE

    parsed = sanitize_error("HTTP/1.1 429 followed by untrusted Unicode 🔐")
    assert parsed.http_status == HTTP_TOO_MANY_REQUESTS
    assert parsed.diagnostic is SafeDiagnostic.RATE_LIMITED

    exception_text = sanitize_error(RuntimeError("HTTP 504", *_bait_details()))
    assert exception_text.http_status == HTTP_GATEWAY_TIMEOUT
    assert exception_text.diagnostic is SafeDiagnostic.REQUEST_TIMEOUT
    assert "NOT-A-REAL-SECRET" not in _surfaces(exception_text)

    explicit_wins = sanitize_error("HTTP 401", http_status=503)
    assert explicit_wins.http_status == HTTP_SERVICE_UNAVAILABLE
    assert explicit_wins.diagnostic is SafeDiagnostic.REMOTE_SERVICE_FAILURE


def _assert_invalid_status_is_not_exposed() -> None:
    for invalid in (True, 0, 99, 600, 9_999, _IntSubclass(503)):
        safe = sanitize_error(RuntimeError("opaque"), http_status=invalid)
        assert safe.http_status is None
        assert "http_status=" not in str(safe)


def _assert_approved_error_types() -> None:
    decoding_error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid")
    cases = (
        (
            TimeoutError("opaque"),
            SafeErrorType.TIMEOUT_ERROR,
            SafeDiagnostic.REQUEST_TIMEOUT,
        ),
        (
            ConnectionError("opaque"),
            SafeErrorType.CONNECTION_ERROR,
            SafeDiagnostic.NETWORK_UNAVAILABLE,
        ),
        (
            URLError("opaque"),
            SafeErrorType.CONNECTION_ERROR,
            SafeDiagnostic.NETWORK_UNAVAILABLE,
        ),
        (
            PermissionError("opaque"),
            SafeErrorType.AUTHORIZATION_ERROR,
            SafeDiagnostic.ACCESS_DENIED,
        ),
        (
            FileNotFoundError("opaque"),
            SafeErrorType.NOT_FOUND_ERROR,
            SafeDiagnostic.RESOURCE_NOT_FOUND,
        ),
        (
            decoding_error,
            SafeErrorType.DECODING_ERROR,
            SafeDiagnostic.INVALID_RESPONSE,
        ),
        (
            ValueError("opaque"),
            SafeErrorType.VALIDATION_ERROR,
            SafeDiagnostic.INVALID_INPUT,
        ),
        (
            OSError("opaque"),
            SafeErrorType.OPERATING_SYSTEM_ERROR,
            SafeDiagnostic.LOCAL_IO_FAILURE,
        ),
        (
            RuntimeError("opaque"),
            SafeErrorType.RUNTIME_ERROR,
            SafeDiagnostic.INTERNAL_FAILURE,
        ),
        (
            Exception("opaque"),
            SafeErrorType.UNKNOWN_ERROR,
            SafeDiagnostic.UNKNOWN_FAILURE,
        ),
    )
    for error, error_type, diagnostic in cases:
        safe = sanitize_error(error)
        assert safe.error_type is error_type
        assert safe.diagnostic is diagnostic
        assert safe.http_status is None


def _assert_limited_text_diagnostics() -> None:
    cases = {
        "rate limit reached": SafeDiagnostic.RATE_LIMITED,
        "authentication failed": SafeDiagnostic.AUTHENTICATION_REQUIRED,
        "access denied": SafeDiagnostic.ACCESS_DENIED,
        "operation timed out": SafeDiagnostic.REQUEST_TIMEOUT,
        "network unreachable": SafeDiagnostic.NETWORK_UNAVAILABLE,
        "resource not found": SafeDiagnostic.RESOURCE_NOT_FOUND,
        "operation cancelled": SafeDiagnostic.OPERATION_CANCELLED,
    }
    for raw, diagnostic in cases.items():
        safe = sanitize_error(raw + " — 機密詳細資料 🔐")
        assert safe.diagnostic is diagnostic
        assert raw not in _surfaces(safe)
        assert "機密詳細資料" not in _surfaces(safe)


def _assert_unicode_is_opaque() -> None:
    raw = "認証失敗：密碼不可公開；路徑不可公開。🔐\n第二行"
    safe = sanitize_error(RuntimeError(raw))
    assert safe.error_type is SafeErrorType.RUNTIME_ERROR
    assert safe.diagnostic is SafeDiagnostic.INTERNAL_FAILURE
    surface = _surfaces(safe)
    assert raw not in surface
    assert "認証" not in surface
    assert "密碼" not in surface
    assert "🔐" not in surface
    assert str(safe) == "type=runtime_error; diagnostic=internal_failure"


def run() -> None:
    _assert_bait_secrets_are_discarded()
    _assert_http_status_is_preserved_safely()
    _assert_invalid_status_is_not_exposed()
    _assert_approved_error_types()
    _assert_limited_text_diagnostics()
    _assert_unicode_is_opaque()
    print("SAFE_ERROR_OK")


if __name__ == "__main__":
    run()
