"""protective runtime adapter for every installed appearance-pack overlay."""

from __future__ import annotations

lazy import hashlib
lazy import re
lazy import zipfile
lazy from collections.abc import Callable, Iterable, Sequence
lazy from pathlib import Path

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QRegion
lazy from application.appearance_ports import AppearanceRenderOptions
lazy from domain.outfit_pack import (
    BODY_PROFILE_ID,
    POSE_ATLAS_SILHOUETTES,
    SELECTION_CATEGORIES,
    AppearanceItem,
    AppearanceVariant,
    IncompatibleBodyProfileError,
    OutfitPackError,
    SelectionResolution,
    inspect_installed_outfit_pack,
    installed_pack_path,
    resolve_active_selection,
    resolve_variant_for_view,
    restore_builtin_outfit,
)
lazy from domain.outfit_pack_store import OFFICIAL_PACK_ROOT
lazy from domain.outfit_pack_makeup import MAKEUP_STATE_FILE
lazy from domain.outfit_pack_store import OfficialPackRoots
lazy from domain.qt_image_io import image_from_png
lazy from domain.outfit_pack_official import native_overlay_is_redundant
lazy from domain.engine_capabilities import current_engine_capabilities
lazy from infrastructure.active_outfit_base_clear import ActiveOutfitBaseClearMixin
lazy from infrastructure.active_outfit_overlay_layers import ActiveOutfitLayerMixin, FULL_BODY_CANVAS
lazy from infrastructure.reviewed_garment_overlay import ReviewedGarmentOverlayMixin
lazy from infrastructure.source_bound_garment_visibility import compose_garment_base
lazy from infrastructure.core_hand_regions import load_core_hand_regions
lazy from infrastructure.appearance_layer_stack import (
    AppearanceCallbacks, AppearanceLayerStack,
    CoreMotionError,
    paint_behind_body,
    split_hand_makeup_depth,
    split_makeup_depth,
)
lazy from infrastructure.outfit_core_composition import (
    _AppearanceCompositionError, _hand_region, _paint_foreground_layers,
    _paint_overlay_layers, _paint_depth_tail, _prepare_core_hand_depth,
)
lazy from infrastructure.outfit_overlay_diagnostics import record_outfit_fallback
lazy from infrastructure.outfit_layer_cache_key import OutfitLayerCacheKey
lazy from infrastructure.outfit_layer_cache import OutfitLayerCacheMixin

SEMVER_COMPONENT_COUNT = 3
APP_VERSION = current_engine_capabilities().version
_AUTO_HAND_REGIONS = sentinel("_AUTO_HAND_REGIONS")
_RANGE = re.compile(r">=(\d+)\.(\d+)\.(\d+),<(\d+)\.(\d+)\.(\d+)\Z")
# One composited layer: pixmap, anchor x/y, the region it may paint, opacity.
Layer = tuple[QPixmap, int, int, QRegion, float]
DEFAULT_APPEARANCE_CALLBACKS = AppearanceCallbacks()


