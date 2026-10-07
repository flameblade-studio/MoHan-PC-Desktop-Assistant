"""Acceptance and hostile-input checks for character-owned runtime data."""

from __future__ import annotations

lazy import copy
lazy import json
lazy from pathlib import Path

lazy import pytest

lazy from domain.character_runtime_data import (
    DEFAULT_EXPRESSION_CATALOG_PATH,
    DEFAULT_RIG_MANIFEST_PATH,
    default_expression_catalog,
    default_rig_manifest,
    load_expression_catalog,
    load_rig_manifest,
)

EXPECTED_VIEW_COUNT = 24
EXPECTED_LAYER_COUNT = 25
EXPECTED_POSE_COUNT = 7
EXPECTED_EXPRESSION_COUNT = 22


def _payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_payload(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_bundled_runtime_data_preserves_the_accepted_contract() -> None:
    rig = default_rig_manifest()
    expressions = default_expression_catalog()

    assert rig.character_id == expressions.character_id == "flameblade.mohan"
    assert (rig.body_profile_id, rig.body_profile_version) == ("mohan-body-v2", 2)
    assert (rig.full_body_canvas.width, rig.full_body_canvas.height) == (1024, 1536)
    assert len(rig.view_ring.yaws) == EXPECTED_VIEW_COUNT
    assert len(rig.layer_z_order) == EXPECTED_LAYER_COUNT
    assert len(rig.poses) == EXPECTED_POSE_COUNT
    assert set(expressions.face_pose_assets) == {"cheek", "lean", "front"}
    assert len(expressions.state_to_pose) == EXPECTED_EXPRESSION_COUNT


def test_default_runtime_data_is_read_once_and_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = Path.read_text
    reads: list[Path] = []

    def tracked_read_text(path: Path, *args, **kwargs) -> str:
        reads.append(path)
        return original(path, *args, **kwargs)

    default_rig_manifest.cache_clear()
    default_expression_catalog.cache_clear()
    monkeypatch.setattr(Path, "read_text", tracked_read_text)

    rig = default_rig_manifest()
    expressions = default_expression_catalog()
    assert default_rig_manifest() is rig
    assert default_expression_catalog() is expressions
    assert reads == [DEFAULT_RIG_MANIFEST_PATH, DEFAULT_EXPRESSION_CATALOG_PATH]


@pytest.mark.parametrize(
    ("source", "loader"),
    [
        (DEFAULT_RIG_MANIFEST_PATH, load_rig_manifest),
        (DEFAULT_EXPRESSION_CATALOG_PATH, load_expression_catalog),
    ],
)
def test_runtime_data_rejects_unknown_fields(
    tmp_path: Path,
    source: Path,
    loader,
) -> None:
    payload = _payload(source)
    payload["unexpected"] = True
    candidate = tmp_path / source.name
    _write_payload(candidate, payload)

    with pytest.raises(ValueError, match="must contain exactly"):
        loader(candidate)


@pytest.mark.parametrize("invalid_version", [True, 2])
def test_runtime_data_rejects_invalid_schema_versions(
    tmp_path: Path,
    invalid_version: object,
) -> None:
    payload = _payload(DEFAULT_RIG_MANIFEST_PATH)
    payload["schema_version"] = invalid_version
    candidate = tmp_path / "rig.json"
    _write_payload(candidate, payload)

    with pytest.raises(ValueError, match="schema_version|unsupported"):
        load_rig_manifest(candidate)


def test_runtime_data_rejects_duplicate_keys(tmp_path: Path) -> None:
    text = DEFAULT_EXPRESSION_CATALOG_PATH.read_text(encoding="utf-8")
    duplicate = text.replace(
        '  "schema_version": 1,',
        '  "schema_version": 1,\n  "schema_version": 1,',
        1,
    )
    candidate = tmp_path / "expressions.json"
    candidate.write_text(duplicate, encoding="utf-8")

    with pytest.raises(ValueError, match="strict JSON"):
        load_expression_catalog(candidate)


def test_rig_rejects_asymmetric_mirror_views(tmp_path: Path) -> None:
    payload = copy.deepcopy(_payload(DEFAULT_RIG_MANIFEST_PATH))
    mirrors = payload["full_body"]["view_ring"]["mirror_views"]
    mirrors["yaw-015-pitch+00"] = "yaw-015-pitch+00"
    candidate = tmp_path / "rig.json"
    _write_payload(candidate, payload)

    with pytest.raises(ValueError, match="exactly once|symmetric"):
        load_rig_manifest(candidate)


def test_expression_catalog_rejects_unknown_pose(tmp_path: Path) -> None:
    payload = copy.deepcopy(_payload(DEFAULT_EXPRESSION_CATALOG_PATH))
    payload["state_to_pose"]["glance"] = "unknown-pose"
    candidate = tmp_path / "expressions.json"
    _write_payload(candidate, payload)

    with pytest.raises(ValueError, match="declared face pose"):
        load_expression_catalog(candidate)


def test_missing_runtime_data_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Cannot read character data"):
        load_rig_manifest(tmp_path / "missing.json")
