"""Compatibility facade for application gesture routing."""

from __future__ import annotations

from application.gesture_action_router import (
    GestureActionDecision,
    GestureActionDisposition,
    GestureActionRouter,
    GestureActionSafety,
    GestureTrigger,
)

__all__ = (
    "GestureActionDecision",
    "GestureActionDisposition",
    "GestureActionRouter",
    "GestureActionSafety",
    "GestureTrigger",
)
