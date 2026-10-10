"""Resolve source-bound and legacy base-clear regions for outfit composition."""

from __future__ import annotations

lazy import zipfile
lazy import numpy as np
lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QImage, QPixmap, QRegion

lazy from domain.outfit_pack import (
    GESTURE_SILHOUETTES,
    OPTIONAL_EXPRESSION_APPEARANCE_SILHOUETTES,
    POSE_ATLAS_SILHOUETTES,
    OutfitPackError,
    resolve_variant_for_view,
)
lazy from domain.outfit_pack_official import (
    OFFICIAL_OUTFIT_CATEGORIES,
    is_official_native_alias,
    official_outfit_pack_id,
)
lazy from domain.character_runtime import (
    CHARACTER_ASSET_PATHS,
    CHARACTER_EXPRESSION_ROLES,
    CHARACTER_LAYER_ROLES,
    character_rig_manifest,
    pose_atlas_layered_relative_root,
)
lazy from domain.outfit_pack_makeup import HALF_BODY_RIGS
lazy from domain.qt_image_pixels import rgba8888_image
lazy from infrastructure.active_outfit_overlay_layers import (
    FULL_BODY_CANVAS,
    HALF_BODY_CANVAS,
)
lazy from infrastructure.image_alpha_regions import visible_alpha_region
lazy from infrastructure.source_bound_garment_visibility import (
    MANIFEST,
    GarmentBinding,
    load_garment_binding,
    validate_garment_removal,
)

V5_NECK_GUARD_SIDE_PX = 25
V5_NECK_GUARD_HEIGHT_PX = 110
NATIVE_HEAD_CLEAR_DILATION_PX = 2
HALF_BODY_NATIVE_HEAD_CLEAR_DILATION_PX = 40
IDENTITY_GUARD_SIDE_PX = 100
IDENTITY_GUARD_TOP_PX = 80
IDENTITY_GUARD_BOTTOM_PX = 100
IDENTITY_SKIN_DILATION_PX = 24
IDENTITY_SKIN_RED_MIN = 125
IDENTITY_SKIN_RED_GREEN_GAP = 12
IDENTITY_SKIN_GREEN_BLUE_GAP = 3
NATIVE_HEAD_LAYERS = (
    CHARACTER_LAYER_ROLES["rear_hair"],
    CHARACTER_LAYER_ROLES["left_side_hair"],
    CHARACTER_LAYER_ROLES["right_side_hair"],
    "ornament",
)
NATIVE_IDENTITY_LAYER = "body"
GESTURE_NATIVE_HAIR_BOTTOM_PX = 650
GESTURE_IDENTITY_SKIN_DILATION_PX = 2
GESTURE_FACE_SKIN_GUARD = QRect(380, 200, 500, 420)
# Source-bound faces stay near the shared portrait anchor, but their former
# broad guards also covered an earring-sized strip beside each ear and the
# shirt collar below the chin.  Keep only the actual eye/brow and mouth bands.
GESTURE_EYE_FEATURE_GUARD = QRect(500, 395, 210, 60)
GESTURE_MOUTH_FEATURE_GUARD = QRect(545, 535, 115, 55)
GESTURE_TILTED_EYE_FEATURE_GUARD = QRect(480, 470, 210, 50)
GESTURE_TILTED_MOUTH_FEATURE_GUARD = QRect(560, 600, 100, 50)
OPTIONAL_CHEEK_WRIST_ARTIFACT_TOP = 1140
OPTIONAL_CHEEK_WRIST_ARTIFACT_BOTTOM = 1217
OPTIONAL_CHEEK_WRIST_ARTIFACT_LEFT = 587
OPTIONAL_CHEEK_WRIST_ARTIFACT_RIGHT = 611
OPTIONAL_CHEEK_WRIST_ARTIFACT_RADIUS = 2
SOURCE_BOUND_EXPRESSION_SILHOUETTES = frozenset((
    *GESTURE_SILHOUETTES,
    *OPTIONAL_EXPRESSION_APPEARANCE_SILHOUETTES,
))
_EXASPERATED_SILHOUETTE = character_rig_manifest().gesture_silhouettes[
    CHARACTER_EXPRESSION_ROLES["exasperation"]
]


