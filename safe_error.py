from __future__ import annotations

lazy import inspect
lazy import re
lazy from dataclasses import dataclass
lazy from enum import StrEnum

__all__ = [
    "SafeDiagnostic",
    "SafeError",
    "SafeErrorType",
    "sanitize_error",
]

type ErrorInput = BaseException | str
type _Classification = tuple["SafeErrorType", "SafeDiagnostic"]


class SafeErrorType(StrEnum):
    """Approved, language-independent error types exposed outside services."""

    HTTP_ERROR = "http_error"
    TIMEOUT_ERROR = "timeout_error"
    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    NOT_FOUND_ERROR = "not_found_error"
    CANCELLED_ERROR = "cancelled_error"
    DECODING_ERROR = "decoding_error"
    VALIDATION_ERROR = "validation_error"
    OPERATING_SYSTEM_ERROR = "operating_system_error"
    RUNTIME_ERROR = "runtime_error"
    UNKNOWN_ERROR = "unknown_error"


class SafeDiagnostic(StrEnum):
    """Finite diagnostic codes suitable for logs and localized UI mapping."""

    AUTHENTICATION_REQUIRED = "authentication_required"
    ACCESS_DENIED = "access_denied"
    RATE_LIMITED = "rate_limited"
    REQUEST_TIMEOUT = "request_timeout"
    NETWORK_UNAVAILABLE = "network_unavailable"
    RESOURCE_NOT_FOUND = "resource_not_found"
    CONFLICT = "conflict"
    INVALID_INPUT = "invalid_input"
    INVALID_RESPONSE = "invalid_response"
    OPERATION_CANCELLED = "operation_cancelled"
    LOCAL_IO_FAILURE = "local_io_failure"
    REMOTE_SERVICE_FAILURE = "remote_service_failure"
    UNEXPECTED_RESPONSE = "unexpected_response"
    INTERNAL_FAILURE = "internal_failure"
    UNKNOWN_FAILURE = "unknown_failure"


@dataclass(frozen=True, slots=True)
class SafeError:
    """A sanitized error value that never retains the original error text."""

    error_type: SafeErrorType
    diagnostic: SafeDiagnostic
    http_status: int | None = None

    def __str__(self) -> str:
        parts = [
            f"type={self.error_type.value}",
            f"diagnostic={self.diagnostic.value}",
        ]
        if self.http_status is not None:
            parts.append(f"http_status={self.http_status}")
        return "; ".join(parts)


_HTTP_STATUS_PATTERN = re.compile(
    r"\bHTTP(?:/\d(?:\.\d)?)?(?:\s+STATUS)?[\s:=_-]+([1-5]\d{2})\b",
    re.IGNORECASE,
)

_EXCEPTION_CLASSIFICATIONS: tuple[
    tuple[type[BaseException], SafeErrorType, SafeDiagnostic], ...
] = (
    (TimeoutError, SafeErrorType.TIMEOUT_ERROR, SafeDiagnostic.REQUEST_TIMEOUT),
    (
        ConnectionError,
        SafeErrorType.CONNECTION_ERROR,
        SafeDiagnostic.NETWORK_UNAVAILABLE,
    ),
    (
        PermissionError,
        SafeErrorType.AUTHORIZATION_ERROR,
        SafeDiagnostic.ACCESS_DENIED,
    ),
    (
        FileNotFoundError,
        SafeErrorType.NOT_FOUND_ERROR,
        SafeDiagnostic.RESOURCE_NOT_FOUND,
    ),
    (
        UnicodeError,
        SafeErrorType.DECODING_ERROR,
        SafeDiagnostic.INVALID_RESPONSE,
    ),
    (ValueError, SafeErrorType.VALIDATION_ERROR, SafeDiagnostic.INVALID_INPUT),
    (TypeError, SafeErrorType.VALIDATION_ERROR, SafeDiagnostic.INVALID_INPUT),
)

