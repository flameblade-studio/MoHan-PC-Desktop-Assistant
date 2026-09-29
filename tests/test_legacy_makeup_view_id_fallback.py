"""select_legacy_makeup_view_id(): the three-tier legacy makeup fallback
(2026-09-29, coordinator ruling round 9) that infrastructure/
layered_face_renderer.py's render() consults whenever the composed frame may
need legacy makeup (native_neutral / gesture portrait sources).

Extracted as a pure function specifically so each tier can be proven in
isolation with a plain stub ``declares_view`` callable, with no renderer,
Qt, or real outfit pack fixture required.

Tier order (highest priority first):
  1. "<silhouette>-legacy/<expression>"  (single-frame candidate)
  2. "<silhouette>-legacy"               (pose-shared, pre-existing key)
  3. None                                (current behaviour, unaffected)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from infrastructure.layered_face_renderer import select_legacy_makeup_view_id


def test_tier1_prefers_the_single_expression_key_when_declared() -> None:
    """Both the expression key and the pose-shared key are declared: tier 1
    wins, and declares_view is never even asked about tier 2."""
    asked: list[str] = []

    def declares(view_id: str) -> bool:
        asked.append(view_id)
        return view_id in {"cheek-rest-legacy/glance", "cheek-rest-legacy"}

    result = select_legacy_makeup_view_id(declares, "cheek-rest", "glance")
    assert result == "cheek-rest-legacy/glance"
    assert asked == ["cheek-rest-legacy/glance"]


def test_tier2_falls_back_to_the_pose_shared_key() -> None:
    """Only the pose-shared key is declared (every currently-shipped pack):
    tier 2 applies, unchanged from before this addition."""

    def declares(view_id: str) -> bool:
        return view_id == "cheek-rest-legacy"

    result = select_legacy_makeup_view_id(declares, "cheek-rest", "glance")
    assert result == "cheek-rest-legacy"


def test_tier3_falls_back_to_none_when_neither_key_is_declared() -> None:
    """Neither key declared (e.g. the builtin makeup, or any pack authored
    before this schema addition): current behaviour, makeup_view_id stays
    None and the caller's own silhouette makeup resolution applies."""
    result = select_legacy_makeup_view_id(lambda _view_id: False, "cheek-rest", "glance")
    assert result is None


def test_missing_declares_view_capability_is_tier3_too() -> None:
    """An outfit overlay without makeup_declares_view at all (getattr
    returns None at the call site) must resolve to the same tier-3 fallback,
    never raise."""
    assert select_legacy_makeup_view_id(None, "cheek-rest", "glance") is None


def test_left_neutral_and_per_expression_keys_are_independent() -> None:
    """A pack declaring only left-neutral-legacy/blink_lean must not leak
    into a cheek-rest lookup for a different expression."""

    def declares(view_id: str) -> bool:
        return view_id == "left-neutral-legacy/blink_lean"

    assert select_legacy_makeup_view_id(declares, "left-neutral", "blink_lean") == "left-neutral-legacy/blink_lean"
    assert select_legacy_makeup_view_id(declares, "cheek-rest", "blink_lean") is None
    assert select_legacy_makeup_view_id(declares, "left-neutral", "idle_lean") is None


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
