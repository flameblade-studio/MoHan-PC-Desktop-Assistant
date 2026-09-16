"""Reference previews stay bound to their receipt, inputs and eye states."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tools.art_pipeline.source_bound_preview import _makeup_state_payload
from tools.art_pipeline.source_bound_reference import (
    normalize_makeup_slot_intensities,
    verify_reference_binding,
)
from tools.art_pipeline.source_bound_stage import digest

VIEW = "yaw+060-pitch+00"
STATES = ("rest", "half", "closed", "reopened")
BASELINE_DIRECTORY = "scratchpad/native-baseline"
NATIVE_TARGET = f"assets/pose-atlas/v5-base/{VIEW}.png"


def test_makeup_only_changes_require_reference_frames(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="four pinned baseline"):
        verify_reference_binding(tmp_path, {"makeup_updates": [{"members": []}]})


def test_reference_cannot_already_contain_makeup_replacements(tmp_path: Path) -> None:
    root, manifest = _fixture(tmp_path)
    relative = f"{BASELINE_DIRECTORY}/input-manifest.json"
    baseline = json.loads((root / relative).read_text(encoding="utf-8"))
    baseline["makeup_updates"] = [{"members": []}]
    manifest["reference_preview"]["input_manifest_sha256"] = _write_json(root, relative, baseline)
    with pytest.raises(ValueError, match="different native, asset or appearance inputs"):
        verify_reference_binding(root, manifest)


def _png_bytes(seed: int) -> bytes:
    pixels = np.zeros((2, 3, 4), dtype=np.uint8)
    pixels[:, :, :] = [seed, seed + 1, seed + 2, 255]
    stream = BytesIO()
    Image.fromarray(pixels, mode="RGBA").save(stream, format="PNG")
    return stream.getvalue()


def _write(root: Path, relative: str, data: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, indent=2) + "\n").encode("utf-8")


def _write_json(root: Path, relative: str, payload: dict) -> str:
    data = _json_bytes(payload)
    _write(root, relative, data)
    return digest(data)


def _fixture(tmp_path: Path) -> tuple[Path, dict]:
    root = tmp_path
    source_paths = (
        NATIVE_TARGET,
        f"assets/pose-atlas/v5-body-overlays/{VIEW}.png",
        f"assets/pose-atlas/v5-hand-overlays/{VIEW}_left.png",
        f"assets/pose-atlas/v5-hand-overlays/{VIEW}_right.png",
    )
    files = []
    for index, relative in enumerate(source_paths):
        data = _png_bytes(index + 1)
        _write(root, relative, data)
        files.append({
            "source": relative,
            "target": relative,
            "sha256": digest(data),
        })

    frame_hashes = {}
    for index, state in enumerate(STATES):
        data = _png_bytes(index + 11)
        _write(root, f"{BASELINE_DIRECTORY}/{state}.png", data)
        frame_hashes[state] = digest(data)

    native = dict(files[0])
    input_manifest = {
        "view_id": VIEW,
        "native": native,
        "files": files,
        "pack_updates": [],
        "makeup": "classic",
        "pack_id": "mohan.official.blue-white-hanfu",
        "ensemble_id": "blue-white-hanfu",
    }
    receipt = {
        "view_id": VIEW,
        "files": {item["target"]: item["sha256"] for item in files},
        "frames": {
            state: {"sha256": frame_hashes[state]} for state in STATES
        },
    }
    receipt_relative = f"{BASELINE_DIRECTORY}/receipt.json"
    input_relative = f"{BASELINE_DIRECTORY}/input-manifest.json"
    receipt_sha256 = _write_json(root, receipt_relative, receipt)
    input_manifest_sha256 = _write_json(root, input_relative, input_manifest)

    manifest = {
        "view_id": VIEW,
        "native": native,
        "files": files,
        "pack_updates": [],
        "makeup": "classic",
        "pack_id": "mohan.official.blue-white-hanfu",
        "ensemble_id": "blue-white-hanfu",
        "reference_preview": {
            "path": BASELINE_DIRECTORY,
            "receipt_sha256": receipt_sha256,
            "input_manifest_sha256": input_manifest_sha256,
        },
        "reference_frames": {
            state: {
                "source": f"{BASELINE_DIRECTORY}/{state}.png",
                "target": f"{state}.png",
                "sha256": frame_hashes[state],
            }
            for state in STATES
        },
    }
    return root, manifest


def test_valid_reference_receipt_and_input_manifest_are_bound(tmp_path: Path) -> None:
    root, manifest = _fixture(tmp_path)

    assert verify_reference_binding(root, manifest) is None


def test_no_reference_contract_is_a_noop_without_appearance_updates(tmp_path: Path) -> None:
    assert verify_reference_binding(
        tmp_path,
        {"reference_frames": {}, "pack_updates": []},
    ) is None


def test_requires_all_four_eye_states(tmp_path: Path) -> None:
    root, manifest = _fixture(tmp_path)
    manifest["reference_frames"] = dict(manifest["reference_frames"])
    manifest["reference_frames"].pop("closed")

    with pytest.raises(ValueError, match="four pinned baseline reference frames"):
        verify_reference_binding(root, manifest)


@pytest.mark.parametrize(
    "mutation",
    ("native", "view", "inputs"),
)
def test_rejects_wrong_native_view_or_inputs(
    tmp_path: Path,
    mutation: str,
) -> None:
    root, manifest = _fixture(tmp_path)
    if mutation == "native":
        manifest["native"] = {
            **manifest["native"],
            "sha256": "0" * 64,
        }
    elif mutation == "view":
        manifest["view_id"] = "yaw+045-pitch+00"
    else:
        manifest["files"] = []

    with pytest.raises(
        ValueError,
        match="different native, asset or appearance inputs",
    ):
        verify_reference_binding(root, manifest)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("source", f"{BASELINE_DIRECTORY}/half.png"),
        ("target", "half.png"),
        ("sha256", "0" * 64),
    ),
)
def test_reference_frame_must_bind_to_its_exact_eye_state(
    tmp_path: Path,
    field: str,
    replacement: str,
) -> None:
    root, manifest = _fixture(tmp_path)
    manifest["reference_frames"]["rest"][field] = replacement

    with pytest.raises(ValueError, match="declared eye state: rest"):
        verify_reference_binding(root, manifest)


@pytest.mark.parametrize("metadata", ("receipt_sha256", "input_manifest_sha256"))
def test_baseline_receipt_or_input_hash_drift_is_rejected(
    tmp_path: Path,
    metadata: str,
) -> None:
    root, manifest = _fixture(tmp_path)
    manifest["reference_preview"][metadata] = "0" * 64

    with pytest.raises(ValueError, match="Pinned input changed"):
        verify_reference_binding(root, manifest)


def test_reference_png_hash_drift_is_rejected(tmp_path: Path) -> None:
    root, manifest = _fixture(tmp_path)
    reference = manifest["reference_frames"]["rest"]
    _write(root, reference["source"], _png_bytes(99))

    with pytest.raises(ValueError, match="Pinned input changed"):
        verify_reference_binding(root, manifest)


def test_reference_preview_must_be_under_scratchpad(tmp_path: Path) -> None:
    root, manifest = _fixture(tmp_path)
    manifest["reference_preview"]["path"] = "artifacts/baseline"

    with pytest.raises(ValueError, match="isolated scratch baseline"):
        verify_reference_binding(root, manifest)


def test_omitted_makeup_slot_intensities_preserve_legacy_defaults() -> None:
    assert normalize_makeup_slot_intensities({}) == {
        "cheeks": 1.0,
        "eyes": 1.0,
        "foundation": 1.0,
        "lips": 1.0,
    }
    assert _makeup_state_payload({}) == {"enabled": True, "intensity": 1.0}


def test_makeup_slot_intensities_use_existing_persisted_format() -> None:
    manifest = {"makeup_slot_intensities": {"eyes": 0.35, "lips": 1}}

    assert normalize_makeup_slot_intensities(manifest) == {
        "cheeks": 1.0,
        "eyes": 0.35,
        "foundation": 1.0,
        "lips": 1.0,
    }
    assert _makeup_state_payload(manifest) == {
        "enabled": True,
        "intensity": 1.0,
        "slot_intensities": {"eyes": 0.35},
    }


@pytest.mark.parametrize(
    ("slot", "value"),
    (
        ("eyes", True),
        ("eyes", float("nan")),
        ("eyes", float("inf")),
        ("eyes", 10**1000),
        ("eyes", -0.01),
        ("eyes", 1.01),
        ("eyes", "0.35"),
        ("unknown", 0.5),
    ),
)
def test_rejects_invalid_makeup_slot_intensities(slot: str, value: object) -> None:
    with pytest.raises(ValueError, match="makeup slot intensit|unsupported slots"):
        normalize_makeup_slot_intensities(
            {"makeup_slot_intensities": {slot: value}},
        )


def test_explicit_default_makeup_settings_match_omitted_baseline(tmp_path: Path) -> None:
    root, manifest = _fixture(tmp_path)
    manifest["makeup_slot_intensities"] = {
        "eyes": 1,
        "cheeks": 1.0,
        "lips": 1,
        "foundation": 1.0,
    }

    assert verify_reference_binding(root, manifest) is None


def test_reference_rejects_different_makeup_slot_intensities(tmp_path: Path) -> None:
    root, manifest = _fixture(tmp_path)
    manifest["makeup_slot_intensities"] = {"eyes": 0.35}

    with pytest.raises(ValueError, match="different native, asset or appearance inputs"):
        verify_reference_binding(root, manifest)
