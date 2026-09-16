"""protective runtime adapter for every installed appearance-pack overlay."""

from __future__ import annotations

lazy import hashlib
lazy import re
lazy import zipfile
lazy from collections.abc import Callable, Iterable, Sequence
lazy from pathlib import Path

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QRegion

lazy from domain.outfit_pack import (
    BODY_PROFILE_ID,
    SELECTION_CATEGORIES,
    IncompatibleBodyProfileError,
    OutfitPackError,
    inspect_installed_outfit_pack,
    installed_pack_path,
    resolve_active_selection,
    resolve_variant_for_view,
    restore_builtin_outfit,
)
lazy from domain.outfit_pack_makeup import MAKEUP_STATE_FILE
lazy from domain.outfit_pack_official import (
    OFFICIAL_OUTFIT_CATEGORIES,
    OFFICIAL_OUTFIT_PACK_ID,
)
lazy from domain.version_info import APP_VERSION
lazy from infrastructure.active_outfit_overlay_layers import ActiveOutfitLayerMixin
lazy from infrastructure.reviewed_garment_overlay import ReviewedGarmentOverlayMixin
lazy from infrastructure.core_hand_regions import load_core_hand_regions
lazy from infrastructure.appearance_layer_stack import (
    AppearanceCallbacks, AppearanceLayerStack,
    CoreMotionError,
    clear_appearance_base,
    paint_behind_body,
    split_hand_makeup_depth,
    split_makeup_depth,
)

lazy from infrastructure.outfit_core_composition import (
    _AppearanceCompositionError, _hand_region, _paint_foreground_layers,
    _paint_overlay_layers, _paint_depth_tail, _prepare_core_hand_depth, replace_restored_body,
)

SEMVER_COMPONENT_COUNT = 3
_AUTO_HAND_REGIONS = sentinel("AUTO_HAND_REGIONS")
_RANGE = re.compile(r">=(\d+)\.(\d+)\.(\d+),<(\d+)\.(\d+)\.(\d+)\Z")
# One composited layer: pixmap, anchor x/y, the region it may paint, opacity.
Layer = tuple[QPixmap, int, int, QRegion, float]


