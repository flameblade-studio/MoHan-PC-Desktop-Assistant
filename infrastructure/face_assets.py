from __future__ import annotations

lazy import struct
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from domain.face_rig import FacePose

PNG_HEADER_LENGTH = 24


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


FACE_ASSET_MANIFESTS = frozendict(
    {
        FacePose.CHEEK: FaceAssetManifest(
            FacePose.CHEEK,
            "idle.png",
            "blink.png",
            "speaking.png",
            "viseme_i.png",
            "viseme_round.png",
            "viseme_o.png",
            "v120_face.png",
            "v120_eyes.png",
            (168, 195, 64, 40),
            ((160, 153, 55, 34), (198, 153, 61, 34)),
        ),
        FacePose.LEAN: FaceAssetManifest(
            FacePose.LEAN,
            "idle_lean.png",
            "blink_lean.png",
            "speaking_lean.png",
            "viseme_i_lean.png",
            "viseme_round_lean.png",
            "viseme_o_lean.png",
            "v120_face_lean.png",
            "v120_eyes_lean.png",
            (158, 194, 62, 42),
            ((153, 153, 55, 34), (191, 153, 61, 34)),
        ),
        FacePose.FRONT: FaceAssetManifest(
            FacePose.FRONT,
            "idle_front.png",
            "blink_front.png",
            "speaking_front.png",
            "viseme_i_front.png",
            "viseme_round_front.png",
            "viseme_o_front.png",
            "v120_face_front.png",
            "v120_eyes_front.png",
            (206, 199, 54, 35),
            ((180, 153, 53, 34), (220, 153, 56, 34)),
        ),
    }
)


def validate_face_assets(root: Path) -> tuple[Path, ...]:
    """Fail closed if any authoritative three-pose rig source is malformed."""

    checked: list[Path] = []
    for manifest in FACE_ASSET_MANIFESTS.values():
        for filename in manifest.filenames:
            path = root / filename
            if not path.is_file():
                raise FileNotFoundError(f"missing face-rig asset: {filename}")
            if _png_dimensions(path) != (1254, 1254):
                raise ValueError(f"unexpected face-rig dimensions: {filename}")
            checked.append(path)
    return tuple(dict.fromkeys(checked))


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as source:
        header = source.read(PNG_HEADER_LENGTH)
    if len(header) != PNG_HEADER_LENGTH or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"invalid face-rig PNG: {path.name}")
    return struct.unpack(">II", header[16:24])
