"""An exact full-body garment binding clears only its verified native cloth."""
from __future__ import annotations

lazy import hashlib
lazy import json
lazy import zipfile
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest
lazy from PySide6.QtCore import QPoint, QRect
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure import active_outfit_overlay as overlay_module
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.appearance_layer_stack import AppearanceCallbacks, AppearanceLayerStack
lazy from infrastructure.source_bound_garment_visibility import (
    GarmentBinding, load_garment_binding, load_garment_removal, validate_garment_removal,
)
lazy from domain.outfit_pack import AppearanceAsset, OutfitPackError

VIEW = "yaw+090-pitch+00"
SELECTION = {"pack_id": "mohan.official.blue-white-hanfu", "item_id": "hanfu-robe", "variant_id": "blue-white"}
HAND_COUNT = 2
PARTIAL_ALPHA = 128


@pytest.fixture(scope="module", autouse=True)
def _gui_application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _case(root: Path, *, native_hands: bool = False) -> tuple[Path, object, object, Path]:
    source = root / "assets/pose-atlas/v5-base" / f"{VIEW}.png"
    source.parent.mkdir(parents=True)
    image = QImage(1024, 1536, QImage.Format_RGBA8888)
    image.fill(QColor("red"))
    assert image.save(str(source))
    mask = root / "assets/pose-atlas/v5-garment-visibility" / f"{VIEW}.png"
    mask.parent.mkdir(parents=True)
    visibility = QImage(1024, 1536, QImage.Format_Grayscale8)
    visibility.fill(255)
    visibility.setPixelColor(20, 20, QColor(0, 0, 0))
    assert visibility.save(str(mask))
    garment = root / "garment.png"
    cloth = QImage(10, 10, QImage.Format_RGBA8888)
    cloth.fill(QColor("blue"))
    assert cloth.save(str(garment))
    archive_path = root / "selected.mohan-outfit"
    member = "assets/new-garment.png"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(member, garment.read_bytes())
    declaration = AppearanceAsset(
        "outerwear", member, _digest(garment.read_bytes()), 10, 10, 15, 15, 10,
    )
    variant = SimpleNamespace(poses={VIEW: (declaration,)})
    selected = SimpleNamespace(**{f"effective_{name}": value for name, value in SELECTION.items()})
    entry = {
        "selection_exact": SELECTION,
        "native_source": {"path": f"assets/pose-atlas/v5-base/{VIEW}.png", "sha256": _digest(source.read_bytes())},
        "garment_member": {"path": member, "sha256": _digest(garment.read_bytes())},
        "visibility": {"path": f"assets/pose-atlas/v5-garment-visibility/{VIEW}.png", "sha256": _digest(mask.read_bytes())},
    }
    if native_hands:
        support = {}
        for side in ("left", "right"):
            hand_path = mask.parent / f"{VIEW}-{side}-native-hand.png"
            hand = QImage(1024, 1536, QImage.Format_RGBA8888)
            hand.fill(QColor(0, 0, 0, 0))
            if side == "left":
                hand.setPixelColor(30, 30, QColor(210, 160, 140, PARTIAL_ALPHA))
            assert hand.save(str(hand_path))
            support[side] = {
                "path": f"assets/pose-atlas/v5-garment-visibility/{hand_path.name}",
                "sha256": _digest(hand_path.read_bytes()),
            }
        entry["native_hand_support"] = support
    (mask.parent / "manifest.json").write_text(
        json.dumps({"schema": "mohan.source-bound-garment-visibility.v1", "views": {VIEW: entry}}),
        encoding="utf-8",
    )
    return mask.parent / "manifest.json", selected, variant, archive_path


def test_missing_binding_keeps_legacy_route(tmp_path: Path) -> None:
    selected = SimpleNamespace(**{f"effective_{name}": value for name, value in SELECTION.items()})
    assert load_garment_removal(tmp_path, VIEW, selected, tmp_path / "absent", object()) is None


def test_exact_selection_and_zero_visibility_remove_only_declared_pixel(tmp_path: Path) -> None:
    _manifest, selected, variant, archive = _case(tmp_path)
    removal = load_garment_removal(tmp_path, VIEW, selected, archive, variant)
    assert removal is not None
    assert removal.contains(QPoint(20, 20))
    assert not removal.contains(QPoint(21, 20))
    native_none = SimpleNamespace(**{**vars(selected), "effective_item_id": "none"})
    assert load_garment_removal(tmp_path, VIEW, native_none, archive, variant) is None


def test_rgba_visibility_uses_alpha_channel(tmp_path: Path) -> None:
    manifest, selected, variant, archive = _case(tmp_path)
    entry = json.loads(manifest.read_text(encoding="utf-8"))
    mask = tmp_path / entry["views"][VIEW]["visibility"]["path"]
    visibility = QImage(1024, 1536, QImage.Format_RGBA8888)
    visibility.fill(QColor(255, 255, 255, 255))
    visibility.setPixelColor(20, 20, QColor(255, 255, 255, 0))
    assert visibility.save(str(mask))
    entry["views"][VIEW]["visibility"]["sha256"] = _digest(mask.read_bytes())
    manifest.write_text(json.dumps(entry), encoding="utf-8")

    removal = load_garment_removal(tmp_path, VIEW, selected, archive, variant)

    assert removal is not None and removal.contains(QPoint(20, 20))


