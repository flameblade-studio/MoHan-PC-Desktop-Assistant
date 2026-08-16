from __future__ import annotations

lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from domain.autonomous_wardrobe import WardrobeCandidate
lazy from domain.outfit_pack import (
    InstalledEnsemble,
    InstalledSelection,
    OutfitPack,
    OutfitPackError,
    apply_appearance_selection,
    apply_ensemble,
    install_outfit_pack,
    list_installed_ensembles,
    list_installed_selections,
    restore_builtin_outfit,
)

BUILTIN_OUTFIT_ID = "mohan.default.blue-silver"


@dataclass(frozen=True, slots=True)
class InstalledOutfit:
    outfit_id: str
    display_name: str
    compatible: bool
    built_in: bool = False
    selection: InstalledSelection | None = None
    ensemble: InstalledEnsemble | None = None


def _selection_id(selection: InstalledSelection) -> str:
    return "/".join(
        (selection.pack_id, selection.item_id, selection.variant_id)
    )


def _localized_name(selection: InstalledSelection, language: str) -> str:
    language = language if language in selection.variant_display_names else "zh-TW"
    return " · ".join(
        (
            selection.pack_display_names[language],
            selection.item_display_names[language],
            selection.variant_display_names[language],
        )
    )


def _ensemble_id(ensemble: InstalledEnsemble) -> str:
    return "/".join((ensemble.pack_id, ensemble.ensemble_id))


def _localized_ensemble_name(
    ensemble: InstalledEnsemble,
    language: str,
) -> str:
    language = (
        language if language in ensemble.ensemble_display_names else "zh-TW"
    )
    return " · ".join(
        (
            ensemble.pack_display_names[language],
            ensemble.ensemble_display_names[language],
        )
    )


class WardrobeService:
    """Validated v2 outfit installation and selection boundary."""

    def __init__(self, install_root: Path) -> None:
        self.install_root = Path(install_root)

    def outfits(self, language: str = "zh-TW") -> tuple[InstalledOutfit, ...]:
        built_in = InstalledOutfit(
            BUILTIN_OUTFIT_ID,
            "墨寒藍銀劍裝",
            True,
            True,
        )
        ensembles = tuple(
            InstalledOutfit(
                _ensemble_id(ensemble),
                _localized_ensemble_name(ensemble, language),
                True,
                ensemble=ensemble,
            )
            for ensemble in list_installed_ensembles(self.install_root)
        )
        ensemble_garments = {
            *(
                (ensemble.pack_id, selection.item_id, selection.variant_id)
                for selection in ensemble.selections
                if selection.category == "garment"
                and selection.item_id is not None
                and selection.variant_id is not None
            )
            for ensemble in list_installed_ensembles(self.install_root)
        }
        separate_variants = tuple(
            InstalledOutfit(
                _selection_id(selection),
                _localized_name(selection, language),
                True,
                selection=selection,
            )
            for selection in list_installed_selections(
                self.install_root,
                "garment",
            )
            if (
                selection.pack_id,
                selection.item_id,
                selection.variant_id,
            ) not in ensemble_garments
        )
        return (built_in, *ensembles, *separate_variants)

    def install(self, source: Path) -> OutfitPack:
        return install_outfit_pack(Path(source), self.install_root)

    def apply(self, outfit_id: str) -> InstalledOutfit:
        if outfit_id == BUILTIN_OUTFIT_ID:
            restore_builtin_outfit(self.install_root)
            return self.outfits()[0]
        match = next(
            (
                outfit
                for outfit in self.outfits()
                if outfit.outfit_id == outfit_id
            ),
            None,
        )
        if match is None:
            raise OutfitPackError(
                "The selected complete outfit is not installed."
            )
        if match.ensemble is not None:
            apply_ensemble(
                self.install_root,
                match.ensemble.pack_id,
                match.ensemble.ensemble_id,
            )
        elif match.selection is not None:
            apply_appearance_selection(self.install_root, match.selection)
        else:
            raise OutfitPackError(
                "The selected complete outfit has no applicable content."
            )
        return match

    def autonomous_candidates(self) -> tuple[WardrobeCandidate, ...]:
        return tuple(
            WardrobeCandidate(
                _ensemble_id(ensemble),
                ensemble.autonomous_profile,
            )
            for ensemble in list_installed_ensembles(self.install_root)
        )

    @staticmethod
    def selected_outfit(setting: object) -> str:
        value = str(setting or "").strip()
        return value or BUILTIN_OUTFIT_ID
