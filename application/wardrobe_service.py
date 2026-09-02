from __future__ import annotations

lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from domain.autonomous_wardrobe import WardrobeCandidate
lazy from domain.outfit_pack import (
    BUILTIN_MAKEUP_PACK_ID,
    BUILTIN_MAKEUP_VARIANTS,
    InstalledEnsemble,
    IncompatibleBodyProfileError,
    InstalledSelection,
    OutfitPack,
    OutfitPackError,
    SELECTION_CATEGORIES,
    apply_appearance_selection,
    apply_ensemble,
    clear_appearance_selection,
    install_outfit_pack,
    list_installed_ensembles,
    list_installed_selections,
    list_stale_body_profile_packs,
    resolve_active_selection,
    restore_builtin_outfit,
)
lazy from domain.outfit_pack_makeup import (
    ACTIVE_STATE_FILE,
    MAKEUP_STATE_FILE,
    read_makeup_intensity,
    select_builtin_makeup,
    verify_makeup_layers,
    write_makeup_intensity,
)
lazy from domain.outfit_pack_official import OFFICIAL_OUTFIT_PACK_ID, official_outfit_ensemble

# Opaque sentinel persisted in the ``active_outfit_id`` setting since v2; it
# means "the built-in look" (today the official Blue-and-White Hanfu pack plus
# the built-in classic makeup) and is kept stable so saved profiles keep working.
BUILTIN_OUTFIT_ID = "mohan.default.blue-silver"
BUILTIN_OUTFIT_FALLBACK_NAME = "墨寒藍白漢服"
BARE_MAKEUP_ID = "none"
BUILTIN_MAKEUP_PREFIX = "builtin/"
SELECTION_ID_PARTS = 3


@dataclass(frozen=True, slots=True)
class InstalledOutfit:
    outfit_id: str
    display_name: str
    compatible: bool
    built_in: bool = False
    selection: InstalledSelection | None = None
    ensemble: InstalledEnsemble | None = None


@dataclass(frozen=True, slots=True)
class MakeupOption:
    """One entry of the wardrobe makeup menu.

    ``option_id`` is ``none`` (bare face), ``builtin/<variant>`` for the two
    built-in variants, or ``pack/item/variant`` for an installed pack.  A
    built-in option is ``available`` only while the official built-in makeup
    pack ships with the app; the entry stays selectable so the choice persists.
    """

    option_id: str
    display_name: str
    built_in: bool
    available: bool
    selection: InstalledSelection | None = None


@dataclass(frozen=True, slots=True)
class MakeupState:
    option_id: str
    requested_option_id: str
    fallback: bool


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
    if ensemble.pack_id == OFFICIAL_OUTFIT_PACK_ID:
        return BUILTIN_OUTFIT_ID
    return "/".join((ensemble.pack_id, ensemble.ensemble_id))


def _localized_pack_name(ensemble: InstalledEnsemble, language: str) -> str:
    language = language if language in ensemble.pack_display_names else "zh-TW"
    return ensemble.pack_display_names[language]


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


def _makeup_option_id(pack_id: str, item_id: str, variant_id: str) -> str:
    if pack_id == "builtin" and item_id == "none":
        return BARE_MAKEUP_ID
    if pack_id in {"builtin", BUILTIN_MAKEUP_PACK_ID}:
        # The ``builtin/builtin/builtin`` sentinel of a fresh profile means the classic variant.
        variant = variant_id if variant_id in BUILTIN_MAKEUP_VARIANTS else BUILTIN_MAKEUP_VARIANTS[0]
        return f"{BUILTIN_MAKEUP_PREFIX}{variant}"
    return "/".join((pack_id, item_id, variant_id))


