"""Select the appearance adapter contract once at the composition boundary."""
from __future__ import annotations

lazy from collections.abc import Callable
lazy from inspect import Parameter, signature
lazy from typing import Any
lazy from PySide6.QtGui import QPixmap
lazy from application.appearance_ports import AppearanceRenderOptions


class AnimatedAppearance:
    """Keep old combined adapters usable alongside phased appearance adapters."""

    def __init__(self, overlay: Any) -> None:
        self._atomic: Callable[..., object] | None = _optional_callable(
            getattr(overlay, "apply_animated", None)
        )
        self._appearance: Callable[..., object] | None = _optional_callable(
            getattr(overlay, "apply_appearance", None)
        )
        self._makeup: Callable[..., object] | None = _optional_callable(
            getattr(overlay, "apply_makeup", None)
        )
        self._combined: Callable[..., object] | None = _optional_callable(
            getattr(overlay, "apply", None)
        )
        self._combined_keywords: frozenset[str] = frozenset()
        self._atomic_after_makeup = False
        self._atomic_makeup_view_id = False
        self._atomic_appearance_options = False
        self._makeup_view_id = False
        self.supports_body_replacement = False
        if callable(self._atomic):
            parameters = signature(self._atomic).parameters
            accepts_any_keyword = any(
                parameter.kind is Parameter.VAR_KEYWORD
                for parameter in parameters.values()
            )
            self._atomic_appearance_options = "appearance_options" in parameters
            self.supports_body_replacement = (
                self._atomic_appearance_options
                or (
                    "replace_body" in parameters
                    and parameters["replace_body"].kind in {
                        Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY,
                    }
                )
            )
            self._atomic_after_makeup = (
                self._atomic_appearance_options
                or (
                    "paint_after_makeup" in parameters
                    and parameters["paint_after_makeup"].kind in {
                        Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY,
                    }
                )
            )
            self._atomic_makeup_view_id = accepts_any_keyword or (
                "makeup_view_id" in parameters and parameters["makeup_view_id"].kind in {
                    Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY,
                }
            )
        if callable(self._makeup):
            parameters = signature(self._makeup).parameters
            accepts_any_keyword = any(
                parameter.kind is Parameter.VAR_KEYWORD
                for parameter in parameters.values()
            )
            self._makeup_view_id = accepts_any_keyword or (
                "makeup_view_id" in parameters and parameters["makeup_view_id"].kind in {
                    Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY,
                }
            )
        if callable(self._combined) and not callable(self._atomic):
            parameters = signature(self._combined).parameters
            accepts_any_keyword = any(
                parameter.kind is Parameter.VAR_KEYWORD
                for parameter in parameters.values()
            )
            self._combined_keywords = frozenset(
                name for name in ("suppress_makeup_slots", "eye_state", "makeup_view_id")
                if accepts_any_keyword or (
                    name in parameters and parameters[name].kind in {
                        Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY,
                    }
                )
            )

    def compose(
        self, frame: QPixmap, view_id: str, paint_motion: Callable[[QPixmap], None],
        appearance_options: AppearanceRenderOptions | None = None,
    ) -> QPixmap:
        appearance_options = (
            AppearanceRenderOptions() if appearance_options is None else appearance_options
        )
        adapter_options = {
            "suppress_makeup_slots": appearance_options.suppress_makeup_slots,
            "eye_state": appearance_options.eye_state,
        }
        if callable(self._atomic):
            # Adapters may paint in place; never expose the renderer's static cache.
            frame = QPixmap(frame)
            if self._atomic_appearance_options:
                atomic_options = {"appearance_options": appearance_options}
            else:
                atomic_options = dict(adapter_options)
                if appearance_options.makeup_view_id is not None and self._atomic_makeup_view_id:
                    atomic_options["makeup_view_id"] = appearance_options.makeup_view_id
                if appearance_options.replace_body is not None and self.supports_body_replacement:
                    atomic_options["replace_body"] = appearance_options.replace_body
                if appearance_options.paint_after_makeup is not None and self._atomic_after_makeup:
                    atomic_options["paint_after_makeup"] = appearance_options.paint_after_makeup
            result = _require_pixmap(
                self._atomic(frame, view_id, paint_motion, **atomic_options)
            )
            if appearance_options.paint_after_makeup is not None and not self._atomic_after_makeup:
                appearance_options.paint_after_makeup(result)
            return result
        if callable(self._appearance) and callable(self._makeup):
            result = _require_pixmap(self._appearance(QPixmap(frame), view_id))
            paint_motion(result)
            makeup_options = dict(adapter_options)
            if appearance_options.makeup_view_id is not None and self._makeup_view_id:
                makeup_options["makeup_view_id"] = appearance_options.makeup_view_id
            result = _require_pixmap(self._makeup(result, view_id, **makeup_options))
            if appearance_options.paint_after_makeup is not None:
                appearance_options.paint_after_makeup(result)
            return result
        result = QPixmap(frame)
        paint_motion(result)
        if callable(self._combined):
            # Inspect the contract once, rather than catching TypeError and
            # possibly hiding an error raised inside an adapter.
            combined_options = dict(adapter_options)
            if appearance_options.makeup_view_id is not None:
                combined_options["makeup_view_id"] = appearance_options.makeup_view_id
            supported = {
                name: combined_options[name]
                for name in self._combined_keywords
                if name in combined_options
                and (name != "eye_state" or appearance_options.eye_state != "rest")
            }
            result = _require_pixmap(self._combined(result, view_id, **supported))
        if appearance_options.paint_after_makeup is not None:
            appearance_options.paint_after_makeup(result)
        return result


def _optional_callable(value: object) -> Callable[..., object] | None:
    return value if callable(value) else None


def _require_pixmap(value: object) -> QPixmap:
    if not isinstance(value, QPixmap):
        raise TypeError("Appearance adapters must return QPixmap.")
    return value
