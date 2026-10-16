"""Acceptance and hostile-input checks for character-owned runtime data."""

from __future__ import annotations

lazy import copy
lazy import json
lazy from pathlib import Path

lazy import pytest

lazy from domain import character_data_types as compatibility_types
lazy from domain.character_pack import character_data_models
lazy from domain.character_pack.character_data import CharacterDataError
lazy from domain.character_runtime_data import (
    DEFAULT_EXPRESSION_CATALOG_PATH,
    DEFAULT_RIG_MANIFEST_PATH,
    default_expression_catalog,
    default_rig_manifest,
    load_expression_catalog,
    load_rig_manifest,
)
lazy from domain.constants import (
    CHARACTER_ASSET_PATHS,
    CHARACTER_EXPRESSION_ROLES,
    CHARACTER_LAYER_ROLES,
    CHARACTER_POSE_ROLES,
)

EXPECTED_VIEW_COUNT = 24
EXPECTED_LAYER_COUNT = 25
EXPECTED_POSE_COUNT = 7
EXPECTED_EXPRESSION_COUNT = 22


def test_legacy_type_path_reexports_canonical_character_pack_contracts() -> None:
    assert compatibility_types.CharacterDataError is character_data_models.CharacterDataError
    assert compatibility_types.CharacterRigManifest is character_data_models.CharacterRigManifest
    assert compatibility_types.ExpressionStateCatalog is character_data_models.ExpressionStateCatalog
    assert compatibility_types.CanvasSpec is character_data_models.CanvasSpec


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


def test_bundled_runtime_bindings_preserve_existing_assets_and_role_values() -> None:
    rig = default_rig_manifest()

    assert dict(CHARACTER_POSE_ROLES) == {
        "front_idle": "front-crossed",
        "left_cheek": "left-cheek-rest",
        "left_idle": "left-neutral",
        "rear_full": "back-full",
        "rear_left": "back-two-thirds-left",
        "rear_right": "back-two-thirds-right",
        "right_idle": "right-neutral",
    }
    assert dict(CHARACTER_EXPRESSION_ROLES) == {
        "amusement": "restrained_amused_front",
        "attention": "attentive_front",
        "bashful": "shy_front",
        "bashful_cute": "shy_cute_front",
        "concern": "worried_front",
        "exasperation": "exasperated_front",
        "gentle": "gentle_smile_front",
        "gentle_scold": "mock_scold",
        "happiness": "happy",
        "insight": "eureka_front",
        "mock_strike": "mock_hit_front",
        "noticed": "caught",
        "pride": "proud_front",
        "protection": "protective_front",
        "relief": "relieved_front",
        "reminder": "reminder",
        "resolve": "determined_front",
        "side_gaze": "glance",
        "surprise": "surprised_front",
        "thought": "thinking_front",
        "worry": "worried",
    }
    assert dict(CHARACTER_LAYER_ROLES) == {
        "left_blush": "blush_left",
        "left_brow": "brow_left",
        "left_eyelid": "eyelid_left",
        "left_eyeliner": "eyeliner_left",
        "left_iris": "iris_left",
        "left_mouth_corner": "corner_left",
        "left_side_hair": "hair_left",
        "left_sleeve": "sleeve_left",
        "lower_lip": "lip_lower",
        "mouth_cavity": "oral_cavity",
        "rear_hair": "hair_back",
        "right_blush": "blush_right",
        "right_brow": "brow_right",
        "right_eyelid": "eyelid_right",
        "right_eyeliner": "eyeliner_right",
        "right_iris": "iris_right",
        "right_mouth_corner": "corner_right",
        "right_side_hair": "hair_right",
        "right_sleeve": "sleeve_right",
        "teeth_and_tongue": "teeth_tongue",
        "upper_lip": "lip_upper",
    }
    assert set(CHARACTER_LAYER_ROLES.values()) == (
        set(rig.layer_z_order) - {"body", "base", "jaw", "ornament"}
    )
    assert dict(CHARACTER_ASSET_PATHS) == {
        "application_icon": "assets/mohan-halfbody.ico",
        "appearance_masks": "assets/pose-atlas/v5-appearance-replacement-masks",
        "appearance_silhouettes": "assets/pose-atlas/v5-appearance-silhouettes",
        "body_overlays": "assets/pose-atlas/v5-body-overlays",
        "dashboard_artwork": "assets/ui/mohan-celestial-palace-v1.png",
        "first_run_portrait": "assets/expressions/idle_front.png",
        "garment_visibility": "assets/pose-atlas/v5-garment-visibility",
        "halfbody_detachable": "assets/expressions/detachable",
        "halfbody_layers": "assets/expressions/layered",
        "halfbody_root": "assets/expressions",
        "hand_overlays": "assets/pose-atlas/v5-hand-overlays",
        "lobby_backdrop": "assets/ui/mohan-strategist-lobby-v1.png",
        "onboarding_artwork": "assets/onboarding/first-run-ink-tech.png",
        "source_bound_expression": "assets/expressions/source-bound-exasperated",
        "theme_artwork": "assets/ui/mohan-cloud.svg",
    }
    required_paths = {
        key: path
        for key, path in CHARACTER_ASSET_PATHS.items()
        if key != "halfbody_detachable"
    }
    assert all(Path(path).exists() for path in required_paths.values())


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

    with pytest.raises(CharacterDataError, match="strict JSON"):
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
    with pytest.raises(CharacterDataError, match="Cannot read character data"):
        load_rig_manifest(tmp_path / "missing.json")
