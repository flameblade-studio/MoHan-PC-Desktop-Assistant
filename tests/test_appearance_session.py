from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.appearance_session import (
    ACTIVE_OUTFIT_SETTING_KEY,
    APPEARANCE_SLOTS,
    AppearanceCommit,
    AppearanceComponent,
    AppearanceSelection,
    AppearanceSession,
)

EXPECTED_CALLS_AFTER_SAVE = 2
EXPECTED_CALLS_AFTER_CANCEL = 3
EXPECTED_CALLS_AFTER_PREVIEW_FAILURE = 5
EXPECTED_CALLS_AFTER_SAVE_FAILURE = 6


def component(pack_id: str, item_id: str) -> AppearanceComponent:
    return AppearanceComponent(pack_id, item_id, "default")


class Resolver:
    def __init__(self, missing: set[tuple[str, str]] | None = None) -> None:
        self.missing = missing or set()

    def resolve(
        self,
        slot: str,
        requested: AppearanceComponent,
    ) -> AppearanceComponent | None:
        if (slot, requested.pack_id) in self.missing:
            return None
        return requested


class PreviewRecorder:
    def __init__(self) -> None:
        self.calls: list[AppearanceSelection] = []
        self.fail_on: AppearanceSelection | None = None

    def preview(self, selection: AppearanceSelection) -> None:
        self.calls.append(selection)
        if selection == self.fail_on:
            raise RuntimeError("preview failed")


class CommitRecorder:
    def __init__(self) -> None:
        self.calls: list[AppearanceCommit] = []
        self.fail = False

    def commit(self, payload: AppearanceCommit) -> None:
        self.calls.append(payload)
        if self.fail:
            raise RuntimeError("commit failed")


class DynamicsResetRecorder:
    def __init__(self) -> None:
        self.calls = 0

    def reset(self) -> object:
        self.calls += 1
        return object()


def initial_selection() -> AppearanceSelection:
    return AppearanceSelection(
        garment=component("builtin", "garment"),
        hairstyle=component("builtin", "hairstyle"),
        headwear=None,
        weapon=None,
        handheld=None,
        jewelry=None,
        foreground_effect=None,
    )


def assert_state_transitions_and_multislot_mixing() -> None:
    original = initial_selection()
    preview = PreviewRecorder()
    session = AppearanceSession(original, Resolver(), preview, CommitRecorder())

    garment = component("robe-pack", "moon-robe")
    weapon = component("weapon-pack", "weapon-a")
    handheld = component("festival-pack", "handheld-a")
    jewelry = component("jewelry-pack", "jewelry-a")
    session.preview_slot("garment", garment)
    session.preview_slot("weapon", weapon)
    session.preview_slot("handheld", handheld)
    session.preview_slot("jewelry", jewelry)
    assert session.preview_selection.garment == garment
    assert session.preview_selection.weapon == weapon
    assert session.preview_selection.handheld == handheld
    assert session.preview_selection.jewelry == jewelry
    assert session.preview_selection.hairstyle == original.hairstyle

    without_handheld = session.preview_slot("handheld", None)
    assert without_handheld.handheld is None
    assert without_handheld.weapon == weapon
    assert without_handheld.jewelry == jewelry
    call_count = len(preview.calls)
    session.preview_slot("handheld", None)
    assert len(preview.calls) == call_count

    ensemble = AppearanceSelection(
        garment=garment,
        hairstyle=component("hair-pack", "long-hair"),
        headwear=component("headwear-pack", "headwear-a"),
        weapon=weapon,
        handheld=handheld,
        jewelry=jewelry,
        foreground_effect=component("effect-pack", "effect-a"),
    )
    session.apply_ensemble(ensemble)
    assert session.preview_selection == ensemble
    assert preview.calls[-1] == ensemble
    assert session.dirty

    session.cancel()
    assert session.preview_selection == original
    assert preview.calls[-1] == original
    assert not session.dirty
    call_count = len(preview.calls)
    session.cancel()
    assert len(preview.calls) == call_count


def assert_callback_failure_rolls_back_full_preview() -> None:
    original = initial_selection()
    preview = PreviewRecorder()
    session = AppearanceSession(original, Resolver(), preview, CommitRecorder())
    accepted = session.apply_ensemble(
        original.replace(
            weapon=component("weapon-pack", "weapon-a"),
            jewelry=component("jewelry-pack", "jewelry-a"),
        )
    )
    failing = accepted.replace(
        handheld=component("broken-pack", "broken-handheld")
    )
    preview.fail_on = failing

    try:
        session.apply_ensemble(failing)
    except RuntimeError as exc:
        assert str(exc) == "preview failed"
    else:
        raise AssertionError("preview callback failure must be visible")
    assert session.preview_selection == accepted
    assert preview.calls[-1] == accepted


