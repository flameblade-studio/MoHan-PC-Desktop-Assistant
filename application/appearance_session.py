from __future__ import annotations

lazy from dataclasses import dataclass, replace
lazy from typing import Literal, Protocol

type AppearanceSlot = Literal[
    "garment",
    "hairstyle",
    "headwear",
    "weapon",
    "handheld",
    "jewelry",
    "foreground-effect",
]
type AppearanceStatus = Literal["resolved", "none", "missing_builtin_fallback"]

ACTIVE_OUTFIT_SETTING_KEY = "active_outfit_id"
APPEARANCE_SLOTS: tuple[AppearanceSlot, ...] = (
    "garment",
    "hairstyle",
    "headwear",
    "weapon",
    "handheld",
    "jewelry",
    "foreground-effect",
)
_ATTRIBUTE_BY_SLOT: dict[AppearanceSlot, str] = {
    "garment": "garment",
    "hairstyle": "hairstyle",
    "headwear": "headwear",
    "weapon": "weapon",
    "handheld": "handheld",
    "jewelry": "jewelry",
    "foreground-effect": "foreground_effect",
}


@dataclass(frozen=True, slots=True)
class AppearanceComponent:
    pack_id: str
    item_id: str
    variant_id: str

    @classmethod
    def builtin(cls, slot: AppearanceSlot) -> AppearanceComponent:
        return cls("builtin", slot, "builtin")


@dataclass(frozen=True, slots=True)
class AppearanceSelection:
    garment: AppearanceComponent | None
    hairstyle: AppearanceComponent | None
    headwear: AppearanceComponent | None
    weapon: AppearanceComponent | None
    handheld: AppearanceComponent | None
    jewelry: AppearanceComponent | None
    foreground_effect: AppearanceComponent | None

    def component(self, slot: AppearanceSlot) -> AppearanceComponent | None:
        return getattr(self, _ATTRIBUTE_BY_SLOT[slot])

    def with_slot(
        self,
        slot: AppearanceSlot,
        component: AppearanceComponent | None,
    ) -> AppearanceSelection:
        return replace(self, **{_ATTRIBUTE_BY_SLOT[slot]: component})

    def replace(self, **changes: AppearanceComponent | None) -> AppearanceSelection:
        return replace(self, **changes)

    @property
    def package_ids(self) -> frozenset[str]:
        return frozenset(
            component.pack_id
            for slot in APPEARANCE_SLOTS
            if (component := self.component(slot)) is not None
            and component.pack_id != "builtin"
        )


@dataclass(frozen=True, slots=True)
class AppearanceCommit:
    selection: AppearanceSelection


class AppearanceResolver(Protocol):
    def resolve(
        self,
        slot: AppearanceSlot,
        requested: AppearanceComponent,
    ) -> AppearanceComponent | None: ...


class AppearancePreview(Protocol):
    def preview(self, selection: AppearanceSelection) -> None: ...


class AppearanceCommitter(Protocol):
    def commit(self, payload: AppearanceCommit) -> None: ...


class AppearanceDynamicsReset(Protocol):
    def reset(self) -> object: ...


class AppearanceSession:
    """Own one atomic, reversible appearance preview transaction."""

    setting_key = ACTIVE_OUTFIT_SETTING_KEY

    def __init__(
        self,
        persisted_selection: AppearanceSelection,
        resolver: AppearanceResolver,
        preview_callback: AppearancePreview,
        commit_callback: AppearanceCommitter,
        dynamics: AppearanceDynamicsReset | None = None,
    ) -> None:
        self._persisted = persisted_selection
        self._requested = persisted_selection
        self._preview = persisted_selection
        self._resolver = resolver
        self._preview_callback = preview_callback
        self._commit_callback = commit_callback
        if dynamics is not None:
            self._dynamics = dynamics
        self._statuses: dict[AppearanceSlot, AppearanceStatus] = {
            slot: "none" if persisted_selection.component(slot) is None else "resolved"
            for slot in APPEARANCE_SLOTS
        }
        self._last_commit: AppearanceCommit | None = None

    @property
    def requested_selection(self) -> AppearanceSelection:
        return self._requested

    @property
    def preview_selection(self) -> AppearanceSelection:
        return self._preview

    @property
    def dirty(self) -> bool:
        return self._preview != self._persisted

    @property
    def active_package_ids(self) -> frozenset[str]:
        return self._persisted.package_ids

    @property
    def preview_package_ids(self) -> frozenset[str]:
        return self._preview.package_ids

    def status_for(self, slot: AppearanceSlot) -> AppearanceStatus:
        return self._statuses[slot]

    def preview_slot(
        self,
        slot: AppearanceSlot,
        requested: AppearanceComponent | None,
    ) -> AppearanceSelection:
        requested_selection = self._requested.with_slot(slot, requested)
        resolved, status = self._resolve(slot, requested)
        preview_selection = self._preview.with_slot(slot, resolved)
        self._publish_preview(preview_selection)
        self._requested = requested_selection
        self._statuses[slot] = status
        self._last_commit = None
        return self._preview

    def apply_ensemble(
        self,
        requested: AppearanceSelection,
    ) -> AppearanceSelection:
        resolved = requested
        statuses: dict[AppearanceSlot, AppearanceStatus] = {}
        for slot in APPEARANCE_SLOTS:
            component, status = self._resolve(slot, requested.component(slot))
            resolved = resolved.with_slot(slot, component)
            statuses[slot] = status
        self._publish_preview(resolved)
        self._requested = requested
        self._statuses = statuses
        self._last_commit = None
        return self._preview

    def cancel(self) -> AppearanceSelection:
        try:
            if self._preview != self._persisted:
                self._publish_preview(self._persisted)
        finally:
            self._reset_dynamics()
        self._requested = self._persisted
        self._statuses = {
            slot: "none" if self._persisted.component(slot) is None else "resolved"
            for slot in APPEARANCE_SLOTS
        }
        self._last_commit = None
        return self._preview

    def save(self) -> AppearanceCommit:
        if self._last_commit is not None and not self.dirty:
            self._reset_dynamics()
            return self._last_commit
        payload = AppearanceCommit(self._preview)
        try:
            self._commit_callback.commit(payload)
        finally:
            self._reset_dynamics()
        self._persisted = self._preview
        self._requested = self._preview
        self._last_commit = payload
        return payload

    def can_delete(self, pack_id: str) -> bool:
        return (
            pack_id != "builtin"
            and pack_id not in self.active_package_ids
            and pack_id not in self.preview_package_ids
        )

    def _resolve(
        self,
        slot: AppearanceSlot,
        requested: AppearanceComponent | None,
    ) -> tuple[AppearanceComponent | None, AppearanceStatus]:
        if requested is None:
            return None, "none"
        resolved = self._resolver.resolve(slot, requested)
        if resolved is None:
            return AppearanceComponent.builtin(slot), "missing_builtin_fallback"
        return resolved, "resolved"

    def _publish_preview(self, selection: AppearanceSelection) -> None:
        previous = self._preview
        if selection == previous:
            return
        try:
            self._preview_callback.preview(selection)
        except Exception:
            try:
                self._preview_callback.preview(previous)
            finally:
                self._reset_dynamics()
            raise
        self._preview = selection
        self._reset_dynamics()

    def _reset_dynamics(self) -> None:
        dynamics = getattr(self, "_dynamics", None)
        if dynamics is not None:
            dynamics.reset()
