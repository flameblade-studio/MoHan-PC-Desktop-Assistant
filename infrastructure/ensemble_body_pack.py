"""Route explicitly selected outfit ensembles through their declared body pack."""
from __future__ import annotations

lazy import zipfile
lazy from builtins import sentinel
lazy from collections.abc import Callable, Iterable, Mapping
lazy from pathlib import Path
lazy from typing import Any, Protocol, cast, overload

lazy from PySide6.QtGui import QPixmap
lazy from domain.body_pack import BodyPackMismatchError, BodyPackSource
lazy from domain.character_layer_plan import CharacterLayerAsset, CharacterLayerMask, CharacterLayerPlan
lazy from domain.character_pose import canonical_view_id
lazy from domain.character_source import CharacterSource
lazy from domain.face_rig import FaceMotionFrame
lazy from domain.character_renderer_compatibility import validated_renderer_rig
lazy from domain.outfit_pack import InstalledEnsemble, OutfitPackError, installed_pack_path, resolve_active_ensemble
lazy from domain.outfit_pack_store import OfficialPackRoots
lazy from infrastructure.body_pack_presentation import (
    _body_pack_makeup_applier,
    body_pack_renderer_factory,
    body_pack_selection_factory,
)
lazy from infrastructure.body_pack_reader import BodyPackReader, resolve_body_pack, validate_body_pack_binding
lazy from infrastructure.body_pack_renderer import BodyPackRenderer, create_body_pack_renderer
lazy from infrastructure.installed_body_packs import installed_body_pack_root
lazy from domain.outfit_pack_makeup import MAKEUP_STATE_FILE


_UNSET = sentinel("_UNSET")


class FaceRendererProtocol(Protocol):
    def render(
        self, base: QPixmap, motion: FaceMotionFrame, layers: object,
        *, aperture: float | None = None,
    ) -> QPixmap: ...

    def render_overlay(
        self, base: QPixmap, source: QPixmap, *, mask: QPixmap | None = None,
        opacity: float = 1.0, eye_state: str = "rest", view_id: str | None = None,
        makeup_view_id: str | None = None,
    ) -> QPixmap: ...


class FullBodyRendererProtocol(Protocol):
    def render_view(
        self, view_id: str, motion: FaceMotionFrame, **options: object,
    ) -> QPixmap: ...


