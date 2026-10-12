"""Protect the body-owned face core with continuous alpha weights."""
from __future__ import annotations

lazy from collections import OrderedDict
lazy from collections.abc import Callable
lazy import re
lazy from PIL import Image as PILImage

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QBitmap, QImage, QPainter, QPixmap, QRegion

lazy from domain.character_layer_plan import (
    CharacterLayerAsset,
    CharacterLayerMask,
    CharacterLayerPlan,
)

LayerRecord = CharacterLayerAsset | CharacterLayerMask
ImageLoader = Callable[[LayerRecord], QPixmap]
__all__ = ["body_pack_alpha_region", "compose_body_pack_frame"]

MAX_ALPHA_REGION_CACHE_BYTES = 8 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ALPHA_REGIONS: OrderedDict[str, tuple[QRegion, int]] = OrderedDict()
_alpha_region_cache_bytes = 0


def compose_body_pack_frame(
    base: QPixmap,
    plan: CharacterLayerPlan | None,
    load_image: ImageLoader,
    face_core: QPixmap | None = None,
    *, makeup_base: QPixmap | None = None,
) -> QPixmap:
    """Blend the protected body and declared character stack on the GUI thread.

    A missing plan returns a copy without calling the loader.
    臉部核心以 alpha 權重保護：X 依 H 非零 alpha 清除 B，再按宣告順序
    （含 base）以 SourceOver 疊所有非 makeup 角色層，完全不考慮 F。
    B′ 是 B 加 makeup SourceAtop；R＝B′·F_α＋X·(1−F_α)。
    預乘 RGBA 逐像素線性插值，makeup 僅在 B′，hair-back 沒有例外。
    脸部核心以 alpha 权重保护：X 按 H 非零 alpha 清除 B，再按声明顺序
    （含 base）以 SourceOver 叠所有非 makeup 角色层，完全不考虑 F。
    B′ 是 B 加 makeup SourceAtop；R＝B′·F_α＋X·(1−F_α)。
    预乘 RGBA 逐像素线性插值，makeup 仅在 B′，hair-back 没有例外。
    Face-core alpha protects the body. X clears B wherever H has nonzero
    alpha, then draws non-makeup character stages in declared order (including
    base) with SourceOver, without considering F. B′ paints makeup SourceAtop
    onto original B. R = B′*F_alpha + X*(1-F_alpha) linearly interpolates
    premultiplied RGBA per pixel. Makeup appears only in B′; hair-back has
    no exception. Transparent F yields X; opaque F always yields B′.
    顔核心を Alpha の重みで保護します。X は H の非ゼロ Alpha で B を
    消去し、base を含む宣言順でメイク以外を SourceOver で重ねます。
    B′ は元の B にメイクを SourceAtop で重ねた結果です。
    R＝B′·F_α＋X·(1−F_α) を乗算済み RGBA で画素ごとに線形補間します。
    メイクは B′ だけに現れ、hair-back に例外はありません。
    素體包獨佔 F_body；L 與 H 保留原始 alpha，僅在最終插值套用 F。
    素体包独占 F_body；L 与 H 保留原始 alpha，仅在最终插值应用 F。
    The body pack alone defines F_body; L and H retain native alpha and
    face protection is applied once, at the final interpolation.
    素体パックだけが F_body を定義し、L と H は元の Alpha を保持し、
    顔保護は最終補間で一度適用します。
    """
    if plan is None and (
        makeup_base is None or face_core is None or makeup_base.cacheKey() == base.cacheKey()
    ):
        return QPixmap(base)
    plan = plan or CharacterLayerPlan(("base",), ())
    if base.isNull():
        raise ValueError("Body-pack composition requires a valid base frame.")

    if face_core is not None:
        if not isinstance(face_core, QPixmap):
            raise TypeError("Face-core weights require a QPixmap.")
        if face_core.isNull() or face_core.size() != base.size():
            raise ValueError("Face-core weights must match the decoded base canvas.")
        if not face_core.hasAlphaChannel():
            raise ValueError("Face-core weights require an alpha channel.")

    cleared_base = QPixmap(base)
    if plan.base_hide is not None:
        mask = _load_canvas_image(load_image, plan.base_hide, base, alpha_required=True)
        erase = QPixmap(base.size())
        erase.fill(Qt.transparent)
        painter = QPainter(erase)
        try:
            painter.setClipRegion(body_pack_alpha_region(mask, plan.base_hide.sha256))
            painter.fillRect(erase.rect(), Qt.white)
        finally:
            painter.end()
        cleared_base = _weight_image(base, erase, inside=False)

    layers_by_kind: dict[str, list[QPixmap]] = {}
    for record in plan.layers:
        image = _load_canvas_image(load_image, record, base, alpha_required=False)
        layers_by_kind.setdefault(record.kind, []).append(image)

    character = QPixmap(base.size())
    character.fill(Qt.transparent)
    protected_body = QPixmap(base if makeup_base is None else makeup_base)
    if protected_body.isNull() or protected_body.size() != base.size():
        raise ValueError("Makeup body must match the decoded base canvas.")
    character_painter = QPainter(character)
    body_painter = QPainter(protected_body)
    try:
        body_painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
        for stage in plan.order:
            if stage == "base":
                character_painter.drawPixmap(0, 0, cleared_base)
                continue
            painter = body_painter if stage == "makeup" else character_painter
            for image in layers_by_kind.get(stage, ()):
                painter.drawPixmap(0, 0, image)
    finally:
        character_painter.end()
        body_painter.end()

    result = _weight_image(character, face_core, inside=False)
    protected_body = _weight_image(protected_body, face_core, inside=True)
    painter = QPainter(result)
    try:
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        painter.drawPixmap(0, 0, protected_body)
    finally:
        painter.end()
    return result


