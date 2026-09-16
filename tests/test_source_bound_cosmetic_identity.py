"""Cosmetic color edits retain native alpha and all unpainted face pixels."""
lazy from pathlib import Path

lazy import numpy as np
lazy import pytest
lazy from PIL import Image

lazy from tools.art_pipeline.source_bound_identity import verify_reference_faces
lazy from tools.art_pipeline.source_bound_stage import digest


def _save(root: Path, name: str, pixels: np.ndarray) -> dict[str, str]:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels).save(path)
    return {"source": name, "target": name, "sha256": digest(path.read_bytes())}


def _case(tmp_path: Path):
    before = np.full((2, 2, 4), (90, 100, 110, 255), dtype=np.uint8)
    after = before.copy()
    after[0, 0, :3] = (96, 98, 107)
    pigment = np.zeros_like(before)
    pigment[0, 0] = (110, 90, 95, 150)
    mask = np.zeros((2, 2), dtype=np.uint8)
    mask[0, 0] = 255
    member: dict[str, object] = dict(_save(tmp_path, "scratchpad/pigment.png", pigment))
    member["allowed_change_mask"] = _save(tmp_path, "scratchpad/mask.png", mask)
    output = tmp_path / "scratchpad/output"
    view = "yaw+060-pitch+00"
    _save(output, f"assets/pose-atlas/v5-base-layered/{view}_base.png", before)
    references = {}
    for state in ("rest", "half", "closed", "reopened"):
        references[state] = _save(tmp_path, f"scratchpad/reference/{state}.png", before)
        _save(output, f"{state}.png", after)
    manifest = {
        "view_id": view,
        "reference_frames": references,
        "makeup_updates": [member],
    }
    return output, manifest, after


def test_cosmetic_rgb_changes_only_exempt_authored_pigment_pixels(tmp_path: Path) -> None:
    output, manifest, _ = _case(tmp_path)
    report = verify_reference_faces(tmp_path, manifest, output)
    assert report["status"] == "same-state-face-core-identical-outside-authored-makeup"
    for frame in report["frames"].values():
        assert frame == {
            "compared_pixels": 3,
            "changed_pixels": 0,
            "cosmetic_pixels": 1,
            "cosmetic_changed_pixels": 1,
            "face_alpha_changed_pixels": 0,
        }


@pytest.mark.parametrize("kind", ["outside_rgb", "inside_alpha", "outside_alpha"])
def test_cosmetic_permission_does_not_allow_other_face_changes(tmp_path: Path, kind: str) -> None:
    output, manifest, after = _case(tmp_path)
    if kind == "outside_rgb":
        after[1, 1, 0] += 1
    elif kind == "inside_alpha":
        after[0, 0, 3] -= 1
    else:
        after[1, 1, 3] -= 1
    _save(output, "rest.png", after)
    with pytest.raises(ValueError, match="face.*changed"):
        verify_reference_faces(tmp_path, manifest, output)


def test_mask_cannot_exempt_pixels_without_existing_pigment_alpha(tmp_path: Path) -> None:
    output, manifest, after = _case(tmp_path)
    manifest["makeup_updates"][0]["allowed_change_mask"] = _save(
        tmp_path, "scratchpad/broad-mask.png", np.full((2, 2), 255, dtype=np.uint8),
    )
    after[1, 1, 0] += 1
    _save(output, "rest.png", after)
    with pytest.raises(ValueError, match="face changed"):
        verify_reference_faces(tmp_path, manifest, output)


def test_unmodified_legacy_contract_keeps_full_face_comparison(tmp_path: Path) -> None:
    output, manifest, _ = _case(tmp_path)
    manifest.pop("makeup_updates")
    with pytest.raises(ValueError, match="face changed"):
        verify_reference_faces(tmp_path, manifest, output)
