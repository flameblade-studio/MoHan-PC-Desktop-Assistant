"""Fail-closed runtime adapter for every installed appearance-pack overlay."""

from __future__ import annotations

lazy import hashlib
lazy import re
lazy import zipfile
lazy from collections.abc import Callable
lazy from pathlib import Path

lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QImage, QPainter, QPixmap, QRegion

lazy from domain.constants import POSE_ATLAS_LAYERED_ROOT_NAME
lazy from domain.outfit_pack import (
    BODY_PROFILE_ID,
    MIN_Z_ORDER,
    SELECTION_CATEGORIES,
    IncompatibleBodyProfileError,
    OutfitPackError,
    inspect_outfit_pack,
    installed_pack_path,
    resolve_active_selection,
    resolve_variant_for_view,
    restore_builtin_outfit,
)
lazy from domain.outfit_pack_makeup import (
    EXCLUSION_RIG_LAYERS,
    MAKEUP_STATE_FILE,
    SAFE_REGION_FILE,
    load_makeup_safe_regions,
    makeup_layer_escapes,
    read_makeup_intensity,
)
lazy from domain.version_info import APP_VERSION

SEMVER_COMPONENT_COUNT = 3
_RANGE = re.compile(r">=(\d+)\.(\d+)\.(\d+),<(\d+)\.(\d+)\.(\d+)\Z")
_HALF_POSE = {
    "cheek-rest": "cheek",
    "left-neutral": "lean",
    "front-crossed": "front",
}
# Makeup always composites below every other category (skin < makeup < hair <
# headwear < garment/accessories); its declared z-order only orders the three
# makeup slots among themselves.
_MAKEUP_Z_BASE = MIN_Z_ORDER * 3

# One composited layer: pixmap, anchor x/y, the region it may paint, opacity.
Layer = tuple[QPixmap, int, int, QRegion, float]


