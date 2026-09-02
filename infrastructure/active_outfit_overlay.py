"""Fail-closed runtime adapter for every installed appearance-pack overlay."""

from __future__ import annotations

lazy import hashlib
lazy import re
lazy import zipfile
lazy from pathlib import Path

lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QImage, QPainter, QPixmap, QRegion

lazy from domain.constants import POSE_ATLAS_LAYERED_ROOT_NAME
lazy from domain.outfit_pack import (
    BODY_PROFILE_ID,
    SELECTION_CATEGORIES,
    OutfitPackError,
    inspect_outfit_pack,
    resolve_active_selection,
    resolve_variant_for_view,
)
lazy from domain.version_info import APP_VERSION

SEMVER_COMPONENT_COUNT = 3
_RANGE = re.compile(r">=(\d+)\.(\d+)\.(\d+),<(\d+)\.(\d+)\.(\d+)\Z")
_HALF_POSE = {
    "cheek-rest": "cheek",
    "left-neutral": "lean",
    "front-crossed": "front",
}


class ActiveOutfitOverlay:
    """Resolve active.json through sealed packs and composite appearance assets.

    Official, user-imported, and cloud-generated packs share the exact same
    archive format, integrity checks and body-profile contract; source kind
    never bypasses a gate.
    """

    def __init__(self, store: Path, asset_root: Path) -> None:
        self._store = Path(store)
        self._asset_root = Path(asset_root)
        self._state_token: tuple[int, int] | None = None
        self._package_tokens: dict[Path, tuple[int, int]] = {}
        self._layers_by_view: dict[
            str,
            tuple[tuple[QPixmap, int, int, QRegion], ...],
        ] = {}
        self._protected_by_view: dict[str, QRegion] = {}

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
        except (OSError, ValueError, OutfitPackError, zipfile.BadZipFile):
            return frame
        if not layers:
            return frame
        result = QPixmap(frame)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        for pixmap, anchor_x, anchor_y, forbidden in layers:
            painter.setClipRegion(QRegion(result.rect()).subtracted(forbidden))
            painter.drawPixmap(anchor_x, anchor_y, pixmap)
        painter.end()
        return result

    def _refresh_state(self) -> None:
        path = self._store / "active.json"
        try:
            stat = path.stat()
        except FileNotFoundError:
            token = None
        else:
            token = (stat.st_mtime_ns, stat.st_size)
        current_package_tokens: dict[Path, tuple[int, int]] = {}
        for package_path in self._package_tokens:
            try:
                package_stat = package_path.stat()
            except FileNotFoundError:
                continue
            current_package_tokens[package_path] = (
                package_stat.st_mtime_ns,
                package_stat.st_size,
            )
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

    def _active_layers(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
    ) -> tuple[tuple[QPixmap, int, int, QRegion], ...]:
        result = []
        for category_index, category in enumerate(SELECTION_CATEGORIES):
            selected = resolve_active_selection(self._store, category)
            if selected.status == "builtin":
                continue
            archive_path = (
                self._store
                / "packages"
                / f"{selected.effective_pack_id}.mohan-outfit"
            )
            archive_stat = archive_path.stat()
            self._package_tokens[archive_path] = (
                archive_stat.st_mtime_ns,
                archive_stat.st_size,
            )
            pack = inspect_outfit_pack(archive_path)
            if pack.compatible_body_profile != BODY_PROFILE_ID or not self._compatible(
                pack.app_range
            ):
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
            resolution = resolve_variant_for_view(variant, view_id)
            forbidden = self._forbidden_face_region(
                category,
                item,
                variant,
                view_id,
            )
            with zipfile.ZipFile(archive_path) as archive:
                for declaration in resolution.assets:
                    if Path(declaration.path).suffix.lower() != ".png":
                        raise OutfitPackError(
                            "Runtime appearance layers must be RGBA PNG."
                        )
                    encoded = archive.read(declaration.path)
                    if hashlib.sha256(encoded).hexdigest() != declaration.sha256:
                        raise OutfitPackError("Runtime appearance hash mismatch.")
                    image = QImage.fromData(encoded, "PNG")
                    if image.isNull() or image.hasAlphaChannel() is False:
                        raise OutfitPackError("Runtime appearance must have alpha.")
                    if (image.width(), image.height()) != (
                        declaration.width,
                        declaration.height,
                    ):
                        raise OutfitPackError(
                            "Runtime appearance dimensions disagree."
                        )
                    if (
                        declaration.anchor_x < 0
                        or declaration.anchor_y < 0
                        or declaration.anchor_x + image.width() > canvas_size[0]
                        or declaration.anchor_y + image.height() > canvas_size[1]
                    ):
                        raise OutfitPackError(
                            "Runtime appearance anchor escaped the canvas."
                        )
                    pixmap = QPixmap.fromImage(
                        image.convertToFormat(QImage.Format_RGBA8888)
                    )
                    has_content = self._validate_alpha(
                        pixmap,
                        declaration.anchor_x,
                        declaration.anchor_y,
                        forbidden,
                        allow_empty=category != "garment",
                    )
                    if not has_content:
                        continue
                    result.append(
                        (
                            declaration.z_order,
                            category_index,
                            pixmap,
                            declaration.anchor_x,
                            declaration.anchor_y,
                            forbidden,
                        )
                    )
        result.sort(key=lambda value: (value[0], value[1]))
        return tuple((value[2], value[3], value[4], value[5]) for value in result)

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