_NAMED_CLASSIFICATIONS: tuple[
    tuple[frozenset[str], SafeErrorType, SafeDiagnostic], ...
] = (
    (
        frozenset({"HTTPError", "BadStatusError", "WebSocketBadStatusException"}),
        SafeErrorType.HTTP_ERROR,
        SafeDiagnostic.UNEXPECTED_RESPONSE,
    ),
    (
        frozenset({"APITimeoutError", "WebSocketTimeoutException"}),
        SafeErrorType.TIMEOUT_ERROR,
        SafeDiagnostic.REQUEST_TIMEOUT,
    ),
    (
        frozenset({
            "APIConnectionError",
            "URLError",
            "WebSocketAddressException",
            "WebSocketConnectionClosedException",
        }),
        SafeErrorType.CONNECTION_ERROR,
        SafeDiagnostic.NETWORK_UNAVAILABLE,
    ),
    (
        frozenset({"AuthenticationError"}),
        SafeErrorType.AUTHENTICATION_ERROR,
        SafeDiagnostic.AUTHENTICATION_REQUIRED,
    ),
    (
        frozenset({"PermissionDeniedError"}),
        SafeErrorType.AUTHORIZATION_ERROR,
        SafeDiagnostic.ACCESS_DENIED,
    ),
    (
        frozenset({"RateLimitError"}),
        SafeErrorType.RATE_LIMIT_ERROR,
        SafeDiagnostic.RATE_LIMITED,
    ),
    (
        frozenset({"NotFoundError"}),
        SafeErrorType.NOT_FOUND_ERROR,
        SafeDiagnostic.RESOURCE_NOT_FOUND,
    ),
    (
        frozenset({"CancelledError", "CanceledError"}),
        SafeErrorType.CANCELLED_ERROR,
        SafeDiagnostic.OPERATION_CANCELLED,
    ),
    (
        frozenset({"JSONDecodeError"}),
        SafeErrorType.DECODING_ERROR,
        SafeDiagnostic.INVALID_RESPONSE,
    ),
)

_TEXT_CLASSIFICATIONS: tuple[
    tuple[tuple[str, ...], SafeErrorType, SafeDiagnostic], ...
] = (
    (
        ("rate limit", "too many requests"),
        SafeErrorType.RATE_LIMIT_ERROR,
        SafeDiagnostic.RATE_LIMITED,
    ),
    (
        (
            "unauthorized",
            "authentication failed",
            "invalid api key",
            "invalid token",
            "expired token",
        ),
        SafeErrorType.AUTHENTICATION_ERROR,
        SafeDiagnostic.AUTHENTICATION_REQUIRED,
    ),
    (
        ("forbidden", "permission denied", "access denied"),
        SafeErrorType.AUTHORIZATION_ERROR,
        SafeDiagnostic.ACCESS_DENIED,
    ),
    (
        ("timeout", "timed out"),
        SafeErrorType.TIMEOUT_ERROR,
        SafeDiagnostic.REQUEST_TIMEOUT,
    ),
    (
        ("connection", "network unreachable", "name resolution", "dns failure"),
        SafeErrorType.CONNECTION_ERROR,
        SafeDiagnostic.NETWORK_UNAVAILABLE,
    ),
    (
        ("not found",),
        SafeErrorType.NOT_FOUND_ERROR,
        SafeDiagnostic.RESOURCE_NOT_FOUND,
    ),
    (
        ("cancelled", "canceled"),
        SafeErrorType.CANCELLED_ERROR,
        SafeDiagnostic.OPERATION_CANCELLED,
    ),
)


def _valid_http_status(value: object) -> int | None:
    if type(value) is not int:
        return None
    return value if 100 <= value <= 599 else None


