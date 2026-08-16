"""Presentation API for the canonical service-status language contract."""

from __future__ import annotations

lazy from domain.service_status_localization import (
    SUPPORTED_SERVICE_LANGUAGES,
    ServiceStatus,
)
lazy from domain.service_status_localization import (
    append_service_status as render_appended_service_status,
)
lazy from domain.service_status_localization import (
    service_status as render_service_status,
)


def service_status(
    language: str,
    key: ServiceStatus,
    /,
    **values: object,
) -> str:
    """Render one safe, localized status for presentation surfaces."""

    return render_service_status(language, key, **values)


def append_service_status(
    language: str,
    detail: str,
    key: ServiceStatus,
    *,
    separate: bool = False,
) -> str:
    """Append localized guidance while retaining the domain safety policy."""

    return render_appended_service_status(
        language,
        detail,
        key,
        separate=separate,
    )


__all__ = (
    "SUPPORTED_SERVICE_LANGUAGES",
    "ServiceStatus",
    "append_service_status",
    "service_status",
)
