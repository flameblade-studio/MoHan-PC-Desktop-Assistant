"""Apply tightly scoped, source-pinned edits to the built-in makeup pack."""

from __future__ import annotations

lazy import json
lazy import zipfile
lazy from io import BytesIO
lazy from pathlib import Path

lazy import numpy as np

lazy from domain.outfit_pack_official import BUILTIN_MAKEUP_ITEM_ID, BUILTIN_MAKEUP_PACK_ID
lazy from tools.art_pipeline.source_bound_material_guard import (
    MaterialGuardError,
    _decode_binary_mask_png,
    _decode_rgba_png,
    verify_material_change,
)
lazy from tools.art_pipeline.source_bound_pack_scope import path_counts
lazy from tools.art_pipeline.source_bound_stage import (
    SHA_PATTERN,
    digest,
    pinned_file,
    read_pinned,
    rebuild_pack,
    relative_path,
)

BUILTIN_PACK_TARGET = f"assets/official-packs/{BUILTIN_MAKEUP_PACK_ID}.mohan-outfit"
EDITABLE_SLOTS = frozenset({"cheeks", "eyes", "lips"})


def _require_pinned_pack(manifest: dict, files: dict[str, bytes]) -> bytes:
    """Return the canonical built-in pack only when its captured pin is intact."""
    declarations = [
        value for value in manifest.get("files", [])
        if isinstance(value, dict) and value.get("target") == BUILTIN_PACK_TARGET
    ]
    if len(declarations) != 1 or BUILTIN_PACK_TARGET not in files:
        raise ValueError("Makeup updates require the pinned built-in makeup pack in files.")
    declaration = declarations[0]
    if (
        declaration.get("source") != BUILTIN_PACK_TARGET
        or declaration.get("target") != BUILTIN_PACK_TARGET
        or not isinstance(declaration.get("sha256"), str)
        or not SHA_PATTERN.fullmatch(declaration["sha256"])
    ):
        raise ValueError("The built-in makeup pack requires its canonical source pin.")
    pack = files[BUILTIN_PACK_TARGET]
    if not isinstance(pack, bytes) or digest(pack) != declaration["sha256"]:
        raise ValueError("Pinned built-in makeup pack bytes changed.")
    return pack


def _unique(values: object, identity: str, label: str) -> dict:
    if not isinstance(values, list):
        raise ValueError(f"Built-in makeup pack lacks a valid {label} collection.")
    matches = [value for value in values if isinstance(value, dict) and value.get("id") == identity]
    if len(matches) != 1:
        raise ValueError(f"Expected one built-in makeup {label}: {identity}")
    return matches[0]


def _selected_members(pack_manifest: dict, manifest: dict) -> dict[str, str]:
    if pack_manifest.get("id") != BUILTIN_MAKEUP_PACK_ID:
        raise ValueError("Makeup updates require the built-in makeup pack.")
    variant_id = manifest.get("makeup")
    view_id = manifest.get("view_id")
    if not isinstance(variant_id, str) or not isinstance(view_id, str):
        raise ValueError("Makeup updates require a selected variant and view.")
    item = _unique(pack_manifest.get("makeup"), BUILTIN_MAKEUP_ITEM_ID, "item")
    variant = _unique(item.get("variants"), variant_id, "variant")

    declarations: list[dict] = []
    poses = variant.get("poses")
    if isinstance(poses, dict) and isinstance(poses.get(view_id), list):
        declarations.extend(poses[view_id])
    eye_states = variant.get("eye_states", {})
    if not isinstance(eye_states, dict):
        raise ValueError("Built-in makeup variant has invalid eye-state declarations.")
    for state_poses in eye_states.values():
        if isinstance(state_poses, dict) and isinstance(state_poses.get(view_id), list):
            declarations.extend(state_poses[view_id])

    selected: dict[str, str] = {}
    for declaration in declarations:
        if not isinstance(declaration, dict):
            raise ValueError("Built-in makeup member declaration is invalid.")
        member, slot = declaration.get("path"), declaration.get("slot")
        if isinstance(member, str) and slot in EDITABLE_SLOTS:
            selected[member] = slot
    return selected


def _verify_rgb_scope(original: bytes, candidate: bytes, mask: bytes) -> dict:
    """Allow RGB edits only where original alpha and the authored mask overlap."""
    report = verify_material_change(original, candidate, mask)
    original_pixels = _decode_rgba_png(original, "original member")
    candidate_pixels = _decode_rgba_png(candidate, "candidate member")
    allowed = _decode_binary_mask_png(mask)
    if not np.array_equal(original_pixels[..., 3], candidate_pixels[..., 3]):
        raise MaterialGuardError("Candidate makeup alpha must exactly match the original member.")
    rgb_changed = np.any(original_pixels[..., :3] != candidate_pixels[..., :3], axis=2)
    outside_visible_mask = rgb_changed & ~((original_pixels[..., 3] > 0) & allowed)
    if np.any(outside_visible_mask):
        raise MaterialGuardError(
            "Candidate makeup RGB changes must stay inside visible original alpha and the "
            "allowed-change mask."
        )
    return report