def _status_from_object(error: ErrorInput) -> int | None:
    if isinstance(error, str):
        return None

    candidates = [
        inspect.getattr_static(error, attribute, None)
        for attribute in ("status", "status_code", "code")
    ]
    response = inspect.getattr_static(error, "response", None)
    candidates.append(inspect.getattr_static(response, "status_code", None))

    for candidate in candidates:
        status = _valid_http_status(candidate)
        if status is not None:
            return status
    return None


def _safe_text(error: ErrorInput) -> str:
    if isinstance(error, str):
        return error
    arguments = BaseException.args.__get__(error, type(error))
    return " ".join(argument for argument in arguments if type(argument) is str)


def _status_from_text(text: str) -> int | None:
    match = _HTTP_STATUS_PATTERN.search(text)
    return int(match.group(1)) if match else None


def _http_diagnostic(status: int) -> SafeDiagnostic:
    diagnostic = SafeDiagnostic.UNEXPECTED_RESPONSE
    match status:
        case 401 | 407:
            diagnostic = SafeDiagnostic.AUTHENTICATION_REQUIRED
        case 403 | 451:
            diagnostic = SafeDiagnostic.ACCESS_DENIED
        case 404 | 410:
            diagnostic = SafeDiagnostic.RESOURCE_NOT_FOUND
        case 408 | 504:
            diagnostic = SafeDiagnostic.REQUEST_TIMEOUT
        case 409:
            diagnostic = SafeDiagnostic.CONFLICT
        case 429:
            diagnostic = SafeDiagnostic.RATE_LIMITED
        case value if 400 <= value < 500:
            diagnostic = SafeDiagnostic.INVALID_INPUT
        case value if 500 <= value < 600:
            diagnostic = SafeDiagnostic.REMOTE_SERVICE_FAILURE
    return diagnostic


def _classification_by_exception(error: ErrorInput) -> _Classification | None:
    if isinstance(error, str):
        return None

    for exception_type, error_type, diagnostic in _EXCEPTION_CLASSIFICATIONS:
        if isinstance(error, exception_type):
            return error_type, diagnostic

    name = type(error).__name__
    for names, error_type, diagnostic in _NAMED_CLASSIFICATIONS:
        if name in names:
            return error_type, diagnostic
    return None


def _classification_by_text(text: str) -> _Classification | None:
    normalized = text.casefold()
    for fragments, error_type, diagnostic in _TEXT_CLASSIFICATIONS:
        if any(fragment in normalized for fragment in fragments):
            return error_type, diagnostic
    return None


def _fallback_classification(error: ErrorInput) -> _Classification:
    if isinstance(error, OSError):
        classification = (
            SafeErrorType.OPERATING_SYSTEM_ERROR,
            SafeDiagnostic.LOCAL_IO_FAILURE,
        )
    elif isinstance(error, RuntimeError):
        classification = (
            SafeErrorType.RUNTIME_ERROR,
            SafeDiagnostic.INTERNAL_FAILURE,
        )
    else:
        classification = (
            SafeErrorType.UNKNOWN_ERROR,
            SafeDiagnostic.UNKNOWN_FAILURE,
        )
    return classification


def sanitize_error(
    error: ErrorInput,
    *,
    http_status: int | None = None,
) -> SafeError:
    """Return only approved metadata; discard all untrusted error detail.

    The returned value never stores or echoes the original exception, message,
    response body, URL, headers, credentials, email address, or local path.
    User-facing layers should localize ``error_type`` and ``diagnostic`` rather
    than display provider text.
    """

    text = _safe_text(error)
    status = _valid_http_status(http_status)
    if status is None:
        status = _status_from_object(error)
    if status is None:
        status = _status_from_text(text)

    if status is not None:
        return SafeError(
            error_type=SafeErrorType.HTTP_ERROR,
            diagnostic=_http_diagnostic(status),
            http_status=status,
        )

    classification = _classification_by_exception(error)
    if classification is None:
        classification = _classification_by_text(text)
    if classification is None:
        classification = _fallback_classification(error)
    return SafeError(*classification)
