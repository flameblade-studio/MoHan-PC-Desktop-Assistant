"""Load source-bound facial motion and cosmetic layers for one approved pose.

The manifest binds every raster to the approved dressed source and to the
native body selected by the caller.  Files are read and decoded once during
loading; the frame loop receives only in-memory ``QImage`` values.
"""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Mapping

from PySide6.QtGui import QImage, QPixmap


SCHEMA = "mohan.reviewed-pose-motion.v1"
FOUNDATION_SCHEMA = "mohan.reviewed-pose-motion.v2"
VARIANT_SCHEMA = "mohan.reviewed-pose-motion.v3"
APPROVED_SOURCE_SHA256 = (
    "bcc8def1ed4dd4cad179951a3733b31addaca97f81bd5211bebce5ea6ca368fe"
)
DIMENSION = 1254
SHA256_HEX_LENGTH = 64
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
RGBA_COLOR_TYPE = 6
GRAYSCALE_COLOR_TYPE = 0
EIGHT_BIT_DEPTH = 8
PATCH_STATES = ("closed", "speech")
COSMETIC_STATES = ("rest", "closed", "speech")
HALF_COSMETIC_STATE = "half"
COSMETIC_SLOTS = ("eyes", "cheeks", "lips")
FOUNDATION_COSMETIC_SLOTS = ("foundation", *COSMETIC_SLOTS)
LEGACY_COSMETIC_VARIANTS = ("light", "classic")
COSMETIC_VARIANTS = (*LEGACY_COSMETIC_VARIANTS, "glamorous")
_PNG_IHDR_START = 16
_PNG_IHDR_END = 24
_PNG_HEADER_LENGTH = 26

# A blink over speech keeps speech foundation/lips and rest cheeks. The eye
# patch separately receives closed-state foundation and eyes before it covers
# the existing frame, preserving the current mouth without recoloring twice.
_SPEECH_CLOSED_SLOT_STATES = {
    "foundation": "speech",
    "eyes": "closed",
    "cheeks": "rest",
    "lips": "speech",
}


@dataclass(frozen=True, slots=True)
class ReviewedPoseMotionPng:
    """An integrity-checked PNG retained as bytes and a detached QImage."""

    path: str
    sha256: str
    payload: bytes
    image: QImage

    def pixmap(self) -> QPixmap:
        """Return a fresh pixmap backed by the already decoded image."""

        return QPixmap.fromImage(self.image)


