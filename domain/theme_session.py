from __future__ import annotations

lazy from dataclasses import dataclass
lazy from typing import Literal, Protocol

BUILTIN_THEME_ID = "builtin"
ACTIVE_THEME_SETTING_KEY = "active_theme_id"
ThemeResolutionStatus = Literal["ready", "missing"]
ThemeRemovalBlock = Literal["builtin", "active", "preview"]
_BOUNDARY_ERRORS = (Exception,)


class ThemeSessionError(RuntimeError):
    """A safe theme preview transaction could not be completed."""


@dataclass(frozen=True, slots=True)
class ThemeResolution:
    requested_id: str
    resolved_id: str
    payload: object
    status: ThemeResolutionStatus


@dataclass(frozen=True, slots=True)
class ThemeCommit:
    previous_id: str
    theme_id: str


class ThemeResolver(Protocol):
    def __call__(self, theme_id: str) -> ThemeResolution: ...


class ThemePreviewer(Protocol):
    def __call__(self, resolution: ThemeResolution) -> None: ...


class ThemeCommitter(Protocol):
    def __call__(self, theme_id: str) -> None: ...


class ThemeSession:
    """Own one preview/save/cancel transaction without knowing Qt or storage.

    Installation, archive validation, UI rendering and persistence remain in
    separate modules.  This state machine only coordinates their explicit
    callbacks and guarantees that a failed preview attempts to restore the
    last known-good visual state.
    """

    setting_key = ACTIVE_THEME_SETTING_KEY

    def __init__(
        self,
        persisted_theme_id: str,
        *,
        resolve: ThemeResolver,
        preview: ThemePreviewer,
        commit: ThemeCommitter,
    ) -> None:
        self._resolve = resolve
        self._preview = preview
        self._commit = commit
        initial = self._resolved(persisted_theme_id)
        self._persisted = initial
        self._current = initial
        self._last_resolution = initial

    @property
    def persisted_theme_id(self) -> str:
        return self._persisted.resolved_id

    @property
    def preview_theme_id(self) -> str:
        return self._current.resolved_id

    @property
    def last_resolution(self) -> ThemeResolution:
        return self._last_resolution

    @property
    def has_unsaved_preview(self) -> bool:
        return self._current.resolved_id != self._persisted.resolved_id

    def preview(self, theme_id: str) -> ThemeResolution:
        target = self._resolved(theme_id)
        self._last_resolution = target
        if target.resolved_id == self._current.resolved_id:
            return target
        previous = self._current
        self._apply_preview(target, rollback=previous)
        self._current = target
        return target

    def cancel(self) -> ThemeResolution:
        if not self.has_unsaved_preview:
            return self._persisted
        previous = self._current
        self._apply_preview(self._persisted, rollback=previous)
        self._current = self._persisted
        self._last_resolution = self._persisted
        return self._persisted

    def save(self) -> ThemeCommit:
        previous_id = self._persisted.resolved_id
        next_id = self._current.resolved_id
        try:
            self._commit(next_id)
        except _BOUNDARY_ERRORS:
            raise ThemeSessionError("Unable to save the selected theme.") from None
        self._persisted = self._current
        return ThemeCommit(previous_id=previous_id, theme_id=next_id)

    def removal_block(self, theme_id: str) -> ThemeRemovalBlock | None:
        if theme_id == BUILTIN_THEME_ID:
            return "builtin"
        if theme_id == self._persisted.resolved_id:
            return "active"
        if theme_id == self._current.resolved_id:
            return "preview"
        return None

    def _resolved(self, theme_id: str) -> ThemeResolution:
        try:
            result = self._resolve(str(theme_id).strip() or BUILTIN_THEME_ID)
        except _BOUNDARY_ERRORS:
            raise ThemeSessionError("Unable to resolve the selected theme.") from None
        if result.status not in {"ready", "missing"}:
            raise ThemeSessionError("Theme resolver returned an invalid status.")
        if result.status == "missing" and result.resolved_id != BUILTIN_THEME_ID:
            raise ThemeSessionError("A missing theme must use the built-in fallback.")
        return result

    def _apply_preview(
        self,
        target: ThemeResolution,
        *,
        rollback: ThemeResolution,
    ) -> None:
        preview_failed = False
        try:
            self._preview(target)
        except _BOUNDARY_ERRORS:
            preview_failed = True
        if not preview_failed:
            return
        try:
            self._preview(rollback)
        except _BOUNDARY_ERRORS:
            raise ThemeSessionError(
                "Theme preview failed and its visual rollback was incomplete."
            ) from None
        raise ThemeSessionError("Unable to preview the selected theme.")