def test_empty_removal_is_not_a_valid_binding(tmp_path: Path) -> None:
    manifest, selected, variant, archive = _case(tmp_path)
    entry = json.loads(manifest.read_text(encoding="utf-8"))
    mask = tmp_path / entry["views"][VIEW]["visibility"]["path"]
    visibility = QImage(1024, 1536, QImage.Format_Grayscale8)
    visibility.fill(255)
    assert visibility.save(str(mask))
    entry["views"][VIEW]["visibility"]["sha256"] = _digest(mask.read_bytes())
    manifest.write_text(json.dumps(entry), encoding="utf-8")

    with pytest.raises(OutfitPackError, match="no native cloth"):
        load_garment_removal(tmp_path, VIEW, selected, archive, variant)


def test_native_hand_support_keeps_partial_alpha_and_empty_other_hand(tmp_path: Path) -> None:
    _manifest, selected, variant, archive = _case(tmp_path, native_hands=True)
    binding = load_garment_binding(tmp_path, VIEW, selected, archive, variant)
    assert binding is not None and binding.hand_overlays is not None
    assert binding.hand_region is not None
    assert len(binding.hand_overlays) == HAND_COUNT
    assert binding.hand_region.contains(QPoint(30, 30))
    assert not binding.hand_region.contains(QPoint(31, 30))
    assert binding.hand_overlays[0][0].toImage().pixelColor(30, 30).alpha() == PARTIAL_ALPHA
    assert binding.hand_overlays[1][3].isEmpty()


def test_hand_support_sha_drift_fails_closed(tmp_path: Path) -> None:
    manifest, selected, variant, archive = _case(tmp_path, native_hands=True)
    entry = json.loads(manifest.read_text(encoding="utf-8"))["views"][VIEW]
    (tmp_path / entry["native_hand_support"]["right"]["path"]).write_bytes(b"changed")
    with pytest.raises(OutfitPackError, match="SHA-256"):
        load_garment_binding(tmp_path, VIEW, selected, archive, variant)


def test_native_hand_support_requires_pair(tmp_path: Path) -> None:
    manifest, selected, variant, archive = _case(tmp_path, native_hands=True)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    del payload["views"][VIEW]["native_hand_support"]["right"]
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(OutfitPackError, match="left and right"):
        load_garment_binding(tmp_path, VIEW, selected, archive, variant)


@pytest.mark.parametrize("invalid", ["grayscale", "small"])
def test_native_hand_support_requires_full_canvas_rgba(
    tmp_path: Path, invalid: str,
) -> None:
    manifest, selected, variant, archive = _case(tmp_path, native_hands=True)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    record = payload["views"][VIEW]["native_hand_support"]["left"]
    hand_path = tmp_path / record["path"]
    image = (
        QImage(1024, 1536, QImage.Format_Grayscale8)
        if invalid == "grayscale" else QImage(8, 8, QImage.Format_RGBA8888)
    )
    image.fill(255)
    assert image.save(str(hand_path))
    record["sha256"] = _digest(hand_path.read_bytes())
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(OutfitPackError, match="8-bit RGBA|1024x1536"):
        load_garment_binding(tmp_path, VIEW, selected, archive, variant)


def test_other_garment_never_loads_bound_hands(tmp_path: Path) -> None:
    manifest, selected, variant, archive = _case(tmp_path, native_hands=True)
    entry = json.loads(manifest.read_text(encoding="utf-8"))["views"][VIEW]
    (tmp_path / entry["native_hand_support"]["left"]["path"]).write_bytes(b"drifted")
    different = SimpleNamespace(**{**vars(selected), "effective_item_id": "another-robe"})
    assert load_garment_binding(tmp_path, VIEW, different, archive, variant) is None


@pytest.mark.parametrize("drift", ["native", "member", "visibility"])
def test_source_drift_fails_closed(tmp_path: Path, drift: str) -> None:
    manifest, selected, variant, archive = _case(tmp_path)
    entry = json.loads(manifest.read_text(encoding="utf-8"))["views"][VIEW]
    if drift == "member":
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr(entry["garment_member"]["path"], b"changed")
    else:
        (tmp_path / entry["native_source" if drift == "native" else "visibility"]["path"]).write_bytes(b"changed")
    with pytest.raises(OutfitPackError, match="SHA-256"):
        load_garment_removal(tmp_path, VIEW, selected, archive, variant)


def test_selected_pack_declaration_must_match_binding(tmp_path: Path) -> None:
    _manifest, selected, variant, archive = _case(tmp_path)
    variant.poses[VIEW] = (SimpleNamespace(path="assets/new-garment.png", sha256="0" * 64),)
    with pytest.raises(OutfitPackError, match="member differs"):
        load_garment_removal(tmp_path, VIEW, selected, archive, variant)


