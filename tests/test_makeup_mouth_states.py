"""Schema unit tests for domain.makeup_mouth_states.parse_mouth_states (INSTALL-1)."""

from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import pytest

lazy from domain.makeup_mouth_states import MOUTH_SHAPES, VISEME_TO_MOUTH_SHAPE, parse_mouth_states
lazy from domain.outfit_pack_assets import OutfitPackError


class _Asset:
    def __init__(self, slot: str, width: int = 1254, height: int = 1254, anchor: tuple[int, int] = (0, 0)) -> None:
        self.slot = slot
        self.width = width
        self.height = height
        self.anchor_x, self.anchor_y = anchor


def _poses(entries: dict[str, tuple[str, ...]]) -> dict[str, tuple[_Asset, ...]]:
    """Fake ``parse_poses``: entries maps a silhouette to the slots it declares."""
    return {silhouette: tuple(_Asset(slot) for slot in slots) for silhouette, slots in entries.items()}


def test_empty_mouth_states_parses_to_empty() -> None:
    assert parse_mouth_states({}, _poses, frozenset()) == frozendict()


def test_requires_exactly_the_three_shapes() -> None:
    with pytest.raises(OutfitPackError, match="a, o and small"):
        parse_mouth_states({"a": {}}, _poses, frozenset())


def test_viseme_to_shape_covers_every_speaking_viseme_and_omits_closed() -> None:
    assert set(VISEME_TO_MOUTH_SHAPE.values()) == MOUTH_SHAPES
    assert VISEME_TO_MOUTH_SHAPE.get("CLOSED") is None
    assert VISEME_TO_MOUTH_SHAPE["A"] == "a"
    assert VISEME_TO_MOUTH_SHAPE["O"] == "o"
    assert VISEME_TO_MOUTH_SHAPE["U"] == "o"
    assert VISEME_TO_MOUTH_SHAPE["CONSONANT"] == "small"


def _yaw_poses(entries: dict[str, tuple[str, ...]]) -> dict[str, tuple[_Asset, ...]]:
    """Like ``_poses`` but sized for the full-body 1024x1536 yaw canvas."""
    return {
        silhouette: tuple(_Asset(slot, width=1024, height=1536) for slot in slots)
        for silhouette, slots in entries.items()
    }


def test_lips_only_silhouette_accepts_a_lone_lips_layer() -> None:
    value = {
        shape: {"front-crossed": ("lips",)}
        for shape in ("a", "o", "small")
    }
    parsed = parse_mouth_states(value, _poses, frozenset())
    assert set(parsed) == {"a", "o", "small"}
    for shape_poses in parsed.values():
        assert {asset.slot for asset in shape_poses["front-crossed"]} == {"lips"}


def test_lips_only_silhouette_rejects_a_stray_foundation_layer() -> None:
    value = {
        shape: {"front-crossed": ("lips", "foundation")}
        for shape in ("a", "o", "small")
    }
    with pytest.raises(OutfitPackError, match="declared mouth layers"):
        parse_mouth_states(value, _poses, frozenset())


def test_foundation_silhouette_requires_both_lips_and_foundation_together() -> None:
    value = {
        shape: {"yaw+000-pitch+00": ("lips",)}
        for shape in ("a", "o", "small")
    }
    with pytest.raises(OutfitPackError, match="declared mouth layers"):
        parse_mouth_states(value, _yaw_poses, frozenset({"yaw+000-pitch+00"}))


def test_foundation_silhouette_accepts_the_paired_layers() -> None:
    value = {
        shape: {"yaw+000-pitch+00": ("lips", "foundation")}
        for shape in ("a", "o", "small")
    }
    parsed = parse_mouth_states(value, _yaw_poses, frozenset({"yaw+000-pitch+00"}))
    for shape_poses in parsed.values():
        assert {asset.slot for asset in shape_poses["yaw+000-pitch+00"]} == {"lips", "foundation"}


def test_shapes_must_cover_the_same_silhouettes() -> None:
    value = {
        "a": {"front-crossed": ("lips",)},
        "o": {"left-neutral": ("lips",)},
        "small": {"front-crossed": ("lips",)},
    }
    with pytest.raises(OutfitPackError, match="same silhouettes"):
        parse_mouth_states(value, _poses, frozenset())


def test_asset_must_cover_its_canvas_at_anchor_zero() -> None:
    def bad_poses(_entries: object) -> dict[str, tuple[_Asset, ...]]:
        return {"front-crossed": (_Asset("lips", width=999),)}

    value = {shape: {"front-crossed": ("lips",)} for shape in ("a", "o", "small")}
    with pytest.raises(OutfitPackError, match="anchor 0,0"):
        parse_mouth_states(value, bad_poses, frozenset())