class ActiveOutfitOverlay(ReviewedGarmentOverlayMixin, ActiveOutfitLayerMixin):
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
        visible_hand_region: Callable[[str], QRegion] | None | sentinel = _AUTO_HAND_REGIONS,
    ) -> None:
        self._store = Path(store)
        self._asset_root = Path(asset_root)
        self._on_stale_body_profile = on_stale_body_profile
        # Core-owned, pose-specific visible skin only; supplied by the core authority.
        # The provider remains immutable for this overlay's lifetime, like rig assets.
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
        self._layers_by_view: dict[str, Sequence[Layer]] = {}
        self._layers_by_view_without_makeup_slots: dict[
            tuple[str, frozenset[str], str], Sequence[Layer]
        ] = {}
        self._phase_layers_by_view: dict[
            tuple[str, str, frozenset[str], str], Sequence[Layer]
        ] = {}
        self._protected_by_view: dict[str, QRegion] = {}
        self._feature_by_view: dict[str, QRegion] = {}
        self._hair_mask_by_view: dict[str, tuple[QImage, QRect] | None] = {}
        self._makeup_exclusion_by_view: dict[tuple[str, str], QRegion] = {}
        self._core_hand_overlays_by_view: dict[str, Sequence[Layer]] = {}
        self._core_body_overlays_by_view: dict[str, Sequence[Layer]] = {}
        self._official_silhouettes_by_view: dict[str, QRegion | None] = {}
        self._official_replacement_masks_by_view: dict[str, QRegion | None] = {}
        self._garment_active_cache: bool | None = None
        self._official_outfit_active_cache: bool | None = None
        self._safe_regions = None
        self._render_size_by_view: dict[str, tuple[int, int]] = {}

    def _invalidate_view(self, view_id: str) -> None:
        """Discard both successful layers and size-dependent masks for a view."""
        getattr(self, "_reviewed_layer_counts", {}).pop(view_id, None)
        for cache in (
            self._layers_by_view, self._protected_by_view, self._feature_by_view,
            self._hair_mask_by_view,
            self._core_hand_overlays_by_view, self._core_body_overlays_by_view,
            self._official_silhouettes_by_view, self._official_replacement_masks_by_view,
        ):
            cache.pop(view_id, None)
        for key in tuple(self._makeup_exclusion_by_view):
            if key[0] == view_id:
                del self._makeup_exclusion_by_view[key]
        for cache in (self._layers_by_view_without_makeup_slots, self._phase_layers_by_view):
            for key in tuple(cache):
                if key[0] == view_id:
                    del cache[key]

    def _bind_canvas(self, view_id: str, size: tuple[int, int]) -> None:
        previous = self._render_size_by_view.get(view_id)
        if previous is not None and previous != size:
            self._invalidate_view(view_id)
        self._render_size_by_view[view_id] = size

    def apply_animated(
        self, frame: QPixmap, view_id: str, paint_motion: Callable[[QPixmap], None], *,
        suppress_makeup_slots: Iterable[str] = (), eye_state: str = "rest",
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
        if eye_state not in {"rest", "half", "closed"}:
            raise ValueError("Use a recognized makeup eye state")

        def replace_core(target: QPixmap) -> QPixmap:
            if replace_body is None:
                return target
            try:
                return replace_body(target)
            except Exception as error:
                raise CoreMotionError(error) from error

        def paint_skin(target: QPixmap) -> QPixmap:
            try:
                paint_motion(target)
            except Exception as error:
                raise CoreMotionError(error) from error
            result = self._apply_phase(
                target, view_id, phase="makeup",
                raise_on_error=True,
                suppress_makeup_slots=frozenset(suppress_makeup_slots), eye_state=eye_state,
            )
            if paint_after_makeup is not None:
                try:
                    paint_after_makeup(result)
                except Exception as error:
                    raise CoreMotionError(error) from error
            return result

        try:
            return self._apply_phase(
                QPixmap(frame), view_id, phase="appearance",
                raise_on_error=True,
                callbacks=AppearanceCallbacks(
                    paint_skin, replace_core if replace_body is not None else None,
                ),
            )
        except CoreMotionError as error:
            raise error.original from error
        except _AppearanceCompositionError:
            self._invalidate_view(view_id)
            result = QPixmap(frame) if replace_body is None else replace_body(QPixmap(frame))
            paint_motion(result)
            return result

    def apply(
        self,
        frame: QPixmap,
        view_id: str,
        *,
        suppress_makeup_slots: Iterable[str] = (),
        eye_state: str = "rest",
    ) -> QPixmap:
        if frame.isNull():
            return frame
        if eye_state not in {"rest", "half", "closed"}:
            raise ValueError("Use a recognized makeup eye state")
        suppressed = frozenset(suppress_makeup_slots)
        self._bind_canvas(view_id, frame.size().toTuple())
        cache = (
            self._layers_by_view
            if not suppressed and eye_state == "rest"
            else self._layers_by_view_without_makeup_slots
        )
        cache_key = (
            view_id
            if not suppressed and eye_state == "rest"
            else (view_id, suppressed, eye_state)
        )
        try:
            self._refresh_state()
            reviewed = self._reviewed_frame(frame, view_id, suppressed, eye_state)
            if reviewed is not None:
                return reviewed
            layers = cache.get(cache_key)
            if layers is None:
                layers = self._active_layers(
                    view_id,
                    frame.size().toTuple(),
                    suppress_makeup_slots=suppressed,
                    eye_state=eye_state,
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
        except IncompatibleBodyProfileError:
            self._invalidate_view(view_id)
            self._reject_stale_active_pack()
            return frame
        except (OSError, ValueError, OutfitPackError, zipfile.BadZipFile):
            self._invalidate_view(view_id)
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
    ) -> QPixmap:
        """Composite only state-aware makeup after dynamic facial motion."""
        return self._apply_phase(
            frame,
            view_id,
            phase="makeup",
            suppress_makeup_slots=frozenset(suppress_makeup_slots),
            eye_state=eye_state,
        )

    def _apply_phase(
        self,
        frame: QPixmap,
        view_id: str,
        *,
        phase: str,
        suppress_makeup_slots: frozenset[str] = frozenset(),
        eye_state: str = "rest",
        raise_on_error: bool = False,
        callbacks: AppearanceCallbacks = AppearanceCallbacks(),
    ) -> QPixmap:
        if frame.isNull():
            return frame
        if eye_state not in {"rest", "half", "closed"}:
            raise ValueError("Use a recognized makeup eye state")
        key = (view_id, phase, suppress_makeup_slots, eye_state)
        include_core = phase == "appearance"
        before_front_hair, replace_body = callbacks.before_front_hair, callbacks.replace_body
        self._bind_canvas(view_id, frame.size().toTuple())
        # Readiness must describe the current split frame, not an older
        # successful combined preview of this same view.
        self._layers_by_view.pop(view_id, None)
        for combined_key in tuple(self._layers_by_view_without_makeup_slots):
            if combined_key[0] == view_id:
                del self._layers_by_view_without_makeup_slots[combined_key]
        try:
            self._refresh_state()
            reviewed = self._reviewed_frame(
                frame, view_id, suppress_makeup_slots, eye_state,
                phase=phase, before_front_hair=before_front_hair,
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
                )
            garment_is_active = include_core and self._garment_is_active()
            body_overlays = (
                self._core_body_overlay_layers(view_id, frame.size().toTuple())
                if garment_is_active
                else ()
            )
            hand_overlays = (
                self._core_hand_overlay_layers(view_id, frame.size().toTuple())
                if garment_is_active
                else ()
            )
            official_silhouette = (
                self._selected_silhouette_region(
                    view_id, frame.size().toTuple(), garment_is_active,
                )
                if include_core
                else None
            )
            replacement_mask = (
                self._official_replacement_region(view_id, frame.size().toTuple())
                if include_core and self._official_outfit_is_active()
                else None
            )
        except IncompatibleBodyProfileError as error:
            self._invalidate_view(view_id)
            self._reject_stale_active_pack()
            if raise_on_error:
                raise _AppearanceCompositionError from error
            return frame
        except (OSError, ValueError, OutfitPackError, zipfile.BadZipFile) as error:
            self._invalidate_view(view_id)
            if raise_on_error:
                raise _AppearanceCompositionError from error
            return frame
        if not layers and not body_overlays and not hand_overlays:
            self._phase_layers_by_view[key] = ()
            result = QPixmap(frame) if replace_body is None else replace_body(QPixmap(frame))
            return result if before_front_hair is None else before_front_hair(result)
        result = clear_appearance_base(frame, official_silhouette, replacement_mask)
        result, body_overlays = replace_restored_body(result, body_overlays, replace_body)
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



    def _selected_silhouette_region(
        self, view_id: str, canvas_size: tuple[int, int], garment_is_active: bool,
    ) -> QRegion | None:
        """Keep garment occlusion when independently changing hair or headwear."""
        if self._official_outfit_is_active():
            return self._official_silhouette_region(view_id, canvas_size)
        if not garment_is_active:
            return None
        garment = resolve_active_selection(self._store, "garment")
        if garment.effective_pack_id != OFFICIAL_OUTFIT_PACK_ID:
            return None
        silhouette = self._official_silhouette_region(view_id, canvas_size)
        if silhouette is None:
            return None
        # A clothing selection owns the body outline below the protected head.
        # Keep the entire head band available for the independently chosen hair.
        head = self._protected_face_region(view_id, canvas_size).boundingRect()
        if head.isEmpty():
            raise OutfitPackError("Protected head boundary is unavailable.")
        head_band = QRegion(QRect(0, 0, canvas_size[0], head.bottom() + 1))
        return silhouette.united(head_band)

    def _official_outfit_is_active(self) -> bool:
        """Keep the official base boundary when its headwear is explicitly removed."""
        if self._official_outfit_active_cache is not None:
            return self._official_outfit_active_cache
        result = True
        for category in OFFICIAL_OUTFIT_CATEGORIES:
            selected = resolve_active_selection(self._store, category)
            if getattr(selected, "effective_pack_id", None) == OFFICIAL_OUTFIT_PACK_ID:
                continue
            requested = tuple(getattr(selected, f"requested_{field}", None)
                              for field in ("pack_id", "item_id", "variant_id"))
            effective = tuple(getattr(selected, f"effective_{field}", None)
                              for field in ("pack_id", "item_id", "variant_id"))
            if (category == "headwear" and getattr(selected, "status", None) == "builtin"
                    and requested == effective == ("builtin", "none", "none")):
                continue
            result = False
            break
        self._official_outfit_active_cache = result
        return result

    def _garment_is_active(self) -> bool:
        """Resolve the active garment once per appearance-state token."""
        if self._garment_active_cache is None:
            self._garment_active_cache = (
                resolve_active_selection(self._store, "garment").status != "builtin"
            )
        return self._garment_active_cache



    def layer_count(
        self,
        view_id: str,
        *,
        suppress_makeup_slots: Iterable[str] = (),
        eye_state: str = "rest",
    ) -> int:
        """Successfully composed layers from either combined or split phases."""
        if eye_state not in {"rest", "half", "closed"}:
            raise ValueError("Use a recognized makeup eye state")
        suppressed = frozenset(suppress_makeup_slots)
        reviewed_count = getattr(self, "_reviewed_layer_counts", {}).get(view_id, 0)
        cache = (
            self._layers_by_view
            if not suppressed and eye_state == "rest"
            else self._layers_by_view_without_makeup_slots
        )
        cache_key = view_id if not suppressed and eye_state == "rest" else (view_id, suppressed, eye_state)
        if cache_key in cache:
            return len(cache[cache_key]) + reviewed_count
        appearance = self._phase_layers_by_view.get((view_id, "appearance", frozenset(), "rest"), ())
        makeup = self._phase_layers_by_view.get((view_id, "makeup", suppressed, eye_state), ())
        return len(appearance) + len(makeup) + reviewed_count

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
        getattr(self, "_reviewed_layer_counts", {}).clear()
        getattr(self, "_reviewed_native_frames", {}).clear()
        getattr(self, "_reviewed_native_eyes", {}).clear()
        if active_changed:
            self._garment_active_cache = None
            self._official_outfit_active_cache = None

    def _selected_variant(self, category: str, selected) -> tuple[Path, object, object]:
        """Locate and validate the active pack, item and variant for one category."""
        archive_path = installed_pack_path(self._store, selected.effective_pack_id)
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
    ) -> AppearanceLayerStack:
        result: list[tuple[int, int, Layer, bool, bool]] = []
        rear: list[tuple[int, Layer]] = []
        for category_index, category in enumerate(SELECTION_CATEGORIES):
            if categories is not None and category not in categories:
                continue
            selected = resolve_active_selection(self._store, category)
            if selected.status == "builtin":
                continue
            archive_path, item, variant = self._selected_variant(category, selected)
            resolution = resolve_variant_for_view(variant, view_id)
            with zipfile.ZipFile(archive_path) as archive:
                if category == "makeup":
                    layers = self._makeup_layers(
                        archive,
                        resolution.assets,
                        variant,
                        view_id,
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
            raise OutfitPackError("Runtime appearance hash mismatch.")
        image = QImage.fromData(encoded, "PNG")
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
                forbidden,
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