class ActiveOutfitBaseClearMixin:
    """Choose the exact body region removed before appearance layers are painted."""

    @staticmethod
    def _dilated_region(region: QRegion, radius: int) -> QRegion:
        result = QRegion(region)
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx or dy:
                    result = result.united(region.translated(dx, dy))
        return result

    @staticmethod
    def _square_dilated_region(region: QRegion, radius: int) -> QRegion:
        horizontal = QRegion(region)
        for offset in range(-radius, radius + 1):
            horizontal = horizontal.united(region.translated(offset, 0))
        result = QRegion(horizontal)
        for offset in range(-radius, radius + 1):
            result = result.united(horizontal.translated(0, offset))
        return result

    @staticmethod
    def _optional_cheek_wrist_artifact_region() -> QRegion:
        """Return the narrow source bracelet seam shared by optional cheek poses."""

        result = QRegion()
        height = (
            OPTIONAL_CHEEK_WRIST_ARTIFACT_BOTTOM
            - OPTIONAL_CHEEK_WRIST_ARTIFACT_TOP
        )
        width = (
            OPTIONAL_CHEEK_WRIST_ARTIFACT_RIGHT
            - OPTIONAL_CHEEK_WRIST_ARTIFACT_LEFT
        )
        diameter = 2 * OPTIONAL_CHEEK_WRIST_ARTIFACT_RADIUS + 1
        for y in range(
            OPTIONAL_CHEEK_WRIST_ARTIFACT_TOP,
            OPTIONAL_CHEEK_WRIST_ARTIFACT_BOTTOM + 1,
        ):
            x = round(
                OPTIONAL_CHEEK_WRIST_ARTIFACT_LEFT
                + width * (y - OPTIONAL_CHEEK_WRIST_ARTIFACT_TOP) / height
            )
            result = result.united(QRegion(QRect(
                x - OPTIONAL_CHEEK_WRIST_ARTIFACT_RADIUS,
                y,
                diameter,
                1,
            )))
        return result

    @staticmethod
    def _skin_region(image: QImage) -> QRegion:
        rgba = rgba8888_image(image)
        rows = np.frombuffer(rgba.constBits(), dtype=np.uint8).reshape(
            rgba.height(), rgba.bytesPerLine(),
        )
        pixels = rows[:, :rgba.width() * 4].reshape(
            rgba.height(), rgba.width(), 4,
        )
        red = pixels[:, :, 0].astype(np.int16)
        green = pixels[:, :, 1].astype(np.int16)
        blue = pixels[:, :, 2].astype(np.int16)
        skin = (
            (pixels[:, :, 3] > 0)
            & (red > IDENTITY_SKIN_RED_MIN)
            & (red > green + IDENTITY_SKIN_RED_GREEN_GAP)
            & (green > blue + IDENTITY_SKIN_GREEN_BLUE_GAP)
        )
        alpha = np.where(skin, 255, 0).astype(np.uint8)
        mask = QImage(
            alpha.data,
            rgba.width(),
            rgba.height(),
            rgba.width(),
            QImage.Format_Alpha8,
        ).copy()
        return visible_alpha_region(mask)

    def _native_gesture_source(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> QImage:
        path = (
            self._asset_root
            / CHARACTER_ASSET_PATHS["halfbody_root"]
            / "complete-expressions"
            / "frames"
            / f"{view_id}-neutral-rest.rgba.png"
        )
        pixmap = QPixmap(str(path))
        if pixmap.isNull() or pixmap.size().toTuple() != canvas_size:
            raise OutfitPackError("Native gesture ownership is unavailable.")
        return pixmap.toImage()

    @staticmethod
    def _native_gesture_hair_region(image: QImage) -> QRegion:
        """Return source-owned non-skin material around an exact-pose head.

        The optional expression sources can contain pale ornaments and blue
        collar pixels as well as dark native hair.  A luminance-only hair
        probe leaves those pixels behind under a replacement hairstyle, so
        clear every visible non-skin source pixel in the head band.  Identity
        and hands are subtracted from the replacement region by their own
        authoritative guards.
        """
        rgba = rgba8888_image(image)
        rows = np.frombuffer(rgba.constBits(), dtype=np.uint8).reshape(
            rgba.height(), rgba.bytesPerLine(),
        )
        pixels = rows[:, :rgba.width() * 4].reshape(
            rgba.height(), rgba.width(), 4,
        )
        yy = np.arange(rgba.height(), dtype=np.int32)[:, None]
        red = pixels[:, :, 0].astype(np.int16)
        green = pixels[:, :, 1].astype(np.int16)
        blue = pixels[:, :, 2].astype(np.int16)
        skin = (
            (pixels[:, :, 3] > 0)
            & (red > IDENTITY_SKIN_RED_MIN)
            & (red > green + IDENTITY_SKIN_RED_GREEN_GAP)
            & (green > blue + IDENTITY_SKIN_GREEN_BLUE_GAP)
        )
        source_material = (
            (pixels[:, :, 3] > 0)
            & (yy < GESTURE_NATIVE_HAIR_BOTTOM_PX)
            & (~skin | (yy < GESTURE_FACE_SKIN_GUARD.top()))
        )
        alpha = np.where(source_material, 255, 0).astype(np.uint8)
        mask = QImage(
            alpha.data,
            rgba.width(),
            rgba.height(),
            rgba.width(),
            QImage.Format_Alpha8,
        ).copy()
        return visible_alpha_region(mask)

    def _native_head_region(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> QRegion:
        cached = self._native_head_regions_by_view.get(view_id)
        if cached is not None:
            return QRegion(cached)
        if view_id in SOURCE_BOUND_EXPRESSION_SILHOUETTES:
            result = self._dilated_region(
                self._native_gesture_hair_region(
                    self._native_gesture_source(view_id, canvas_size)
                ),
                NATIVE_HEAD_CLEAR_DILATION_PX,
            )
            self._native_head_regions_by_view[view_id] = QRegion(result)
            return result
        half_body = view_id in HALF_BODY_RIGS
        root = self._asset_root / (
            CHARACTER_ASSET_PATHS["halfbody_layers"]
            if half_body else pose_atlas_layered_relative_root()
        )
        prefix = HALF_BODY_RIGS.get(view_id, view_id)
        region = QRegion()
        for layer in NATIVE_HEAD_LAYERS:
            pixmap = QPixmap(str(root / f"{prefix}_{layer}.png"))
            if pixmap.isNull() or pixmap.size().toTuple() != canvas_size:
                raise OutfitPackError("Native hair ownership is unavailable.")
            region = region.united(visible_alpha_region(pixmap.toImage()))
        result = (
            self._square_dilated_region(
                region,
                HALF_BODY_NATIVE_HEAD_CLEAR_DILATION_PX,
            )
            if half_body
            else self._dilated_region(region, NATIVE_HEAD_CLEAR_DILATION_PX)
        )
        self._native_head_regions_by_view[view_id] = QRegion(result)
        return result

    def _native_identity_region(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> QRegion:
        cached = self._native_identity_regions_by_view.get(view_id)
        if cached is not None:
            return QRegion(cached)
        if view_id in SOURCE_BOUND_EXPRESSION_SILHOUETTES:
            source = self._native_gesture_source(view_id, canvas_size)
            identity = self._square_dilated_region(
                self._skin_region(source).intersected(
                    QRegion(GESTURE_FACE_SKIN_GUARD)
                ),
                GESTURE_IDENTITY_SKIN_DILATION_PX,
            )
            # Protect the authored pixels that actually animate.  A broad
            # rectangle also retained native temple hair and ornament edges,
            # which then showed through the replacement hairstyle as dark
            # diagonal streaks.  Synthetic/minimal assets used by tests may
            # not provide a full expression matrix, so keep the fixed bands
            # as a compatibility fallback only.
            feature = self._gesture_expression_feature_region(view_id)
            if feature is None or feature.isEmpty():
                feature = (
                    QRegion(GESTURE_TILTED_EYE_FEATURE_GUARD).united(
                        QRegion(GESTURE_TILTED_MOUTH_FEATURE_GUARD)
                    )
                    if view_id == _EXASPERATED_SILHOUETTE
                    else QRegion(GESTURE_EYE_FEATURE_GUARD).united(
                        QRegion(GESTURE_MOUTH_FEATURE_GUARD)
                    )
                )
            identity = identity.united(
                self._square_dilated_region(feature, 12)
            )
            self._native_identity_regions_by_view[view_id] = QRegion(identity)
            return identity
        feature = self._feature_region(view_id)
        # The explicit protected-face cut-out owns the forehead and temples as
        # well as the animated feature core.  Starting from feature pixels
        # alone lets an expanded native-hair clear punch holes through skin.
        protected = QRegion(self._protected_face_region(view_id, canvas_size))
        if view_id in HALF_BODY_RIGS:
            source = QImage(str(self._protected_face_path(view_id)))
            if not source.isNull() and source.size().toTuple() == canvas_size:
                protected = protected.intersected(
                    self._square_dilated_region(self._skin_region(source), 2)
                )
        identity = protected.united(feature)
        bounds = feature.boundingRect()
        if not bounds.isEmpty():
            identity = identity.united(QRegion(QRect(
                bounds.left() - IDENTITY_GUARD_SIDE_PX,
                bounds.top() - IDENTITY_GUARD_TOP_PX,
                bounds.width() + 2 * IDENTITY_GUARD_SIDE_PX,
                bounds.height() + IDENTITY_GUARD_TOP_PX + IDENTITY_GUARD_BOTTOM_PX,
            )))
        half_body = view_id in HALF_BODY_RIGS
        root = self._asset_root / (
            CHARACTER_ASSET_PATHS["halfbody_layers"]
            if half_body else pose_atlas_layered_relative_root()
        )
        prefix = HALF_BODY_RIGS.get(view_id, view_id)
        body = QPixmap(str(root / f"{prefix}_{NATIVE_IDENTITY_LAYER}.png"))
        if body.isNull() or body.size().toTuple() != canvas_size:
            raise OutfitPackError("Native identity ownership is unavailable.")
        head_bounds = self._native_head_region(view_id, canvas_size).boundingRect()
        if head_bounds.isEmpty():
            raise OutfitPackError("Native head ownership is unavailable.")
        head_guard = QRegion(QRect(
            head_bounds.left() - IDENTITY_GUARD_SIDE_PX,
            head_bounds.top() - IDENTITY_GUARD_TOP_PX,
            head_bounds.width() + 2 * IDENTITY_GUARD_SIDE_PX,
            head_bounds.height() + IDENTITY_GUARD_TOP_PX + IDENTITY_GUARD_BOTTOM_PX,
        ))
        body_identity = self._square_dilated_region(
            self._skin_region(body.toImage()),
            IDENTITY_SKIN_DILATION_PX,
        ).intersected(head_guard)
        identity = identity.united(body_identity)
        self._native_identity_regions_by_view[view_id] = QRegion(identity)
        return identity

    def _active_hairstyle_region(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
        hairstyle,
    ) -> QRegion:
        archive_path, _item, variant = self._selected_variant(
            "hairstyle", hairstyle,
        )
        declarations = resolve_variant_for_view(variant, view_id).assets
        region = QRegion()
        self._diagnostic_pack_id = hairstyle.effective_pack_id
        with zipfile.ZipFile(archive_path) as archive:
            for declaration in declarations:
                _encoded, image = self._decoded_layer(archive, declaration)
                if (
                    declaration.anchor_x < 0
                    or declaration.anchor_y < 0
                    or declaration.anchor_x + image.width() > canvas_size[0]
                    or declaration.anchor_y + image.height() > canvas_size[1]
                ):
                    raise OutfitPackError(
                        "Runtime appearance anchor escaped the canvas."
                    )
                region = region.united(
                    visible_alpha_region(image).translated(
                        declaration.anchor_x,
                        declaration.anchor_y,
                    )
                )
        return region

    def _generic_hair_replacement_region(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> tuple[QRegion, QRegion | None]:
        hairstyle = self._resolve_base_clear_selection("hairstyle")
        if hairstyle.status == "builtin":
            return QRegion(), None
        identity = (
            hairstyle.effective_pack_id,
            hairstyle.effective_item_id,
            hairstyle.effective_variant_id,
        )
        if is_official_native_alias("hairstyle", identity):
            return QRegion(), None
        native_head = self._native_head_region(view_id, canvas_size)
        authored_hair = self._active_hairstyle_region(
            view_id,
            canvas_size,
            hairstyle,
        )
        replacement = native_head.subtracted(
            self._native_identity_region(view_id, canvas_size)
        )
        if (
            view_id in SOURCE_BOUND_EXPRESSION_SILHOUETTES
            and self._visible_hand_region is not None
        ):
            hands = self._visible_hand_region(view_id)
            if not isinstance(hands, QRegion):
                raise OutfitPackError("Native hand ownership is invalid.")
            replacement = replacement.subtracted(hands)
        # Exact-frame expressions do not share the front rig's hair geometry.
        # Clear every native-hair pixel outside their source identity guard.
        if (
            view_id not in SOURCE_BOUND_EXPRESSION_SILHOUETTES
            and view_id not in HALF_BODY_RIGS
        ):
            # Full-body authoring predates the portrait rig and relies on
            # native hair below its opaque replacement silhouette.
            replacement = replacement.subtracted(authored_hair)
        return replacement, native_head

    def _generic_garment_replacement_region(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
        native_head: QRegion | None,
    ) -> tuple[QRegion, bool]:
        garment = self._resolve_base_clear_selection("garment")
        if (
            garment.status == "builtin"
            or garment.effective_pack_id == official_outfit_pack_id()
        ):
            return QRegion(), False
        archive_path, _item, variant = self._selected_variant("garment", garment)
        declarations = tuple(
            declaration
            for declaration in resolve_variant_for_view(variant, view_id).assets
            if declaration.clears_base
        )
        if not declarations:
            return QRegion(), False
        head = native_head or self._native_head_region(view_id, canvas_size)
        garment_region = QRegion()
        with zipfile.ZipFile(archive_path) as archive:
            for declaration in declarations:
                _encoded, image = self._decoded_layer(archive, declaration)
                garment_region = garment_region.united(
                    visible_alpha_region(image).translated(
                        declaration.anchor_x,
                        declaration.anchor_y,
                    )
                )
        native_identity = (
            self._skin_region(self._native_gesture_source(view_id, canvas_size))
            if view_id in SOURCE_BOUND_EXPRESSION_SILHOUETTES
            else self._native_identity_region(view_id, canvas_size)
        )
        if view_id in OPTIONAL_EXPRESSION_APPEARANCE_SILHOUETTES:
            # These five exact-pose sources share a thin bracelet/metal seam at
            # the lower wrist.  It is warm enough to pass the general skin
            # classifier, so remove only its measured diagonal support.  The
            # pack's rear repair layer restores the approved bare-skin pixels.
            native_identity = native_identity.subtracted(
                self._optional_cheek_wrist_artifact_region()
            )
        protected = self._protected_face_region(
            view_id, canvas_size,
        ).united(head).united(native_identity)
        if self._visible_hand_region is not None:
            hands = self._visible_hand_region(view_id)
            if not isinstance(hands, QRegion):
                raise OutfitPackError("Native hand ownership is invalid.")
            protected = protected.united(hands)
        return garment_region.subtracted(protected), True

    def _generic_replacement_region(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> tuple[QRegion | None, bool]:
        supported_canvas = (
            view_id in POSE_ATLAS_SILHOUETTES
            and canvas_size == FULL_BODY_CANVAS
        ) or (
            view_id in HALF_BODY_RIGS
            and canvas_size == HALF_BODY_CANVAS
        )
        if not supported_canvas:
            return None, False
        if view_id in self._generic_base_clear_by_view:
            cached, clears_garment = self._generic_base_clear_by_view[view_id]
            return (
                None if cached is None else QRegion(cached),
                clears_garment,
            )
        replacement, native_head = self._generic_hair_replacement_region(
            view_id, canvas_size,
        )
        garment_region, clears_garment = self._generic_garment_replacement_region(
            view_id, canvas_size, native_head,
        )
        replacement = replacement.united(garment_region)
        result = None if replacement.isEmpty() else replacement
        self._generic_base_clear_by_view[view_id] = (
            None if result is None else QRegion(result),
            clears_garment,
        )
        return result, clears_garment

    def _base_clear_regions(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
        garment_is_active: bool,
        include_core: bool,
    ) -> tuple[QRegion | None, QRegion | None, GarmentBinding | None]:
        """Prefer an exact source-bound removal; retain the legacy route otherwise."""
        binding = None
        if garment_is_active and (self._asset_root / MANIFEST).exists():
            selected = self._resolve_base_clear_selection("garment")
            archive_path, _item, variant = self._selected_variant("garment", selected)
            binding = load_garment_binding(
                self._asset_root, view_id, selected, archive_path, variant,
            )
            if binding is not None:
                visible_hands = self._visible_hand_region
                if binding.hand_region is not None:
                    hand_region = binding.hand_region
                    visible_hands = lambda _view: hand_region
                validate_garment_removal(
                    self._asset_root, view_id, canvas_size, binding.removal,
                    self._protected_face_region(view_id, canvas_size),
                    visible_hands,
                )
        if binding is not None:
            silhouette = None
            replacement = QRegion(binding.removal)
        else:
            silhouette = (
                self._selected_silhouette_region(
                    view_id, canvas_size, garment_is_active,
                )
                if include_core else None
            )
            replacement = (
                self._official_replacement_region(view_id, canvas_size)
                if include_core and self._official_outfit_is_active() else None
            )
            if (
                include_core
                and view_id in POSE_ATLAS_SILHOUETTES
                and canvas_size == FULL_BODY_CANVAS
            ):
                head = self._protected_face_region(
                    view_id, canvas_size,
                ).boundingRect()
                if not head.isEmpty():
                    native_head = QRegion(
                        QRect(0, 0, canvas_size[0], head.bottom() + 1)
                    )
                    native_head = native_head.united(QRegion(QRect(
                        head.left() - V5_NECK_GUARD_SIDE_PX,
                        head.bottom() + 1,
                        head.width() + 2 * V5_NECK_GUARD_SIDE_PX,
                        V5_NECK_GUARD_HEIGHT_PX,
                    )))
                    if silhouette is not None:
                        silhouette = silhouette.united(native_head)
                    if replacement is not None:
                        replacement = replacement.subtracted(native_head)
        generic, generic_clears_garment = (None, False)
        if include_core:
            generic, generic_clears_garment = self._generic_replacement_region(
                view_id, canvas_size,
            )
            if generic is not None:
                replacement = (
                    generic
                    if replacement is None
                    else replacement.united(generic)
                )
        if binding is not None and replacement is not None:
            binding = GarmentBinding(
                replacement,
                binding.hand_overlays,
                binding.hand_region,
            )
        elif generic_clears_garment and replacement is not None:
            # A sealed base-clear deliberately retains the base-owned hands.
            # The empty tuple prevents unrelated global V5 hand fragments from
            # being painted over an already complete native body frame.
            binding = GarmentBinding(replacement, (), None)
        return silhouette, replacement, binding

    def _selected_silhouette_region(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
        garment_is_active: bool,
    ) -> QRegion | None:
        """Keep garment occlusion when independently changing hair or headwear."""
        if self._official_outfit_is_active():
            return self._official_silhouette_region(view_id, canvas_size)
        if not garment_is_active:
            return None
        garment = self._resolve_base_clear_selection("garment")
        if garment.effective_pack_id != official_outfit_pack_id():
            return None
        silhouette = self._official_silhouette_region(view_id, canvas_size)
        if silhouette is None:
            return None
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
            selected = self._resolve_base_clear_selection(category)
            if (
                getattr(selected, "effective_pack_id", None)
                == official_outfit_pack_id()
            ):
                continue
            requested = tuple(
                getattr(selected, f"requested_{field}", None)
                for field in ("pack_id", "item_id", "variant_id")
            )
            effective = tuple(
                getattr(selected, f"effective_{field}", None)
                for field in ("pack_id", "item_id", "variant_id")
            )
            if (
                category == "headwear"
                and getattr(selected, "status", None) == "builtin"
                and requested == effective == ("builtin", "none", "none")
            ):
                continue
            result = False
            break
        self._official_outfit_active_cache = result
        return result

    def _garment_is_active(self) -> bool:
        """Resolve the active garment once per appearance-state token."""
        if self._garment_active_cache is None:
            self._garment_active_cache = (
                self._resolve_base_clear_selection("garment").status != "builtin"
            )
        return self._garment_active_cache