@dataclass(frozen=True, slots=True)
class ReviewedPoseMotion:
    """Validated motion and makeup inputs for one source-bound pose."""

    root: Path
    source_sha256: str
    native_body_sha256: str
    patches: Mapping[str, ReviewedPoseMotionPng]
    cosmetics: Mapping[str, Mapping[str, ReviewedPoseMotionPng]]
    mouth_cavity: ReviewedPoseMotionPng | None = None
    native_body: ReviewedPoseMotionPng | None = None
    variants: Mapping[
        str, Mapping[str, Mapping[str, ReviewedPoseMotionPng]]
    ] | None = None
    half_inputs: Mapping[str, ReviewedPoseMotionPng] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "patches", MappingProxyType(dict(self.patches)))
        if self.half_inputs is not None:
            object.__setattr__(
                self, "half_inputs", MappingProxyType(dict(self.half_inputs))
            )
        frozen_cosmetics = {
            state: MappingProxyType(dict(slots))
            for state, slots in self.cosmetics.items()
        }
        object.__setattr__(self, "cosmetics", MappingProxyType(frozen_cosmetics))
        if self.variants is not None:
            frozen_variants = {
                variant: MappingProxyType({
                    state: MappingProxyType(dict(slots))
                    for state, slots in states.items()
                })
                for variant, states in self.variants.items()
            }
            object.__setattr__(self, "variants", MappingProxyType(frozen_variants))
            if "classic" in frozen_variants:
                # Keep the v1/v2 field useful to callers that only inspect the
                # default cosmetic map.  v3 selection still uses ``variants``.
                object.__setattr__(self, "cosmetics", frozen_variants["classic"])

    def patch(self, state: str) -> QPixmap:
        """Return the cached full-canvas native patch for ``closed`` or ``speech``."""

        if state not in PATCH_STATES:
            raise ValueError(f"Unsupported reviewed pose motion patch state: {state}")
        if state not in self.patches:
            raise ValueError(f"Reviewed pose motion patch state is unavailable: {state}")
        return self.patches[state].pixmap()

    @property
    def cosmetic_slots(self) -> tuple[str, ...]:
        """Return the validated slots in paint order, with foundation first."""
        if "foundation" in self.cosmetics["rest"]:
            return FOUNDATION_COSMETIC_SLOTS
        return COSMETIC_SLOTS

    def cosmetic(self, state: str, slot: str, variant: str = "classic") -> QPixmap:
        """Return one cached cosmetic slot, resolving speech and variant state."""

        if state == "speech-closed":
            selected_state = _SPEECH_CLOSED_SLOT_STATES.get(slot)
        elif state in COSMETIC_STATES:
            selected_state = state
        elif state == HALF_COSMETIC_STATE and self.variants is not None:
            selected_state = HALF_COSMETIC_STATE
        else:
            selected_state = None
        if selected_state is None or slot not in self.cosmetic_slots:
            raise ValueError(
                f"Unsupported reviewed pose cosmetic selection: {state}/{slot}"
            )
        # v1/v2 have one source-bound map.  Accepting the optional variant here
        # keeps callers source-compatible while the overlay supplies the legacy
        # light intensity fallback for those schemas.
        cosmetics = self.cosmetics
        if self.variants is None and variant not in LEGACY_COSMETIC_VARIANTS:
            raise ValueError(f"Unsupported reviewed pose cosmetic variant: {variant}")
        if self.variants is not None:
            if not isinstance(variant, str) or variant not in self.variants:
                raise ValueError(
                    f"Unsupported reviewed pose cosmetic variant: {variant}"
                )
            cosmetics = self.variants[variant]
        selected_slots = cosmetics.get(selected_state)
        if selected_slots is None or slot not in selected_slots:
            raise ValueError(
                f"Reviewed pose motion cosmetic state unavailable: {state}/{slot}"
            )
        return selected_slots[slot].pixmap()

    def half_input(self, name: str) -> QPixmap:
        """Return one validated native HALF input retained by the loader."""

        if self.half_inputs is None or name not in self.half_inputs:
            raise ValueError(f"Reviewed pose motion HALF input is unavailable: {name}")
        return self.half_inputs[name].pixmap()


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == SHA256_HEX_LENGTH
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_relative_path(root: Path, value: object, *, context: str) -> tuple[str, Path]:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Invalid reviewed pose motion path: {context}")
    portable = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        value.startswith(("/", "\\"))
        or "\\" in value
        or windows.drive
        or windows.is_absolute()
        or portable.is_absolute()
        or portable.as_posix() != value
        or any(part in {"", ".", ".."} for part in portable.parts)
    ):
        raise ValueError(f"Reviewed pose motion path must stay inside its root: {context}")
    candidate = (root / Path(*portable.parts)).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"Reviewed pose motion path escapes its root: {context}")
    return value, candidate


def _png_header(payload: bytes, *, context: str) -> tuple[int, int, int]:
    if len(payload) < _PNG_HEADER_LENGTH or payload[:8] != PNG_SIGNATURE:
        raise ValueError(f"Reviewed pose motion asset is not a PNG: {context}")
    width, height = struct.unpack(">II", payload[_PNG_IHDR_START:_PNG_IHDR_END])
    depth, color_type = payload[24], payload[25]
    if depth != EIGHT_BIT_DEPTH:
        raise ValueError(f"Reviewed pose motion asset must be 8-bit: {context}")
    if (width, height) != (DIMENSION, DIMENSION):
        raise ValueError(f"Reviewed pose motion asset must be 1254x1254: {context}")
    return width, height, color_type


