"""Constrain replacements to the ensemble and pose actually being previewed."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

CATEGORY_KEYS = {"garment": "looks", "hairstyle": "hairstyles", "headwear": "headwear"}
ONE_MATCH = 1


def unique_item(values: list[dict], identity: str) -> dict:
    matches = [value for value in values if value.get("id") == identity]
    if len(matches) != ONE_MATCH:
        raise ValueError(f"Expected one pack declaration: {identity}")
    return matches[0]


def path_counts(node: object) -> Counter[str]:
    counts: Counter[str] = Counter()
    if isinstance(node, dict):
        if isinstance(node.get("path"), str):
            counts[node["path"]] += 1
        for value in node.values():
            counts.update(path_counts(value))
    elif isinstance(node, list):
        for value in node:
            counts.update(path_counts(value))
    return counts


def selected_members(pack: dict, request: dict) -> set[str]:
    if pack.get("id") != request["pack_id"]:
        raise ValueError("Pack identity differs from the requested ensemble.")
    ensemble = unique_item(pack["ensembles"], request["ensemble_id"])
    members: set[str] = set()
    for category, key in CATEGORY_KEYS.items():
        selection = ensemble["selections"].get(category)
        if selection is None:
            continue
        item = unique_item(pack[key], selection["item_id"])
        variant = unique_item(item["variants"], selection["variant_id"])
        members.update(layer["path"] for layer in variant["poses"][request["view_id"]])
    return members


def verify_pack_scope(pack: dict, request: dict, replacements: set[str]) -> None:
    """Reject inactive or shared members, including cross-view aliases."""
    selected = selected_members(pack, request)
    counts = path_counts(pack)
    if not replacements <= selected:
        raise ValueError("Replacement is outside the selected ensemble and pose.")
    if any(counts[member] != ONE_MATCH for member in replacements):
        raise ValueError("Replacement member is shared or repeated in the pack.")


def resolve_runtime_members(store: Path, request: dict, output: Path) -> dict[str, str]:
    """Report the exact authored members selected by the product resolver."""
    from domain import outfit_pack

    resolved: dict[str, str] = {}
    for category in CATEGORY_KEYS:
        selection = outfit_pack.resolve_active_selection(store, category)
        if selection.effective_pack_id != request["pack_id"]:
            raise ValueError(f"Runtime selected a different pack for {category}.")
        path = outfit_pack.installed_pack_path(store, selection.effective_pack_id)
        if path.resolve() != (output / f"assets/official-packs/{request['pack_id']}.mohan-outfit").resolve():
            raise ValueError("Runtime selected a pack outside this isolated preview.")
        pack = outfit_pack.inspect_outfit_pack(path)
        item = next(item for item in pack.items if (
            item.category == category and item.item_id == selection.effective_item_id
        ))
        variant = next(value for value in item.variants if value.variant_id == selection.effective_variant_id)
        pose = outfit_pack.resolve_variant_for_view(variant, request["view_id"])
        resolved.update({asset.path: asset.sha256 for asset in pose.assets})
    for pack in request.get("pack_updates", []):
        for member in pack["members"]:
            if resolved.get(member["target"]) != member["sha256"]:
                raise ValueError(f"Runtime did not select the replacement member: {member['target']}")
    return resolved
