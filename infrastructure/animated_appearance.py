"""Select the appearance adapter contract once at the composition boundary."""
from __future__ import annotations

lazy from collections.abc import Callable
lazy from inspect import Parameter, signature
lazy from typing import Any
lazy from PySide6.QtGui import QPixmap


class AnimatedAppearance:
    """Keep old combined adapters usable alongside phased appearance adapters."""

    def __init__(self, overlay: Any) -> None:
        self._atomic = getattr(overlay, "apply_animated", None)
        self._appearance = getattr(overlay, "apply_appearance", None)
        self._makeup = getattr(overlay, "apply_makeup", None)
        self._combined = getattr(overlay, "apply", None)
        self._combined_keywords: frozenset[str] = frozenset()
        self._atomic_after_makeup = False
        self.supports_body_replacement = False
        if callable(self._atomic):
            parameters = signature(self._atomic).parameters
            self.supports_body_replacement = (
                "replace_body" in parameters
                and parameters["replace_body"].kind in (
                    Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY,
                )
            )
            self._atomic_after_makeup = (
                "paint_after_makeup" in parameters
                and parameters["paint_after_makeup"].kind in (
                    Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY,
                )
            )
        if callable(self._combined) and not callable(self._atomic):
            parameters = signature(self._combined).parameters
            accepts_any_keyword = any(
                parameter.kind is Parameter.VAR_KEYWORD
                for parameter in parameters.values()
            )
            self._combined_keywords = frozenset(
                name for name in ("suppress_makeup_slots", "eye_state")
                if accepts_any_keyword or (
                    name in parameters and parameters[name].kind in (
                        Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY,
                    )
                )
            )

    def compose(
        self, frame: QPixmap, view_id: str, paint_motion: Callable[[QPixmap], None], *,
        suppress_makeup_slots: frozenset[str], eye_state: str,
        paint_after_makeup: Callable[[QPixmap], None] | None = None,
        replace_body: Callable[[QPixmap], QPixmap] | None = None,
    ) -> QPixmap:
        options = {"suppress_makeup_slots": suppress_makeup_slots, "eye_state": eye_state}
        if callable(self._atomic):
            # Adapters may paint in place; never expose the renderer's static cache.
            frame = QPixmap(frame)
            if replace_body is not None and self.supports_body_replacement:
                options["replace_body"] = replace_body
            if paint_after_makeup is not None and self._atomic_after_makeup:
                return self._atomic(
                    frame, view_id, paint_motion, **options,
                    paint_after_makeup=paint_after_makeup,
                )
            result = self._atomic(frame, view_id, paint_motion, **options)
            if paint_after_makeup is not None:
                paint_after_makeup(result)
            return result
        if callable(self._appearance) and callable(self._makeup):
            result = self._appearance(QPixmap(frame), view_id)
            paint_motion(result)
            result = self._makeup(result, view_id, **options)
            if paint_after_makeup is not None:
                paint_after_makeup(result)
            return result
        result = QPixmap(frame)
        paint_motion(result)
        if callable(self._combined):
            # Inspect the contract once, rather than catching TypeError and
            # possibly hiding an error raised inside an adapter.
            supported = ({name: options[name] for name in self._combined_keywords}
                         if eye_state != "rest" else {})
            result = self._combined(result, view_id, **supported)
        if paint_after_makeup is not None:
            paint_after_makeup(result)
        return result
