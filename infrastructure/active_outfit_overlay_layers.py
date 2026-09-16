"""Focused layer, mask, and face-safety helpers for outfit composition."""

from __future__ import annotations

lazy import zipfile
lazy from pathlib import Path

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QBitmap, QColor, QImage, QPainter, QPixmap, QRegion

lazy from domain.constants import POSE_ATLAS_LAYERED_ROOT_NAME
lazy from domain.outfit_pack import (
    FOUNDATION_SLOT,
    MAKEUP_SLOTS,
    MAKEUP_SLOTS_V2,
    MIN_Z_ORDER,
    OutfitPackError,
)
lazy from domain.outfit_pack_makeup import (
    EXCLUSION_RIG_LAYERS,
    FEATURE_CORE_LAYERS,
    HAIRSTYLE_FEATURE_CORE_DILATION_PX,
    HAIRSTYLE_FEATURE_CORE_FEATHER_PX,
    HALF_BODY_RIGS,
    SAFE_REGION_FILE,
    load_makeup_safe_regions,
    makeup_layer_escapes,
    read_makeup_intensity,
    read_makeup_slot_intensities,
)
lazy from domain.outfit_pack_official import OFFICIAL_OUTFIT_PACK_ID
lazy from infrastructure.image_alpha_regions import visible_alpha_region

HALF_BODY_CANVAS = (1254, 1254)
FULL_BODY_CANVAS = (1024, 1536)
_DILATION_OFFSETS = tuple(
    (dx, dy)
    for dx in (-1, 0, 1)
    for dy in (-1, 0, 1)
    if dx or dy
)
_OPAQUE = 255
_MAKEUP_Z_BASE = MIN_Z_ORDER * 3

Layer = tuple[QPixmap, int, int, QRegion, float]


