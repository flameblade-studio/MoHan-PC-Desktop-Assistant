"""Pose-shared legacy makeup-key selection."""
from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from infrastructure.layered_face_renderer import select_legacy_makeup_view_id


def test_declared_pose_shared_key_is_selected() -> None:
    asked: list[str] = []

    def declares(view_id: str) -> bool:
        asked.append(view_id)
        return view_id == "cheek-rest-legacy"

    result = select_legacy_makeup_view_id(declares, "cheek-rest")
    assert result == "cheek-rest-legacy"
    assert asked == ["cheek-rest-legacy"]


def test_undeclared_pose_shared_key_falls_back_to_none() -> None:
    result = select_legacy_makeup_view_id(lambda _view_id: False, "cheek-rest")
    assert result is None


def test_missing_declares_view_capability_falls_back_to_none() -> None:
    assert select_legacy_makeup_view_id(None, "cheek-rest") is None


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
