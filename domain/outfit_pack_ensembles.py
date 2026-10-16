"""Parse body-pack-backed appearance ensembles outside the pack facade."""

from __future__ import annotations

lazy import hashlib
lazy import zipfile
lazy from builtins import frozendict
lazy from collections.abc import Callable, Iterable
lazy from dataclasses import dataclass
lazy from domain._outfit_pack_models import (
    AppearanceEnsemble,
    AppearanceItem,
    AutonomousStyleProfile,
    EnsembleRender,
    EnsembleSelection,
)
lazy from domain.body_pack import BodyPackError, parse_body_pack_reference
lazy from domain.character_layer_plan import CharacterLayerPlanError, parse_character_layer_views
lazy from domain.outfit_pack_assets import OutfitPackError


ACCESSORY_KINDS = ("weapon", "handheld", "jewelry", "foreground-effect")


@dataclass(frozen=True, slots=True)
class EnsembleParser:
    identifier: Callable[[object, str], str]
    localized_names: Callable[[object], frozendict[str, str]]
    autonomous_profile: Callable[[object], AutonomousStyleProfile]
    selection_categories: tuple[str, ...]
    optional_categories: frozenset[str]


def _available_variants(items: list[AppearanceItem]) -> set[tuple[str, str, str]]:
    return {
        *((item.category, item.item_id, variant.variant_id) for item in items for variant in item.variants),
    }


def _ensemble_selection(
    category: str,
    selection: object,
    available: set[tuple[str, str, str]],
    parser: EnsembleParser,
) -> EnsembleSelection:
    if selection is None:
        if category not in {"headwear", "makeup", *ACCESSORY_KINDS}:
            raise OutfitPackError("Garment and hairstyle require a selected variant.")
        return EnsembleSelection(category, None, None)
    if not isinstance(selection, dict) or set(selection) != {"item_id", "variant_id"}:
        raise OutfitPackError("Provide a supported ensemble selection.")
    identity = (
        category,
        parser.identifier(selection["item_id"], "ensemble item"),
        parser.identifier(selection["variant_id"], "ensemble variant"),
    )
    if identity not in available:
        raise OutfitPackError("Ensemble must reference an item in the same pack.")
    return EnsembleSelection(*identity)


def _ensemble_render(value: object, archive: zipfile.ZipFile, names: set[str]) -> EnsembleRender:
    if not isinstance(value, dict) or set(value) != {"type", "body_pack", "layer_views"}:
        raise OutfitPackError("Provide a supported ensemble render declaration.")
    if value["type"] != "body_pack":
        raise OutfitPackError("Only the body_pack ensemble renderer is supported.")
    try:
        body_pack = parse_body_pack_reference(value["body_pack"])
        layer_views = parse_character_layer_views(value["layer_views"])
    except (BodyPackError, CharacterLayerPlanError) as error:
        raise OutfitPackError(f"Ensemble render declaration is invalid: {error}") from None
    for plan in layer_views.values():
        for asset in (*plan.layers, *((plan.base_hide,) if plan.base_hide is not None else ())):
            if not asset.path.lower().endswith(".png") or asset.path not in names:
                raise OutfitPackError("Every body-pack layer must reference a declared PNG member.")
            payload = archive.read(asset.path)
            if hashlib.sha256(payload).hexdigest() != asset.sha256:
                raise OutfitPackError(
                    "Body-pack layer integrity check requires attention.",
                    reason="manifest_asset_hash_mismatch",
                    asset_path=asset.path,
                )
    return EnsembleRender("body_pack", body_pack, layer_views)


def _ensemble(
    entry: object,
    available: set[tuple[str, str, str]],
    archive: zipfile.ZipFile,
    names: set[str],
    parser: EnsembleParser,
) -> AppearanceEnsemble:
    required = {"id", "display_names", "selections", "autonomous_profile"}
    allowed = required | {"render"}
    if not isinstance(entry, dict) or not required <= set(entry) or set(entry) - allowed:
        raise OutfitPackError("Provide a supported ensemble declaration.")
    selections = entry["selections"]
    required = set(parser.selection_categories) - parser.optional_categories
    if not isinstance(selections, dict) or not required <= set(selections) <= set(parser.selection_categories):
        raise OutfitPackError("Ensemble must declare every appearance category.")
    typed = tuple(
        _ensemble_selection(category, selections[category], available, parser)
        for category in parser.selection_categories
        if category in selections
    )
    profile = parser.autonomous_profile(entry["autonomous_profile"])
    render = _ensemble_render(entry["render"], archive, names) if "render" in entry else None
    return AppearanceEnsemble(
        parser.identifier(entry["id"], "ensemble"),
        parser.localized_names(entry["display_names"]),
        typed,
        profile,
        render,
    )


def parse_ensembles(
    value: object,
    items: list[AppearanceItem],
    archive: zipfile.ZipFile,
    names: set[str],
    parser: EnsembleParser,
) -> tuple[AppearanceEnsemble, ...]:
    if not isinstance(value, list):
        raise OutfitPackError("Ensembles must be a list.")
    available = _available_variants(items)
    parsed = tuple(_ensemble(
        entry, available, archive, names,
        parser=parser,
    ) for entry in value)
    if len({ensemble.ensemble_id for ensemble in parsed}) != len(parsed):
        raise OutfitPackError("Duplicate ensemble identifier.")
    return parsed


def render_layer_paths(ensembles: Iterable[AppearanceEnsemble]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(
        asset.path
        for ensemble in ensembles
        if ensemble.render is not None
        for plan in ensemble.render.layer_views.values()
        for asset in (*plan.layers, *((plan.base_hide,) if plan.base_hide is not None else ()))
    ))


__all__ = ("EnsembleParser", "parse_ensembles", "render_layer_paths")
