"""Build source-bound visible-observation measurements for the pose atlas.

Every binding is validated against real bytes before anything is measured: the
canvas from the PNG ``IHDR``, the canvas declared by ``artifact.size``, the
478x3 point shape, finiteness, the artifact path, the artifact's own source
link, the sidecar declaration, and the metadata declaration. A mismatch stops
the run with exit code 2 and writes no report; ``--diagnose-drift`` reports the
same checks as findings instead.

The report separates four things that were previously merged:

* canonical fields measured from visible observations,
* canonical fields withheld because a required vertex was not visible,
* canonical fields with no authorized source,
* non-canonical image-outline diagnostics,

plus a declared-versus-measured height block, and it hands the field records to
``domain.visible_identity_audit`` for the versioned verdicts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from domain.character_identity_audit import (  # noqa: E402
    expected_visibility,
)
from domain.visible_identity_audit import (  # noqa: E402
    BAND_FIELDS,
    SCHEMA as AUDIT_SCHEMA,
    FieldStatus,
    VisibleFieldRecord,
    VisibleViewRecord,
    audit_visible_identity,
)
from tools import identity_geometry as geometry  # noqa: E402

SCHEMA = "mohan.pose-atlas-visible-identity-measurements.v1"
ATLAS_RELATIVE = Path("assets/pose-atlas/v5-base")
LAYERED_RELATIVE = Path("assets/pose-atlas/v5-base-layered")
OCCLUDER_LAYERS = ("hair_back", "hair_left", "hair_right", "ornament")
SKIN_LAYERS = ("base", "jaw")
AXIS_INDEX = {"x": 0, "y": 1, "z": 2}
FEATURE_LAYERS = (
    "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right",
)
ALPHA_THRESHOLDS = (("nonzero", 0), ("semi", 128), ("opaque", 250))
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_IHDR_LENGTH = 13
PNG_RGBA_COLOR_TYPE = 6
PNG_BIT_DEPTH = 8


class SourceContractError(ValueError):
    """A declared source binding does not match the bytes on disk."""


def view_id(yaw: int) -> str:
    return f"yaw{yaw:+04d}-pitch+00"


def yaws() -> tuple[int, ...]:
    from domain.character_pose import CANONICAL_YAWS

    return tuple(CANONICAL_YAWS)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise SourceContractError(f"missing json: {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SourceContractError(f"invalid json: {path.name}") from error


def png_canvas(path: Path) -> tuple[int, int]:
    """Read the canvas from the PNG header after verifying its checksum."""

    data = path.read_bytes()
    header_end = len(PNG_SIGNATURE) + 8 + PNG_IHDR_LENGTH + 4
    if len(data) < header_end or not data.startswith(PNG_SIGNATURE):
        raise SourceContractError(f"{path.name} is not a PNG")
    if struct.unpack(">I", data[8:12])[0] != PNG_IHDR_LENGTH or data[12:16] != b"IHDR":
        raise SourceContractError(f"{path.name} has no leading IHDR")
    ihdr = data[16:29]
    expected = struct.unpack(">I", data[29:33])[0]
    if zlib.crc32(b"IHDR" + ihdr) & 0xFFFFFFFF != expected:
        raise SourceContractError(f"{path.name} has an invalid IHDR checksum")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", ihdr
    )
    if depth != PNG_BIT_DEPTH or color != PNG_RGBA_COLOR_TYPE:
        raise SourceContractError(f"{path.name} is not 8-bit RGBA")
    if compression or filtering or interlace not in {0, 1}:
        raise SourceContractError(f"{path.name} uses unsupported PNG fields")
    if width <= 0 or height <= 0:
        raise SourceContractError(f"{path.name} has an invalid canvas")
    return int(width), int(height)


def alpha_mask(path: Path, threshold: int = 0) -> np.ndarray:
    with Image.open(path) as image:
        rgba = np.asarray(image.convert("RGBA"))
    return rgba[..., 3] > threshold


def validate_points(artifact: dict, name: str) -> np.ndarray:
    points = artifact.get("landmarks")
    if not isinstance(points, list) or len(points) != geometry.EXPLICIT_MESH_POINT_COUNT:
        raise SourceContractError(f"{name} artifact does not hold 478 points")
    array = np.empty((geometry.EXPLICIT_MESH_POINT_COUNT, 3), dtype=float)
    for position, point in enumerate(points):
        if not isinstance(point, dict) or not {"x", "y", "z"} <= set(point):
            raise SourceContractError(
                f"{name} artifact point {position} lacks x/y/z"
            )
        for axis, index in AXIS_INDEX.items():
            value = point[axis]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise SourceContractError(
                    f"{name} artifact point {position}.{axis} is not a finite number"
                )
            array[position, index] = float(value)
    return array


def _declaration_problems(
    name: str,
    yaw: int,
    canvas: tuple[int, int],
    png_sha: str,
    sidecar_sha: str,
    sidecar: dict,
    metadata_record: dict,
) -> list[str]:
    face = sidecar["native_face_landmarks"]
    relative_png = (ATLAS_RELATIVE / f"{name}.png").as_posix()
    checks = (
        (metadata_record.get("normalized_sha256") == png_sha, "metadata_png_sha_mismatch"),
        (metadata_record.get("body_sidecar_sha256") == sidecar_sha,
         "metadata_sidecar_sha_mismatch"),
        (sidecar.get("view_id") == name, "sidecar_view_id_mismatch"),
        (int(sidecar.get("yaw_degrees", 10_000)) == yaw, "sidecar_yaw_mismatch"),
        (list(canvas) == [int(sidecar.get("width", -1)), int(sidecar.get("height", -1))],
         "sidecar_canvas_mismatch"),
        (face.get("source", {}).get("path") == relative_png,
         "sidecar_face_source_path_mismatch"),
        (face.get("source", {}).get("sha256") == png_sha, "sidecar_face_source_sha_mismatch"),
        (metadata_record.get("native_face", {}).get("landmark_count")
         == face.get("landmark_count"), "metadata_native_face_count_mismatch"),
        (metadata_record.get("native_face", {}).get("source_sha256") == png_sha,
         "metadata_native_face_sha_mismatch"),
        (face.get("landmark_count") in {0, geometry.EXPLICIT_MESH_POINT_COUNT},
         "unsupported_landmark_count"),
    )
    return [message for condition, message in checks if not condition]


def _read_artifact(
    artifact_path: Path,
    name: str,
    canvas: tuple[int, int],
    png_sha: str,
    declared_path: object,
    declared_sha: object,
    problems: list[str],
) -> tuple[str | None, np.ndarray | None]:
    relative_png = (ATLAS_RELATIVE / f"{name}.png").as_posix()
    if declared_path != (ATLAS_RELATIVE / artifact_path.name).as_posix():
        problems.append("artifact_path_mismatch")
    if not artifact_path.is_file():
        problems.append("artifact_missing")
        return None, None
    artifact_sha = sha256(artifact_path)
    artifact = read_json(artifact_path)
    checks = (
        (artifact.get("source", {}).get("path") == relative_png,
         "artifact_source_path_mismatch"),
        (artifact.get("source", {}).get("sha256") == png_sha, "artifact_source_sha_mismatch"),
        (list(artifact.get("size", [])) == list(canvas), "artifact_canvas_mismatch"),
        (artifact_sha == declared_sha, "artifact_declaration_sha_mismatch"),
    )
    problems.extend(message for condition, message in checks if not condition)
    return artifact_sha, validate_points(artifact, name)


def collect_view(
    atlas: Path, layers_root: Path, yaw: int, metadata_record: dict
) -> tuple[geometry.ViewGeometryEvidence, dict]:
    """Read one view, validating every declared binding against real bytes."""

    name = view_id(yaw)
    png_path = atlas / f"{name}.png"
    sidecar_path = atlas / f"{name}.landmarks.json"
    artifact_path = atlas / f"{name}.native-landmarks.json"
    canvas = png_canvas(png_path)
    png_sha = sha256(png_path)
    sidecar_sha = sha256(sidecar_path)
    sidecar = read_json(sidecar_path)
    problems = _declaration_problems(
        name, yaw, canvas, png_sha, sidecar_sha, sidecar, metadata_record
    )
    face = sidecar["native_face_landmarks"]
    declared_count = int(face.get("landmark_count", -1))
    artifact_sha: str | None = None
    points: np.ndarray | None = None
    if declared_count:
        artifact_sha, points = _read_artifact(
            artifact_path, name, canvas, png_sha,
            face.get("artifact", {}).get("path"),
            face.get("artifact", {}).get("sha256"),
            problems,
        )
    else:
        if face.get("artifact") is not None:
            problems.append("zero_count_artifact_declared")
        if artifact_path.is_file():
            problems.append("undeclared_artifact_present")

    occluder_layers, occluders, skin, features = _load_layer_masks(
        layers_root, name, canvas
    )
    chin_row = (
        None if points is None
        else int(round(float(points[geometry.CHIN_VERTEX_INDEX][1]) * canvas[1]))
    )
    evidence = geometry.ViewGeometryEvidence(
        view_id=name,
        yaw_degrees=yaw,
        canvas=canvas,
        png_sha256=png_sha,
        artifact_sha256=artifact_sha,
        points=points,
        figure_alpha=alpha_mask(png_path),
        skin_alpha=skin,
        occluder_alpha=occluders,
        occluder_layer_alpha=occluder_layers,
        feature_alpha=features,
        chin_row=chin_row,
    )
    binding = {
        "canvas_from_png": list(canvas),
        "png_sha256": png_sha,
        "sidecar_sha256": sidecar_sha,
        "artifact_declared_sha256": face.get("artifact", {}).get("sha256"),
        "artifact_actual_sha256": artifact_sha,
        "declared_landmark_count": declared_count,
        "chin_row_index_152": chin_row,
        "problems": problems,
    }
    return evidence, binding


def _load_layer_masks(
    layers_root: Path, name: str, canvas: tuple[int, int]
) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Authored occluder, skin, and facial-feature alpha for one view."""

    occluders = np.zeros((canvas[1], canvas[0]), dtype=bool)
    skin = np.zeros((canvas[1], canvas[0]), dtype=bool)
    occluder_layers: dict[str, np.ndarray] = {}
    features: dict[str, np.ndarray] = {}
    for part in OCCLUDER_LAYERS:
        layer = layers_root / f"{name}_{part}.png"
        if not layer.is_file():
            raise SourceContractError(f"missing occluder layer {layer.name}")
        occluder_layers[part] = alpha_mask(layer)
        occluders |= occluder_layers[part]
    for part in SKIN_LAYERS:
        layer = layers_root / f"{name}_{part}.png"
        if not layer.is_file():
            raise SourceContractError(f"missing skin layer {layer.name}")
        skin |= alpha_mask(layer)
    for part in FEATURE_LAYERS:
        layer = layers_root / f"{name}_{part}.png"
        if not layer.is_file():
            raise SourceContractError(f"missing feature layer {layer.name}")
        features[part] = alpha_mask(layer)
    return occluder_layers, occluders, skin, features


