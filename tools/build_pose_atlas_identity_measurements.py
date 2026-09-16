from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import math
lazy import struct
lazy import zlib
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Any

lazy from domain.character_identity_audit import (
    REAR_YAW,
    REAR_THREE_QUARTER_YAW,
    SIGNATURE_FIELDS,
    audit_character_identity,
)
lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id


SCHEMA = "mohan.pose-atlas-identity-measurements.v1"
REPORT_NAME = "measurements.json"
FACE_LANDMARK_COUNT = 478
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_IHDR_LENGTH = 13
PNG_RGBA_COLOR_TYPE = 6
PNG_BIT_DEPTH = 8
SCALE_PROBLEM_PREFIXES = ("subject_scale_drift:", "mirror_scale_drift:")
REGISTRATION_PROBLEMS = frozenset({
    "missing_subject_registration",
    "incomplete_subject_registration",
    "invalid_subject_registration",
})


class SourceContractError(ValueError):
    """The declared atlas source chain is missing or no longer matches bytes."""


@dataclass(frozen=True, slots=True)
class ViewMeasurement:
    view_id: str
    yaw_degrees: int
    png_sha256: str
    sidecar_sha256: str
    sidecar_provenance_path: str
    width: int
    height: int
    target_subject_height: float
    native_face_landmark_count: int
    native_face_artifact: dict[str, Any] | None

    @property
    def normalized_subject_height(self) -> float:
        return self.target_subject_height / self.height

    @property
    def native_face_status(self) -> str:
        if abs(self.yaw_degrees) == REAR_YAW:
            return "rear_none"
        if self.native_face_landmark_count == FACE_LANDMARK_COUNT:
            return "native_478_available"
        return "missing_no_single_face_result"

    def to_dict(self) -> dict[str, Any]:
        return {
            "view_id": self.view_id,
            "yaw_degrees": self.yaw_degrees,
            "source_png": {
                "path": f"{self.view_id}.png",
                "sha256": self.png_sha256,
            },
            "body_sidecar": {
                "path": f"{self.view_id}.landmarks.json",
                "provenance_path": self.sidecar_provenance_path,
                "sha256": self.sidecar_sha256,
            },
            "canvas": [self.width, self.height],
            "target_subject_height": self.target_subject_height,
            "normalized_subject_height": self.normalized_subject_height,
            "native_face_landmark_count": self.native_face_landmark_count,
            "native_face_status": self.native_face_status,
            "native_face_artifact": self.native_face_artifact,
            "face_geometry_signature": None,
        }


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise SourceContractError(f"missing {label}: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SourceContractError(f"invalid {label}: {path}") from error
    if not isinstance(value, dict):
        raise SourceContractError(f"{label} must be a JSON object: {path}")
    return value


def _sha256(path: Path, label: str) -> str:
    if not path.is_file():
        raise SourceContractError(f"missing {label}: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_png_canvas(path: Path, label: str) -> tuple[int, int]:
    data = path.read_bytes()
    header_end = len(PNG_SIGNATURE) + 8 + PNG_IHDR_LENGTH + 4
    if len(data) < header_end or not data.startswith(PNG_SIGNATURE):
        raise SourceContractError(f"{label} must contain a PNG header")
    length = struct.unpack(">I", data[8:12])[0]
    chunk_type = data[12:16]
    if length != PNG_IHDR_LENGTH or chunk_type != b"IHDR":
        raise SourceContractError(f"{label} must begin with a valid IHDR chunk")
    ihdr = data[16:29]
    expected_crc = struct.unpack(">I", data[29:33])[0]
    if zlib.crc32(chunk_type + ihdr) & 0xFFFFFFFF != expected_crc:
        raise SourceContractError(f"{label} has an invalid IHDR checksum")
    width, height, depth, color_type, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB",
        ihdr,
    )
    if width <= 0 or height <= 0:
        raise SourceContractError(f"{label} has an invalid canvas")
    if depth != PNG_BIT_DEPTH or color_type != PNG_RGBA_COLOR_TYPE:
        raise SourceContractError(f"{label} must be 8-bit RGBA")
    if compression or filtering or interlace not in {0, 1}:
        raise SourceContractError(f"{label} has unsupported PNG encoding fields")
    return width, height


def _require_sha(actual: str, declared: object, label: str) -> None:
    if not isinstance(declared, str) or actual != declared:
        raise SourceContractError(f"{label} SHA256 does not match its declaration")


def _require_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise SourceContractError(f"{label} must be an integer")
    return value


def _require_positive_number(value: object, label: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) <= 0.0
    ):
        raise SourceContractError(f"{label} must be a positive finite number")
    return float(value)


