"""Canonical presentation API for the flagship control center.

Public symbols come straight from their physical owners.  This keeps Python
3.15 lazy loading while preserving callability and exact symbol identity.
"""

from __future__ import annotations

lazy from presentation.flagship.cloud_health import (
    CloudHealthSignals,
    CloudHealthWorker,
)
lazy from presentation.flagship.control_center import FlagshipControlCenter
lazy from presentation.flagship.oauth import OAuthPKCEFlow, OAuthSignals, OAuthWorker
lazy from presentation.flagship.shared import (
    ASSIST_INTENT_MARKERS,
    CALENDAR_MARKERS,
    CALENDAR_WRITE_MARKERS,
    CHINESE_DAY_COUNTS,
    CHINESE_MAIL_COUNTS,
    CORE_PERMISSION_LABELS,
    DRIVE_MARKERS,
    DRIVE_WRITE_MARKERS,
    GESTURE_PERMISSION_CAPABILITIES,
    GMAIL_MARKERS,
    GMAIL_SEND_MARKERS,
    GMAIL_SEND_NEGATIONS,
    READ_INTENT_MARKERS,
    FlagshipDraftValues,
    GestureRecorderPort,
    UnavailableGestureRecorder,
)
lazy from presentation.flagship.workflow_editor import WorkflowEditor
lazy from presentation.flagship_theme import (
    apply_flagship_theme,
    create_flagship_ornament,
)
lazy from presentation.flagship_ui_localization import FlagshipTranslator

__all__ = (
    "ASSIST_INTENT_MARKERS",
    "CALENDAR_MARKERS",
    "CALENDAR_WRITE_MARKERS",
    "CHINESE_DAY_COUNTS",
    "CHINESE_MAIL_COUNTS",
    "CORE_PERMISSION_LABELS",
    "DRIVE_MARKERS",
    "DRIVE_WRITE_MARKERS",
    "GESTURE_PERMISSION_CAPABILITIES",
    "GMAIL_MARKERS",
    "GMAIL_SEND_MARKERS",
    "GMAIL_SEND_NEGATIONS",
    "READ_INTENT_MARKERS",
    "CloudHealthSignals",
    "CloudHealthWorker",
    "FlagshipControlCenter",
    "FlagshipDraftValues",
    "FlagshipTranslator",
    "GestureRecorderPort",
    "OAuthPKCEFlow",
    "OAuthSignals",
    "OAuthWorker",
    "UnavailableGestureRecorder",
    "WorkflowEditor",
    "apply_flagship_theme",
    "create_flagship_ornament",
)

# The aggregate API is a compatibility boundary, not a startup dependency.
# Force its direct owner exports to their real identities so external callers
# never observe CPython 3.15rc1 lazy proxy objects through ``vars(module)``.
_MATERIALIZED_EXPORTS = (
    ASSIST_INTENT_MARKERS,
    CALENDAR_MARKERS,
    CALENDAR_WRITE_MARKERS,
    CHINESE_DAY_COUNTS,
    CHINESE_MAIL_COUNTS,
    CORE_PERMISSION_LABELS,
    DRIVE_MARKERS,
    DRIVE_WRITE_MARKERS,
    GESTURE_PERMISSION_CAPABILITIES,
    GMAIL_MARKERS,
    GMAIL_SEND_MARKERS,
    GMAIL_SEND_NEGATIONS,
    READ_INTENT_MARKERS,
    CloudHealthSignals,
    CloudHealthWorker,
    FlagshipControlCenter,
    FlagshipDraftValues,
    FlagshipTranslator,
    GestureRecorderPort,
    OAuthPKCEFlow,
    OAuthSignals,
    OAuthWorker,
    UnavailableGestureRecorder,
    WorkflowEditor,
    apply_flagship_theme,
    create_flagship_ornament,
)