def _file_token(path: Path) -> tuple[int, int, int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino


def _layer_view_aliases(
    source: CharacterSource,
    body: BodyPackSource,
    layer_views: Mapping[str, CharacterLayerPlan],
) -> dict[str, str]:
    """Bind authored silhouettes such as front-exasperated to physical body views."""
    rig = validated_renderer_rig(source)
    half_views = {view.view_id for view in body.manifest.half_body}
    aliases = {}
    for mapping in (rig.pose_silhouettes, rig.gesture_silhouettes):
        aliases.update({
            source_view: silhouette for source_view, silhouette in mapping.items()
            if source_view in half_views and silhouette in layer_views and silhouette != source_view
        })
    if "exasperated" in half_views and "front-exasperated" in layer_views:
        aliases["exasperated"] = "front-exasperated"
    return aliases


class EnsembleBodyPackRouter:
    """Resolve explicit active ensembles and share one bounded body renderer."""

    def __init__(
        self,
        source: CharacterSource,
        outfit_store: Path,
        official_pack_roots: OfficialPackRoots,
        *,
        body_pack_roots: Iterable[str | Path] | None = None,
    ) -> None:
        self._source = source
        self._outfit_store = Path(outfit_store)
        self._official_pack_roots = official_pack_roots
        self._body_pack_roots = tuple(
            Path(root) for root in (
                body_pack_roots if body_pack_roots is not None else (installed_body_pack_root(),)
            )
        )
        self._selection_token: object | tuple[int, int, int, int] | None = _UNSET
        self._state_token: object | tuple[object, object] = _UNSET
        self._selection: InstalledEnsemble | None = None
        self._selection_error: BodyPackMismatchError | None = None
        self._renderer: BodyPackRenderer | None = None
        self._renderer_signature: tuple[object, ...] | None = None
        self._archive_token: object | tuple[int, int, int, int] | None = _UNSET

    def face_renderer(self, legacy: FaceRendererProtocol) -> EnsembleFaceRenderer:
        return EnsembleFaceRenderer(legacy, self)

    def full_body_renderer(self, legacy: FullBodyRendererProtocol) -> EnsembleFullBodyRenderer:
        return EnsembleFullBodyRenderer(legacy, self)

    def _clear_renderer_cache(self) -> None:
        if self._renderer is not None:
            self._renderer.clear_cache()

    def _refresh_selection(self) -> None:
        active_token = _file_token(self._outfit_store / "active.json")
        makeup_token = _file_token(self._outfit_store / MAKEUP_STATE_FILE)
        state_token = (active_token, makeup_token)
        if state_token != self._state_token:
            self._state_token = state_token
            self._clear_renderer_cache()
        if active_token == self._selection_token:
            if self._selection_error is not None:
                raise self._selection_error
            return
        self._selection_token = active_token
        self._archive_token = _UNSET
        self._selection = None
        self._selection_error = None
        try:
            self._selection = resolve_active_ensemble(
                self._outfit_store, official_pack_root=self._official_pack_roots,
            )
        except OutfitPackError as error:
            self._selection_error = BodyPackMismatchError(
                "outfit_pack_missing",
                f"The explicitly selected outfit ensemble is unavailable; download and install its pack: {error}",
            )
            raise self._selection_error from error

    @overload
    def renderer_for(self, legacy: FaceRendererProtocol) -> FaceRendererProtocol | BodyPackRenderer: ...

    @overload
    def renderer_for(self, legacy: FullBodyRendererProtocol) -> FullBodyRendererProtocol | BodyPackRenderer: ...

    def renderer_for(
        self, legacy: FaceRendererProtocol | FullBodyRendererProtocol,
    ) -> FaceRendererProtocol | FullBodyRendererProtocol | BodyPackRenderer:
        self._refresh_selection()
        selected = self._selection
        if selected is None or selected.render is None:
            return legacy
        try:
            archive_path = installed_pack_path(
                self._outfit_store, selected.pack_id,
                official_pack_root=self._official_pack_roots,
            )
        except OutfitPackError as error:
            raise BodyPackMismatchError(
                "outfit_pack_missing",
                "Download and install the outfit package required by this body-pack ensemble.",
                selected.pack_id,
            ) from error
        archive_token = _file_token(archive_path)
        if archive_token != self._archive_token:
            if self._archive_token is not _UNSET:
                try:
                    selected = resolve_active_ensemble(
                        self._outfit_store, official_pack_root=self._official_pack_roots,
                    )
                except OutfitPackError as error:
                    raise BodyPackMismatchError(
                        "outfit_pack_missing",
                        "The selected outfit package changed and must be downloaded and installed again.",
                    ) from error
                self._selection = selected
                if selected is None or selected.render is None:
                    self._clear_renderer_cache()
                    self._renderer_signature = None
                    return legacy
            self._archive_token = archive_token
        reference = selected.render.body_pack
        body_tokens = tuple(
            _file_token(root / reference.id / "manifest.json")
            for root in self._body_pack_roots
        )
        signature = (
            selected.pack_id,
            selected.ensemble_id,
            reference,
            archive_token,
            body_tokens,
        )
        if signature != self._renderer_signature:
            self._clear_renderer_cache()
            self._renderer = self._create_renderer(selected, archive_path)
            self._renderer_signature = signature
        if self._renderer is None:
            raise BodyPackMismatchError(
                "body_pack_missing", "Download and install the required body pack.", reference.id,
            )
        return self._renderer

    def _create_renderer(
        self,
        selected: InstalledEnsemble,
        archive_path: Path,
    ) -> BodyPackRenderer:
        render = selected.render
        if render is None:
            raise TypeError("A body-pack renderer requires an explicit ensemble binding.")
        try:
            body = resolve_body_pack(render.body_pack, self._body_pack_roots)
            rig = validated_renderer_rig(self._source)
            aliases = _layer_view_aliases(self._source, body, render.layer_views)
            half_ids = {view.view_id for view in body.manifest.half_body}
            full_ids = {view.view_id for view in body.manifest.full_body}
            validation_views = {
                view_id: plan for view_id, plan in render.layer_views.items()
                if view_id in full_ids or view_id in half_ids
            }
            for body_view, layer_view in aliases.items():
                if body_view not in validation_views and layer_view in render.layer_views:
                    validation_views[body_view] = render.layer_views[layer_view]
            validate_body_pack_binding(
                body,
                expected_full_canvas=(rig.full_body_canvas.width, rig.full_body_canvas.height),
                expected_half_canvas=(rig.half_body_asset_canvas.width, rig.half_body_asset_canvas.height),
                required_view_ids=tuple(canonical_view_id(yaw) for yaw in rig.view_ring.yaws),
                layer_views=validation_views,
            )
            with zipfile.ZipFile(archive_path) as archive:
                declared = set(archive.namelist())
        except BodyPackMismatchError:
            raise
        except (OSError, zipfile.BadZipFile, OutfitPackError, ValueError, TypeError) as error:
            raise BodyPackMismatchError(
                "invalid_manifest",
                f"The selected body-pack ensemble could not be validated: {type(error).__name__}.",
                selected.ensemble_id,
            ) from error

        def load_layer(record: CharacterLayerAsset | CharacterLayerMask) -> bytes:
            if record.path not in declared:
                raise BodyPackMismatchError(
                    "missing_file", "Download and reinstall the outfit package with its declared body layers.",
                    record.path,
                )
            try:
                with zipfile.ZipFile(archive_path) as archive:
                    return archive.read(record.path)
            except (OSError, zipfile.BadZipFile, KeyError) as error:
                raise BodyPackMismatchError(
                    "missing_file", "Download and reinstall the outfit package with its declared body layers.",
                    record.path,
                ) from error

        return create_body_pack_renderer(
            body,
            render.layer_views,
            load_layer,
            apply_makeup=_body_pack_makeup_applier(
                self._outfit_store, self._source.assets.asset_root,
                tuple(Path(root) for root in (
                    self._official_pack_roots
                    if isinstance(self._official_pack_roots, tuple)
                    else (self._official_pack_roots,)
                )),
            ),
            view_aliases=aliases,
        )


class EnsembleFaceRenderer:
    """Face-renderer port that follows the currently explicit ensemble."""

    def __init__(self, legacy: FaceRendererProtocol, router: EnsembleBodyPackRouter) -> None:
        self._legacy = legacy
        self._router = router

    def _current(self) -> FaceRendererProtocol:
        return cast(FaceRendererProtocol, self._router.renderer_for(self._legacy))

    @property
    def _outfit_overlay(self) -> object | None:
        """Preserve the legacy native-eye authority hook for blink compositing."""
        return getattr(self._current(), "_outfit_overlay", None)

    @property
    def supports_wink(self) -> bool:
        return bool(getattr(self._current(), "supports_wink", True))

    def supports_discrete_speech(self, expression: str) -> bool:
        method = getattr(self._current(), "supports_discrete_speech", None)
        return bool(method(expression)) if callable(method) else False

    def render(
        self, base: QPixmap, motion: FaceMotionFrame, layers: object,
        *, aperture: float | None = None,
    ) -> QPixmap:
        return self._current().render(base, motion, layers, aperture=aperture)

    def render_complete_blink(self, base: QPixmap, eye_state: str) -> QPixmap | None:
        renderer = self._current()
        method = getattr(renderer, "render_complete_blink", None)
        return cast(QPixmap | None, method(base, eye_state)) if callable(method) else None

    def render_overlay(
        self,
        base: QPixmap,
        source: QPixmap,
        *,
        mask: QPixmap | None = None,
        opacity: float = 1.0,
        eye_state: str = "rest",
        view_id: str | None = None,
        makeup_view_id: str | None = None,
    ) -> QPixmap:
        return self._current().render_overlay(
            base, source, mask=mask, opacity=opacity, eye_state=eye_state,
            view_id=view_id, makeup_view_id=makeup_view_id,
        )


class EnsembleFullBodyRenderer:
    """Full-body renderer port that shares the face route's body renderer."""

    def __init__(self, legacy: FullBodyRendererProtocol, router: EnsembleBodyPackRouter) -> None:
        self._legacy = legacy
        self._router = router
        self.body_pack_required = False

    def render_view(
        self, view_id: str, motion: FaceMotionFrame, **options: object,
    ) -> QPixmap:
        renderer = cast(FullBodyRendererProtocol, self._router.renderer_for(self._legacy))
        self.body_pack_required = isinstance(renderer, BodyPackRenderer)
        return renderer.render_view(view_id, motion, **options)


def route_face_renderer(
    router: EnsembleBodyPackRouter | None,
    legacy: FaceRendererProtocol,
) -> FaceRendererProtocol:
    return legacy if router is None else router.face_renderer(legacy)


def route_full_body_renderer(
    router: EnsembleBodyPackRouter | None,
    legacy: object,
) -> FullBodyRendererProtocol:
    return cast(
        FullBodyRendererProtocol,
        legacy if router is None else router.full_body_renderer(
            cast(FullBodyRendererProtocol, legacy),
        ),
    )


def create_body_pack_presentation_context(
    character_source: CharacterSource,
    data_root: Path,
    official_pack_roots: OfficialPackRoots,
) -> tuple[Path, Callable[[], bool], Any, bool, Any, Callable[[], Any], Any, bool]:
    """Build the shared body route and its official-selection predicate."""

    outfit_dir = data_root / "outfits"
    pack_roots = tuple(Path(root) for root in (
        official_pack_roots if isinstance(official_pack_roots, tuple)
        else (official_pack_roots,)
    ))
    official_selection = body_pack_selection_factory(
        character_source, outfit_dir, pack_roots,
    )
    body_pack, fallback_active, body_error, body_renderer, ensemble_router = create_body_pack_context(
        character_source, data_root, official_pack_roots,
        official_selection=official_selection,
    )
    selection_aware = body_pack is not None and hasattr(
        getattr(character_source, "appearance", None), "appearance_defaults",
    )
    return (
        outfit_dir, official_selection, body_pack, fallback_active, body_error,
        body_renderer, ensemble_router, selection_aware,
    )


def create_body_pack_context(
    source: CharacterSource,
    data_root: Path,
    official_pack_roots: OfficialPackRoots,
    *,
    official_selection: Callable[[], bool] | None = None,
) -> tuple[BodyPackReader | None, bool, BodyPackMismatchError | None, Callable[[], BodyPackRenderer], EnsembleBodyPackRouter | None]:
    body_pack = cast(BodyPackReader | None, getattr(source, "resolved_body_pack", None))
    if callable(body_pack):
        body_pack = body_pack()
    fallback_active = bool(getattr(source, "body_pack_fallback_active", False))
    body_pack_error = getattr(source, "body_pack_resolution_error", None)
    pack_roots = tuple(Path(root) for root in (official_pack_roots if isinstance(official_pack_roots, tuple) else (official_pack_roots,)))
    body_renderer = body_pack_renderer_factory(
        source,
        body_pack,
        data_root / "outfits",
        pack_roots,
        official_selection=official_selection,
    )
    router = (
        EnsembleBodyPackRouter(source, data_root / "outfits", official_pack_roots)
        if body_pack is None and hasattr(source, "appearance") and not fallback_active
        else None
    )
    return body_pack, fallback_active, body_pack_error, body_renderer, router


__all__ = (
    "EnsembleBodyPackRouter",
    "EnsembleFaceRenderer",
    "EnsembleFullBodyRenderer",
    "create_body_pack_context",
    "route_face_renderer",
    "route_full_body_renderer",
)
