from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain import safe_error_localization as localization
lazy from domain.safe_error import SafeDiagnostic, SafeError, SafeErrorType
lazy from domain.safe_error_localization import safe_error_message

SUPPORTED_LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")

ERROR_DIAGNOSTICS = {
    SafeErrorType.HTTP_ERROR: SafeDiagnostic.UNEXPECTED_RESPONSE,
    SafeErrorType.TIMEOUT_ERROR: SafeDiagnostic.REQUEST_TIMEOUT,
    SafeErrorType.CONNECTION_ERROR: SafeDiagnostic.NETWORK_UNAVAILABLE,
    SafeErrorType.AUTHENTICATION_ERROR: SafeDiagnostic.AUTHENTICATION_REQUIRED,
    SafeErrorType.AUTHORIZATION_ERROR: SafeDiagnostic.ACCESS_DENIED,
    SafeErrorType.RATE_LIMIT_ERROR: SafeDiagnostic.RATE_LIMITED,
    SafeErrorType.NOT_FOUND_ERROR: SafeDiagnostic.RESOURCE_NOT_FOUND,
    SafeErrorType.CANCELLED_ERROR: SafeDiagnostic.OPERATION_CANCELLED,
    SafeErrorType.DECODING_ERROR: SafeDiagnostic.INVALID_RESPONSE,
    SafeErrorType.VALIDATION_ERROR: SafeDiagnostic.INVALID_INPUT,
    SafeErrorType.OPERATING_SYSTEM_ERROR: SafeDiagnostic.LOCAL_IO_FAILURE,
    SafeErrorType.RUNTIME_ERROR: SafeDiagnostic.INTERNAL_FAILURE,
    SafeErrorType.UNKNOWN_ERROR: SafeDiagnostic.UNKNOWN_FAILURE,
}

HTTP_DIAGNOSTICS = {
    100: SafeDiagnostic.UNEXPECTED_RESPONSE,
    200: SafeDiagnostic.UNEXPECTED_RESPONSE,
    302: SafeDiagnostic.UNEXPECTED_RESPONSE,
    400: SafeDiagnostic.INVALID_INPUT,
    401: SafeDiagnostic.AUTHENTICATION_REQUIRED,
    403: SafeDiagnostic.ACCESS_DENIED,
    404: SafeDiagnostic.RESOURCE_NOT_FOUND,
    408: SafeDiagnostic.REQUEST_TIMEOUT,
    409: SafeDiagnostic.CONFLICT,
    418: SafeDiagnostic.INVALID_INPUT,
    429: SafeDiagnostic.RATE_LIMITED,
    451: SafeDiagnostic.ACCESS_DENIED,
    500: SafeDiagnostic.REMOTE_SERVICE_FAILURE,
    503: SafeDiagnostic.REMOTE_SERVICE_FAILURE,
    504: SafeDiagnostic.REQUEST_TIMEOUT,
    599: SafeDiagnostic.REMOTE_SERVICE_FAILURE,
}


def _bait_details() -> tuple[str, ...]:
    marker = "NOT" + "-A-REAL-SECRET-LOCALIZATION-42"
    return (
        "api" + f"_key={marker}",
        "tok" + f"en={marker}",
        "pass" + f"word={marker}",
        "Coo" + "kie: session=" + marker,
        "Author" + "ization: " + "Bearer " + marker,
        "maintainer" + "@example.test",
        "C:" + "\\Users\\private-user\\AppData\\secret.txt",
        "/home/" + "private-user/.config/secret.json",
        "/Users/" + "private-user/Library/secret.json",
        "\\\\server\\Users\\private-user\\secret.txt",
        "密" + "碼＝" + marker,
        "トー" + "クン＝" + marker,
        "🔐 " + marker,
    )


def _assert_catalog_order_and_completeness() -> None:
    assert tuple(localization._MESSAGES) == tuple(SafeDiagnostic)
    for diagnostic, translations in localization._MESSAGES.items():
        assert tuple(translations) == SUPPORTED_LANGUAGES, diagnostic
        assert all(message.strip() for message in translations.values()), diagnostic


def _assert_every_error_type_renders() -> None:
    assert set(ERROR_DIAGNOSTICS) == set(SafeErrorType)
    for error_type, diagnostic in ERROR_DIAGNOSTICS.items():
        status = 502 if error_type is SafeErrorType.HTTP_ERROR else None
        safe = SafeError(error_type, diagnostic, status)
        for language in SUPPORTED_LANGUAGES:
            expected = localization._MESSAGES[diagnostic][language]
            metadata = (
                f"type={error_type.value}; diagnostic={diagnostic.value}"
            )
            if status is not None:
                expected = f"{expected} [{metadata}; HTTP {status}]"
            else:
                expected = f"{expected} [{metadata}]"
            assert safe_error_message(language, safe) == expected


def _assert_http_statuses_render_safely() -> None:
    for status, diagnostic in HTTP_DIAGNOSTICS.items():
        for language in SUPPORTED_LANGUAGES:
            expected = localization._MESSAGES[diagnostic][language]
            expected = (
                f"{expected} [type=http_error; "
                f"diagnostic={diagnostic.value}; HTTP {status}]"
            )
            rendered = safe_error_message(
                language,
                RuntimeError("opaque provider failure"),
                http_status=status,
            )
            assert rendered == expected, (language, status, rendered)


def _assert_sensitive_details_never_render() -> None:
    baits = _bait_details()
    combined = " | ".join(baits)
    inputs: tuple[BaseException | str, ...] = (
        combined,
        RuntimeError(combined),
        ValueError(combined),
        ConnectionError(combined),
    )
    for language in SUPPORTED_LANGUAGES:
        for error in inputs:
            rendered = safe_error_message(language, error)
            for bait in baits:
                assert bait not in rendered
            for private_fragment in (
                "NOT-A-REAL-SECRET",
                "private-user",
                "example.test",
                "Bearer",
                "session=",
                "🔐",
            ):
                assert private_fragment not in rendered


def _assert_serialized_safe_error_keeps_diagnostic() -> None:
    for diagnostic in SafeDiagnostic:
        safe = SafeError(SafeErrorType.UNKNOWN_ERROR, diagnostic)
        serialized = str(safe)
        for language in SUPPORTED_LANGUAGES:
            assert safe_error_message(language, serialized) == safe_error_message(
                language,
                safe,
            )

    safe_http = SafeError(
        SafeErrorType.HTTP_ERROR,
        SafeDiagnostic.CONFLICT,
        409,
    )
    for language in SUPPORTED_LANGUAGES:
        assert safe_error_message(language, str(safe_http)) == safe_error_message(
            language,
            safe_http,
        )


def run() -> None:
    _assert_catalog_order_and_completeness()
    _assert_every_error_type_renders()
    _assert_http_statuses_render_safely()
    _assert_sensitive_details_never_render()
    _assert_serialized_safe_error_keeps_diagnostic()
    print("SAFE_ERROR_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