def apply_makeup_updates(root: Path, manifest: dict, files: dict[str, bytes]) -> dict:
    """Validate and rebuild one captured built-in makeup pack in memory.

    ``makeup_updates`` is a list of pinned candidate members. Each member also
    carries a separately pinned, authored binary ``allowed_change_mask``.
    """
    updates = manifest.get("makeup_updates", [])
    if updates in (None, []):
        return {}
    if not isinstance(updates, list):
        raise ValueError("makeup_updates must be a list.")

    source_pack = _require_pinned_pack(manifest, files)
    try:
        with zipfile.ZipFile(BytesIO(source_pack)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("Duplicate archive member.")
            pack_manifest = json.loads(archive.read("manifest.json"))
            selected = _selected_members(pack_manifest, manifest)
            counts = path_counts(pack_manifest)
            replacements: dict[str, bytes] = {}
            member_reports: dict[str, dict] = {}
            for declaration in updates:
                if not isinstance(declaration, dict):
                    raise ValueError("Each makeup update must be an object.")
                pin = pinned_file(declaration)
                relative_path(pin.target)
                if pin.target in replacements:
                    raise ValueError(f"Repeated makeup member: {pin.target}")
                if pin.target not in selected:
                    raise ValueError(
                        "Makeup update is outside the selected variant, view, or editable slots."
                    )
                if counts[pin.target] != 1:
                    raise ValueError("Makeup update member is shared with another declaration.")
                if pin.target not in names:
                    raise ValueError("Makeup update must name an existing archive member.")
                if not pin.source.startswith("scratchpad/") or not pin.source.endswith(".png"):
                    raise ValueError("Makeup candidate must be an authored scratchpad PNG.")

                mask_value = declaration.get("allowed_change_mask")
                if not isinstance(mask_value, dict):
                    raise ValueError("Makeup update requires an authored allowed-change mask pin.")
                mask_pin = pinned_file(mask_value)
                relative_path(mask_pin.target)
                if (
                    mask_pin.source != mask_pin.target
                    or not mask_pin.source.startswith("scratchpad/")
                    or not mask_pin.source.endswith(".png")
                ):
                    raise ValueError("Allowed-change mask must be a canonical authored scratchpad pin.")

                candidate = read_pinned(root, pin)
                mask = read_pinned(root, mask_pin)
                original = archive.read(pin.target)
                facts = _verify_rgb_scope(original, candidate, mask)
                replacements[pin.target] = candidate
                member_reports[pin.target] = {
                    **facts,
                    "slot": selected[pin.target],
                    "source": pin.source,
                    "sha256_before": digest(original),
                    "sha256_after": digest(candidate),
                    "allowed_change_mask": {
                        "source": mask_pin.source,
                        "sha256": mask_pin.sha256,
                    },
                }
    except (KeyError, TypeError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        raise ValueError("Built-in makeup pack is malformed.") from error

    rebuilt = rebuild_pack(source_pack, replacements)
    files[BUILTIN_PACK_TARGET] = rebuilt
    return {
        "pack_target": BUILTIN_PACK_TARGET,
        "sha256_before": digest(source_pack),
        "sha256_after": digest(rebuilt),
        "members": member_reports,
    }


def resolve_runtime_makeup_members(store: Path, request: dict, output: Path) -> dict[str, str]:
    """Resolve product-selected makeup members and bind requested updates to their SHA."""
    from domain import outfit_pack

    selection = outfit_pack.resolve_active_selection(store, "makeup")
    expected_identity = (
        BUILTIN_MAKEUP_PACK_ID,
        BUILTIN_MAKEUP_ITEM_ID,
        request.get("makeup"),
    )
    effective_identity = (
        selection.effective_pack_id,
        selection.effective_item_id,
        selection.effective_variant_id,
    )
    if effective_identity != expected_identity:
        raise ValueError("Runtime selected a different makeup variant.")
    path = outfit_pack.installed_pack_path(store, selection.effective_pack_id)
    expected_path = output / BUILTIN_PACK_TARGET
    if path.resolve() != expected_path.resolve():
        raise ValueError("Runtime selected a makeup pack outside this isolated preview.")
    pack = outfit_pack.inspect_outfit_pack(path)
    items = [
        item for item in pack.items
        if item.category == "makeup" and item.item_id == selection.effective_item_id
    ]
    if len(items) != 1:
        raise ValueError("Runtime makeup item is unavailable or ambiguous.")
    variants = [
        variant for variant in items[0].variants
        if variant.variant_id == selection.effective_variant_id
    ]
    if len(variants) != 1:
        raise ValueError("Runtime makeup variant is unavailable or ambiguous.")
    variant = variants[0]
    pose = outfit_pack.resolve_variant_for_view(variant, request["view_id"])
    assets = list(pose.assets)
    for state_poses in variant.eye_states.values():
        try:
            assets.extend(state_poses[request["view_id"]])
        except KeyError:
            raise ValueError("Runtime makeup eye state lacks the selected view.") from None
    resolved = {asset.path: asset.sha256 for asset in assets}
    if len(resolved) != len(assets):
        raise ValueError("Runtime selected a shared or repeated makeup member.")
    for update in request.get("makeup_updates", []):
        if resolved.get(update["target"]) != update["sha256"]:
            raise ValueError(
                f"Runtime did not select the replacement makeup member: {update['target']}"
            )
    return resolved
