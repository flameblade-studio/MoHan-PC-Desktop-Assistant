"""Resolve and validate declared outfit assets as safe canvas layers."""

from __future__ import annotations

lazy import zipfile
lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QPixmap, QRegion
lazy from domain.outfit_pack import OutfitPackError

Layer = tuple[QPixmap, int, int, QRegion, float]


class ActiveOutfitGarmentLayerMixin:
    """Build bounded, identity-safe paint layers from garment declarations."""

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
