"""Consumer screenshot baseline checks, one test per fixed scene."""

from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy import pytest
lazy from tools.render_visual_baseline import (
    QtUnavailableError,
    check_baseline,
    scene_specs,
)


def _assert_scene(scene: str) -> None:
    if scene not in {spec.name for spec in scene_specs()}:
        pytest.skip(f"runtime does not expose visual scene {scene}")
    try:
        reports = check_baseline((scene,))
    except QtUnavailableError as exc:
        pytest.skip(str(exc))
    assert len(reports) == 1
    report = reports[0]
    assert report.error is None, report.error
    assert report.passed, report
    assert report.difference_pixels == 0
    assert report.difference_ratio == 0.0
    assert report.max_difference_block_area == 0
    assert report.max_difference_bbox is None


def test_idle_front() -> None:
    _assert_scene("idle_front")


def test_speaking_open() -> None:
    _assert_scene("speaking_open")


def test_speaking_closed() -> None:
    _assert_scene("speaking_closed")


def test_blink_closed() -> None:
    _assert_scene("blink_closed")


def test_head_crop() -> None:
    _assert_scene("head_crop")


def test_yaw_plus_030() -> None:
    _assert_scene("yaw+030")


def test_yaw_minus_030() -> None:
    _assert_scene("yaw-030")


def main() -> int:
    return pytest.main([str(Path(__file__).resolve()), "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
