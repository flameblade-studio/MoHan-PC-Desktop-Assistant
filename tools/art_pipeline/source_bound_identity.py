"""Bind source-bound previews to native body and hands before composition."""

from __future__ import annotations

from dataclasses import asdict
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from tools.art_pipeline.native_identity_guard import (
    IdentityOverlays, NATIVE_PNG_BIT_DEPTH, PNG_BIT_DEPTH_OFFSET, PNG_COLOR_TYPE_OFFSET,
    PNG_HEADER_LENGTH, PNG_RGBA_COLOR_TYPE, PNG_SIGNATURE,
    load_native_rgba_source, validate_native_identity,
)

BINARY_MASK_ON = 255


def decode_rgba(data: bytes) -> np.ndarray:
    if (
        len(data) < PNG_HEADER_LENGTH or not data.startswith(PNG_SIGNATURE)
        or data[PNG_BIT_DEPTH_OFFSET] != NATIVE_PNG_BIT_DEPTH
        or data[PNG_COLOR_TYPE_OFFSET] != PNG_RGBA_COLOR_TYPE
    ):
        raise ValueError("Identity layers require 8-bit RGBA PNG input.")
    with Image.open(BytesIO(data)) as image:
        if image.mode != "RGBA":
            raise ValueError("Identity layers require RGBA input.")
        return np.array(image)


def verify_native_layers(root: Path, manifest: dict, files: dict[str, bytes]) -> dict:
    """Require native-colored body and paired hands with no expanded alpha."""
    view = manifest["view_id"]
    native = manifest["native"]
    source = load_native_rgba_source(root / native["source"], native["sha256"])
    body = f"assets/pose-atlas/v5-body-overlays/{view}.png"
    hand_paths = {
        side: f"assets/pose-atlas/v5-hand-overlays/{view}_{side}.png"
        for side in ("left", "right")
    }
    if body not in files or any(path not in files for path in hand_paths.values()):
        raise ValueError("Source-bound previews require a native body and both hand overlays.")
    report = validate_native_identity(source, IdentityOverlays(
        body=decode_rgba(files[body]),
        hands={side: decode_rgba(files[path]) for side, path in hand_paths.items()},
    ))
    if not report.passed:
        raise ValueError(f"Native identity ownership failed: {report.problems}")
    return {
        "passed": report.passed, "native_sha256": report.source_sha256,
        "checks": [asdict(check) for check in report.checks],
    }


def verify_reference_faces(root: Path, manifest: dict, output: Path) -> dict:
    """Compare each composed face to the pinned same-state native baseline."""
    from tools.art_pipeline.source_bound_stage import pinned_file, read_pinned

    references = manifest.get("reference_frames", {})
    if not references:
        return {"status": "reference-comparison-not-requested"}
    expected_states = {"rest", "half", "closed", "reopened"}
    if set(references) != expected_states:
        raise ValueError("Reference comparison requires all four eye states.")
    face_path = output / f"assets/pose-atlas/v5-base-layered/{manifest['view_id']}_base.png"
    face = decode_rgba(face_path.read_bytes())[:, :, 3] > 0
    if not face.any():
        raise ValueError("Native face comparison mask is empty.")
    cosmetics = _makeup_color_region(root, manifest, face.shape)
    protected = face & ~cosmetics
    if not protected.any():
        raise ValueError("Authored makeup cannot remove the entire native face protection.")
    comparisons: dict[str, dict] = {}
    for state, pin in references.items():
        expected = decode_rgba(read_pinned(root, pinned_file(pin)))
        actual = decode_rgba((output / f"{state}.png").read_bytes())
        if actual.shape != expected.shape or face.shape != actual.shape[:2]:
            raise ValueError("Reference frame dimensions differ from native face mask.")
        alpha_changed = int(np.count_nonzero((actual[:, :, 3] != expected[:, :, 3]) & face))
        if alpha_changed:
            raise ValueError(f"Composed native face alpha changed in {state}: {alpha_changed} pixels")
        difference = np.any(actual != expected, axis=2)
        changed = int(np.count_nonzero(difference & protected))
        if changed:
            raise ValueError(f"Composed native face changed in {state}: {changed} pixels")
        comparisons[state] = {"compared_pixels": int(protected.sum()), "changed_pixels": changed}
        if manifest.get("makeup_updates"):
            comparisons[state].update(
                cosmetic_pixels=int(np.count_nonzero(face & cosmetics)),
                cosmetic_changed_pixels=int(np.count_nonzero(difference & face & cosmetics)),
                face_alpha_changed_pixels=alpha_changed,
            )
    status = (
        "same-state-face-core-identical-outside-authored-makeup"
        if manifest.get("makeup_updates") else "same-state-face-core-identical"
    )
    return {"status": status, "frames": comparisons}


def _makeup_color_region(root: Path, manifest: dict, shape: tuple[int, int]) -> np.ndarray:
    """Restrict cosmetic RGB changes to pinned pigment alpha and authored masks.

    The staging contract separately verifies these alpha channels against the
    original selected pack members before rendering any candidate.
    """
    from tools.art_pipeline.source_bound_stage import pinned_file, read_pinned

    allowed = np.zeros(shape, dtype=bool)
    for member in manifest.get("makeup_updates", []):
        pigment = decode_rgba(read_pinned(root, pinned_file(member)))
        mask_bytes = read_pinned(root, pinned_file(member["allowed_change_mask"]))
        with Image.open(BytesIO(mask_bytes)) as mask:
            if mask.mode != "L":
                raise ValueError("Authored cosmetic mask must be grayscale.")
            values = np.array(mask)
        if values.shape != shape or pigment.shape[:2] != shape:
            raise ValueError("Authored cosmetic mask differs from the native face canvas.")
        if not np.isin(values, (0, BINARY_MASK_ON)).all():
            raise ValueError("Authored cosmetic mask must be binary.")
        allowed |= (values == BINARY_MASK_ON) & (pigment[:, :, 3] > 0)
    return allowed
