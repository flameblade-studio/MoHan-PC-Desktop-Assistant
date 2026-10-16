"""Assemble the shared body renderer and its character makeup adapter."""
from __future__ import annotations

lazy from collections.abc import Callable, Mapping
lazy from functools import cache
lazy from pathlib import Path
lazy from PySide6.QtGui import QPixmap
lazy from domain.body_pack import BodyPackSource
lazy from domain.companion_animation_contract import outfit_silhouette
lazy from domain.character_source import CharacterSource
lazy from domain.face_rig import FaceMotionFrame
lazy from typing import Any
lazy from domain.outfit_pack import (
    list_installed_ensembles,
    resolve_active_ensemble,
    OutfitPackError,
)
lazy from domain.outfit_pack_official import OFFICIAL_BODY_PACK_ENSEMBLE_ID
lazy from domain.outfit_pack_store import OFFICIAL_PACK_ROOT, OfficialPackRoots
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.body_pack_renderer import BodyPackRenderer, MakeupApplier, create_body_pack_renderer
lazy from typing import cast


def outfit_selection_token(
    outfit_dir: Path, official_pack_roots: tuple[Path, ...],
) -> tuple[tuple[str, int, int], ...]:
    """Return the filesystem token used to notice active-selection changes."""

    paths = [outfit_dir / "active.json", outfit_dir / "packages", *official_pack_roots]
    for root in (outfit_dir / "packages", *official_pack_roots):
        paths.extend(sorted(root.glob("*.mohan-outfit")))
    stamps = []
    for path in paths:
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        stamps.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(stamps)


def _official_body_pack_selection(
    character_source: CharacterSource,
    outfit_dir: Path,
    official_pack_roots: tuple[Path, ...],
) -> bool:
    """Recognize only the owner-approved selection for native body layers."""

    appearance = getattr(character_source, "appearance", None)
    defaults = getattr(appearance, "appearance_defaults", None)
    if defaults is None:
        # Structural test sources do not expose appearance defaults.  Preserve
        # their declared body-pack route; real character sources always do.
        return True
    try:
        ensembles = list_installed_ensembles(
            outfit_dir, official_pack_root=official_pack_roots,
        )
        default = next((item for item in ensembles if (
            item.pack_id, item.ensemble_id
        ) == (defaults.outfit_pack_id, defaults.outfit_ensemble_id)), None)
        if default is not None and active_selection_matches_ensemble(
            outfit_dir, default, official_pack_root=official_pack_roots,
        ):
            return True
        active = resolve_active_ensemble(
            outfit_dir, official_pack_root=official_pack_roots,
        )
    except (OSError, OutfitPackError, TypeError, ValueError):
        return False
    return active is not None and active.ensemble_id == OFFICIAL_BODY_PACK_ENSEMBLE_ID


def body_pack_selection_factory(
    character_source: CharacterSource,
    outfit_dir: Path,
    official_pack_roots: tuple[Path, ...],
) -> Callable[[], bool]:
    """Cache the official-selection decision and refresh it on state changes."""

    selection_token: tuple[tuple[str, int, int], ...] | None = None
    official = True

    def official_selected() -> bool:
        nonlocal selection_token, official
        token = outfit_selection_token(outfit_dir, official_pack_roots)
        if token != selection_token:
            official = _official_body_pack_selection(
                character_source, outfit_dir, official_pack_roots,
            )
            selection_token = token
        return official

    return official_selected


def active_selection_matches_ensemble(
    store: Path,
    ensemble: Any,
    *,
    official_pack_root: OfficialPackRoots = OFFICIAL_PACK_ROOT,
) -> bool:
    """Return whether every non-makeup slot still matches one ensemble."""

    from domain.outfit_pack import resolve_active_selection

    for item in ensemble.selections:
        if item.category == "makeup":
            continue
        selected = resolve_active_selection(
            store, item.category, official_pack_root=official_pack_root,
        )
        if item.item_id is None:
            if selected.status != "builtin":
                return False
            continue
        expected = (ensemble.pack_id, item.item_id, item.variant_id)
        if (
            selected.effective_pack_id,
            selected.effective_item_id,
            selected.effective_variant_id,
        ) != expected:
            return False
    return True