def _resolve_project_file(project_root: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise SourceContractError(f"{label} must declare a path")
    path = Path(value)
    resolved = (path if path.is_absolute() else project_root / path).resolve()
    if not resolved.is_relative_to(project_root):
        raise SourceContractError(f"{label} must stay within project_root")
    return resolved


def _canonical_records(metadata: dict[str, Any]) -> dict[int, dict[str, Any]]:
    raw_records = metadata.get("views")
    if not isinstance(raw_records, list):
        raise SourceContractError("BUILD-METADATA.json must contain a views list")
    records: dict[int, dict[str, Any]] = {}
    for value in raw_records:
        if not isinstance(value, dict):
            raise SourceContractError("each BUILD-METADATA view must be an object")
        yaw = _require_int(value.get("yaw_degrees"), "view yaw_degrees")
        if yaw not in CANONICAL_YAWS:
            raise SourceContractError(f"non-canonical view yaw: {yaw:+04d}")
        if yaw in records:
            raise SourceContractError(f"duplicate canonical view: {yaw:+04d}")
        if value.get("view_id") != canonical_view_id(yaw):
            raise SourceContractError(f"view ID does not match yaw: {yaw:+04d}")
        records[yaw] = value
    if set(records) != set(CANONICAL_YAWS):
        missing = sorted(set(CANONICAL_YAWS) - set(records))
        raise SourceContractError(f"missing canonical views: {missing}")
    return records


def _scale_problems(heights: dict[int, float]) -> tuple[str, ...]:
    audit = audit_character_identity(
        (),
        normalized_subject_heights=frozendict(heights),
    )
    return tuple(
        problem
        for problem in audit.problems
        if problem.startswith(SCALE_PROBLEM_PREFIXES)
        or problem in REGISTRATION_PROBLEMS
    )


def _measurement_values(
    sidecar: dict[str, Any],
    view_id: str,
    png_sha: str,
    png_canvas: tuple[int, int],
) -> tuple[int, int, float]:
    width = _require_int(sidecar.get("width"), f"{view_id} canvas width")
    height = _require_int(sidecar.get("height"), f"{view_id} canvas height")
    if width <= 0 or height <= 0:
        raise SourceContractError(f"invalid body sidecar canvas: {view_id}")
    if (width, height) != png_canvas:
        raise SourceContractError(f"body sidecar canvas does not match PNG: {view_id}")
    measurement = sidecar.get("measurement")
    if not isinstance(measurement, dict):
        raise SourceContractError(f"missing body measurement: {view_id}")
    _require_sha(
        png_sha,
        measurement.get("source_sha256"),
        f"body measurement source {view_id}",
    )
    target_height = _require_positive_number(
        measurement.get("target_subject_height"),
        f"{view_id} target_subject_height",
    )
    return width, height, target_height


def _validate_source_binding(
    binding: object,
    *,
    project_root: Path,
    png_path: Path,
    png_sha: str,
    label: str,
) -> None:
    if not isinstance(binding, dict):
        raise SourceContractError(f"missing {label} source")
    source_path = _resolve_project_file(project_root, binding.get("path"), f"{label} source")
    if source_path != png_path:
        raise SourceContractError(f"{label} source path does not match PNG")
    _require_sha(png_sha, binding.get("sha256"), f"{label} source")


def _actual_landmark_count(artifact: dict[str, Any], view_id: str) -> int:
    landmarks = artifact.get("landmarks")
    if not isinstance(landmarks, list):
        raise SourceContractError(f"native face artifact landmarks must be a list: {view_id}")
    for index, point in enumerate(landmarks):
        if not isinstance(point, dict) or not {"x", "y", "z"} <= set(point):
            raise SourceContractError(f"invalid native face point {index}: {view_id}")
        values = (point["x"], point["y"], point["z"])
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            for value in values
        ):
            raise SourceContractError(f"non-finite native face point {index}: {view_id}")
    return len(landmarks)