def _weight_image(image: QPixmap, mask: QPixmap | None, *, inside: bool) -> QPixmap:
    """Multiply an isolated layer by mask alpha or its complement."""
    buffer = QPixmap(image.size())
    buffer.fill(Qt.transparent)
    painter = QPainter(buffer)
    try:
        if mask is None and inside:
            return buffer
        painter.drawPixmap(0, 0, image)
        if mask is not None:
            painter.setCompositionMode(
                QPainter.CompositionMode_DestinationIn
                if inside else QPainter.CompositionMode_DestinationOut
            )
            painter.drawPixmap(0, 0, mask)
    finally:
        painter.end()
    return buffer


def _load_canvas_image(
    load_image: ImageLoader,
    record: LayerRecord,
    base: QPixmap,
    *,
    alpha_required: bool,
) -> QPixmap:
    image = load_image(record)
    if not isinstance(image, QPixmap):
        raise TypeError(f"Image loader must return QPixmap for {record.path!r}.")
    if image.isNull():
        raise ValueError(f"Character asset {record.path!r} could not be decoded.")
    if image.size() != base.size():
        raise ValueError(f"Character asset {record.path!r} must match the base canvas size.")
    if record.anchor != (0, 0):
        raise ValueError(f"Character asset {record.path!r} must use anchor [0, 0].")
    if alpha_required and not image.hasAlphaChannel():
        raise ValueError(f"Base hide mask {record.path!r} must contain alpha.")
    return image


def body_pack_alpha_region(mask: QPixmap, digest: str | None = None) -> QRegion:
    """Return nonzero-alpha pixels using Qt masks; call on the GUI thread.

    A supplied SHA-256 identifies immutable package bytes and shares the
    bounded alpha-region cache across decoded pixmaps. In-memory callers use
    the pixmap cache key. Alpha values 1–127 remain included.
    """
    if not isinstance(mask, QPixmap):
        raise TypeError("Alpha regions require a QPixmap.")
    if mask.isNull():
        raise ValueError("Alpha regions require a decoded image.")
    if not mask.hasAlphaChannel():
        raise ValueError("Alpha regions require an alpha channel.")

    global _alpha_region_cache_bytes
    if digest is not None and not _SHA256.fullmatch(digest):
        raise ValueError("Alpha-region cache digest must be a lowercase SHA-256.")
    cache_key = f"sha256:{digest}" if digest is not None else f"pixmap:{mask.cacheKey()}"
    cached = _ALPHA_REGIONS.get(cache_key)
    if cached is not None:
        _ALPHA_REGIONS.move_to_end(cache_key)
        return QRegion(cached[0])

    image = mask.toImage().convertToFormat(QImage.Format_RGBA8888)
    pixels = bytes(image.constBits()[:image.sizeInBytes()])
    alpha = PILImage.frombytes("RGBA", (image.width(), image.height()), pixels).getchannel("A")
    binary_alpha = alpha.point(lambda value: 255 if value else 0).tobytes()
    binary_pixels = bytearray(image.width() * image.height() * 4)
    binary_pixels[3::4] = binary_alpha
    binary_image = QImage(
        binary_pixels, image.width(), image.height(), image.width() * 4, QImage.Format_RGBA8888,
    ).copy()
    alpha_mask = binary_image.createAlphaMask()
    region = QRegion(QBitmap.fromImage(alpha_mask))
    weight = max(128, region.rectCount() * 64)
    if weight <= MAX_ALPHA_REGION_CACHE_BYTES:
        previous = _ALPHA_REGIONS.pop(cache_key, None)
        if previous is not None:
            _alpha_region_cache_bytes -= previous[1]
        _ALPHA_REGIONS[cache_key] = (QRegion(region), weight)
        _alpha_region_cache_bytes += weight
        while _alpha_region_cache_bytes > MAX_ALPHA_REGION_CACHE_BYTES:
            _, (_, removed_weight) = _ALPHA_REGIONS.popitem(last=False)
            _alpha_region_cache_bytes -= removed_weight
    return region