def _read_png(
    root: Path,
    record: object,
    *,
    context: str,
    grayscale: bool = False,
) -> ReviewedPoseMotionPng:
    if not isinstance(record, dict):
        raise ValueError(f"Invalid reviewed pose motion PNG record: {context}")
    relative, path = _safe_relative_path(root, record.get("path"), context=context)
    expected_sha = record.get("sha256")
    if not _valid_sha256(expected_sha):
        raise ValueError(f"Invalid reviewed pose motion SHA-256: {context}")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"Missing reviewed pose motion asset: {relative}") from exc
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != expected_sha:
        raise ValueError(f"Reviewed pose motion SHA-256 mismatch: {relative}")
    width, height, color_type = _png_header(payload, context=relative)
    expected_color_type = GRAYSCALE_COLOR_TYPE if grayscale else RGBA_COLOR_TYPE
    if color_type != expected_color_type:
        expected = "8-bit grayscale" if grayscale else "8-bit RGBA"
        raise ValueError(f"Reviewed pose motion asset must be {expected}: {relative}")
    image = QImage.fromData(payload, "PNG")
    if image.isNull() or (width, height) != (DIMENSION, DIMENSION):
        raise ValueError(f"Invalid reviewed pose motion PNG dimensions: {relative}")
    decoded = image.convertToFormat(
        QImage.Format.Format_Grayscale8
        if grayscale
        else QImage.Format.Format_RGBA8888
    ).copy()
    return ReviewedPoseMotionPng(relative, expected_sha, payload, decoded)


def _manifest(root: Path) -> dict[str, object]:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Reviewed pose motion root lacks manifest.json.")
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid reviewed pose motion manifest JSON.") from exc
    if not isinstance(value, dict) or value.get("schema") not in (
        SCHEMA, FOUNDATION_SCHEMA, VARIANT_SCHEMA,
    ):
        raise ValueError("Invalid reviewed pose motion manifest schema.")
    return value


def _is_ordinary_native_manifest(manifest: Mapping[str, object]) -> bool:
    """Recognize the explicit ordinary source contract with no speech endpoint."""

    policy = manifest.get("motion_state_policy")
    if not isinstance(policy, dict):
        return False
    return (
        manifest.get("source_kind") == "ordinary_native"
        and policy.get("speech") == "missing_ordinary_native_mouth_source"
        and policy.get("no_fabricated_states") is True
        and policy.get("available") == ["rest", "half", "closed"]
    )


def _read_variant_cosmetics(
    root: Path,
    raw_cosmetics: object,
    *,
    allow_missing_speech: bool = False,
) -> tuple[
    dict[str, dict[str, ReviewedPoseMotionPng]],
    dict[str, dict[str, dict[str, ReviewedPoseMotionPng]]],
]:
    if (
        not isinstance(raw_cosmetics, dict)
        or not set(LEGACY_COSMETIC_VARIANTS).issubset(raw_cosmetics)
        or not set(raw_cosmetics).issubset(COSMETIC_VARIANTS)
    ):
        raise ValueError(
            "Reviewed pose motion variants must declare light and classic."
        )
    variants: dict[str, dict[str, dict[str, ReviewedPoseMotionPng]]] = {}
    for variant in COSMETIC_VARIANTS:
        if variant not in raw_cosmetics:
            continue
        raw_states = raw_cosmetics.get(variant)
        if not isinstance(raw_states, dict):
            raise ValueError(
                f"Incomplete reviewed pose motion variant states: {variant}"
            )
        state_names = set(raw_states)
        accepted_states = {"rest", "closed"}
        if state_names == set(COSMETIC_STATES):
            pass
        elif not allow_missing_speech or state_names != accepted_states:
            raise ValueError(
                f"Incomplete reviewed pose motion variant states: {variant}"
            )
        required_states = tuple(
            state for state in COSMETIC_STATES if state in state_names
        )
        variant_cosmetics: dict[str, dict[str, ReviewedPoseMotionPng]] = {}
        for state in required_states:
            raw_slots = raw_states.get(state)
            if not isinstance(raw_slots, dict) or set(raw_slots) != set(
                FOUNDATION_COSMETIC_SLOTS
            ):
                raise ValueError(
                    f"Incomplete reviewed pose motion cosmetics: {variant}/{state}"
                )
            variant_cosmetics[state] = {
                slot: _read_png(
                    root,
                    raw_slots.get(slot),
                    context=f"cosmetics/{variant}/{state}/{slot}",
                )
                for slot in FOUNDATION_COSMETIC_SLOTS
            }
        variants[variant] = variant_cosmetics
    return variants["classic"], variants


