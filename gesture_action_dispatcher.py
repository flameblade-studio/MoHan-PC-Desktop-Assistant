"""Compatibility facade for application gesture dispatch."""

from __future__ import annotations

from application.gesture_action_dispatcher import (
    GestureActionDispatcher,
    GestureActionPort,
    GestureAuthorizer,
    GestureDispatchDisposition,
    GestureDispatchResult,
)

__all__ = (
    "GestureActionDispatcher",
    "GestureActionPort",
    "GestureAuthorizer",
    "GestureDispatchDisposition",
    "GestureDispatchResult",
)