def assert_save_is_immutable_and_idempotent() -> None:
    commits = CommitRecorder()
    session = AppearanceSession(
        initial_selection(), Resolver(), PreviewRecorder(), commits
    )
    session.preview_slot("hairstyle", component("hair-pack", "braid"))
    session.preview_slot("foreground-effect", component("effect-pack", "glow"))

    first = session.save()
    second = session.save()
    assert isinstance(first, AppearanceCommit)
    assert first is second
    assert first.selection == session.preview_selection
    assert len(commits.calls) == 1
    assert not session.dirty
    try:
        first.selection.hairstyle.pack_id = "changed"  # type: ignore[misc]
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("commit payload must be immutable")


def assert_commit_failure_keeps_transaction_open() -> None:
    original = initial_selection()
    commits = CommitRecorder()
    session = AppearanceSession(
        original, Resolver(), PreviewRecorder(), commits
    )
    session.preview_slot("weapon", component("weapon-pack", "weapon-a"))
    commits.fail = True

    try:
        session.save()
    except RuntimeError as exc:
        assert str(exc) == "commit failed"
    else:
        raise AssertionError("commit callback failure must be visible")
    assert session.dirty
    assert session.active_package_ids == frozenset()
    assert session.preview_package_ids == frozenset({"weapon-pack"})


def assert_missing_pack_falls_back_explicitly() -> None:
    preview = PreviewRecorder()
    resolver = Resolver({("hairstyle", "missing-pack")})
    session = AppearanceSession(
        initial_selection(), resolver, preview, CommitRecorder()
    )
    resolved = session.preview_slot(
        "hairstyle", component("missing-pack", "lost-hair")
    )
    assert resolved.hairstyle == AppearanceComponent.builtin("hairstyle")
    assert session.status_for("hairstyle") == "missing_builtin_fallback"
    assert session.requested_selection.hairstyle.pack_id == "missing-pack"
    assert preview.calls[-1] == resolved


def assert_delete_guard_covers_every_active_and_preview_slot() -> None:
    original = initial_selection().replace(
        garment=component("active-garment", "garment"),
        jewelry=component("active-jewelry", "jewelry"),
    )
    session = AppearanceSession(
        original, Resolver(), PreviewRecorder(), CommitRecorder()
    )
    session.preview_slot("weapon", component("preview-weapon", "weapon"))
    session.preview_slot(
        "foreground-effect", component("preview-effect", "effect")
    )
    assert session.active_package_ids == frozenset(
        {"active-garment", "active-jewelry"}
    )
    assert session.preview_package_ids == frozenset(
        {
            "active-garment",
            "active-jewelry",
            "preview-weapon",
            "preview-effect",
        }
    )
    for protected in (
        "builtin",
        "active-garment",
        "active-jewelry",
        "preview-weapon",
        "preview-effect",
    ):
        assert not session.can_delete(protected)
    assert session.can_delete("unused-pack")


def assert_lifecycle_boundaries_clear_secondary_motion() -> None:
    dynamics = DynamicsResetRecorder()
    commits = CommitRecorder()
    preview = PreviewRecorder()
    session = AppearanceSession(
        initial_selection(), Resolver(), preview, commits, dynamics
    )
    session.preview_slot("weapon", component("weapon-pack", "weapon"))
    assert dynamics.calls == 1
    session.save()
    assert dynamics.calls == EXPECTED_CALLS_AFTER_SAVE
    session.cancel()
    assert dynamics.calls == EXPECTED_CALLS_AFTER_CANCEL

    session.preview_slot("handheld", component("handheld-pack", "handheld"))
    preview.fail_on = session.preview_selection.replace(
        jewelry=component("broken-pack", "jewelry")
    )
    try:
        session.preview_slot("jewelry", component("broken-pack", "jewelry"))
    except RuntimeError:
        pass
    else:
        raise AssertionError("preview failure must remain visible")
    assert dynamics.calls == EXPECTED_CALLS_AFTER_PREVIEW_FAILURE

    commits.fail = True
    try:
        session.save()
    except RuntimeError:
        pass
    else:
        raise AssertionError("save failure must remain visible")
    assert dynamics.calls == EXPECTED_CALLS_AFTER_SAVE_FAILURE


def run() -> None:
    assert ACTIVE_OUTFIT_SETTING_KEY == "active_outfit_id"
    assert AppearanceSession.setting_key == ACTIVE_OUTFIT_SETTING_KEY
    assert APPEARANCE_SLOTS == (
        "garment",
        "hairstyle",
        "headwear",
        "weapon",
        "handheld",
        "jewelry",
        "foreground-effect",
    )
    assert_state_transitions_and_multislot_mixing()
    assert_callback_failure_rolls_back_full_preview()
    assert_save_is_immutable_and_idempotent()
    assert_commit_failure_keeps_transaction_open()
    assert_missing_pack_falls_back_explicitly()
    assert_delete_guard_covers_every_active_and_preview_slot()
    assert_lifecycle_boundaries_clear_secondary_motion()
    print("APPEARANCE_SESSION_OK")


if __name__ == "__main__":
    run()