def _read_legacy_cosmetics(
    root: Path,
    raw_cosmetics: object,
    *,
    schema: object,
    allow_missing_speech: bool = False,
) -> dict[str, dict[str, ReviewedPoseMotionPng]]:
    if not isinstance(raw_cosmetics, dict):
        raise ValueError(
            "Reviewed pose motion cosmetics must declare rest/closed/speech."
        )
    states = set(raw_cosmetics)
    if states != set(COSMETIC_STATES) and not (
        allow_missing_speech and states == {"rest", "closed"}
    ):
        raise ValueError(
            "Reviewed pose motion cosmetics must declare rest/closed/speech."
        )
    expected_slots = (
        FOUNDATION_COSMETIC_SLOTS if schema == FOUNDATION_SCHEMA else COSMETIC_SLOTS
    )
    cosmetics: dict[str, dict[str, ReviewedPoseMotionPng]] = {}
    for state in raw_cosmetics:
        raw_slots = raw_cosmetics.get(state)
        if not isinstance(raw_slots, dict) or set(raw_slots) != set(expected_slots):
            raise ValueError(f"Incomplete reviewed pose motion cosmetics: {state}")
        cosmetics[state] = {
            slot: _read_png(
                root,
                raw_slots.get(slot),
                context=f"cosmetics/{state}/{slot}",
            )
            for slot in expected_slots
        }
    return cosmetics


def _read_half_inputs(
    root: Path,
    raw_half: object,
) -> dict[str, ReviewedPoseMotionPng] | None:
    """Load the native HALF endpoint and its source-pinned masks."""

    if raw_half is None:
        return None
    if not isinstance(raw_half, dict):
        raise ValueError("Invalid reviewed pose motion HALF contract.")
    required_rgba = ("native_endpoint", "patch", "eye_support", "eye_aperture")
    required_gray = ("coverage", "oral_cavity")
    inputs: dict[str, ReviewedPoseMotionPng] = {}
    for name in required_rgba:
        inputs[name] = _read_png(
            root,
            raw_half.get(name),
            context=f"half/{name}",
        )
    for name in required_gray:
        inputs[name] = _read_png(
            root,
            raw_half.get(name),
            context=f"half/{name}",
            grayscale=True,
        )
    return inputs


def _attach_half_cosmetics(
    root: Path,
    raw_half: object,
    variants: dict[str, dict[str, dict[str, ReviewedPoseMotionPng]]],
) -> None:
    """Attach HALF cosmetics to each v3 variant without changing old schemas."""

    if not isinstance(raw_half, dict):
        return
    raw_cosmetics = raw_half.get("cosmetics")
    if not isinstance(raw_cosmetics, dict):
        raise ValueError("Reviewed pose motion HALF cosmetics are missing.")
    if set(raw_cosmetics) != set(variants):
        raise ValueError("Reviewed pose motion HALF cosmetics do not match variants.")
    for variant, raw_slots in raw_cosmetics.items():
        if not isinstance(raw_slots, dict) or set(raw_slots) != set(
            FOUNDATION_COSMETIC_SLOTS
        ):
            raise ValueError(f"Incomplete reviewed pose motion HALF cosmetics: {variant}")
        variants[variant][HALF_COSMETIC_STATE] = {
            slot: _read_png(
                root,
                raw_slots.get(slot),
                context=f"half/cosmetics/{variant}/{slot}",
            )
            for slot in FOUNDATION_COSMETIC_SLOTS
        }