def _native_face_evidence(
    sidecar: dict[str, Any],
    record: dict[str, Any],
    view_id: str,
    project_root: Path,
    png_path: Path,
    png_sha: str,
    png_canvas: tuple[int, int],
) -> tuple[int, dict[str, Any] | None]:
    native_face = sidecar.get("native_face_landmarks")
    if not isinstance(native_face, dict):
        raise SourceContractError(f"missing native face record: {view_id}")
    declared_count = _require_int(
        native_face.get("landmark_count"),
        f"{view_id} native face landmark_count",
    )
    if declared_count not in {0, FACE_LANDMARK_COUNT}:
        raise SourceContractError(f"unsupported native face landmark count: {view_id}")
    _validate_source_binding(
        native_face.get("source"),
        project_root=project_root,
        png_path=png_path,
        png_sha=png_sha,
        label=f"native face {view_id}",
    )
    metadata_face = record.get("native_face")
    if not isinstance(metadata_face, dict):
        raise SourceContractError(f"missing metadata native face record: {view_id}")
    if metadata_face.get("landmark_count") != declared_count:
        raise SourceContractError(f"native face count mismatch: {view_id}")
    _require_sha(
        png_sha,
        metadata_face.get("source_sha256"),
        f"metadata native face source {view_id}",
    )
    artifact_reference = native_face.get("artifact")
    if declared_count == 0:
        if artifact_reference is not None:
            raise SourceContractError(f"zero-count native face must not declare an artifact: {view_id}")
        return 0, None
    if not isinstance(artifact_reference, dict):
        raise SourceContractError(f"missing native face artifact: {view_id}")
    artifact_path = _resolve_project_file(
        project_root,
        artifact_reference.get("path"),
        f"native face artifact {view_id}",
    )
    artifact_sha = _sha256(artifact_path, f"native face artifact {view_id}")
    _require_sha(
        artifact_sha,
        artifact_reference.get("sha256"),
        f"native face artifact {view_id}",
    )
    artifact = _read_json(artifact_path, f"native face artifact {view_id}")
    if artifact.get("size") != list(png_canvas):
        raise SourceContractError(f"native face artifact canvas does not match PNG: {view_id}")
    _validate_source_binding(
        artifact.get("source"),
        project_root=project_root,
        png_path=png_path,
        png_sha=png_sha,
        label=f"native face artifact {view_id}",
    )
    actual_count = _actual_landmark_count(artifact, view_id)
    if actual_count != FACE_LANDMARK_COUNT or actual_count != declared_count:
        raise SourceContractError(f"native face artifact point count mismatch: {view_id}")
    return actual_count, {
        "path": artifact_reference["path"],
        "sha256": artifact_sha,
        "landmark_count": actual_count,
        "size": list(png_canvas),
        "confidence": artifact.get("confidence"),
        "source_sha256": png_sha,
    }


def _measure_view(
    atlas_root: Path,
    project_root: Path,
    record: dict[str, Any],
    yaw: int,
) -> ViewMeasurement:
    view_id = canonical_view_id(yaw)
    png_path = atlas_root / f"{view_id}.png"
    png_sha = _sha256(png_path, f"view PNG {view_id}")
    _require_sha(png_sha, record.get("normalized_sha256"), f"view PNG {view_id}")
    png_canvas = _load_png_canvas(png_path, f"view PNG {view_id}")
    provenance_path = record.get("body_sidecar")
    if not isinstance(provenance_path, str) or not provenance_path.strip():
        raise SourceContractError(f"body sidecar {view_id} must declare a path")
    sidecar_path = atlas_root / f"{view_id}.landmarks.json"
    sidecar_sha = _sha256(sidecar_path, f"body sidecar {view_id}")
    _require_sha(
        sidecar_sha,
        record.get("body_sidecar_sha256"),
        f"body sidecar {view_id}",
    )
    sidecar = _read_json(sidecar_path, f"body sidecar {view_id}")
    if sidecar.get("view_id") != view_id:
        raise SourceContractError(f"body sidecar view ID mismatch: {view_id}")
    if _require_int(sidecar.get("yaw_degrees"), f"{view_id} sidecar yaw") != yaw:
        raise SourceContractError(f"body sidecar yaw mismatch: {view_id}")
    width, height, target_height = _measurement_values(
        sidecar,
        view_id,
        png_sha,
        png_canvas,
    )
    landmark_count, face_artifact = _native_face_evidence(
        sidecar,
        record,
        view_id,
        project_root,
        png_path,
        png_sha,
        png_canvas,
    )
    if abs(yaw) == REAR_YAW and landmark_count:
        raise SourceContractError(f"rear view must not expose face landmarks: {view_id}")
    return ViewMeasurement(
        view_id,
        yaw,
        png_sha,
        sidecar_sha,
        provenance_path,
        width,
        height,
        target_height,
        landmark_count,
        face_artifact,
    )