class _BodyPackWithCheekFallback(BodyPackRenderer):
    """Keep Stage 1 cheek pixels on the established legacy renderer."""

    def __init__(
        self, body: BodyPackRenderer, views: Mapping[str, object],
        fallback_factory: Callable[[], Any],
    ) -> None:
        self._body = body
        self._views = views
        self._fallback_factory = fallback_factory
        self._fallback: Any = None
        self._last_used_fallback = False

    def _legacy(self) -> Any:
        if self._fallback is None:
            self._fallback = self._fallback_factory()
        return self._fallback

    def _is_excluded_cheek(self, motion: FaceMotionFrame) -> bool:
        return (
            outfit_silhouette(motion.expression, motion.pose.value) == "cheek-rest"
            and "cheek-rest" not in self._views
        )

    def render(
        self, base: QPixmap, motion: FaceMotionFrame, layers: object,
        *, aperture: float | None = None,
    ) -> QPixmap:
        if self._is_excluded_cheek(motion):
            self._last_used_fallback = True
            return self._legacy().render(base, motion, layers, aperture=aperture)
        self._last_used_fallback = False
        return self._body.render(base, motion, layers, aperture=aperture)

    def render_complete_blink(self, base: QPixmap, eye_state: str) -> QPixmap:
        renderer = self._legacy() if self._last_used_fallback else self._body
        return renderer.render_complete_blink(base, eye_state)

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
        renderer = self._legacy() if self._last_used_fallback else self._body
        return renderer.render_overlay(
            base, source, mask=mask, opacity=opacity, eye_state=eye_state,
            view_id=view_id, makeup_view_id=makeup_view_id,
        )

    def render_view(self, view_id: str, motion: FaceMotionFrame, **options: object) -> QPixmap:
        # Full-body previews share this cached wrapper with the face port; they
        # must not reset the face route chosen for the pending blink/overlay.
        return self._body.render_view(view_id, motion, **options)

    def clear_cache(self) -> None:
        self._body.clear_cache()
        if self._fallback is not None:
            self._fallback.clear_cache()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._body, name)


class _SelectionAwareFaceRenderer:
    """Switch between native official frames and the established outfit route."""

    def __init__(
        self,
        body_factory: Callable[[], Any],
        legacy_factory: Callable[[], Any],
        official_selection: Callable[[], bool],
    ) -> None:
        self._body_factory = body_factory
        self._legacy_factory = legacy_factory
        self._official_selection = official_selection
        self._last_selection: bool | None = None
        self._last_renderer: Any = None

    def _current(self) -> Any:
        selected = self._official_selection()
        if selected != self._last_selection:
            self._last_renderer = None
            self._last_selection = selected
        if self._last_renderer is None:
            self._last_renderer = (
                self._body_factory() if selected else self._legacy_factory()
            )
        return self._last_renderer

    def render(self, base: QPixmap, motion: FaceMotionFrame, layers: object, **options: object) -> QPixmap:
        return self._current().render(base, motion, layers, **options)

    def render_complete_blink(self, base: QPixmap, eye_state: str) -> QPixmap | None:
        renderer = self._last_renderer or self._current()
        method = getattr(renderer, "render_complete_blink", None)
        return cast(QPixmap | None, method(base, eye_state)) if callable(method) else None

    def render_overlay(self, base: QPixmap, source: QPixmap, **options: object) -> QPixmap:
        renderer = self._last_renderer or self._current()
        return renderer.render_overlay(base, source, **options)

    @property
    def _outfit_overlay(self) -> Any:
        renderer = self._last_renderer or self._current()
        return getattr(renderer, "_outfit_overlay", None)

    @property
    def supports_wink(self) -> bool:
        renderer = self._last_renderer or self._current()
        return bool(getattr(renderer, "supports_wink", True))

    def supports_discrete_speech(self, expression: str) -> bool:
        renderer = self._last_renderer or self._current()
        method = getattr(renderer, "supports_discrete_speech", None)
        return bool(method(expression)) if callable(method) else False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._last_renderer or self._current(), name)


class _SelectionAwareFullBodyRenderer:
    """Switch full-body previews with the same selection token as the face port."""

    def __init__(
        self,
        body_factory: Callable[[], Any],
        legacy_factory: Callable[[], Any],
        official_selection: Callable[[], bool],
    ) -> None:
        self._body_factory = body_factory
        self._legacy_factory = legacy_factory
        self._official_selection = official_selection
        self._last_selection: bool | None = None
        self._last_renderer: Any = None
        self.body_pack_required = False

    def render_view(self, view_id: str, motion: FaceMotionFrame, **options: object) -> QPixmap:
        official = self._official_selection()
        if official != self._last_selection:
            self._last_renderer = None
            self._last_selection = official
        if self._last_renderer is None:
            self._last_renderer = (
                self._body_factory() if official else self._legacy_factory()
            )
        self.body_pack_required = official
        return self._last_renderer.render_view(view_id, motion, **options)


