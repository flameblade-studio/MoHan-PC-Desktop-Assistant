"""Fail closed when paired facial layers erase authored left/right asymmetry."""

from __future__ import annotations

lazy import argparse
lazy import json
lazy from dataclasses import asdict, dataclass
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

lazy from domain.face_motion import interpolate_frame
lazy from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme
lazy from infrastructure.layered_full_body_assets import VIEW_IDS


ROOT = Path(__file__).resolve().parents[1]
PAIR_STEMS = ("eyelid", "eyeliner", "iris", "brow", "corner", "blush")
HALF_POSES = ("front", "lean", "cheek")
SCHEMA = "mohan.face-layer-asymmetry-audit.v1"
ALPHA_THRESHOLD = 16
IMAGE_DIMENSIONS = 3
RGBA_CHANNELS = 4
MAX_CONTROL_STEP = 0.25
MAX_ACCELERATION_STEP = 0.05
MAX_JERK_STEP = 0.10


@dataclass(frozen=True, slots=True)
class AsymmetryIssue:
    code: str
    view_id: str
    feature: str
    left_path: str
    right_path: str


def audit_motion_series(values: tuple[float, ...]) -> tuple[str, ...]:
    """Check normalized 50 Hz control samples for pops and derivative spikes."""

    velocity = tuple(end - start for start, end in zip(values, values[1:]))
    acceleration = tuple(
        end - start for start, end in zip(velocity, velocity[1:])
    )
    jerk = tuple(
        end - start for start, end in zip(acceleration, acceleration[1:])
    )
    issues = []
    if any(abs(value) > MAX_CONTROL_STEP for value in velocity):
        issues.append("control-single-frame-pop")
    if any(abs(value) > MAX_ACCELERATION_STEP for value in acceleration):
        issues.append("control-acceleration-spike")
    if any(abs(value) > MAX_JERK_STEP for value in jerk):
        issues.append("control-jerk-spike")
    return tuple(issues)


def _runtime_motion_issues() -> tuple[AsymmetryIssue, ...]:
    start = FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.CLOSED,
        MouthShape(aperture=0.0),
        ExpressionShape(blink=0.0),
        gaze_x=-0.5,
    )
    end = FaceMotionFrame(
        FacePose.FRONT,
        "speaking_front",
        Viseme.A,
        MouthShape(aperture=1.0),
        ExpressionShape(blink=1.0),
        gaze_x=0.5,
    )
    frames = tuple(interpolate_frame(start, end, index / 5) for index in range(6))
    controls = {
        "mouth": tuple(frame.mouth.aperture for frame in frames),
        "blink": tuple(frame.expression_shape.blink for frame in frames),
        "gaze": tuple((frame.gaze_x + 0.5) for frame in frames),
    }
    issues = []
    for feature, values in controls.items():
        for code in audit_motion_series(values):
            issues.append(
                AsymmetryIssue(
                    code,
                    "50hz-runtime",
                    feature,
                    "interpolate_frame:start",
                    "interpolate_frame:end",
                )
            )
    return tuple(issues)


def _load(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if (
        image is None
        or image.ndim != IMAGE_DIMENSIONS
        or image.shape[2] != RGBA_CHANNELS
    ):
        raise ValueError(f"invalid RGBA layer: {path}")
    return image


def _content(image: np.ndarray) -> np.ndarray:
    points = cv2.findNonZero((image[:, :, 3] > ALPHA_THRESHOLD).astype(np.uint8))
    if points is None:
        return image[:0, :0]
    x, y, width, height = cv2.boundingRect(points)
    return image[y : y + height, x : x + width]


def audit_pair(
    left_path: Path,
    right_path: Path,
    *,
    view_id: str,
    feature: str,
) -> tuple[AsymmetryIssue, ...]:
    left = _content(_load(left_path))
    right = _content(_load(right_path))
    code = ""
    # At profile/back views one or both authored features may be genuinely
    # occluded. That is natural asymmetry, not evidence of mirroring.
    if left.size == 0 or right.size == 0:
        return ()
    if left.shape == right.shape and np.array_equal(left, right):
        code = "paired-layer-byte-identical"
    elif left.shape == right.shape and np.array_equal(left, cv2.flip(right, 1)):
        code = "paired-layer-exact-mirror"
    if not code:
        return ()
    return (
        AsymmetryIssue(
            code,
            view_id,
            feature,
            str(left_path),
            str(right_path),
        ),
    )


def audit_roots(
    half_root: Path,
    full_root: Path,
) -> dict[str, object]:
    issues: list[AsymmetryIssue] = []
    pairs_checked = 0
    for root, views in ((Path(half_root), HALF_POSES), (Path(full_root), VIEW_IDS)):
        for view_id in views:
            for feature in PAIR_STEMS:
                left = root / f"{view_id}_{feature}_left.png"
                right = root / f"{view_id}_{feature}_right.png"
                pairs_checked += 1
                if not left.is_file() or not right.is_file():
                    issues.append(
                        AsymmetryIssue(
                            "paired-layer-missing",
                            view_id,
                            feature,
                            str(left),
                            str(right),
                        )
                    )
                    continue
                issues.extend(
                    audit_pair(
                        left,
                        right,
                        view_id=view_id,
                        feature=feature,
                    )
                )
    issues.extend(_runtime_motion_issues())
    return {
        "schema": SCHEMA,
        "passed": not issues,
        "pairs_checked": pairs_checked,
        "issue_count": len(issues),
        "issues": [asdict(issue) for issue in issues],
        "runtime_contract": {
            "pair_policy": "distinct-authority-layers-never-synthesized-by-mirroring",
            "control_policy": "shared-semantic-control-preserves-authored-pixel-differences",
            "clock_hz": 50,
            "max_control_step": MAX_CONTROL_STEP,
            "max_acceleration_step": MAX_ACCELERATION_STEP,
            "max_jerk_step": MAX_JERK_STEP,
            "randomized_asymmetry": False,
            "yaw_continuity_gate": "tools.audit_pose_atlas_identity",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--half-root",
        type=Path,
        default=ROOT / "assets" / "expressions" / "layered",
    )
    parser.add_argument(
        "--full-root",
        type=Path,
        default=ROOT / "assets" / "pose-atlas" / "v4-layered",
    )
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    try:
        report = audit_roots(args.half_root, args.full_root)
    except (OSError, ValueError) as error:
        print(f"FACE_LAYER_ASYMMETRY_ERROR: {error}")
        return 2
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