class WardrobeService:
    """Validated v2 outfit installation and selection boundary."""

    def __init__(self, install_root: Path) -> None:
        self.install_root = Path(install_root)

    def outfits(self, language: str = "zh-TW") -> tuple[InstalledOutfit, ...]:
        # The official default pack is the built-in entry itself; it is never
        # listed a second time as a removable ensemble or loose variant.
        every_ensemble = list_installed_ensembles(self.install_root)
        official = official_outfit_ensemble(every_ensemble)
        installed_ensembles = tuple(
            ensemble for ensemble in every_ensemble if ensemble.pack_id != OFFICIAL_OUTFIT_PACK_ID
        )
        built_in = InstalledOutfit(
            BUILTIN_OUTFIT_ID,
            BUILTIN_OUTFIT_FALLBACK_NAME if official is None else _localized_pack_name(official, language),
            True,
            True,
            ensemble=official,
        )
        ensembles = tuple(
            InstalledOutfit(
                _ensemble_id(ensemble),
                _localized_ensemble_name(ensemble, language),
                True,
                ensemble=ensemble,
            )
            for ensemble in installed_ensembles
        )
        ensemble_garments = {
            *(
                (ensemble.pack_id, selection.item_id, selection.variant_id)
                for selection in ensemble.selections
                if selection.category == "garment"
                and selection.item_id is not None
                and selection.variant_id is not None
            )
            for ensemble in (*installed_ensembles, *(() if official is None else (official,)))
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
        # Generation-1 packs stay visible so the owner can see why they are
        # greyed out and remove them; they are never resolvable or applied.
        stale = tuple(
            InstalledOutfit(pack_id, pack_id, False)
            for pack_id in list_stale_body_profile_packs(self.install_root)
        )
        return (built_in, *ensembles, *separate_variants, *stale)

    def install(self, source: Path) -> OutfitPack:
        # Makeup arrives through the same single-file import as every other
        # category; its pixel gate runs before the archive is copied into place.
        verify_makeup_layers(Path(source))
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
        if not match.compatible:
            raise IncompatibleBodyProfileError(
                f"Outfit pack {match.outfit_id!r} was authored for another body-profile generation."
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

    # -- makeup category ----------------------------------------------------

    def makeup_options(self, language: str = "zh-TW") -> tuple[MakeupOption, ...]:
        """Bare face, the two built-in variants, then every installed makeup variant."""
        installed = list_installed_selections(self.install_root, "makeup")
        official = {
            selection.variant_id: selection
            for selection in installed
            if selection.pack_id == BUILTIN_MAKEUP_PACK_ID
        }
        built_in = tuple(
            MakeupOption(
                f"{BUILTIN_MAKEUP_PREFIX}{variant_id}",
                _localized_name(official[variant_id], language) if variant_id in official else "",
                True,
                variant_id in official,
                official.get(variant_id),
            )
            for variant_id in BUILTIN_MAKEUP_VARIANTS
        )
        packs = tuple(
            MakeupOption(
                _selection_id(selection),
                _localized_name(selection, language),
                False,
                True,
                selection,
            )
            for selection in installed
            if selection.pack_id != BUILTIN_MAKEUP_PACK_ID
        )
        return (MakeupOption(BARE_MAKEUP_ID, "", True, True), *built_in, *packs)

    def active_makeup(self) -> MakeupState:
        """The effective makeup option; ``fallback`` marks a vanished pack replaced by the built-in default."""
        resolution = resolve_active_selection(self.install_root, "makeup")
        effective = _makeup_option_id(
            resolution.effective_pack_id,
            resolution.effective_item_id,
            resolution.effective_variant_id,
        )
        requested = _makeup_option_id(
            resolution.requested_pack_id,
            resolution.requested_item_id,
            resolution.requested_variant_id,
        )
        if resolution.status == "builtin" and resolution.requested_pack_id == "builtin" and resolution.requested_item_id != "none":
            # The built-in variant is chosen but its official art is not shipped yet:
            # keep showing the user's choice rather than pretending they picked bare.
            effective = requested
        fallback = (
            resolution.requested_pack_id not in {"builtin", BUILTIN_MAKEUP_PACK_ID}
            and resolution.requested_pack_id != resolution.effective_pack_id
        )
        return MakeupState(effective, requested, fallback)

    def apply_makeup(self, option_id: str) -> None:
        if option_id == BARE_MAKEUP_ID:
            clear_appearance_selection(self.install_root, "makeup")
            return
        if option_id.startswith(BUILTIN_MAKEUP_PREFIX):
            select_builtin_makeup(self.install_root, option_id[len(BUILTIN_MAKEUP_PREFIX):])
            return
        parts = option_id.split("/")
        if len(parts) != SELECTION_ID_PARTS:
            raise OutfitPackError("Invalid makeup selection identifier.")
        match = next(
            (
                selection
                for selection in list_installed_selections(self.install_root, "makeup")
                if _selection_id(selection) == option_id
            ),
            None,
        )
        if match is None:
            raise OutfitPackError("The selected makeup is not installed.")
        apply_appearance_selection(self.install_root, match)

    def makeup_intensity(self) -> float:
        return read_makeup_intensity(self.install_root)

    def appearance_active(self) -> bool:
        """True when any slot resolves to an installed pack, so a bare preview would be wrong."""
        try:
            return any(
                resolve_active_selection(self.install_root, category).status == "installed"
                for category in SELECTION_CATEGORIES
            )
        except (IncompatibleBodyProfileError, OutfitPackError, OSError, ValueError):
            return False

    def appearance_signature(self) -> tuple[tuple[int, int] | None, ...]:
        """Change token of the active look: the selection and makeup state file stamps."""
        tokens: list[tuple[int, int] | None] = []
        for name in (ACTIVE_STATE_FILE, MAKEUP_STATE_FILE):
            try:
                stat = (self.install_root / name).stat()
            except OSError:
                tokens.append(None)
            else:
                tokens.append((stat.st_mtime_ns, stat.st_size))
        return tuple(tokens)

    def set_makeup_intensity(self, value: float) -> float:
        return write_makeup_intensity(self.install_root, value)

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