class ActiveOutfitOverlay:
    """Resolve active.json through sealed packs and composite appearance assets.

    Official, user-imported, and cloud-generated packs share the exact same
    archive format, integrity checks and body-profile contract; source kind
    never bypasses a gate.
    """

    def __init__(
        self,
        store: Path,
        asset_root: Path,
        on_stale_body_profile: Callable[[], None] | None = None,
    ) -> None:
        self._store = Path(store)
        self._asset_root = Path(asset_root)
        self._on_stale_body_profile = on_stale_body_profile
        self._stale_pack_handled = False
        # (active.json token, makeup.json token); a missing file is None, so a
        # fresh store matches this initial value and keeps pre-seeded layers.
        self._state_token: tuple[tuple[int, int] | None, ...] = (None, None)
        self._package_tokens: dict[Path, tuple[int, int]] = {}
        self._layers_by_view: dict[str, tuple[Layer, ...]] = {}
        self._protected_by_view: dict[str, QRegion] = {}
        self._makeup_exclusion_by_view: dict[str, QRegion] = {}
        self._safe_regions = None

    def apply(self, frame: QPixmap, view_id: str) -> QPixmap:
        if frame.isNull():
            return frame
        try:
            self._refresh_state()
            layers = self._layers_by_view.get(view_id)
            if layers is None:
                layers = self._active_layers(
                    view_id,
                    frame.size().toTuple(),
                )
                self._layers_by_view[view_id] = layers
        except IncompatibleBodyProfileError:
            self._reject_stale_active_pack()
            return frame
        except (OSError, ValueError, OutfitPackError, zipfile.BadZipFile):
            return frame
        if not layers:
            return frame
        result = QPixmap(frame)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        for pixmap, anchor_x, anchor_y, clip, opacity in layers:
            painter.setClipRegion(clip)
            painter.setOpacity(opacity)
            painter.drawPixmap(anchor_x, anchor_y, pixmap)
        painter.end()
        return result

    def _reject_stale_active_pack(self) -> None:
        """Issue #140, option 3: a generation-1 pack is never rendered on the generation-2 body.

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

    def _selected_variant(self, category: str, selected) -> tuple[Path, object, object]:
        """Locate and validate the active pack, item and variant for one category."""
        archive_path = installed_pack_path(self._store, selected.effective_pack_id)
        archive_stat = archive_path.stat()
        self._package_tokens[archive_path] = (
            archive_stat.st_mtime_ns,
            archive_stat.st_size,
        )
        pack = inspect_outfit_pack(archive_path)
        if pack.compatible_body_profile != BODY_PROFILE_ID:
            raise IncompatibleBodyProfileError(
                f"Active pack {pack.pack_id!r} targets {pack.compatible_body_profile!r}, not {BODY_PROFILE_ID!r}."
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
            raise OutfitPackError("The active appearance item is missing.")
        variant = next(
            (
                value
                for value in item.variants
                if value.variant_id == selected.effective_variant_id
            ),
            None,
        )
        if variant is None:
            raise OutfitPackError("The active appearance variant is missing.")
        return archive_path, item, variant

    def _active_layers(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> tuple[Layer, ...]:
        result: list[tuple[int, int, Layer]] = []
        for category_index, category in enumerate(SELECTION_CATEGORIES):
            selected = resolve_active_selection(self._store, category)
            if selected.status == "builtin":
                continue
            archive_path, item, variant = self._selected_variant(category, selected)
            resolution = resolve_variant_for_view(variant, view_id)
            with zipfile.ZipFile(archive_path) as archive:
                if category == "makeup":
                    layers = self._makeup_layers(archive, resolution.assets, variant, view_id)
                else:
                    layers = self._garment_layers(
                        archive, resolution.assets, category, item, variant, view_id, canvas_size
                    )
            result.extend((z_order, category_index, layer) for z_order, layer in layers)
        result.sort(key=lambda value: (value[0], value[1]))
        return tuple(layer for _z_order, _index, layer in result)

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
        allowed = QRegion(QRect(0, 0, canvas_size[0], canvas_size[1])).subtracted(forbidden)
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
            layers.append((
                declaration.z_order,
                (pixmap, declaration.anchor_x, declaration.anchor_y, allowed, 1.0),
            ))
        return layers

    def _makeup_layers(
        self,
        archive: zipfile.ZipFile,
        declarations,
        variant,
        view_id: str,
    ) -> list[tuple[int, Layer]]:
        """Makeup is exempt from the protected-face mask but clipped to its safe region.

        The authored variant intensity and the user's slider multiply into one painter
        opacity: 0 leaves the bare base untouched, 1 paints the authored layer as-is.
        """
        opacity = float(variant.intensity) * read_makeup_intensity(self._store)
        region = self._makeup_safe_regions()[view_id]
        layers: list[tuple[int, Layer]] = []
        for declaration in declarations:
            encoded, image = self._decoded_layer(archive, declaration)
            if (image.width(), image.height()) != region.canvas or (declaration.anchor_x, declaration.anchor_y) != (0, 0):
                raise OutfitPackError("Makeup layers must cover the silhouette canvas at anchor 0,0.")
            # Runtime is as strict as import: a layer that paints outside its slot's safe
            # region fails closed instead of reaching the face.
            if makeup_layer_escapes(encoded, region, declaration.slot):
                raise OutfitPackError("Makeup layer paints outside its safe region.")
            if opacity <= 0.0:
                continue
            clip = self._makeup_clip(view_id, region, declaration.slot)
            layers.append((
                _MAKEUP_Z_BASE + declaration.z_order,
                (QPixmap.fromImage(image), 0, 0, clip, min(1.0, opacity)),
            ))
        return layers

    def _makeup_safe_regions(self):
        if self._safe_regions is None:
            self._safe_regions = load_makeup_safe_regions(self._asset_root / "assets" / SAFE_REGION_FILE)
        return self._safe_regions

    def _makeup_clip(self, view_id: str, region, slot: str) -> QRegion:
        clip = QRegion()
        for x, y, width, height in region.rects(slot):
            clip = clip.united(QRegion(QRect(x, y, width, height)))
        return clip.subtracted(self._makeup_exclusion_region(view_id, region))

    def _makeup_exclusion_region(self, view_id: str, region) -> QRegion:
        """Visible iris and open oral cavity, from the layered rig, never receive makeup."""
        cached = self._makeup_exclusion_by_view.get(view_id)
        if cached is not None:
            return cached
        excluded = QRegion()
        for painted_layers, covering_layers in EXCLUSION_RIG_LAYERS:
            painted = self._rig_union(region.rig, painted_layers)
            covering = self._rig_union(region.rig, covering_layers)
            excluded = excluded.united(painted.subtracted(covering))
        self._makeup_exclusion_by_view[view_id] = excluded
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
            raise OutfitPackError("Runtime garment layer is empty.")
        overlap = content.intersected(forbidden)
        # Runtime is deliberately stricter than the quarantine-time tolerance:
        # a garment never has a legitimate reason to paint identity pixels.
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
        face = self._protected_face_region(view_id, self._canvas_size(view_id))
        bounds = face.boundingRect()
        allowed = QRegion()
        if category == "hairstyle":
            rule = "none" if variant.face_masks is None else variant.face_masks[view_id]
            if rule == "hairline-safe":
                allowed = QRegion(QRect(bounds.x(), bounds.y(), bounds.width(), max(1, bounds.height() // 4)))
            elif rule == "bangs-safe":
                allowed = QRegion(QRect(bounds.x(), bounds.y(), bounds.width(), max(1, bounds.height() * 48 // 100)))
            elif rule == "side-locks-safe":
                width = max(1, bounds.width() * 28 // 100)
                allowed = QRegion(QRect(bounds.x(), bounds.y(), width, bounds.height()))
                allowed = allowed.united(QRegion(QRect(bounds.right() - width + 1, bounds.y(), width, bounds.height())))
        elif category == "headwear":
            safe_mask = str(item.safe_mask or "")
            if safe_mask == "crown-safe":
                allowed = QRegion(QRect(bounds.x(), bounds.y(), bounds.width(), max(1, bounds.height() // 5)))
            elif safe_mask in {"temple-safe", "ear-safe"}:
                width = max(1, bounds.width() // 5)
                allowed = QRegion(QRect(bounds.x(), bounds.y(), width, bounds.height()))
                allowed = allowed.united(QRegion(QRect(bounds.right() - width + 1, bounds.y(), width, bounds.height())))
        forbidden = face.subtracted(allowed)
        if category in {"hairstyle", "headwear"}:
            forbidden = forbidden.united(self._feature_region(view_id))
        return forbidden

    def _feature_region(self, view_id: str) -> QRegion:
        root = (
            self._asset_root / "assets" / "expressions" / "layered"
            if view_id in _HALF_POSE
            else self._asset_root / "assets" / "pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME
        )
        prefix = _HALF_POSE.get(view_id, view_id)
        region = QRegion()
        for layer in (
            "iris_left",
            "iris_right",
            "eyelid_left",
            "eyelid_right",
            "oral_cavity",
            "lip_upper",
            "lip_lower",
        ):
            source = QPixmap(str(root / f"{prefix}_{layer}.png"))
            if not source.isNull():
                region = region.united(QRegion(source.mask()))
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
        pose = _HALF_POSE.get(view_id)
        if pose is not None:
            return self._asset_root / "assets" / "expressions" / "layered" / f"{pose}_base.png"
        return self._asset_root / "assets" / "pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME / f"{view_id}_base.png"

    @staticmethod
    def _canvas_size(view_id: str) -> tuple[int, int]:
        return (1254, 1254) if view_id in _HALF_POSE else (1024, 1536)

    @staticmethod
    def _compatible(app_range: str) -> bool:
        # Reject a malformed pack range first: the pack's own metadata is the
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