def _native_face_provider(metadata: dict[str, Any]) -> dict[str, Any]:
    evidence = metadata.get("native_face_evidence")
    if not isinstance(evidence, dict):
        raise SourceContractError("BUILD-METADATA.json must declare native_face_evidence")
    model = evidence.get("model")
    coordinates = evidence.get("coordinates")
    model_sha256 = evidence.get("model_sha256")
    if not isinstance(model, str) or not model.strip():
        raise SourceContractError("native_face_evidence must declare a model")
    if not isinstance(coordinates, str) or not coordinates.strip():
        raise SourceContractError("native_face_evidence must declare coordinates")
    if not isinstance(model_sha256, dict) or not model_sha256:
        raise SourceContractError("native_face_evidence must declare model SHA256 values")
    return {
        "model": model,
        "coordinates": coordinates,
        "model_sha256": model_sha256,
    }


def build_measurements(
    atlas_root: Path,
    *,
    project_root: Path,
) -> dict[str, Any]:
    """Build source-bound measurement evidence without inventing geometry."""

    atlas_root = atlas_root.resolve()
    project_root = project_root.resolve()
    metadata_path = atlas_root / "BUILD-METADATA.json"
    metadata = _read_json(metadata_path, "BUILD-METADATA.json")
    records = _canonical_records(metadata)
    measured = tuple(
        _measure_view(atlas_root, project_root, records[yaw], yaw)
        for yaw in CANONICAL_YAWS
    )
    available = [
        view.view_id
        for view in measured
        if view.native_face_status == "native_478_available"
    ]
    missing = [
        view.view_id
        for view in measured
        if view.native_face_status == "missing_no_single_face_result"
    ]
    rear_none = [view.view_id for view in measured if view.native_face_status == "rear_none"]
    normalized_heights = {
        view.yaw_degrees: view.normalized_subject_height for view in measured
    }

    scale_problems = _scale_problems(normalized_heights)
    complete_geometry = 0
    geometry_required = len(CANONICAL_YAWS) - len(rear_none)
    return {
        "schema": SCHEMA,
        "status": "blocked_missing_identity_geometry_or_scale_registration",
        "passed": False,
        "source": {
            "atlas_root": atlas_root.as_posix(),
            "metadata": {
                "path": "BUILD-METADATA.json",
                "sha256": _sha256(metadata_path, "BUILD-METADATA.json"),
            },
        },
        "native_face_landmarks": {
            "provider": _native_face_provider(metadata),
            "required_count_per_available_view": FACE_LANDMARK_COUNT,
            "available_478": available,
            "missing_non_rear": missing,
            "missing_rear_three_quarter": [
                canonical_view_id(yaw)
                for yaw in CANONICAL_YAWS
                if canonical_view_id(yaw) in missing
                and abs(yaw) >= REAR_THREE_QUARTER_YAW
            ],
            "rear_none": rear_none,
        },
        "geometry": {
            "signature_fields": list(SIGNATURE_FIELDS),
            "required_non_rear_signatures": geometry_required,
            "complete_signatures": complete_geometry,
            "status": "not_measured",
        },
        "scale_audit": {
            "passed": not scale_problems,
            "problems": list(scale_problems),
        },
        "views": [view.to_dict() for view in measured],
    }


def write_measurements(output: Path, report: dict[str, Any]) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    path = output / REPORT_NAME
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build source-bound PoseAtlas identity measurement evidence."
    )
    parser.add_argument("--atlas-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args(argv)
    try:
        report = build_measurements(
            arguments.atlas_root,
            project_root=arguments.project_root,
        )
    except SourceContractError as error:
        print(json.dumps({"status": "source_contract_error", "error": str(error)}))
        return 2
    path = write_measurements(arguments.output, report)
    print(json.dumps({
        "status": report["status"],
        "output": str(path),
        "scale_problem_count": len(report["scale_audit"]["problems"]),
    }))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