def image_height_measurement(png_path: Path, canvas: tuple[int, int]) -> dict[str, object]:
    """Height of the alpha-visible subject, measured from the image bytes."""

    measurements: dict[str, object] = {}
    for label, threshold in ALPHA_THRESHOLDS:
        mask = alpha_mask(png_path, threshold)
        rows = np.flatnonzero(mask.any(axis=1))
        if not len(rows):
            measurements[label] = {"status": "empty_mask", "alpha_threshold": threshold}
            continue
        top, bottom = int(rows[0]), int(rows[-1])
        measurements[label] = {
            "status": "measured",
            "alpha_threshold": threshold,
            "bbox_top": top,
            "bbox_bottom": bottom,
            "bbox_height_px": bottom - top + 1,
            "canvas_height_px": canvas[1],
            "normalized_height": (bottom - top + 1) / canvas[1],
            "formula": "(bbox_bottom - bbox_top + 1) / canvas_height",
            "touches_top_edge": top == 0,
            "touches_bottom_edge": bottom == canvas[1] - 1,
        }
    return measurements


def scale_audit(heights: dict[int, float]) -> dict[str, object]:
    """Run the existing 1% registration check on one height series."""

    from domain.character_identity_audit import audit_character_identity
    from tools.build_pose_atlas_identity_measurements import (
        REGISTRATION_PROBLEMS,
        SCALE_PROBLEM_PREFIXES,
    )

    report = audit_character_identity((), normalized_subject_heights=dict(heights))
    problems = tuple(
        problem for problem in report.problems
        if problem.startswith(SCALE_PROBLEM_PREFIXES) or problem in REGISTRATION_PROBLEMS
    )
    return {
        "passed": not problems,
        "problems": list(problems),
        "excluded_view_presence_problems": sorted(set(report.problems) - set(problems)),
    }