def selection_aware_face_renderer(
    body_factory: Callable[[], Any],
    legacy_factory: Callable[[], Any],
    official_selection: Callable[[], bool],
    *,
    selection_aware: bool,
) -> Any:
    """Create the body renderer while preserving the legacy selection route."""

    if not selection_aware:
        return body_factory()
    return _SelectionAwareFaceRenderer(
        body_factory, legacy_factory, official_selection,
    )


def selection_aware_full_body_renderer(
    body_factory: Callable[[], Any],
    legacy_factory: Callable[[], Any],
    official_selection: Callable[[], bool],
    *,
    selection_aware: bool,
) -> Any:
    """Create the full-body renderer with the same selection contract."""

    if not selection_aware:
        return body_factory()
    return _SelectionAwareFullBodyRenderer(
        body_factory, legacy_factory, official_selection,
    )


def legacy_mohan_presentation_ports(
    asset_root: Path, create_ports: Callable[[Any], Any],
) -> Any:
    """Lazily build the established renderer for non-official outfits."""

    from infrastructure.bundled_character_source import LegacyMohanCharacterSource

    return create_ports(LegacyMohanCharacterSource(asset_root, load_body_layers=False))


def create_body_pack_outfit_overlay_factory(
    body_pack: Any,
    selection_aware: bool,
    overlay_callbacks: tuple[Callable[..., Any], ...],
    outfit_dir: Path,
    asset_root: Path,
    official_pack_roots: OfficialPackRoots,
    frame_state: tuple[Any, Any],
) -> Callable[..., Any]:
    """Create the shared overlay route without duplicating hand-region state.

    ``overlay_callbacks`` is ``(no_outfit_overlay, overlay_class,
    hand_region_loader)``; the composition root injects the last two so it
    stays the single seam where callers and tests replace them.
    """

    no_outfit_overlay, overlay_class, hand_region_loader = overlay_callbacks
    default_look, native_frames = frame_state
    hand_regions: Any = None
    hand_regions_loaded = False

    def shared_hand_regions() -> Any:
        nonlocal hand_regions, hand_regions_loaded
        if not hand_regions_loaded:
            hand_regions = hand_region_loader(asset_root)
            hand_regions_loaded = True
        return hand_regions

    def outfit_overlay_factory(on_stale_body_profile: Any = None) -> Any:
        if body_pack is not None and not selection_aware:
            return no_outfit_overlay()
        return overlay_class(
            outfit_dir,
            asset_root,
            on_stale_body_profile=on_stale_body_profile,
            visible_hand_region=shared_hand_regions(),
            official_pack_root=official_pack_roots,
            native_frames=(
                False if body_pack is not None
                else default_look.native_frames if default_look is not None else native_frames
            ),
        )

    return outfit_overlay_factory


def create_body_pack_rendering_state(
    character_source: CharacterSource,
    data_root: Path,
    official_pack_roots: OfficialPackRoots,
    *,
    default_character_id: str,
    context_factory: Callable[..., tuple[Any, ...]],
    cheek_fallback_factory: Callable[[], Any],
    render_callbacks: tuple[Callable[..., Any], ...],
) -> tuple[Any, ...]:
    """Assemble body routing state before the composition root builds ports.

    ``render_callbacks`` is ``(frame_paths, default_look_factory,
    no_outfit_overlay, overlay_class, hand_region_loader)``.
    """

    frame_paths, default_look_factory, *overlay_callbacks = render_callbacks
    asset_root = character_source.assets.asset_root
    (
        outfit_dir, official_selection, body_pack, _fallback_active,
        body_pack_error, body_renderer, ensemble_body_router,
        selection_aware_body_pack,
    ) = context_factory(
        character_source, data_root, official_pack_roots,
        default_character_id=default_character_id,
        cheek_fallback_factory=cheek_fallback_factory,
    )
    bindings, native_frames = frame_paths(character_source)
    default_look = (
        default_look_factory(character_source, outfit_dir, official_pack_roots)
        if body_pack is None and "default_look_fullbody" in bindings else None
    )
    outfit_overlay_factory = create_body_pack_outfit_overlay_factory(
        body_pack, selection_aware_body_pack, tuple(overlay_callbacks),
        outfit_dir, asset_root, official_pack_roots, (default_look, native_frames),
    )
    return (
        outfit_dir, official_selection, body_pack, body_pack_error, body_renderer,
        ensemble_body_router, selection_aware_body_pack, bindings, native_frames,
        default_look, outfit_overlay_factory,
    )