@pytest.mark.parametrize("callback", [False, True])
@pytest.mark.parametrize("local_hands", [False, True])
def test_bound_clear_runs_after_body_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, callback: bool, local_hands: bool,
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    overlay = ActiveOutfitOverlay(store, tmp_path, visible_hand_region=lambda _view: QRegion())
    manifest = tmp_path / "assets/pose-atlas/v5-garment-visibility/manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("binding present", encoding="utf-8")
    garment = QPixmap(1, 1)
    garment.fill(QColor("blue"))
    layers = AppearanceLayerStack((), ((garment, 1, 1, QRegion(QRect(1, 1, 1, 1)), 1.0),))
    monkeypatch.setattr(overlay, "_refresh_state", lambda: None)
    monkeypatch.setattr(overlay, "_reviewed_frame", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(overlay, "_active_layers", lambda *_args, **_kwargs: layers)
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: True)
    monkeypatch.setattr(
        overlay, "_core_body_overlay_layers",
        lambda *_args: pytest.fail("Source-bound native body must not paint legacy body support"),
    )
    global_hand_calls: list[int] = []

    def global_hands(*_args: object) -> tuple[()]:
        global_hand_calls.append(1)
        return ()

    monkeypatch.setattr(overlay, "_core_hand_overlay_layers", global_hands)
    monkeypatch.setattr(overlay, "_selected_variant", lambda *_args: (tmp_path / "selected", None, object()))
    monkeypatch.setattr(overlay, "_protected_face_region", lambda *_args: QRegion())
    visible_hands: list[QRegion] = []
    monkeypatch.setattr(
        overlay_module, "validate_garment_removal",
        lambda _root, _view, _size, _removal, _face, provider:
        visible_hands.append(provider(VIEW)),
    )
    hand = QPixmap(6, 6)
    hand.fill(QColor(0, 0, 0, 0))
    painter = QPainter(hand)
    painter.fillRect(QRect(4, 4, 1, 1), QColor(0, 255, 0, PARTIAL_ALPHA))
    painter.end()
    hand_region = QRegion(QRect(4, 4, 1, 1))
    hand_layers = ((hand, 0, 0, hand_region, 1.0),) if local_hands else None
    monkeypatch.setattr(
        overlay_module, "load_garment_binding",
        lambda *_args: GarmentBinding(
            QRegion(QRect(3, 3, 1, 1)), hand_layers,
            hand_region if local_hands else None,
        ),
    )
    frame = QPixmap(6, 6)
    frame.fill(QColor(255, 0, 0, PARTIAL_ALPHA))
    replacements: list[int] = []

    def replace_body(_frame: QPixmap) -> QPixmap:
        replacements.append(1)
        return QPixmap(_frame)

    result = overlay._apply_phase(
        frame, VIEW, phase="appearance",
        callbacks=AppearanceCallbacks(replace_body=replace_body if callback else None),
    )

    assert len(replacements) == int(callback)
    assert len(global_hand_calls) == int(not local_hands)
    assert visible_hands[0].contains(QPoint(4, 4)) == local_hands
    assert result.toImage().pixelColor(3, 3).alpha() == 0
    assert result.toImage().pixelColor(1, 1) == QColor("blue")
    assert result.toImage().pixelColor(0, 0) == frame.toImage().pixelColor(0, 0)
    assert (result.toImage().pixelColor(4, 4).alpha() > PARTIAL_ALPHA) == local_hands


def test_bound_clear_rejects_missing_native_hair(
    tmp_path: Path,
) -> None:
    with pytest.raises(OutfitPackError, match="hair ownership"):
        validate_garment_removal(
            tmp_path, VIEW, (1024, 1536), QRegion(QRect(20, 20, 1, 1)),
            QRegion(), lambda _view: QRegion(),
        )


@pytest.mark.parametrize("point", [(1, 1), (2, 2), (3, 3)])
def test_bound_clear_preserves_face_faint_hair_and_hands(
    tmp_path: Path, point: tuple[int, int],
) -> None:
    layered = tmp_path / "assets/pose-atlas/v5-base-layered"
    layered.mkdir(parents=True)
    for name in ("hair_back", "hair_left", "hair_right", "ornament"):
        image = QImage(8, 8, QImage.Format_RGBA8888)
        image.fill(QColor(0, 0, 0, 0))
        if name == "hair_back":
            image.setPixelColor(2, 2, QColor(40, 40, 40, 1))
        assert image.save(str(layered / f"{VIEW}_{name}.png"))
    face = QRegion(QRect(1, 1, 1, 1))
    hands = lambda _view: QRegion(QRect(3, 3, 1, 1))
    with pytest.raises(OutfitPackError, match="protected native identity"):
        validate_garment_removal(
            tmp_path, VIEW, (8, 8), QRegion(QRect(*point, 1, 1)), face, hands,
        )
    validate_garment_removal(
        tmp_path, VIEW, (8, 8), QRegion(QRect(4, 4, 1, 1)), face, hands,
    )
