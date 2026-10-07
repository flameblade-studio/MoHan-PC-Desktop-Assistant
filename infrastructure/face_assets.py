from __future__ import annotations

lazy import struct
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from domain.character_runtime_data import (
    default_expression_catalog,
    default_rig_manifest,
)
lazy from domain.face_rig import FacePose

PNG_HEADER_LENGTH = 24
_EXPRESSION_CATALOG = default_expression_catalog()
_RIG_MANIFEST = default_rig_manifest()


@dataclass(frozen=True, slots=True)
class FaceAssetManifest:
    pose: FacePose
    base: str
    blink: str
    open_mouth: str
    viseme_i: str
    viseme_u: str
    viseme_o: str
    face: str
    eyes: str
    mouth_rect: tuple[int, int, int, int]
    eye_rects: tuple[tuple[int, int, int, int], ...]

    @property
    def filenames(self) -> tuple[str, ...]:
        return (
            self.base,
            self.blink,
            self.open_mouth,
            self.viseme_i,
            self.viseme_u,
            self.viseme_o,
            self.face,
            self.eyes,
        )


def _face_asset_manifest(pose: FacePose) -> FaceAssetManifest:
    spec = _EXPRESSION_CATALOG.face_pose_assets[pose.value]
    return FaceAssetManifest(
        pose,
        spec.base,
        spec.blink,
        spec.open_mouth,
        spec.viseme_i,
        spec.viseme_u,
        spec.viseme_o,
        spec.face,
        spec.eyes,
        spec.mouth_rect,
        spec.eye_rects,
    )


FACE_ASSET_MANIFESTS = frozendict(
    {pose: _face_asset_manifest(pose) for pose in FacePose}
)


def validate_face_assets(root: Path) -> tuple[Path, ...]:
    """Fail closed if any authoritative three-pose rig source is malformed."""

    checked: list[Path] = []
    for manifest in FACE_ASSET_MANIFESTS.values():
        for filename in manifest.filenames:
            path = root / filename
            if not path.is_file():
                raise FileNotFoundError(f"missing face-rig asset: {filename}")
            if _png_dimensions(path) != (
                _RIG_MANIFEST.half_body_asset_canvas.width,
                _RIG_MANIFEST.half_body_asset_canvas.height,
            ):
                raise ValueError(f"unexpected face-rig dimensions: {filename}")
            checked.append(path)
    return tuple(dict.fromkeys(checked))


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as source:
        header = source.read(PNG_HEADER_LENGTH)
    if len(header) != PNG_HEADER_LENGTH or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"invalid face-rig PNG: {path.name}")
    return struct.unpack(">II", header[16:24])