class ActiveOutfitLayerMixin:
    """Provide reusable asset loading, clipping, and validation operations."""

    def _official_replacement_region(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> QRegion | None:
        """Load a mask whose interior is fully rebuilt by official layers.

        This optional contract prevents a differently coiffed or clothed base
        portrait from showing through the transparent boundaries between a
        complete same-coordinate body/hand/garment/hair partition.
        """
        if view_id in self._official_replacement_masks_by_view:
            cached = self._official_replacement_masks_by_view[view_id]
            return None if cached is None else QRegion(cached)
        path = (
            self._asset_root
            / "assets/pose-atlas/v5-appearance-replacement-masks"
            / OFFICIAL_OUTFIT_PACK_ID
            / f"{view_id}.png"
        )
        if not path.exists():
            self._official_replacement_masks_by_view[view_id] = None
            return None
        image = QImage(str(path))
        if (
            image.isNull()
            or not image.hasAlphaChannel()
            or image.size().toTuple() != canvas_size
        ):
            raise OutfitPackError(f"Invalid official replacement mask: {path.name}")
        region = QRegion(QBitmap.fromImage(image.createAlphaMask()))
        if region.isEmpty():
            raise OutfitPackError(f"Empty official replacement mask: {path.name}")
        self._official_replacement_masks_by_view[view_id] = region
        return QRegion(region)


    def _core_body_overlay_layers(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> tuple[Layer, ...]:
        """Load optional visible non-hand body skin for a dressed full-body view."""
        cached = self._core_body_overlays_by_view.get(view_id)
        if cached is not None:
            return cached
        path = self._asset_root / "assets/pose-atlas/v5-body-overlays" / f"{view_id}.png"
        if not path.exists():
            self._core_body_overlays_by_view[view_id] = ()
            return ()
        image = QImage(str(path))
        if (
            image.isNull()
            or not image.hasAlphaChannel()
            or image.size().toTuple() != canvas_size
        ):
            raise OutfitPackError(f"Invalid core body overlay: {path.name}")
        pixmap = QPixmap.fromImage(image.convertToFormat(QImage.Format_RGBA8888))
        if visible_alpha_region(image).isEmpty():
            raise OutfitPackError(f"Empty core body overlay: {path.name}")
        canvas = QRegion(QRect(0, 0, canvas_size[0], canvas_size[1]))
        result = ((pixmap, 0, 0, canvas, 1.0),)
        self._core_body_overlays_by_view[view_id] = result
        return result


    def _official_silhouette_region(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> QRegion | None:
        """Load the optional whole-appearance silhouette for exact body occlusion."""
        if view_id in self._official_silhouettes_by_view:
            cached = self._official_silhouettes_by_view[view_id]
            return None if cached is None else QRegion(cached)
        path = (
            self._asset_root
            / "assets/pose-atlas/v5-appearance-silhouettes"
            / OFFICIAL_OUTFIT_PACK_ID
            / f"{view_id}.png"
        )
        if not path.exists():
            self._official_silhouettes_by_view[view_id] = None
            return None
        image = QImage(str(path))
        if (
            image.isNull()
            or not image.hasAlphaChannel()
            or image.size().toTuple() != canvas_size
        ):
            raise OutfitPackError(f"Invalid official appearance silhouette: {path.name}")
        region = QRegion(QBitmap.fromImage(image.createAlphaMask()))
        if region.isEmpty():
            raise OutfitPackError(f"Empty official appearance silhouette: {path.name}")
        self._official_silhouettes_by_view[view_id] = region
        return QRegion(region)


    def _core_hand_overlay_layers(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> tuple[Layer, ...]:
        """Load an optional immutable pair of core-owned RGBA hand overlays."""
        cached = self._core_hand_overlays_by_view.get(view_id)
        if cached is not None:
            return cached
        region_provider = self._visible_hand_region
        if region_provider is None:
            self._core_hand_overlays_by_view[view_id] = ()
            return ()
        image_provider = getattr(region_provider, "overlay_images", None)
        if image_provider is None:
            directory = self._asset_root / "assets/pose-atlas/v5-hand-overlays"
            paths = tuple(directory / f"{view_id}_{side}.png" for side in ("left", "right"))
            if not any(path.exists() for path in paths):
                self._core_hand_overlays_by_view[view_id] = ()
                return ()
            if not all(path.exists() for path in paths):
                raise OutfitPackError("Core hand-overlay pair requires both sides.")
            images = tuple(QImage(str(path)) for path in paths)
        else:
            images = image_provider(view_id)
            if images is None:
                self._core_hand_overlays_by_view[view_id] = ()
                return ()
        layers: list[Layer] = []
        for image in images:
            if (
                image.isNull()
                or not image.hasAlphaChannel()
                or image.size().toTuple() != canvas_size
            ):
                raise OutfitPackError("Provide a supported core hand overlay snapshot.")
            pixmap = QPixmap.fromImage(image.convertToFormat(QImage.Format_RGBA8888))
            ownership = visible_alpha_region(image)
            if ownership.isEmpty():
                continue
            layers.append((pixmap, 0, 0, ownership, 1.0))
        result = tuple(layers)
        self._core_hand_overlays_by_view[view_id] = result
        return result


    def _hand_allowed_region(self, canvas: QRegion, category: str, variant, view_id: str) -> QRegion:
        """Keep core-visible hands above cloth and declared behind-hand items."""
        if self._visible_hand_region is None:
            return canvas
        rule = None
        if variant.hand_rules is not None:
            rule = variant.hand_rules.get(view_id)
            if rule not in {"behind-hands", "front-of-hands"}:
                raise OutfitPackError("Provide hand occlusion for the active view.")
        if category != "garment" and rule != "behind-hands":
            return canvas
        hands = self._visible_hand_region(view_id)
        full_canvas = QRegion(0, 0, *self._canvas_size(view_id))
        if not isinstance(hands, QRegion) or not hands.subtracted(full_canvas).isEmpty():
            raise OutfitPackError("Core hand region escaped the active canvas.")
        has_overlay = getattr(self._visible_hand_region, "has_repaintable_overlay", None)
        if has_overlay is not None and has_overlay(view_id):
            return canvas
        return canvas.subtracted(hands)


    def _feathered_hair_layer(self, pixmap: QPixmap, anchor_x: int, anchor_y: int, view_id: str) -> QPixmap:
        """Multiply the hair alpha by the feathered feature-core mask (0 inside, 1 beyond the feather)."""
        mask = self._hair_core_mask(view_id)
        if mask is None:
            return pixmap
        alpha, bounds = mask
        body = self._body_outline_region(view_id)
        if body is None:
            return self._masked_hair(pixmap, anchor_x, anchor_y, alpha, bounds)
        # Feather against skin, not the desktop behind the character. Keep the
        # complete dilated feature core reserved, including the body boundary.
        protected = self._feature_region(view_id)
        for _step in range(HAIRSTYLE_FEATURE_CORE_DILATION_PX):
            expanded = protected
            for dx, dy in _DILATION_OFFSETS:
                expanded = expanded.united(protected.translated(dx, dy))
            protected = expanded
        silhouette = QRegion()
        # Rig cut-outs leave internal holes; those are not desktop background.
        for y in range(bounds.top(), bounds.bottom() + 1):
            row = body.intersected(QRegion(bounds.left(), y, bounds.width(), 1)).boundingRect()
            if not row.isEmpty():
                silhouette = silhouette.united(QRegion(row))
        background = QRegion(bounds).subtracted(silhouette).subtracted(protected)
        alpha = alpha.copy()
        painter = QPainter(alpha)
        painter.setClipRegion(background.translated(-bounds.x(), -bounds.y()))
        painter.fillRect(alpha.rect(), QColor(0, 0, 0, _OPAQUE))
        painter.end()
        return self._masked_hair(pixmap, anchor_x, anchor_y, alpha, bounds)


    def _body_outline_region(self, view_id: str) -> QRegion | None:
        base = self._protected_face_path(view_id)
        path = base.with_name(base.name.removesuffix("_base.png") + "_body_outline.png")
        if not path.exists():
            return None
        image = QImage(str(path))
        if image.isNull() or not image.hasAlphaChannel() or image.size().toTuple() != self._canvas_size(view_id):
            raise OutfitPackError("Provide a supported core body outline.")
        region = QRegion(QBitmap.fromImage(image.createAlphaMask()))
        if region.isEmpty():
            raise OutfitPackError("Core body outline requires visible content.")
        return region


    @staticmethod
    def _masked_hair(pixmap: QPixmap, anchor_x: int, anchor_y: int, alpha: QImage, bounds: QRect) -> QPixmap:
        image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawImage(bounds.x() - anchor_x, bounds.y() - anchor_y, alpha)
        painter.end()
        return QPixmap.fromImage(image)


    def _hair_core_mask(self, view_id: str) -> tuple[QImage, QRect] | None:
        """Alpha multiplier around the feature core, cached per view.

        Inside the core dilated by HAIRSTYLE_FEATURE_CORE_DILATION_PX the multiplier
        is 0; it ramps linearly to 1 over the next HAIRSTYLE_FEATURE_CORE_FEATHER_PX
        pixels, so the clip edge follows a feathered transition.  The image covers the core's neighbourhood (``bounds``); everything outside keeps its alpha.
        """
        if view_id in self._hair_mask_by_view:
            return self._hair_mask_by_view[view_id]
        core = self._feature_region(view_id)
        result = None
        if not core.isEmpty():
            dilation, feather = HAIRSTYLE_FEATURE_CORE_DILATION_PX, HAIRSTYLE_FEATURE_CORE_FEATHER_PX
            margin = dilation + feather + 1
            canvas = QRect(0, 0, *self._canvas_size(view_id))
            bounds = core.boundingRect().adjusted(-margin, -margin, margin, margin).intersected(canvas)
            ring = QImage(bounds.size(), QImage.Format_ARGB32)
            ring.fill(QColor(0, 0, 0, _OPAQUE))
            painter = QPainter(ring)
            painter.setClipRegion(core.translated(-bounds.x(), -bounds.y()))
            painter.fillRect(ring.rect(), Qt.white)
            painter.end()
            for _step in range(dilation):
                ring = self._dilated(ring)
            rings = [ring]
            for _step in range(feather):
                rings.append(self._dilated(rings[-1]))
            multiplier = QImage(bounds.size(), QImage.Format_ARGB32)
            multiplier.fill(QColor(_OPAQUE, _OPAQUE, _OPAQUE, _OPAQUE))
            painter = QPainter(multiplier)
            # Outermost ring first; each inner ring overrides with a lower value.
            for step in range(feather - 1, -1, -1):
                value = round(_OPAQUE * step / feather)
                coat = QImage(bounds.size(), QImage.Format_ARGB32)
                coat.fill(QColor(value, value, value, _OPAQUE))
                coat.setAlphaChannel(rings[step].convertToFormat(QImage.Format_Grayscale8))
                painter.drawImage(0, 0, coat)
            painter.end()
            alpha = QImage(bounds.size(), QImage.Format_ARGB32)
            alpha.fill(QColor(0, 0, 0, _OPAQUE))
            alpha.setAlphaChannel(multiplier.convertToFormat(QImage.Format_Grayscale8))
            result = (alpha, bounds)
        self._hair_mask_by_view[view_id] = result
        return result


    @staticmethod
    def _dilated(binary: QImage) -> QImage:
        """Grow the white pixels of an opaque black/white image by one pixel (8-neighbour)."""
        grown = QImage(binary)
        painter = QPainter(grown)
        painter.setCompositionMode(QPainter.CompositionMode_Lighten)
        for dx, dy in _DILATION_OFFSETS:
            painter.drawImage(dx, dy, binary)
        painter.end()
        return grown


    def _makeup_layers(
        self,
        archive: zipfile.ZipFile,
        declarations,
        variant,
        view_id: str,
        *,
        suppress_makeup_slots: frozenset[str] = frozenset(),
        eye_state: str = "rest",
    ) -> list[tuple[int, Layer]]:
        """Makeup is exempt from the protected-face mask but clipped to its safe region.

        The authored variant intensity and the user's slider multiply into one painter
        opacity: 0 leaves the bare base untouched, 1 paints the authored layer as-is.
        """
        opacity = float(variant.intensity) * read_makeup_intensity(self._store)
        region = self._makeup_safe_regions()[view_id]
        layers: list[tuple[int, Layer]] = []
        state_assets = variant.eye_states.get(eye_state)
        state_declarations = ()
        state_slots = frozenset()
        if state_assets is not None:
            try:
                state_declarations = state_assets[view_id]
            except KeyError:
                raise OutfitPackError("Provide the active silhouette for the makeup eye state.") from None
            state_slots = frozenset(asset.slot for asset in state_declarations)
            declarations = tuple(
                asset for asset in declarations if asset.slot not in state_slots
            ) + state_declarations
        declared_slots = frozenset(asset.slot for asset in declarations)
        slot_intensities = read_makeup_slot_intensities(
            self._store,
            slots=MAKEUP_SLOTS_V2 if FOUNDATION_SLOT in declared_slots else MAKEUP_SLOTS,
        )
        for declaration in declarations:
            encoded, image = self._decoded_layer(archive, declaration)
            if (image.width(), image.height()) != region.canvas or (declaration.anchor_x, declaration.anchor_y) != (0, 0):
                raise OutfitPackError("Makeup layers must cover the silhouette canvas at anchor 0,0.")
            # Runtime is as strict as import: a layer that paints outside its slot's safe
            # region fails closed instead of reaching the face.
            if makeup_layer_escapes(encoded, region, declaration.slot, state=eye_state):
                raise OutfitPackError("Makeup layer paints outside its safe region.")
            # A closed-eye authority must be able to cover open-eye makeup.
            # Validation above still runs for every declaration, so this is a
            # state-aware composition choice, not an import/runtime gate bypass.
            if declaration.slot in suppress_makeup_slots and declaration.slot not in state_slots:
                continue
            slot_opacity = opacity * slot_intensities[declaration.slot]
            if slot_opacity <= 0.0:
                continue
            clip = self._makeup_clip(view_id, region, declaration.slot, state=eye_state)
            layers.append((
                _MAKEUP_Z_BASE + declaration.z_order,
                (QPixmap.fromImage(image), 0, 0, clip, min(1.0, slot_opacity)),
            ))
        return layers


    def _makeup_safe_regions(self):
        if self._safe_regions is None:
            self._safe_regions = load_makeup_safe_regions(self._asset_root / "assets" / SAFE_REGION_FILE)
        return self._safe_regions


    def _makeup_clip(self, view_id: str, region, slot: str, *, state: str = "rest") -> QRegion:
        clip = QRegion()
        if slot == FOUNDATION_SLOT:
            mask = region.foundation_mask(state)
            if mask is None or len(mask.alpha) != mask.canvas[0] * mask.canvas[1]:
                raise OutfitPackError("Foundation safe mask is unavailable for the active eye state.")
            image = QImage(
                bytes(mask.alpha), mask.canvas[0], mask.canvas[1], mask.canvas[0],
                QImage.Format_Alpha8,
            )
            if image.isNull():
                raise OutfitPackError("Foundation safe mask needs a supported value.")
            # QImage.createAlphaMask() treats Format_Alpha8 as a colour
            # plane on Qt 6.11 and can turn a non-empty alpha plane into an
            # empty QRegion.  Use the shared nonzero-alpha ownership path,
            # which first binarizes and converts to ARGB32.
            clip = visible_alpha_region(image)
        else:
            for x, y, width, height in region.rects(slot):
                clip = clip.united(QRegion(QRect(x, y, width, height)))
        return clip.subtracted(
            self._makeup_exclusion_region(view_id, region, state=state)
        )


    def _makeup_exclusion_region(self, view_id: str, region, *, state: str = "rest") -> QRegion:
        """Keep visible eye apertures and the open oral cavity free of makeup."""
        cache_key = (view_id, state)
        cached = self._makeup_exclusion_by_view.get(cache_key)
        if cached is not None:
            return cached
        excluded = QRegion()
        eye_mask = region.eye_aperture_mask(state)
        if eye_mask is None:
            # Legacy v1 regions do not carry canonical motion masks.  Preserve
            # their existing rest-rig exclusion for every eye state.
            painted = self._rig_union(region.rig, EXCLUSION_RIG_LAYERS[0][0])
            covering = self._rig_union(region.rig, EXCLUSION_RIG_LAYERS[0][1])
            excluded = excluded.united(painted.subtracted(covering))
        else:
            if eye_mask.canvas != region.canvas or len(eye_mask.alpha) != region.canvas[0] * region.canvas[1]:
                raise OutfitPackError("Provide a supported eye aperture mask for the active silhouette.")
            image = QImage(
                bytes(eye_mask.alpha),
                eye_mask.canvas[0],
                eye_mask.canvas[1],
                eye_mask.canvas[0],
                QImage.Format_Alpha8,
            )
            if image.isNull():
                raise OutfitPackError("Eye aperture mask needs a supported value.")
            excluded = visible_alpha_region(image)
        # Oral cavity remains rig-derived because it is not driven by eye state.
        painted = self._rig_union(region.rig, EXCLUSION_RIG_LAYERS[1][0])
        covering = self._rig_union(region.rig, EXCLUSION_RIG_LAYERS[1][1])
        excluded = excluded.united(painted.subtracted(covering))
        self._makeup_exclusion_by_view[cache_key] = excluded
        return excluded


    def _rig_union(self, rig: str, layers) -> QRegion:
        union = QRegion()
        for layer in layers:
            source = QPixmap(str(self._asset_root / f"{rig}_{layer}.png"))
            if not source.isNull():
                union = union.united(QRegion(source.mask()))
        return union


    def _validate_alpha(
        self,
        pixmap: QPixmap,
        anchor_x: int,
        anchor_y: int,
        forbidden: QRegion,
        *,
        allow_empty: bool,
    ) -> bool:
        content = QRegion(pixmap.mask()).translated(anchor_x, anchor_y)
        if content.isEmpty():
            if allow_empty:
                return False
            raise OutfitPackError("Runtime garment layer requires content.")
        overlap = content.intersected(forbidden)
        # Runtime is deliberately stricter than the quarantine-time tolerance:
        # a garment keeps identity pixels outside its paint region.
        if not overlap.isEmpty():
            raise OutfitPackError("Runtime garment overlaps protected identity.")
        return True


    def _forbidden_face_region(
        self,
        category: str,
        item,
        variant,
        view_id: str,
    ) -> QRegion:
        # Hair may lie anywhere on the face except the feature core (eyes and
        # mouth); its authored face_masks rule no longer widens the clip.
        if category == "hairstyle":
            return self._feature_region(view_id)
        face = self._protected_face_region(view_id, self._canvas_size(view_id))
        bounds = face.boundingRect()
        allowed = QRegion()
        if category == "headwear":
            safe_mask = str(item.safe_mask or "")
            if safe_mask == "crown-safe":
                allowed = QRegion(QRect(bounds.x(), bounds.y(), bounds.width(), max(1, bounds.height() // 5)))
            elif safe_mask in {"temple-safe", "ear-safe"}:
                width = max(1, bounds.width() // 5)
                allowed = QRegion(QRect(bounds.x(), bounds.y(), width, bounds.height()))
                allowed = allowed.united(QRegion(QRect(bounds.right() - width + 1, bounds.y(), width, bounds.height())))
        forbidden = face.subtracted(allowed)
        if category == "headwear":
            forbidden = forbidden.united(self._feature_region(view_id))
        return forbidden


    def _feature_region(self, view_id: str) -> QRegion:
        """Union of the feature-core rig cut-outs (iris, eyelids, oral cavity, lips)."""
        cached = self._feature_by_view.get(view_id)
        if cached is not None:
            return cached
        root = (
            self._asset_root / "assets" / "expressions" / "layered"
            if view_id in HALF_BODY_RIGS
            else self._asset_root / "assets" / "pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME
        )
        prefix = HALF_BODY_RIGS.get(view_id, view_id)
        region = QRegion()
        for layer in FEATURE_CORE_LAYERS:
            source = QPixmap(str(root / f"{prefix}_{layer}.png"))
            if not source.isNull():
                region = region.united(QRegion(source.mask()))
        self._feature_by_view[view_id] = region
        return region


    def _protected_face_region(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> QRegion:
        cached = self._protected_by_view.get(view_id)
        if cached is not None:
            return cached
        path = self._protected_face_path(view_id)
        source = QPixmap(str(path))
        if source.isNull() or source.size().toTuple() != canvas_size:
            raise OutfitPackError("Protected identity mask is unavailable.")
        region = QRegion(source.mask())
        self._protected_by_view[view_id] = region
        return region


    def _protected_face_path(self, view_id: str) -> Path:
        rig = HALF_BODY_RIGS.get(view_id)
        if rig is not None:
            return self._asset_root / "assets" / "expressions" / "layered" / f"{rig}_base.png"
        return self._asset_root / "assets" / "pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME / f"{view_id}_base.png"


    @staticmethod
    def _canvas_size(view_id: str) -> tuple[int, int]:
        return HALF_BODY_CANVAS if view_id in HALF_BODY_RIGS else FULL_BODY_CANVAS


