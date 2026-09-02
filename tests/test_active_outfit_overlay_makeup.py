"""Makeup compositing: z-position, safe-region clip, intensity, and the half-body rect swaps."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import sys
lazy import zipfile
lazy from pathlib import Path
lazy from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import pytest
lazy from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRect, Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme
lazy from domain.outfit_pack import (
    BODY_PROFILE_ID,
    AppearanceAsset,
    AppearanceItem,
    AppearanceVariant,
    OutfitPack,
)
lazy from domain.outfit_pack_makeup import (
    SAFE_REGION_PATH,
    load_makeup_safe_regions,
    write_makeup_intensity,
)
lazy from infrastructure import active_outfit_overlay as adapter_module
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.layered_face_assets import load_layered_face_assets
lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer

CANVAS = 1254
HALF_BODY_PREVIEW = 465
BASE_GRAY = QColor(240, 240, 240, 255)
LIP_RED = QColor(255, 0, 0, 255)
CHEEK_ROSE = QColor(230, 40, 60, 255)
GARMENT_BLUE = QColor(20, 80, 180, 255)
MIDPOINT_TOLERANCE = 2
STRONG_RED = 180
WEAK_GREEN = 90
BARE_PERCENT = 0
HALF_PERCENT = 50
FULL_PERCENT = 100
CHEEK_BLOCK = 60
CHEEK_PROBE_DROP = 25
# Synthetic front-crossed safe region used by the overlay tests: the lips
# rectangle deliberately lies outside the synthetic protected-face mask so a
# garment may legitimately overlap it and prove the z-order.
FRONT_SLOTS = {
    "eyes": [[560, 220, 80, 60]],
    "cheeks": [[420, 300, 120, 80], [700, 300, 120, 80]],
    "lips": [[560, 500, 120, 60]],
}
LIPS_PIXEL = (600, 520)
EYES_PIXEL = (600, 250)
OUTSIDE_PIXEL = (600, 200)
LAYERED_DIR = ROOT / "assets" / "expressions" / "layered"
MOUTH_CLIP_FRONT = QRect(206, 199, 54, 35)
BLINK_RECTS_FRONT = (QRect(180, 153, 53, 34), QRect(220, 153, 56, 34))
EYE_PROBE = (200, 168)


def _app() -> object:
    return QApplication.instance() or QApplication([])


def _encode(image: QImage) -> bytes:
    payload = QByteArray()
    buffer = QBuffer(payload)
    assert buffer.open(QIODevice.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(payload)


def _layer(blocks: tuple[tuple[int, int, int, int, QColor], ...] = ()) -> bytes:
    image = QImage(CANVAS, CANVAS, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    for x, y, width, height, color in blocks:
        for row in range(y, y + height):
            for column in range(x, x + width):
                image.setPixelColor(column, row, color)
    return _encode(image)


def _garment(color: QColor = GARMENT_BLUE) -> bytes:
    """A 96 px garment tile with a transparent rim, like the garment fixtures elsewhere."""
    image = QImage(96, 96, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    for y in range(8, 88):
        for x in range(8, 88):
            image.setPixelColor(x, y, color)
    return _encode(image)


def _authority(root: Path) -> None:
    """Synthetic front rig: a protected face (400..800 x 100..450), one iris pixel, safe regions."""
    layered = root / "assets" / "expressions" / "layered"
    layered.mkdir(parents=True)
    face = QImage(CANVAS, CANVAS, QImage.Format_RGBA8888)
    face.fill(QColor(0, 0, 0, 0))
    for y in range(100, 451):
        for x in range(400, 801):
            face.setPixelColor(x, y, QColor(255, 255, 255, 255))
    assert face.save(str(layered / "front_base.png"), "PNG")
    iris = QImage(CANVAS, CANVAS, QImage.Format_RGBA8888)
    iris.fill(QColor(0, 0, 0, 0))
    iris.setPixelColor(*EYES_PIXEL, QColor(255, 255, 255, 255))
    assert iris.save(str(layered / "front_iris_left.png"), "PNG")
    document = json.loads(SAFE_REGION_PATH.read_text(encoding="utf-8"))
    document["silhouettes"]["front-crossed"]["slots"] = FRONT_SLOTS
    (root / "assets" / "makeup-safe-regions.json").write_text(json.dumps(document), encoding="utf-8")


def _asset(path: str, payload: bytes, slot: str, z_order: int, size: int = CANVAS, anchor=(0, 0)) -> AppearanceAsset:
    return AppearanceAsset(slot, path, hashlib.sha256(payload).hexdigest(), size, size, anchor[0], anchor[1], z_order)


def _configure(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    painted: dict[str, bytes] | None = None,
    *,
    garment: bytes | None = None,
    makeup_selected: bool = True,
    authored_intensity: float = 1.0,
) -> Path:
    """Install one synthetic pack: three makeup layers (``painted`` overrides per slot) and an optional garment."""
    store = root / "store"
    packages = store / "packages"
    packages.mkdir(parents=True, exist_ok=True)
    archive_path = packages / "pack.mohan-outfit"
    layers = {slot: (painted or {}).get(slot) or _layer() for slot in ("cheeks", "eyes", "lips")}
    with zipfile.ZipFile(archive_path, "w") as archive:
        for slot, payload in layers.items():
            archive.writestr(f"assets/{slot}.png", payload)
        if garment is not None:
            archive.writestr("assets/garment.png", garment)
    makeup_variant = AppearanceVariant(
        "classic",
        frozendict(),
        frozendict({
            "front-crossed": tuple(
                _asset(f"assets/{slot}.png", payload, slot, z_order)
                for z_order, (slot, payload) in enumerate(layers.items())
            )
        }),
        intensity=authored_intensity,
    )
    items = [AppearanceItem("makeup", "face", frozendict(), (makeup_variant,))]
    if garment is not None:
        garment_variant = AppearanceVariant(
            "navy",
            frozendict(),
            frozendict({
                "front-crossed": (_asset("assets/garment.png", garment, "outerwear", 10, 96, (LIPS_PIXEL[0] - 40, LIPS_PIXEL[1] - 40)),)
            }),
        )
        items.append(AppearanceItem("garment", "robe", frozendict(), (garment_variant,)))
    pack = OutfitPack(
        "pack", "1.0.0", ">=4.0.0,<5.0.0", frozendict(), "original", "artist", "MIT",
        BODY_PROFILE_ID, tuple(items), (),
    )

    def selection(_store: Path, category: str) -> SimpleNamespace:
        if category == "makeup" and makeup_selected:
            return SimpleNamespace(status="installed", effective_pack_id="pack", effective_item_id="face", effective_variant_id="classic")
        if category == "garment" and garment is not None:
            return SimpleNamespace(status="installed", effective_pack_id="pack", effective_item_id="robe", effective_variant_id="navy")
        return SimpleNamespace(status="builtin")

    monkeypatch.setattr(adapter_module, "resolve_active_selection", selection)
    monkeypatch.setattr(adapter_module, "inspect_outfit_pack", lambda _: pack)
    return store


def _frame() -> QPixmap:
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(BASE_GRAY)
    return frame


def _lips_block() -> bytes:
    return _layer(((LIPS_PIXEL[0] - 3, LIPS_PIXEL[1] - 3, 7, 7, LIP_RED),))


def test_makeup_paints_above_skin_and_below_garment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _app()
    _authority(tmp_path)
    store = _configure(monkeypatch, tmp_path, {"lips": _lips_block()}, garment=_garment())
    dressed = ActiveOutfitOverlay(store, tmp_path).apply(_frame(), "front-crossed").toImage()
    assert dressed.pixelColor(*LIPS_PIXEL) == GARMENT_BLUE
    store = _configure(monkeypatch, tmp_path, {"lips": _lips_block()})
    bare_body = ActiveOutfitOverlay(store, tmp_path).apply(_frame(), "front-crossed").toImage()
    assert bare_body.pixelColor(*LIPS_PIXEL) == LIP_RED
    assert bare_body.pixelColor(*OUTSIDE_PIXEL) == BASE_GRAY


def test_makeup_outside_safe_region_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _app()
    _authority(tmp_path)
    escaped = _layer(((OUTSIDE_PIXEL[0], OUTSIDE_PIXEL[1], 3, 3, LIP_RED),))
    store = _configure(monkeypatch, tmp_path, {"lips": escaped})
    frame = _frame()
    assert ActiveOutfitOverlay(store, tmp_path).apply(frame, "front-crossed").toImage() == frame.toImage()


@pytest.mark.parametrize("percent", [BARE_PERCENT, HALF_PERCENT, FULL_PERCENT])
def test_intensity_scales_makeup_alpha(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, percent: int) -> None:
    _app()
    _authority(tmp_path)
    store = _configure(monkeypatch, tmp_path, {"lips": _lips_block()})
    write_makeup_intensity(store, percent / FULL_PERCENT)
    pixel = ActiveOutfitOverlay(store, tmp_path).apply(_frame(), "front-crossed").toImage().pixelColor(*LIPS_PIXEL)
    if percent == BARE_PERCENT:
        assert pixel == BASE_GRAY
    elif percent == FULL_PERCENT:
        assert pixel == LIP_RED
    else:
        expected = tuple((BASE_GRAY.getRgb()[index] + LIP_RED.getRgb()[index]) / 2 for index in range(3))
        assert all(abs(pixel.getRgb()[index] - expected[index]) <= MIDPOINT_TOLERANCE for index in range(3))


def test_authored_variant_intensity_multiplies_the_slider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _app()
    _authority(tmp_path)
    store = _configure(monkeypatch, tmp_path, {"lips": _lips_block()}, authored_intensity=0.5)
    pixel = ActiveOutfitOverlay(store, tmp_path).apply(_frame(), "front-crossed").toImage().pixelColor(*LIPS_PIXEL)
    expected = tuple((BASE_GRAY.getRgb()[index] + LIP_RED.getRgb()[index]) / 2 for index in range(3))
    assert all(abs(pixel.getRgb()[index] - expected[index]) <= MIDPOINT_TOLERANCE for index in range(3))


def test_bare_selection_leaves_the_frame_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _app()
    _authority(tmp_path)
    store = _configure(monkeypatch, tmp_path, {"lips": _lips_block()}, makeup_selected=False)
    frame = _frame()
    assert ActiveOutfitOverlay(store, tmp_path).apply(frame, "front-crossed").toImage() == frame.toImage()


def test_visible_iris_is_excluded_from_eye_makeup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _app()
    _authority(tmp_path)
    eyes = _layer(((EYES_PIXEL[0] - 2, EYES_PIXEL[1] - 2, 5, 5, LIP_RED),))
    store = _configure(monkeypatch, tmp_path, {"eyes": eyes})
    result = ActiveOutfitOverlay(store, tmp_path).apply(_frame(), "front-crossed").toImage()
    assert result.pixelColor(*EYES_PIXEL) == BASE_GRAY
    assert result.pixelColor(EYES_PIXEL[0] - 2, EYES_PIXEL[1]) == LIP_RED


def _scaled_point(x: int, y: int) -> tuple[int, int]:
    return (x * HALF_BODY_PREVIEW // CANVAS, y * HALF_BODY_PREVIEW // CANVAS)


def _rounded_mask(rects: tuple[QRect, ...]) -> QPixmap:
    mask = QPixmap(HALF_BODY_PREVIEW, HALF_BODY_PREVIEW)
    mask.fill(Qt.transparent)
    painter = QPainter(mask)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(255, 255, 255, 255))
    for rect in rects:
        painter.drawRoundedRect(rect, 8, 8)
    painter.end()
    return mask


def _authority_pixmap(name: str) -> QPixmap:
    return QPixmap(str(ROOT / "assets" / "expressions" / f"{name}.png")).scaled(
        HALF_BODY_PREVIEW, HALF_BODY_PREVIEW, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )


def _masked(source: QPixmap, mask: QPixmap) -> QPixmap:
    patch = QPixmap(source)
    painter = QPainter(patch)
    painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    painter.drawPixmap(0, 0, mask)
    painter.end()
    return patch


def _is_rose(color: QColor) -> bool:
    return color.red() >= STRONG_RED and color.green() <= WEAK_GREEN


def _cheek_center() -> tuple[int, int]:
    x, y, width, height = load_makeup_safe_regions()["front-crossed"].rects("cheeks")[0]
    return (x + width // 2, y + height // 2)


def _cheek_layer(center: tuple[int, int]) -> bytes:
    half_block = CHEEK_BLOCK // 2
    return _layer(((center[0] - half_block, center[1] - half_block, CHEEK_BLOCK, CHEEK_BLOCK, CHEEK_ROSE),))


def _half_body_frames(renderer: LayeredParametricFaceRenderer) -> tuple[QImage, QImage]:
    """(closed-mouth idle frame, open-mouth speech frame) at the 465 px presentation size."""
    base = QPixmap(HALF_BODY_PREVIEW, HALF_BODY_PREVIEW)
    base.fill(Qt.transparent)
    closed_motion = FaceMotionFrame(FacePose.FRONT, "idle_front", Viseme.CLOSED, MouthShape(), ExpressionShape())
    open_motion = FaceMotionFrame(
        FacePose.FRONT, "speaking_front", Viseme.A, MouthShape(aperture=0.9, width=0.7), ExpressionShape()
    )
    speech_layers = SimpleNamespace(
        mouth_source=_authority_pixmap("speaking_front"),
        mouth_mask=_rounded_mask((MOUTH_CLIP_FRONT,)),
    )
    return (
        renderer.render(base, closed_motion, None).toImage(),
        renderer.render(base, open_motion, speech_layers, aperture=0.9).toImage(),
    )


def test_half_body_makeup_stays_registered_across_mouth_and_blink_swaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Makeup is composited on the 1254 canvas before the speech/blink rect swaps.

    Outside the swapped rectangles every frame keeps the identical makeup pixels;
    inside them the swap lands exactly where it lands without makeup, so the
    authority mouth/eye patches still line up.
    """
    _app()
    cheek_center = _cheek_center()
    store = _configure(monkeypatch, tmp_path, {"cheeks": _cheek_layer(cheek_center)})
    manifest = load_layered_face_assets(LAYERED_DIR)
    closed, opened = _half_body_frames(
        LayeredParametricFaceRenderer(manifest, outfit_overlay=ActiveOutfitOverlay(store, ROOT))
    )
    _plain_closed, plain_opened = _half_body_frames(LayeredParametricFaceRenderer(manifest))
    # Probe below the block centre: clear of the eye rectangles above and the mouth clip beside it.
    probe = _scaled_point(cheek_center[0], cheek_center[1] + CHEEK_PROBE_DROP)
    assert _is_rose(closed.pixelColor(*probe))
    assert opened.pixelColor(*probe) == closed.pixelColor(*probe)
    assert not _is_rose(plain_opened.pixelColor(*probe))
    mouth_probe = MOUTH_CLIP_FRONT.center()
    assert opened.pixelColor(mouth_probe) == plain_opened.pixelColor(mouth_probe)
    blink_patch = _masked(_authority_pixmap("blink_front"), _rounded_mask(BLINK_RECTS_FRONT))
    blinked = LayeredParametricFaceRenderer(manifest).render_overlay(
        QPixmap.fromImage(closed), blink_patch, opacity=1.0
    ).toImage()
    assert blinked.pixelColor(*probe) == closed.pixelColor(*probe)
    assert blinked.pixelColor(*EYE_PROBE) == blink_patch.toImage().pixelColor(*EYE_PROBE)