def load_reviewed_pose_motion(
    root: Path,
    *,
    expected_native_body_sha256: str,
    expected_source_sha256: str | None = None,
) -> ReviewedPoseMotion:
    """Load one reviewed motion root and fail closed on every installation gap.

    The caller supplies the native body digest from its already selected body
    asset.  A mismatch fails closed before any motion or cosmetic layer is
    exposed, so an old body source cannot silently receive the new face.
    """

    requested_root = Path(root)
    if not requested_root.exists():
        raise ValueError("Reviewed pose motion root is missing.")
    if not requested_root.is_dir():
        raise ValueError("Reviewed pose motion root must be a directory.")
    if not _valid_sha256(expected_native_body_sha256):
        raise ValueError("Invalid expected native body SHA-256.")
    resolved_root = requested_root.resolve()
    manifest = _manifest(resolved_root)
    ordinary_native = _is_ordinary_native_manifest(manifest)

    source_sha = manifest.get("source_sha256")
    expected_source = (
        APPROVED_SOURCE_SHA256
        if expected_source_sha256 is None
        else expected_source_sha256
    )
    if not _valid_sha256(expected_source):
        raise ValueError("Invalid expected source SHA-256.")
    if not _valid_sha256(source_sha) or source_sha != expected_source:
        raise ValueError("Reviewed pose motion is not bound to the approved source.")
    native_body_sha = manifest.get("native_body_sha256")
    if not _valid_sha256(native_body_sha):
        raise ValueError("Invalid reviewed pose motion native body SHA-256.")
    if native_body_sha != expected_native_body_sha256:
        raise ValueError("Reviewed pose motion native body SHA-256 mismatch.")

    patches = {
        state: _read_png(resolved_root, manifest.get(state), context=state)
        for state in PATCH_STATES
        if state in manifest
    }
    if "closed" not in patches or (not ordinary_native and set(patches) != set(PATCH_STATES)):
        raise ValueError("Reviewed pose motion lacks its required endpoint patches.")
    raw_cosmetics = manifest.get("cosmetics")
    variants: dict[str, dict[str, dict[str, ReviewedPoseMotionPng]]] | None
    if manifest["schema"] == VARIANT_SCHEMA:
        cosmetics, variants = _read_variant_cosmetics(
            resolved_root,
            raw_cosmetics,
            allow_missing_speech=ordinary_native,
        )
    else:
        cosmetics = _read_legacy_cosmetics(
            resolved_root,
            raw_cosmetics,
            schema=manifest["schema"],
            allow_missing_speech=ordinary_native,
        )
        variants = None

    raw_half = manifest.get("half")
    half_inputs = _read_half_inputs(resolved_root, raw_half)
    if ordinary_native and half_inputs is None:
        raise ValueError("Ordinary native pose motion lacks its HALF contract.")
    if half_inputs is not None and variants is not None:
        _attach_half_cosmetics(resolved_root, raw_half, variants)

    mouth_cavity = None
    if "mouth_cavity" in manifest:
        mouth_cavity = _read_png(
            resolved_root,
            manifest.get("mouth_cavity"),
            context="mouth_cavity",
        )

    native_body = None
    if "native_body" in manifest:
        native_body = _read_png(
            resolved_root,
            manifest.get("native_body"),
            context="native_body",
        )
        if native_body.sha256 != native_body_sha:
            raise ValueError("Reviewed pose motion native body asset SHA-256 mismatch.")

    return ReviewedPoseMotion(
        resolved_root,
        source_sha,
        native_body_sha,
        patches,
        cosmetics,
        mouth_cavity,
        native_body,
        variants,
        half_inputs,
    )


__all__ = (
    "APPROVED_SOURCE_SHA256",
    "COSMETIC_SLOTS",
    "COSMETIC_STATES",
    "COSMETIC_VARIANTS",
    "DIMENSION",
    "FOUNDATION_COSMETIC_SLOTS",
    "FOUNDATION_SCHEMA",
    "PATCH_STATES",
    "ReviewedPoseMotion",
    "ReviewedPoseMotionPng",
    "SCHEMA",
    "VARIANT_SCHEMA",
    "load_reviewed_pose_motion",
)