def _to_contract_record(field: str, record: dict) -> VisibleFieldRecord:
    status = FieldStatus(record["status"])
    basis = record.get("measurement_basis", geometry.MODEL_DERIVED_BASIS)
    return VisibleFieldRecord(
        field=field,
        status=status,
        value=None if status is not FieldStatus.MEASURED else float(record["value"]),
        method=f"{record['method']} [{basis}]",
        source_path=record["source_path"],
        source_sha256=(
            None if status is FieldStatus.NOT_APPLICABLE else record["source_sha256"]
        ),
        reason=record.get("reason"),
        hidden_vertices=tuple(
            int(index) for index in record.get("hidden_vertices", {})
        ),
        model_inferred_value=record.get("model_inferred_value"),
    )


def build_report(atlas: Path, layers_root: Path) -> dict[str, object]:
    metadata_path = atlas / "BUILD-METADATA.json"
    metadata = read_json(metadata_path)
    records = {record["view_id"]: record for record in metadata["views"]}
    bindings: dict[str, dict] = {}
    measurements: dict[str, dict] = {}
    contract_views: list[VisibleViewRecord] = []
    heights: dict[str, dict] = {}
    declared_series: dict[int, float] = {}
    measured_series: dict[str, dict[int, float]] = {
        label: {} for label, _ in ALPHA_THRESHOLDS
    }
    for yaw in yaws():
        name = view_id(yaw)
        evidence, binding = collect_view(atlas, layers_root, yaw, records[name])
        visibility = expected_visibility(yaw)
        measured = geometry.measure_view_fields(
            evidence, applicable_fields=BAND_FIELDS[visibility]
        )
        bindings[name] = binding
        measurements[name] = measured
        contract_views.append(VisibleViewRecord(
            view_id=name,
            yaw_degrees=yaw,
            visibility=visibility,
            fields={
                field: _to_contract_record(field, record)
                for field, record in measured["fields"].items()
            },
        ))
        height_record = _height_record(atlas, name, evidence)
        heights[name] = height_record
        declared_series[yaw] = height_record["declared_registration"]["normalized_height"]
        for label, _ in ALPHA_THRESHOLDS:
            value = height_record["image_measurement"][label]
            if value["status"] == "measured":
                measured_series[label][yaw] = float(value["normalized_height"])

    audit = audit_visible_identity(tuple(contract_views))
    field_counts: dict[str, dict[str, int]] = {}
    for record in measurements.values():
        for field, field_record in record["fields"].items():
            bucket = field_counts.setdefault(field, {})
            bucket[field_record["status"]] = bucket.get(field_record["status"], 0) + 1
    diagnostic_counts: dict[str, int] = {}
    for record in measurements.values():
        for field, field_record in record["image_outline_diagnostics"].items():
            if field_record["status"] == geometry.MEASURED:
                diagnostic_counts[field] = diagnostic_counts.get(field, 0) + 1
    return {
        "schema": SCHEMA,
        "audit_schema": AUDIT_SCHEMA,
        "atlas_root": atlas.as_posix(),
        "layers_root": layers_root.as_posix(),
        "metadata": {
            "path": "BUILD-METADATA.json",
            "sha256": sha256(metadata_path),
            "declared_status": metadata.get("status"),
        },
        "z_scale_evidence": geometry.Z_SCALE_EVIDENCE,
        "coverage": {
            "views": len(yaws()),
            "views_with_478_landmark_artifact": sum(
                1 for binding in bindings.values()
                if binding["declared_landmark_count"] == geometry.EXPLICIT_MESH_POINT_COUNT
            ),
            "measured_field_records": sum(
                counts.get(geometry.MEASURED, 0) for counts in field_counts.values()
            ),
            "occluded_field_records": sum(
                counts.get(geometry.OCCLUDED, 0) for counts in field_counts.values()
            ),
            "unsupported_field_records": sum(
                counts.get(geometry.UNSUPPORTED_SOURCE, 0)
                for counts in field_counts.values()
            ),
            "not_applicable_field_records": sum(
                counts.get(geometry.NOT_APPLICABLE, 0) for counts in field_counts.values()
            ),
            "diagnostic_records": sum(diagnostic_counts.values()),
            "complete_signatures": 0,
        },
        "per_field_status": field_counts,
        "per_diagnostic": diagnostic_counts,
        "bindings": bindings,
        "binding_problems": {
            name: binding["problems"]
            for name, binding in bindings.items()
            if binding["problems"]
        },
        "heights": heights,
        "height_audits": {
            "declared_registration": scale_audit(declared_series),
            **{
                f"image_measurement_{label}": scale_audit(series)
                for label, series in measured_series.items()
            },
        },
        "audit": {
            "schema": audit.schema,
            "passed": audit.passed,
            "certification_claim": audit.certification_claim,
            "outcome_counts": audit.outcome_counts,
            "coverage": audit.coverage,
            "incomplete_views": sorted(
                {
                    problem.split(":", 1)[1]
                    for problem in audit.problems
                    if problem.startswith("incomplete_visible_coverage:")
                }
            ),
            "problems": list(audit.problems),
            "over_threshold": [
                {
                    "view_id": item.view_id,
                    "field": item.field,
                    "reference_view_id": item.reference_view_id,
                    "delta": item.delta,
                    "limit": item.limit,
                }
                for item in audit.over_threshold
            ],
            "unverified_count": len(audit.unverified),
            "comparisons": [
                {
                    "view_id": item.view_id,
                    "field": item.field,
                    "reference_view_id": item.reference_view_id,
                    "outcome": item.outcome.value,
                    "delta": item.delta,
                    "limit": item.limit,
                    "reason": item.reason,
                }
                for item in audit.comparisons
            ],
        },
        "views": measurements,
    }


