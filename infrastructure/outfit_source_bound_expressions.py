"""Resolve portable whole-portrait expressions from the active outfit pack."""

from __future__ import annotations

lazy import hashlib
lazy import zipfile
lazy from pathlib import Path

lazy from domain.outfit_pack import (
    OFFICIAL_PACK_ROOT,
    OutfitPackError,
    inspect_installed_outfit_pack,
    installed_pack_path,
    resolve_active_selection,
)
lazy from infrastructure.exasperated_candidate_assets import (
    ExasperatedCandidateAssets,
)


class OutfitSourceBoundExpressionProvider:
    """Return a portrait only when its garment and hair bindings are active."""

    def __init__(
        self,
        store: Path,
        *,
        official_pack_root: Path = OFFICIAL_PACK_ROOT,
    ) -> None:
        self._store = Path(store)
        self._official_pack_root = Path(official_pack_root)

    def assets_for(
        self,
        expression_id: str,
    ) -> ExasperatedCandidateAssets | None:
        try:
            active = {
                category: resolve_active_selection(
                    self._store,
                    category,
                    official_pack_root=self._official_pack_root,
                )
                for category in ("garment", "hairstyle")
            }
            pack_ids = {
                selection.effective_pack_id for selection in active.values()
            }
            if len(pack_ids) != 1 or "builtin" in pack_ids:
                return None
            pack_id = pack_ids.pop()
            path = installed_pack_path(
                self._store,
                pack_id,
                official_pack_root=self._official_pack_root,
            )
            pack = inspect_installed_outfit_pack(path)
            if pack is None:
                return None
            expression = pack.source_bound_expressions.get(expression_id)
            if expression is None:
                return None
            for category, binding in expression.selections.items():
                selection = active[category]
                if (
                    selection.effective_item_id,
                    selection.effective_variant_id,
                ) != (binding.item_id, binding.variant_id):
                    return None
            with zipfile.ZipFile(path) as archive:
                portrait = archive.read(expression.portrait.path)
                mouths = {
                    name: archive.read(asset.path)
                    for name, asset in expression.mouths.items()
                }
            records = {
                expression.portrait.path: (
                    portrait,
                    expression.portrait.sha256,
                ),
                **{
                    expression.mouths[name].path: (
                        payload,
                        expression.mouths[name].sha256,
                    )
                    for name, payload in mouths.items()
                },
            }
            if any(
                hashlib.sha256(payload).hexdigest() != digest
                for payload, digest in records.values()
            ):
                return None
            return ExasperatedCandidateAssets(
                {},
                mouths,
                portrait=portrait,
                cache_key=f"{pack_id}:{expression.cache_key}",
            )
        except (
            KeyError,
            OSError,
            OutfitPackError,
            ValueError,
            zipfile.BadZipFile,
        ):
            return None
