"""Validate character-owned semantic roles and runtime asset paths."""

from __future__ import annotations

lazy import json
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath


RUNTIME_BINDINGS_SCHEMA = "flameblade.character-runtime-bindings.v1"
RUNTIME_BINDINGS_VERSION = 1

_ROOT_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "asset_paths",
        "pose_roles",
        "expression_roles",
        "layer_roles",
    }
)
_SECTION_KEYS = frozendict(
    {
        "asset_paths": frozenset(
            {
                "application_icon",
                "appearance_masks",
                "appearance_silhouettes",
                "body_overlays",
                "dashboard_artwork",
                "first_run_portrait",
                "garment_visibility",
                "halfbody_detachable",
                "halfbody_layers",
                "halfbody_root",
                "hand_overlays",
                "lobby_backdrop",
                "onboarding_artwork",
                "source_bound_expression",
                "theme_artwork",
            }
        ),
        "pose_roles": frozenset(
            {
                "front_idle",
                "left_cheek",
                "left_idle",
                "rear_full",
                "rear_left",
                "rear_right",
                "right_idle",
            }
        ),
        "expression_roles": frozenset(
            {
                "amusement",
                "attention",
                "bashful",
                "bashful_cute",
                "concern",
                "exasperation",
                "gentle",
                "gentle_scold",
                "happiness",
                "insight",
                "mock_strike",
                "noticed",
                "pride",
                "protection",
                "relief",
                "reminder",
                "resolve",
                "side_gaze",
                "surprise",
                "thought",
                "worry",
            }
        ),
        "layer_roles": frozenset(
            {
                "left_blush",
                "left_brow",
                "left_eyelid",
                "left_eyeliner",
                "left_iris",
                "left_mouth_corner",
                "left_side_hair",
                "left_sleeve",
                "lower_lip",
                "mouth_cavity",
                "rear_hair",
                "right_blush",
                "right_brow",
                "right_eyelid",
                "right_eyeliner",
                "right_iris",
                "right_mouth_corner",
                "right_side_hair",
                "right_sleeve",
                "teeth_and_tongue",
                "upper_lip",
            }
        ),
    }
)


@dataclass(frozen=True, slots=True)
class CharacterRuntimeBindings:
    """Immutable character mappings consumed by engine runtime policy."""

    asset_paths: frozendict[str, str]
    pose_roles: frozendict[str, str]
    expression_roles: frozendict[str, str]
    layer_roles: frozendict[str, str]


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate runtime-binding field: {key}")
        result[key] = value
    return result


def load_character_runtime_bindings(path: Path) -> CharacterRuntimeBindings:
    """Load one strict UTF-8 runtime-binding document."""

    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise RuntimeError("Character runtime bindings must be valid UTF-8 JSON.") from error
    if (
        not isinstance(payload, dict)
        or set(payload) != _ROOT_KEYS
        or payload.get("schema") != RUNTIME_BINDINGS_SCHEMA
        or payload.get("schema_version") != RUNTIME_BINDINGS_VERSION
    ):
        raise RuntimeError("Character runtime bindings use an unsupported schema.")
    sections: dict[str, frozendict[str, str]] = {}
    for section, expected_keys in _SECTION_KEYS.items():
        values = payload[section]
        if (
            not isinstance(values, dict)
            or set(values) != expected_keys
            or any(
                not isinstance(key, str)
                or not key
                or not isinstance(value, str)
                or not value
                for key, value in values.items()
            )
        ):
            raise RuntimeError("Character runtime bindings require complete non-empty text maps.")
        sections[section] = frozendict(values)
    for value in sections["asset_paths"].values():
        relative = PurePosixPath(value)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
            or "\\" in value
        ):
            raise RuntimeError("Character asset paths must remain canonical relative paths.")
    return CharacterRuntimeBindings(
        asset_paths=sections["asset_paths"],
        pose_roles=sections["pose_roles"],
        expression_roles=sections["expression_roles"],
        layer_roles=sections["layer_roles"],
    )


__all__ = (
    "RUNTIME_BINDINGS_SCHEMA",
    "RUNTIME_BINDINGS_VERSION",
    "CharacterRuntimeBindings",
    "load_character_runtime_bindings",
)
