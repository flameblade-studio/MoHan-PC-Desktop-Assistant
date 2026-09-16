"""Validate four reference frames against their source-bound preview receipt."""

from __future__ import annotations

lazy import json
lazy from math import isfinite
lazy from pathlib import Path

lazy from domain.outfit_pack import MAKEUP_SLOTS_V2
lazy from tools.art_pipeline.source_bound_stage import PinnedFile, pinned_file, read_pinned, relative_path

EYE_STATES = {"rest", "half", "closed", "reopened"}


def normalize_makeup_slot_intensities(manifest: dict) -> dict[str, float]:
    """Return the complete, finite per-slot preview setting."""

    raw = manifest.get("makeup_slot_intensities")
    values = {slot: 1.0 for slot in sorted(MAKEUP_SLOTS_V2)}
    if raw is None:
        return values
    if not isinstance(raw, dict) or not set(raw).issubset(MAKEUP_SLOTS_V2):
        raise ValueError("Preview makeup slot intensities use unsupported slots.")
    for slot, value in raw.items():
        if (
            type(value) not in {int, float}
            or not 0.0 <= value <= 1.0
            or not isfinite(value)
        ):
            raise ValueError(f"Invalid preview makeup slot intensity: {slot}")
        values[slot] = float(value)
    return values


def verify_reference_binding(root: Path, manifest: dict) -> None:
    makeup_slot_intensities = normalize_makeup_slot_intensities(manifest)
    references = manifest.get("reference_frames", {})
    if not references and not manifest.get("pack_updates") and not manifest.get("makeup_updates"):
        return
    if set(references) != EYE_STATES:
        raise ValueError("Appearance updates require four pinned baseline reference frames.")
    baseline = manifest["reference_preview"]
    directory = baseline["path"]
    relative_path(directory)
    if not directory.startswith("scratchpad/"):
        raise ValueError("Reference preview must be an isolated scratch baseline.")
    receipt = json.loads(read_pinned(root, PinnedFile(
        f"{directory}/receipt.json", baseline["receipt_sha256"], "receipt.json",
    )))
    inputs = json.loads(read_pinned(root, PinnedFile(
        f"{directory}/input-manifest.json", baseline["input_manifest_sha256"], "input-manifest.json",
    )))
    if (
        receipt["view_id"] != manifest["view_id"] or inputs["view_id"] != manifest["view_id"]
        or inputs["native"] != manifest["native"] or inputs["files"] != manifest["files"]
        or inputs.get("pack_updates") or inputs.get("makeup_updates")
        or inputs["makeup"] != manifest["makeup"]
        or normalize_makeup_slot_intensities(inputs) != makeup_slot_intensities
        or inputs["pack_id"] != manifest["pack_id"]
        or inputs["ensemble_id"] != manifest["ensemble_id"]
    ):
        raise ValueError("Reference preview uses different native, asset or appearance inputs.")
    expected_files = {pin["target"]: pin["sha256"] for pin in manifest["files"]}
    if receipt["files"] != expected_files:
        raise ValueError("Reference receipt does not match its pinned input manifest.")
    for state, value in references.items():
        pin = pinned_file(value)
        if (
            pin.source != f"{directory}/{state}.png" or pin.target != f"{state}.png"
            or pin.sha256 != receipt["frames"][state]["sha256"]
        ):
            raise ValueError(f"Reference frame is not bound to its declared eye state: {state}")
        read_pinned(root, pin)