class ActiveOutfitOverlay(
    OutfitLayerCacheMixin,
    ReviewedGarmentOverlayMixin,
    ActiveOutfitLayerMixin,
    ActiveOutfitBaseClearMixin,
):
    """Resolve active.json through sealed packs and composite appearance assets.

    Official, user-imported, and cloud-generated packs share the exact same
    archive format, integrity checks and body-profile contract; every source kind follows the same gate.
    """

    def __init__(
        self,
        store: Path,
        asset_root: Path,
        on_stale_body_profile: Callable[[], None] | None = None,
        *,
        visible_hand_region: Callable[[str], QRegion] | sentinel | None = _AUTO_HAND_REGIONS,
        official_pack_root: OfficialPackRoots = OFFICIAL_PACK_ROOT,
    ) -> None:
        self._store = Path(store)
        self._asset_root = Path(asset_root)
        self._on_stale_body_profile = on_stale_body_profile
        self._official_pack_root = official_pack_root
        # Core-owned, pose-specific visible skin only; supplied by the core authority.
        # The sentinel is the composition root's frozen mask result.
        self._visible_hand_region = (
            load_core_hand_regions(self._asset_root)
            if visible_hand_region is _AUTO_HAND_REGIONS else visible_hand_region
        )
        self._stale_pack_handled = False
        # (active.json token, makeup.json token); an absent file maps to None, so a
        # fresh store matches this initial value and keeps pre-seeded layers.
        self._state_token: tuple[tuple[int, int] | None, ...] = (None, None)
        self._package_tokens: dict[Path, tuple[int, int]] = {}
        self._layers_by_view: dict[OutfitLayerCacheKey, Sequence[Layer]] = {}
        self._layers_by_view_without_makeup_slots: dict[OutfitLayerCacheKey, Sequence[Layer]] = {}
        self._phase_layers_by_view: dict[OutfitLayerCacheKey, Sequence[Layer]] = {}
        self._protected_by_view: dict[str, QRegion] = {}
        self._feature_by_view: dict[str, QRegion] = {}
        self._gesture_expression_feature_by_view: dict[str, QRegion] = {}
        self._hair_mask_by_view: dict[str, tuple[QImage, QRect] | None] = {}
        self._makeup_exclusion_by_view: dict[tuple[str, str], QRegion] = {}
        self._core_hand_overlays_by_view: dict[str, Sequence[Layer]] = {}
        self._core_body_overlays_by_view: dict[str, Sequence[Layer]] = {}
        self._official_silhouettes_by_view: dict[str, QRegion | None] = {}
        self._official_replacement_masks_by_view: dict[str, QRegion | None] = {}
        self._native_head_regions_by_view: dict[str, QRegion] = {}
        self._native_identity_regions_by_view: dict[str, QRegion] = {}
        self._generic_base_clear_by_view: dict[str, tuple[QRegion | None, bool]] = {}
        self._garment_active_cache: bool | None = None
        self._official_outfit_active_cache: bool | None = None
        self._safe_regions = None
        self._render_size_by_view: dict[str, tuple[int, int]] = {}
        # The viseme currently being rendered (mouth_states substitution),
        # set by the renderer via set_active_mouth_state() before each
        # render. None means no substitution (including the CLOSED/rest
        # mouth). Included in every layer cache key below so a stale entry
        # computed under one viseme can never be reused under another; the
        # oral mask (native-canvas QPixmap, already resolved by the renderer
        # from the complete-expression manifest's own oral_masks field) is
        # only used to build the mouth-state safe-region exclusion and is not
        # itself part of any cache key.
        self._active_viseme: str | None = None
        self._active_oral_mask: QPixmap | None = None
        self._logged_fallbacks: set[tuple[str, str]] = set()
        self._diagnostic_pack_id: str | None = None

    def set_active_mouth_state(
        self, viseme: str | None, oral_mask: QPixmap | None = None,
    ) -> None:
        """Tell the makeup layer resolver which viseme is being rendered.

        Called by the full-body renderer immediately before each render.
        `oral_mask` is the same native-canvas mask the renderer already
        resolved for restoring skin under the mouth after makeup; when a
        mouth_states substitution applies, it replaces the rest-rig oral
        exclusion slit for lips/foundation/other makeup slots alike.
        """
        self._active_viseme = viseme
        self._active_oral_mask = oral_mask if viseme is not None else None

    def _resolve_base_clear_selection(self, category: str):
        """Keep base-clear selection reads on this module's patchable boundary."""
        return resolve_active_selection(
            self._store,
            category,
            official_pack_root=self._official_pack_root,
        )

    def _bind_canvas(self, view_id: str, size: tuple[int, int]) -> None:
        previous = self._render_size_by_view.get(view_id)
        if previous is not None and previous != size:
            self._invalidate_view(view_id)
        self._render_size_by_view[view_id] = size

    def apply_animated(
        self, frame: QPixmap, view_id: str, paint_motion: Callable[[QPixmap], None], *,
        appearance_options: AppearanceRenderOptions | None = None,
        paint_after_makeup: Callable[[QPixmap], None] | None = None,
        replace_body: Callable[[QPixmap], QPixmap] | None = None,
    ) -> QPixmap:
        """Compose skin motion and makeup below front hair atomically.

        The callback paints deterministic core motion into its private canvas.
        On either asset-phase attention event it is replayed on the untouched bare
        frame, so rollback removes all appearance while preserving animation.
        """
        if frame.isNull():
            return frame
        options = AppearanceRenderOptions() if appearance_options is None else appearance_options
        body_replacement = replace_body or options.replace_body
        after_makeup = paint_after_makeup or options.paint_after_makeup
        if options.eye_state not in {"rest", "half", "closed"}:
            raise ValueError("Use a recognized makeup eye state")

        def replace_core(target: QPixmap) -> QPixmap:
            if body_replacement is None:
                return target
            try:
                return body_replacement(target)
            except Exception as error:
                raise CoreMotionError(error) from error

        def paint_skin(target: QPixmap) -> QPixmap:
            try:
                paint_motion(target)
            except Exception as error:
                raise CoreMotionError(error) from error
            result = self._apply_phase(
                target, view_id, phase="makeup",
                callbacks=AppearanceCallbacks(raise_on_error=True),
                suppress_makeup_slots=options.suppress_makeup_slots,
                eye_state=options.eye_state,
                makeup_view_id=options.makeup_view_id,
            )
            if after_makeup is not None:
                try:
                    after_makeup(result)
                except Exception as error:
                    raise CoreMotionError(error) from error
            return result

        try:
            return self._apply_phase(
                QPixmap(frame), view_id, phase="appearance",
                callbacks=AppearanceCallbacks(
                    paint_skin,
                    replace_core if body_replacement is not None else None,
                    raise_on_error=True,
                ),
            )
        except CoreMotionError as error:
            raise error.original from error
        except _AppearanceCompositionError as error:
            self._invalidate_view(view_id)
            record_outfit_fallback(error, view_id=view_id, seen=self._logged_fallbacks)
            result = (
                QPixmap(frame)
                if body_replacement is None
                else body_replacement(QPixmap(frame))
            )
            paint_motion(result)
            return result

    def apply(
        self,
        frame: QPixmap,
        view_id: str,
        *,
        suppress_makeup_slots: Iterable[str] = (),
        eye_state: str = "rest",
        makeup_view_id: str | None = None,
    ) -> QPixmap:
        if frame.isNull():
            return frame
        if eye_state not in {"rest", "half", "closed"}:
            raise ValueError("Use a recognized makeup eye state")
        suppressed = frozenset(suppress_makeup_slots)
        self._bind_canvas(view_id, frame.size().toTuple())
        # makeup_view_id lets the makeup category alone resolve against a
        # different silhouette key than the garment/silhouette-clip/hand
        # layers below (e.g. a legacy-face-aligned makeup set while the
        # garment stays keyed to its usual silhouette). None (the default)
        # is byte-identical to the previous behavior: every call site that
        # does not pass it is unaffected, including the cache key below.
        # A mouth_states viseme substitution forces the tuple-keyed cache path
        # (with viseme in the key) even when suppressed/eye_state would
        # otherwise qualify for the plain view_id key, so a cached entry from
        # one viseme is never read back under another. When no substitution
        # is active (viseme is None, including the CLOSED/rest path) this is
        # byte-identical to the previous behavior.
        simple = not suppressed and eye_state == "rest" and self._active_viseme is None and makeup_view_id is None
        cache = self._layers_by_view if simple else self._layers_by_view_without_makeup_slots
        cache_key = OutfitLayerCacheKey.combined(
            view_id, suppressed, eye_state, self._active_viseme, makeup_view_id,
        )
        try:
            self._refresh_state()
            reviewed = self._reviewed_frame(
                frame, view_id, suppressed, eye_state, makeup_view_id=makeup_view_id,
            )
            if reviewed is not None:
                return reviewed
            layers = cache.get(cache_key)
            if layers is None:
                layers = self._active_layers(
                    view_id,
                    frame.size().toTuple(),
                    suppress_makeup_slots=suppressed,
                    eye_state=eye_state,
                    makeup_view_id=makeup_view_id,
                )
            garment_is_active = self._garment_is_active()
            hand_overlays = (
                self._core_hand_overlay_layers(view_id, frame.size().toTuple())
                if garment_is_active
                else ()
            )
            body_overlays = (
                self._core_body_overlay_layers(view_id, frame.size().toTuple())
                if garment_is_active
                else ()
            )
            official_silhouette = self._selected_silhouette_region(
                view_id, frame.size().toTuple(), garment_is_active,
            )
        except IncompatibleBodyProfileError as error:
            self._invalidate_view(view_id)
            self._reject_stale_active_pack()
            record_outfit_fallback(error, view_id=view_id, seen=self._logged_fallbacks)
            return frame
        except (OSError, ValueError, OutfitPackError, zipfile.BadZipFile) as error:
            self._invalidate_view(view_id)
            record_outfit_fallback(error, view_id=view_id, seen=self._logged_fallbacks)
            return frame
        if not layers:
            cache[cache_key] = ()
            return frame
        if official_silhouette is None:
            result = QPixmap(frame)
        else:
            # Some fully opaque sources decode as RGB32.  Repaint them onto a
            # transparent canvas so CompositionMode_Clear can remove body
            # pixels outside the authored dressed silhouette.
            result = QPixmap(frame.size())
            result.fill(Qt.transparent)
            base_painter = QPainter(result)
            base_painter.drawPixmap(0, 0, frame)
            base_painter.end()
        painter = QPainter(result)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if official_silhouette is not None:
            canvas = QRegion(QRect(0, 0, frame.width(), frame.height()))
            protruding = canvas.subtracted(official_silhouette)
            if not protruding.isEmpty():
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.setClipRegion(protruding)
                painter.fillRect(result.rect(), QColor(0, 0, 0, 0))
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        foreground = paint_behind_body(painter, layers)
        # Repaintable core hands divide the appearance stack by authored depth.
        # Legacy base-owned hands keep the established hard-region path.
        above_hands = _prepare_core_hand_depth(
            painter, layers, foreground, body_overlays, hand_overlays,
        )
        _paint_overlay_layers(painter, hand_overlays)
        _paint_depth_tail(painter, layers, above_hands)
        painter.end()
        cache[cache_key] = layers
        return result

    def makeup_declares_view(self, view_id: str) -> bool:
        """Whether the *active makeup selection's* variant declares a rest
        (poses) entry for view_id -- used by a render caller to decide whether
        it is safe to pass this view_id as apply()'s makeup_view_id, falling
        back to the caller's regular
        silhouette otherwise (owner-specified: "若包內無該 key 則 fallback 為
        現行行為").  Any failure (builtin/no selection, incompatible pack,
        missing item/variant) is treated as "no", never raised -- this is a
        capability probe, not a rendering call.
        """
        try:
            selected = self._resolve_base_clear_selection("makeup")
            if selected.status == "builtin":
                return False
            _archive_path, _item, variant = self._selected_variant("makeup", selected)
        except (IncompatibleBodyProfileError, OSError, ValueError, OutfitPackError, zipfile.BadZipFile):
            return False
        return view_id in variant.poses

    def apply_appearance(self, frame: QPixmap, view_id: str) -> QPixmap:
        """Composite detachable body, hair, clothing, and accessories.

        Full-body face motion is painted after this phase so a same-coordinate
        dressed skin overlay can replace the base hairline and neckline while preserving authored blink and mouth motion.
        """
        return self._apply_phase(
            frame,
            view_id,
            phase="appearance",
        )

    def apply_makeup(
        self,
        frame: QPixmap,
        view_id: str,
        *,
        suppress_makeup_slots: Iterable[str] = (),
        eye_state: str = "rest",
        makeup_view_id: str | None = None,
    ) -> QPixmap:
        """Composite only state-aware makeup after dynamic facial motion.

        makeup_view_id: see apply() -- same additive, default-None meaning.
        """
        return self._apply_phase(
            frame,
            view_id,
            phase="makeup",
            suppress_makeup_slots=frozenset(suppress_makeup_slots),
            eye_state=eye_state,
            makeup_view_id=makeup_view_id,
        )

    def _apply_phase(
        self,
        frame: QPixmap,
        view_id: str,
        *,
        phase: str,
        suppress_makeup_slots: frozenset[str] = frozenset(),
        eye_state: str = "rest",
        callbacks: AppearanceCallbacks = DEFAULT_APPEARANCE_CALLBACKS,
        makeup_view_id: str | None = None,
    ) -> QPixmap:
        if frame.isNull():
            return frame
        if eye_state not in {"rest", "half", "closed"}:
            raise ValueError("Use a recognized makeup eye state")
        key = OutfitLayerCacheKey.for_phase(
            view_id, phase, suppress_makeup_slots, eye_state,
            self._active_viseme, makeup_view_id,
        )
        include_core = phase == "appearance"
        before_front_hair, replace_body = callbacks.before_front_hair, callbacks.replace_body
        self._bind_canvas(view_id, frame.size().toTuple())
        # Readiness must describe the current split frame, not an older
        # successful combined preview of this same view.
        self._layers_by_view.pop(OutfitLayerCacheKey.combined(view_id), None)
        for combined_key in tuple(self._layers_by_view_without_makeup_slots):
            if combined_key.view_id == view_id:
                del self._layers_by_view_without_makeup_slots[combined_key]
        try:
            self._refresh_state()
            reviewed = self._reviewed_frame(
                frame, view_id, suppress_makeup_slots, eye_state,
                phase=phase, before_front_hair=before_front_hair,
                makeup_view_id=makeup_view_id,
            )
            callbacks.validate_reviewed_frame(reviewed)
            if reviewed is not None:
                return reviewed
            layers = self._phase_layers_by_view.get(key)
            if layers is None:
                layers = self._active_layers(
                    view_id,
                    frame.size().toTuple(),
                    suppress_makeup_slots=suppress_makeup_slots,
                    eye_state=eye_state,
                    categories=(frozenset(SELECTION_CATEGORIES) - {"makeup"}
                                if include_core else frozenset({"makeup"})),
                    makeup_view_id=makeup_view_id,
                )
            garment_is_active = include_core and self._garment_is_active()
            official_silhouette, replacement_mask, binding = self._base_clear_regions(
                view_id, frame.size().toTuple(), garment_is_active, include_core,
            )
            hand_overlays = (
                binding.hand_overlays
                if binding is not None and binding.hand_overlays is not None
                else self._core_hand_overlay_layers(view_id, frame.size().toTuple())
                if garment_is_active else ()
            )
            body_overlays = (
                self._core_body_overlay_layers(view_id, frame.size().toTuple())
                if garment_is_active and binding is None else ()
            )
        except IncompatibleBodyProfileError as error:
            self._invalidate_view(view_id)
            self._reject_stale_active_pack()
            record_outfit_fallback(error, view_id=view_id, seen=self._logged_fallbacks)
            if callbacks.raise_on_error:
                raise _AppearanceCompositionError from error
            return frame
        except (OSError, ValueError, OutfitPackError, zipfile.BadZipFile) as error:
            self._invalidate_view(view_id)
            record_outfit_fallback(error, view_id=view_id, seen=self._logged_fallbacks)
            if callbacks.raise_on_error:
                raise _AppearanceCompositionError from error
            return frame
        if not layers and not body_overlays and not hand_overlays:
            self._phase_layers_by_view[key] = ()
            result = QPixmap(frame) if replace_body is None else replace_body(QPixmap(frame))
            return result if before_front_hair is None else before_front_hair(result)
        result, body_overlays = compose_garment_base(
            frame, body_overlays, replace_body, official_silhouette, replacement_mask,
            binding is not None,
        )
        painter = QPainter(result)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        foreground = paint_behind_body(painter, layers)
        if before_front_hair is not None and hand_overlays:
            _paint_overlay_layers(painter, body_overlays)
            under_hands, early, foreground = split_hand_makeup_depth(
                layers, foreground, _hand_region(hand_overlays),
            )
            _paint_foreground_layers(painter, under_hands, under_hands, makeup_prefix_count=0)
            _paint_foreground_layers(painter, early, early, makeup_prefix_count=0)
        else:
            foreground = _prepare_core_hand_depth(
                painter, layers, foreground, body_overlays, hand_overlays,
            )
            if before_front_hair is not None:
                early, foreground = split_makeup_depth(layers, foreground)
                _paint_depth_tail(
                    painter,
                    layers,
                    early,
                    makeup_prefix_count=layers.makeup_prefix_count,
                )
        if before_front_hair is not None:
            # Legacy garments stay early; declared occluders join front hair.
            painter.end()
            result = before_front_hair(result)
            painter = QPainter(result)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
        _paint_overlay_layers(painter, hand_overlays)
        _paint_depth_tail(
            painter,
            layers,
            foreground,
            makeup_prefix_count=(0 if before_front_hair is not None else None),
        )
        painter.end()
        self._phase_layers_by_view[key] = layers
        return result

    def _reject_stale_active_pack(self) -> None:
        """Issue #140, option 3: a generation-1 pack stays outside the generation-2 body renderer.

        The built-in outfit is restored once and the owner of this overlay is told once;
        later frames read the rewritten ``active.json`` and render the built-in look quietly.
        """
        if self._stale_pack_handled:
            return
        self._stale_pack_handled = True
        try:
            restore_builtin_outfit(self._store)
        except OSError:
            pass  # every later frame still falls back to the built-in look above
        if self._on_stale_body_profile is not None:
            self._on_stale_body_profile()

    @staticmethod
    def _file_token(path: Path) -> tuple[int, int] | None:
        try:
            stat = path.stat()
        except FileNotFoundError:
            return None
        return (stat.st_mtime_ns, stat.st_size)

    def _refresh_state(self) -> None:
        # The makeup intensity lives next to active.json; a slider move must
        # invalidate the cached layers exactly like a selection change.
        token = (
            self._file_token(self._store / "active.json"),
            self._file_token(self._store / MAKEUP_STATE_FILE),
        )
        current_package_tokens: dict[Path, tuple[int, int]] = {}
        for package_path in self._package_tokens:
            package_token = self._file_token(package_path)
            if package_token is not None:
                current_package_tokens[package_path] = package_token
        if (
            token == self._state_token
            and current_package_tokens == self._package_tokens
        ):
            return
        active_changed = token != self._state_token
        self._state_token = token
        self._package_tokens = (
            {} if active_changed else current_package_tokens
        )
        self._layers_by_view.clear()
        self._layers_by_view_without_makeup_slots.clear()
        self._phase_layers_by_view.clear()
        self._generic_base_clear_by_view.clear()
        getattr(self, "_reviewed_layer_counts", {}).clear()
        getattr(self, "_reviewed_native_frames", {}).clear()
        getattr(self, "_reviewed_native_eyes", {}).clear()
        if active_changed:
            self._garment_active_cache = None
            self._official_outfit_active_cache = None

    def _selected_variant(
        self,
        category: str,
        selected: SelectionResolution,
    ) -> tuple[Path, AppearanceItem, AppearanceVariant]:
        """Locate and validate the active pack, item and variant for one category."""
        archive_path = installed_pack_path(
            self._store,
            selected.effective_pack_id,
            official_pack_root=self._official_pack_root,
        )
        archive_stat = archive_path.stat()
        token = (archive_stat.st_mtime_ns, archive_stat.st_size)
        self._package_tokens[archive_path] = token
        pack = inspect_installed_outfit_pack(archive_path)
        if pack is None or pack.compatible_body_profile != BODY_PROFILE_ID:
            raise IncompatibleBodyProfileError(
                f"Active pack {selected.effective_pack_id!r} targets another body-profile generation."
            )
        if not self._compatible(pack.app_range):
            raise OutfitPackError("The active outfit is not runtime compatible.")
        item = next(
            (
                value
                for value in pack.items
                if value.category == category
                and value.item_id == selected.effective_item_id
            ),
            None,
        )
        if item is None:
            raise OutfitPackError("Provide the active appearance item.")
        variant = next(
            (
                value
                for value in item.variants
                if value.variant_id == selected.effective_variant_id
            ),
            None,
        )
        if variant is None:
            raise OutfitPackError("Provide the active appearance variant.")
        return archive_path, item, variant

    def _active_layers(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
        *,
        suppress_makeup_slots: frozenset[str] = frozenset(),
        eye_state: str = "rest",
        categories: frozenset[str] | None = None,
        makeup_view_id: str | None = None,
    ) -> AppearanceLayerStack:
        result: list[tuple[int, int, Layer, bool, bool]] = []
        rear: list[tuple[int, Layer]] = []
        for category_index, category in enumerate(SELECTION_CATEGORIES):
            if categories is not None and category not in categories:
                continue
            selected = self._resolve_base_clear_selection(category)
            if selected.status == "builtin":
                continue
            self._diagnostic_pack_id = selected.effective_pack_id
            archive_path, item, variant = self._selected_variant(category, selected)
            identity = (
                selected.effective_pack_id,
                selected.effective_item_id,
                selected.effective_variant_id,
            )
            resolution = resolve_variant_for_view(variant, view_id)
            assets = resolution.assets
            asset_sha256 = getattr(assets[0], "sha256", None) if len(assets) == 1 else None
            if (view_id in POSE_ATLAS_SILHOUETTES and canvas_size == FULL_BODY_CANVAS
                    and native_overlay_is_redundant(
                        category, identity, view_id, asset_sha256=asset_sha256,
                    )):
                continue
            with zipfile.ZipFile(archive_path) as archive:
                if category == "makeup":
                    makeup_resolution = (
                        resolve_variant_for_view(variant, makeup_view_id)
                        if makeup_view_id is not None else resolution
                    )
                    layers = self._makeup_layers(
                        archive,
                        makeup_resolution.assets,
                        variant,
                        makeup_view_id if makeup_view_id is not None else view_id,
                        suppress_makeup_slots=suppress_makeup_slots,
                        eye_state=eye_state,
                    )
                    result.extend((z_order, category_index, layer, False, False) for z_order, layer in layers)
                else:
                    declarations = resolution.assets
                    if category == "hairstyle":
                        rear.extend(self._garment_layers(
                            archive, tuple(d for d in declarations if d.slot == "back"),
                            category, item, variant, view_id, canvas_size,
                        ))
                        declarations = tuple(d for d in declarations if d.slot != "back")
                    for declaration in declarations:
                        layers = self._garment_layers(
                            archive, (declaration,), category, item, variant, view_id, canvas_size
                        )
                        behind_hands = category == "garment" or (
                            variant.hand_rules is not None
                            and variant.hand_rules.get(view_id) == "behind-hands"
                        )
                        result.extend(
                            (z_order, category_index, layer, declaration.occludes_makeup, behind_hands)
                            for z_order, layer in layers
                        )
        result.sort(key=lambda value: (value[0], value[1]))
        rear.sort(key=lambda value: value[0])
        makeup_index = SELECTION_CATEGORIES.index("makeup")
        makeup_prefix_count = sum(
            1 for _z_order, category_index, _layer, _occludes, _behind_hands in result
            if category_index == makeup_index
        )
        if any(
            category_index == makeup_index
            for _z_order, category_index, _layer, _occludes, _behind_hands in result[makeup_prefix_count:]
        ):
            raise OutfitPackError("Makeup layers must precede appearance layers.")
        return AppearanceLayerStack(
            tuple(layer for _z_order, layer in rear),
            tuple(layer for _z_order, _index, layer, _occludes, _behind_hands in result),
            makeup_prefix_count,
            front_hair_indices=frozenset(
                index for index, (_z_order, category_index, _layer, _occludes, _behind_hands) in enumerate(result)
                if category_index == SELECTION_CATEGORIES.index("hairstyle")
            ),
            makeup_occluder_indices=frozenset(
                index for index, (_z_order, _category_index, _layer, occludes, _behind_hands) in enumerate(result)
                if occludes
            ),
            behind_hand_indices=frozenset(
                index for index, (_z_order, _category_index, _layer, _occludes, behind_hands) in enumerate(result)
                if behind_hands
            ),
        )

    def _decoded_layer(self, archive: zipfile.ZipFile, declaration) -> tuple[bytes, QImage]:
        if Path(declaration.path).suffix.lower() != ".png":
            raise OutfitPackError("Runtime appearance layers must be RGBA PNG.")
        encoded = archive.read(declaration.path)
        if hashlib.sha256(encoded).hexdigest() != declaration.sha256:
            raise OutfitPackError(
                "Runtime appearance hash mismatch.",
                reason="manifest_asset_hash_mismatch",
                pack_id=self._diagnostic_pack_id,
                asset_path=declaration.path,
            )
        image = image_from_png(encoded)
        if image.isNull() or image.hasAlphaChannel() is False:
            raise OutfitPackError("Runtime appearance must have alpha.")
        if (image.width(), image.height()) != (declaration.width, declaration.height):
            raise OutfitPackError("Runtime appearance dimensions disagree.")
        return encoded, image.convertToFormat(QImage.Format_RGBA8888)

    def _garment_layers(
        self,
        archive: zipfile.ZipFile,
        declarations,
        category: str,
        item,
        variant,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> list[tuple[int, Layer]]:
        forbidden = self._forbidden_face_region(category, item, variant, view_id)
        allowed = QRegion(QRect(0, 0, canvas_size[0], canvas_size[1]))
        # Hair falls over the face naturally: it is faded out of the feature core
        # below instead of being cut by the protected-face rectangle.
        if category != "hairstyle":
            allowed = allowed.subtracted(forbidden)
        allowed = self._hand_allowed_region(allowed, category, variant, view_id)
        layers: list[tuple[int, Layer]] = []
        for declaration in declarations:
            if declaration.clears_base:
                continue
            _encoded, image = self._decoded_layer(archive, declaration)
            if (
                declaration.anchor_x < 0
                or declaration.anchor_y < 0
                or declaration.anchor_x + image.width() > canvas_size[0]
                or declaration.anchor_y + image.height() > canvas_size[1]
            ):
                raise OutfitPackError("Runtime appearance anchor escaped the canvas.")
            pixmap = QPixmap.fromImage(image)
            has_content = self._validate_alpha(
                pixmap,
                declaration.anchor_x,
                declaration.anchor_y,
                QRegion() if category == "hairstyle" else forbidden,
                allow_empty=category != "garment",
            )
            if not has_content:
                continue
            # A back-hair layer is authored behind the face and is already
            # kept outside the exact eye or mouth core when its alpha reaches that region.  Keep
            # its remaining alpha intact so the front-hair feather cannot
            # punch desktop-coloured holes beside the chin.
            if category == "hairstyle" and declaration.slot != "back":
                pixmap = self._feathered_hair_layer(pixmap, declaration.anchor_x, declaration.anchor_y, view_id)
            layers.append((
                declaration.z_order,
                (pixmap, declaration.anchor_x, declaration.anchor_y, allowed, 1.0),
            ))
        return layers

    @staticmethod
    def _compatible(app_range: str) -> bool:
        # Validate a pack range first: the pack's own metadata is the
        # untrusted input here and must fail closed.
        match = _RANGE.fullmatch(app_range)
        if match is None:
            return False
        # Our own APP_VERSION may be a development build ("4.6.dev0", a git
        # describe string, …).  Parsing it used to run before any guard, so
        # the ValueError escaped into apply()'s broad handler and silently
        # disabled every outfit on dev builds.  A non-semver local version now
        # skips the range comparison and counts as compatible instead.
        try:
            version = tuple(int(value) for value in APP_VERSION.split(".")[:3])
        except ValueError:
            return True
        if len(version) != SEMVER_COMPONENT_COUNT:
            return True
        values = tuple(int(value) for value in match.groups())
        return values[:3] <= version < values[3:]
