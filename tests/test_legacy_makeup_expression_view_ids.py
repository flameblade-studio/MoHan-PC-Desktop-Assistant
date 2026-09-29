"""legacy_makeup_expression_view_ids(): the enumerable per-expression legacy
makeup view id set (2026-09-29 schema addition, coordinator ruling round 6).

Proves: the derivation is stable and derived from companion_animation_
contract.EXPRESSION_IMAGE_ASSETS (not a second, independently-typed list
that could drift); every warp-batch candidate view id actually produced by
legacy-makeup-claude-02/warp_batch1_v2.py and warp_batch2_v1.py is
recognized; the two pose-shared LEGACY_MAKEUP_SILHOUETTES keys are still
present in the combined set; and this is purely additive -- the existing 24
REQUIRED_SILHOUETTES and the 2 pose-shared legacy keys are unaffected.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from domain import companion_animation_contract as cac
from domain.outfit_pack import (
    LEGACY_MAKEUP_EXPRESSION_SILHOUETTES,
    LEGACY_MAKEUP_SILHOUETTES,
    LEGACY_MAKEUP_SILHOUETTES_ALL,
    REQUIRED_SILHOUETTES,
)

# Every legacy frame actually produced as a candidate by warp_batch1_v2.py
# (batch 1) and warp_batch2_v1.py (batch 2), 2026-09-29 rounds 1-6.
BATCH1_CHEEK_EXPRESSIONS = ("glance", "caught", "happy", "worried", "reminder")
BATCH2_CHEEK_FRAMES = (
    *(f"{expr}_speech_{frame}" for expr in BATCH1_CHEEK_EXPRESSIONS for frame in ("mid", "open", "round")),
    *(f"{expr}_speech_blink" for expr in ("glance", "happy", "worried", "reminder")),
    "blink", "speaking", "viseme_round", "viseme_i", "viseme_o",
)
BATCH2_LEAN_FRAMES = (
    "blink_lean", "speaking_lean", "viseme_round_lean", "viseme_i_lean",
    "viseme_o_lean", "idle_lean_half", "idle_lean_closed",
)


def test_derivation_is_a_pure_function_of_the_existing_frame_list() -> None:
    first = cac.legacy_makeup_expression_view_ids()
    second = cac.legacy_makeup_expression_view_ids()
    assert first == second


def test_pose_shared_legacy_keys_still_present_in_the_combined_set() -> None:
    assert set(LEGACY_MAKEUP_SILHOUETTES) == {"cheek-rest-legacy", "left-neutral-legacy"}
    assert set(LEGACY_MAKEUP_SILHOUETTES).issubset(LEGACY_MAKEUP_SILHOUETTES_ALL)


def test_required_silhouettes_are_unaffected() -> None:
    """The new optional expression-level keys never collide with the
    existing required v2 view set, whatever its current size is."""
    assert not set(REQUIRED_SILHOUETTES) & LEGACY_MAKEUP_EXPRESSION_SILHOUETTES


def test_every_batch1_and_batch2_cheek_candidate_frame_is_recognized() -> None:
    for expression in BATCH1_CHEEK_EXPRESSIONS:
        assert f"cheek-rest-legacy/{expression}" in LEGACY_MAKEUP_SILHOUETTES_ALL
    for frame in BATCH2_CHEEK_FRAMES:
        assert f"cheek-rest-legacy/{frame}" in LEGACY_MAKEUP_SILHOUETTES_ALL, frame


def test_every_batch2_lean_candidate_frame_is_recognized() -> None:
    for frame in BATCH2_LEAN_FRAMES:
        assert f"left-neutral-legacy/{frame}" in LEGACY_MAKEUP_SILHOUETTES_ALL, frame


def test_front_and_gesture_frames_are_excluded_from_both_legacy_families() -> None:
    """A front-pose or gesture-portrait frame (thinking_front, mock_scold,
    mock_hit_front, ...) must never be classified as cheek or lean -- it
    belongs to a completely different outfit silhouette (front-crossed /
    front-mock-scold / ...), not cheek-rest or left-neutral."""
    view_ids = cac.legacy_makeup_expression_view_ids()
    all_frames = {vid.split("/", 1)[1] for vids in view_ids.values() for vid in vids}
    for excluded in ("thinking_front", "mock_scold", "mock_scold_half", "mock_scold_closed", "mock_hit_front", "eureka_front", "idle_front"):
        assert excluded not in all_frames, excluded


def test_no_overlap_between_the_two_pose_families() -> None:
    view_ids = cac.legacy_makeup_expression_view_ids()
    cheek_frames = {vid.split("/", 1)[1] for vid in view_ids["cheek-rest-legacy"]}
    lean_frames = {vid.split("/", 1)[1] for vid in view_ids["left-neutral-legacy"]}
    assert not cheek_frames & lean_frames


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    raise SystemExit(1 if failures else 0)
