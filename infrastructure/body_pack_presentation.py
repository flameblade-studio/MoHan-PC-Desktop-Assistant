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
lazy from domain.outfit_pack import resolve_active_selection
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.body_pack_renderer import BodyPackRenderer, MakeupApplier, create_body_pack_renderer


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
        self._last_used_fallback = False
        return self._body.render_view(view_id, motion, **options)

    def clear_cache(self) -> None:
        self._body.clear_cache()
        if self._fallback is not None:
            self._fallback.clear_cache()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._body, name)


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
) -> Callable[[], BodyPackRenderer]:
    """Share one lazy renderer across half-body and full-body presentation ports."""
    selection_token: tuple[tuple[str, int, int], ...] | None = None
    visible = True

    def clothing_visible() -> bool:
        nonlocal selection_token, visible
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
        token = tuple(stamps)
        if token != selection_token:
            selected = resolve_active_selection(
                outfit_dir, "garment", official_pack_root=official_pack_roots,
            )
            visible = selected.status == "installed"
            selection_token = token
        return visible

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
