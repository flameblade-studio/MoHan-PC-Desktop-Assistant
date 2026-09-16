"""Runtime inventory and root identity contracts for the 24x25 PoseAtlas."""

from __future__ import annotations

lazy import re
lazy import shutil
lazy import json
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np
lazy import pytest

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from domain.constants import (
    FULL_BODY_LAYER_Z_ORDER,
    POSE_ATLAS_GENERATION,
    POSE_ATLAS_ROOT_NAME,
)
lazy from infrastructure import layered_full_body_assets as layered_assets
lazy from presentation.pose_atlas_assets import PoseAtlasAssets

ROOT = Path(__file__).resolve().parents[1]
LAYERED_ROOT = ROOT / "assets" / "pose-atlas" / "v5-base-layered"
CURRENT_ROOT = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_ROOT_NAME
ARCHIVED_V4_ROOT = ROOT / "assets" / "pose-atlas" / "v4"


def _copy_layers(root: Path, view_id: str, layers: set[str] | tuple[str, ...]) -> None:
    for layer in layers:
        shutil.copy2(
            LAYERED_ROOT / f"{view_id}_{layer}.png",
            root / f"{view_id}_{layer}.png",
        )


def _load_one_view(root: Path, view_id: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(layered_assets, "VIEW_IDS", (view_id,))
    return layered_assets.load_layered_full_body_assets(root)


@pytest.mark.parametrize("yaw", (-90, 0, 90))
def test_visible_view_missing_any_of_twenty_five_layers_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    yaw: int,
) -> None:
    """Front and profile boundary views require their complete layer sets."""

    view_id = canonical_view_id(yaw)
    _copy_layers(tmp_path, view_id, FULL_BODY_LAYER_Z_ORDER)
    for missing_layer in FULL_BODY_LAYER_Z_ORDER:
        missing_path = tmp_path / f"{view_id}_{missing_layer}.png"
        missing_path.unlink()
        with pytest.raises(FileNotFoundError, match=re.escape(missing_path.name)):
            _load_one_view(tmp_path, view_id, monkeypatch)
        shutil.copy2(
            LAYERED_ROOT / missing_path.name,
            missing_path,
        )


@pytest.mark.parametrize("yaw", (-180, -105, 105, 165))
def test_rear_view_keeps_seven_required_layers_and_allows_missing_face_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    yaw: int,
) -> None:
    """Back-facing views retain the established transparent-face exception."""

    view_id = canonical_view_id(yaw)
    _copy_layers(tmp_path, view_id, layered_assets.REQUIRED_LAYERS)
    manifest = _load_one_view(tmp_path, view_id, monkeypatch)
    assert set(manifest.view(view_id).layers) == set(layered_assets.REQUIRED_LAYERS)


def test_all_twenty_five_transparent_png_layers_are_valid_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Presence and canvas validity, rather than opacity, define inventory."""

    view_id = canonical_view_id(0)
    transparent = np.zeros(
        (layered_assets.FULL_BODY_DIMENSION_HEIGHT,
         layered_assets.FULL_BODY_DIMENSION_WIDTH,
         layered_assets.RGBA_CHANNELS),
        dtype=np.uint8,
    )
    source = tmp_path / "transparent.png"
    assert cv2.imwrite(str(source), transparent)
    for layer in FULL_BODY_LAYER_Z_ORDER:
        shutil.copy2(source, tmp_path / f"{view_id}_{layer}.png")

    manifest = _load_one_view(tmp_path, view_id, monkeypatch)
    assert set(manifest.view(view_id).layers) == set(FULL_BODY_LAYER_Z_ORDER)


def test_current_canonical_root_constructs() -> None:
    assets = PoseAtlasAssets(CURRENT_ROOT, image_size=1)

    assert assets.generation == POSE_ATLAS_GENERATION
    assert assets.view_ids


@pytest.mark.parametrize("wrong_root_kind", ("archived-v4", "custom-metadata"))
def test_noncanonical_pose_atlas_root_is_rejected_before_runtime_load(
    tmp_path: Path,
    wrong_root_kind: str,
) -> None:
    if wrong_root_kind == "archived-v4":
        wrong_root = ARCHIVED_V4_ROOT
    else:
        wrong_root = tmp_path / "custom-pose-atlas"
        wrong_root.mkdir()
        shutil.copy2(
            CURRENT_ROOT / "BUILD-METADATA.json",
            wrong_root / "BUILD-METADATA.json",
        )

    with pytest.raises(ValueError, match="(canonical|current|generation|root)"):
        PoseAtlasAssets(wrong_root, image_size=1)


def _metadata_payload() -> dict[str, object]:
    return json.loads(
        (CURRENT_ROOT / "BUILD-METADATA.json").read_text(encoding="utf-8")
    )


def _load_metadata_probe(root: Path) -> dict[str, object]:
    probe = object.__new__(PoseAtlasAssets)
    probe._root = root
    return probe._load_metadata()


def _write_metadata_probe(root: Path, payload: object) -> dict[str, object]:
    metadata_root = root / "metadata"
    metadata_root.mkdir()
    (metadata_root / "BUILD-METADATA.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    return _load_metadata_probe(metadata_root)


@pytest.mark.parametrize(
    "invalid_case",
    (
        "duplicate-record",
        "noncanonical-view",
        "missing-view-id",
        "wrong-record-type",
        "yaw-view-mismatch",
        "bool-yaw",
        "noninteger-yaw",
    ),
)
def test_pose_atlas_metadata_rejects_invalid_canonical_ring_records(
    tmp_path: Path,
    invalid_case: str,
) -> None:
    payload = _metadata_payload()
    records = payload["views"]
    assert isinstance(records, list)
    if invalid_case == "duplicate-record":
        payload["views"] = [dict(records[0]) for _ in range(24)]
    elif invalid_case == "noncanonical-view":
        record = dict(records[0])
        record["view_id"] = "yaw+007-pitch+00"
        records[0] = record
    elif invalid_case == "missing-view-id":
        record = dict(records[0])
        record.pop("view_id")
        records[0] = record
    elif invalid_case == "wrong-record-type":
        records[0] = "not-a-view-record"
    elif invalid_case == "yaw-view-mismatch":
        record = dict(records[0])
        record["yaw_degrees"] = 0
        records[0] = record
    elif invalid_case == "bool-yaw":
        record = dict(records[0])
        record["yaw_degrees"] = True
        records[0] = record
    else:
        record = dict(records[0])
        record["yaw_degrees"] = "-180"
        records[0] = record

    with pytest.raises(ValueError):
        _write_metadata_probe(tmp_path, payload)


def test_pose_atlas_metadata_rejects_non_dict_top_level(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _write_metadata_probe(tmp_path, ["not", "an", "object"])


def test_pose_atlas_metadata_accepts_complete_canonical_ring_in_any_order(
    tmp_path: Path,
) -> None:
    payload = _metadata_payload()
    records = payload["views"]
    assert isinstance(records, list)
    payload["views"] = list(reversed(records))

    loaded = _write_metadata_probe(tmp_path, payload)
    loaded_records = loaded["views"]
    assert isinstance(loaded_records, list)
    assert {
        record["view_id"]
        for record in loaded_records
        if isinstance(record, dict)
    } == {canonical_view_id(yaw) for yaw in CANONICAL_YAWS}


def test_pose_atlas_metadata_current_formal_root_still_loads() -> None:
    loaded = _load_metadata_probe(CURRENT_ROOT)
    records = loaded["views"]

    assert isinstance(records, list)
    assert len(records) == len(CANONICAL_YAWS)