def create_body_pack_face_renderer(
    body_pack: Any,
    body_renderer: Callable[[], Any],
    legacy_factory: Callable[[], Any],
    official_selection: Callable[[], bool],
    *,
    selection_aware: bool,
) -> Any | None:
    """Return the body face route when a body pack is declared."""

    if body_pack is None:
        return None
    return selection_aware_face_renderer(
        body_renderer, legacy_factory, official_selection,
        selection_aware=selection_aware,
    )


def create_body_pack_full_body_renderer(
    body_pack: Any,
    body_renderer: Callable[[], Any],
    legacy_factory: Callable[[], Any],
    official_selection: Callable[[], bool],
    *,
    selection_aware: bool,
) -> Any | None:
    """Return the body full-body route when a body pack is declared."""

    if body_pack is None:
        return None
    return selection_aware_full_body_renderer(
        body_renderer, legacy_factory, official_selection,
        selection_aware=selection_aware,
    )


def create_body_pack_routes(
    body_pack: Any,
    body_renderer: Callable[[], Any],
    asset_root: Path,
    create_ports: Callable[[Any], Any],
    official_selection: Callable[[], bool],
    *,
    selection_aware: bool,
    outfit_overlay_factory: Callable[..., Any],
) -> tuple[Callable[[], Any] | None, Callable[[Any], Any] | None]:
    """Prepare lazy face/full-body routes for one declared body pack."""

    if body_pack is None:
        return None, None

    def face_route() -> Any:
        return create_body_pack_face_renderer(
            body_pack, body_renderer,
            lambda: legacy_mohan_presentation_ports(
                asset_root, create_ports,
            ).face_renderer_factory(),
            official_selection, selection_aware=selection_aware,
        )

    def full_body_route(outfit_overlay: Any = None) -> Any:
        return create_body_pack_full_body_renderer(
            body_pack, body_renderer,
            lambda: legacy_mohan_presentation_ports(
                asset_root, create_ports,
            ).full_body_renderer_factory(
                outfit_overlay=(
                    outfit_overlay
                    if outfit_overlay is not None else outfit_overlay_factory()
                ),
            ),
            official_selection, selection_aware=selection_aware,
        )

    return face_route, full_body_route


def _body_pack_makeup_applier(
    outfit_dir: Path, asset_root: Path, official_pack_roots: tuple[Path, ...],
) -> MakeupApplier:
    """Apply the selected character makeup to the protected body frame."""
    overlay = ActiveOutfitOverlay(
        outfit_dir, asset_root, visible_hand_region=None,
        official_pack_root=official_pack_roots, native_frames=True,
    )

    def apply_body_makeup(
        frame: QPixmap, view: str, eye_state: str, viseme: str | None,
    ) -> QPixmap:
        overlay.set_active_mouth_state(viseme)
        return overlay.apply_makeup(frame, view, eye_state=eye_state)

    return apply_body_makeup


def body_pack_renderer_factory(
    character_source: CharacterSource, body_pack: BodyPackSource | None,
    outfit_dir: Path, official_pack_roots: tuple[Path, ...],
    *, cheek_fallback_factory: Callable[[], Any] | None = None,
    official_selection: Callable[[], bool] | None = None,
) -> Callable[[], BodyPackRenderer]:
    """Share one lazy renderer across half-body and full-body presentation ports."""
    official_selection = official_selection or body_pack_selection_factory(
        character_source, outfit_dir, official_pack_roots,
    )

    def clothing_visible() -> bool:
        return official_selection()

    @cache
    def renderer() -> BodyPackRenderer:
        body_renderer = create_body_pack_renderer(
            body_pack, character_source.appearance.character_layer_views,
            character_source.assets.load_character_layer,
            clothing_visible=clothing_visible,
            apply_makeup=_body_pack_makeup_applier(
                outfit_dir, character_source.assets.asset_root, official_pack_roots,
            ),
        )
        if cheek_fallback_factory is None:
            return body_renderer
        return _BodyPackWithCheekFallback(
            body_renderer, character_source.appearance.character_layer_views,
            cheek_fallback_factory,
        )

    return renderer