def _height_record(
    atlas: Path, name: str, evidence: geometry.ViewGeometryEvidence
) -> dict[str, object]:
    """Declared registration beside the height measured from the image bytes."""

    sidecar = read_json(atlas / f"{name}.landmarks.json")
    declared = float(sidecar["measurement"]["target_subject_height"])
    return {
        "declared_registration": {
            "status": "declared_not_measured",
            "source": "sidecar.measurement.target_subject_height",
            "target_subject_height_declared": declared,
            "normalized_height": declared / evidence.canvas[1],
        },
        "image_measurement": image_height_measurement(
            atlas / f"{name}.png", evidence.canvas
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-root", type=Path, default=PROJECT_ROOT / ATLAS_RELATIVE)
    parser.add_argument("--layers-root", type=Path,
                        default=PROJECT_ROOT / LAYERED_RELATIVE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--diagnose-drift", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        report = build_report(arguments.atlas_root.resolve(), arguments.layers_root.resolve())
    except SourceContractError as error:
        print(json.dumps({"status": "source_contract_error", "error": str(error)}))
        return 2
    if arguments.diagnose_drift:
        print(json.dumps({
            "status": "drift_diagnosis",
            "binding_problems": report["binding_problems"],
        }, indent=2))
        return 2 if report["binding_problems"] else 0
    if report["binding_problems"]:
        print(json.dumps({
            "status": "source_contract_error",
            "error": "declared bindings do not match the bytes",
            "binding_problems": report["binding_problems"],
        }, indent=2))
        return 2
    if arguments.output is None:
        parser.error("--output is required unless --diagnose-drift is used")
    arguments.output.mkdir(parents=True, exist_ok=True)
    path = arguments.output / "visible-identity-measurements.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "output": path.as_posix(),
        "coverage": report["coverage"],
        "audit_passed": report["audit"]["passed"],
        "outcome_counts": report["audit"]["outcome_counts"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
