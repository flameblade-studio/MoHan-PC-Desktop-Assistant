"""Bindings and validation for character-owned complete frames."""
from __future__ import annotations

lazy import hashlib
lazy import io
lazy import json
lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import pytest
lazy from PIL import Image
lazy from PySide6.QtGui import QColor, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from application.appearance_ports import AppearanceRenderOptions
lazy from domain.character_runtime_bindings import load_character_runtime_bindings
lazy from domain.face_rig import EyeState
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.character_native_frames import load_native_fullbody_frames
lazy from infrastructure.complete_halfbody_expressions import (
    COMPLETE_CHEEK_POSES,
    EYES,
    FAMILIES,
    REQUIRED_COMPLETE_POSES,
    SCHEMA as COMPLETE_HALF_BODY_SCHEMA,
    CompleteHalfbodyFrames,
)
lazy from infrastructure.complete_halfbody_renderer import CompleteHalfbodyRenderer
lazy from infrastructure import complete_halfbody_renderer as complete_halfbody_renderer_module
lazy from infrastructure.layered_full_body_assets import VIEW_IDS

MOHAN_BINDINGS_PATH = ROOT / "assets" / "characters" / "mohan" / "rig" / "runtime-bindings.json"
LIN_KEYUN_BINDINGS_PATH = ROOT / "assets" / "characters" / "lin-keyun" / "rig" / "runtime-bindings.json"
MOHAN_COMPLETE_HALF_ROOT = ROOT / "assets" / "expressions" / "complete-expressions"


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    return QApplication.instance() or QApplication([])


def _rgba_png_bytes(size: tuple[int, int]) -> bytes:
    image = Image.new("RGBA", size, (35, 65, 95, 255))
    image.putpixel((0, 0), (0, 0, 0, 0))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _write_rgba_png(path: Path, size: tuple[int, int]) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _rgba_png_bytes(size)
    path.write_bytes(data)
    return data


def _runtime_asset_paths(path: Path) -> dict[str, str]:
    return dict(load_character_runtime_bindings(path).asset_paths)


def test_character_runtime_bindings_parse_native_and_shared_frame_roots() -> None:
    mohan = _runtime_asset_paths(MOHAN_BINDINGS_PATH)
    lin_keyun = _runtime_asset_paths(LIN_KEYUN_BINDINGS_PATH)

    assert mohan["fullbody_complete_root"] == "assets/pose-atlas/v5-base"
    assert mohan["fullbody_complete_layered"] == "assets/pose-atlas/v5-base-layered"
    assert mohan["halfbody_complete"] == "assets/expressions/complete-expressions"

    assert lin_keyun["fullbody_complete_root"] == "assets/characters/lin-keyun/native/full"
    assert lin_keyun["fullbody_complete_layered"] == mohan["fullbody_complete_layered"]
    assert lin_keyun["halfbody_complete"] == "assets/characters/lin-keyun/native/half"
    assert lin_keyun["halfbody_complete_supplement"] == (
        "assets/characters/lin-keyun/expressions/complete-halfbody-supplement.json"
    )


def _write_native_fullbody_set(
    root: Path,
    blink_views: frozenset[str],
    *,
    omit: tuple[str, str] | None = None,
) -> None:
    image_data = _rgba_png_bytes((1024, 1536))
    root.mkdir(parents=True, exist_ok=True)
    for view_id in VIEW_IDS:
        (root / f"{view_id}.png").write_bytes(image_data)
    for view_id in blink_views:
        for state in ("half", "closed"):
            if omit != (view_id, state):
                (root / f"{view_id}_blink_{state}.png").write_bytes(image_data)


def test_native_fullbody_loader_requires_all_views_and_only_declared_blinks(tmp_path: Path) -> None:
    blink_view_count = len(VIEW_IDS) // 2
    blink_views = frozenset(VIEW_IDS[:blink_view_count])
    _write_native_fullbody_set(tmp_path, blink_views)

    frames = load_native_fullbody_frames(tmp_path, blink_views)

    expected_frame_count = len(VIEW_IDS) + 2 * blink_view_count
    assert len(list(tmp_path.glob("*.png"))) == expected_frame_count
    assert set(frames) == set(VIEW_IDS)
    assert set(frames[VIEW_IDS[0]]) == {EyeState.REST, EyeState.HALF, EyeState.CLOSED}
    assert set(frames[VIEW_IDS[-1]]) == {EyeState.REST}
    assert frames[VIEW_IDS[0]][EyeState.REST] == (tmp_path / f"{VIEW_IDS[0]}.png").read_bytes()


def test_native_fullbody_loader_reports_a_missing_declared_eye_frame(tmp_path: Path) -> None:
    view_id = VIEW_IDS[0]
    _write_native_fullbody_set(tmp_path, frozenset({view_id}), omit=(view_id, "closed"))

    with pytest.raises(FileNotFoundError) as error:
        load_native_fullbody_frames(tmp_path, frozenset({view_id}))

    assert f"{view_id}/closed" in str(error.value)


def _halfbody_manifest(
    root: Path,
    *,
    missing_family: str | None = None,
    missing_eye: tuple[str, str] | None = None,
) -> None:
    image_data = _write_rgba_png(root / "frames" / "frame.png", (1254, 1254))
    record = {"path": "frames/frame.png", "sha256": hashlib.sha256(image_data).hexdigest()}
    pose = sorted(COMPLETE_CHEEK_POSES)[0]
    frames = {}
    for family in sorted(FAMILIES):
        if family == missing_family:
            continue
        states = dict.fromkeys(sorted(EYES), record)
        if missing_eye is not None and missing_eye[0] == family:
            states.pop(missing_eye[1])
        frames[family] = states
    document = {
        "schema": COMPLETE_HALF_BODY_SCHEMA,
        "poses": {
            pose: {
                "source_lineage": {"approval": "test-source"},
                "blink_composition": "whole-frame",
                "frames": frames,
            }
        },
        "expressions": {
            f"test-{family}": {"pose": pose, "family": family}
            for family in sorted(frames)
        },
    }
    (root / "manifest.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("missing_family", "missing_eye", "message"),
    (
        ("a", None, "requires neutral/small/a/o families"),
        (None, ("neutral", "closed"), "requires rest/half/closed"),
    ),
)
def test_native_halfbody_rejects_an_incomplete_family_or_eye_grid(
    tmp_path: Path,
    missing_family: str | None,
    missing_eye: tuple[str, str] | None,
    message: str,
) -> None:
    root = tmp_path / "native-half"
    root.mkdir()
    _halfbody_manifest(root, missing_family=missing_family, missing_eye=missing_eye)

    with pytest.raises(ValueError, match=message):
        CompleteHalfbodyRenderer(tmp_path / "legacy", complete_root=root, require_complete=True)


def test_explicit_complete_halfbody_root_fails_when_manifest_is_missing(tmp_path: Path) -> None:
    root = tmp_path / "native-half"
    root.mkdir()

    with pytest.raises(FileNotFoundError):
        CompleteHalfbodyRenderer(tmp_path / "legacy", complete_root=root, require_complete=True)


@pytest.mark.parametrize("missing", ["pose", "whole-frame-blink"])
def test_native_halfbody_eagerly_requires_all_canonical_poses_and_full_blinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    pose = sorted(REQUIRED_COMPLETE_POSES)[0]
    frames = {item: {} for item in REQUIRED_COMPLETE_POSES}
    blinks = set(REQUIRED_COMPLETE_POSES)
    if missing == "pose":
        frames.pop(pose)
        message = "Missing complete half-body poses"
    else:
        blinks.remove(pose)
        message = "Native half-body requires whole-frame blinks"
    assets = CompleteHalfbodyFrames(
        frames=frames,
        expressions={},
        oral_masks={},
        whole_frame_blinks=frozenset(blinks),
    )
    monkeypatch.setattr(
        complete_halfbody_renderer_module,
        "load_complete_halfbody_frames",
        lambda _root: assets,
    )

    with pytest.raises(ValueError, match=message):
        CompleteHalfbodyRenderer(
            tmp_path / "legacy",
            complete_root=tmp_path / "native-half",
            require_complete=True,
        )


def test_mohan_complete_halfbody_keeps_its_existing_eye_patch_blinks() -> None:
    renderer = CompleteHalfbodyRenderer(
        ROOT / "assets" / "expressions",
        complete_root=MOHAN_COMPLETE_HALF_ROOT,
        require_complete=False,
    )

    assert renderer._assets is not None
    assert "front-crossed" not in renderer._assets.whole_frame_blinks


def test_native_outfit_overlay_preserves_source_art_and_requests_makeup_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    overlay = ActiveOutfitOverlay(
        tmp_path / "state",
        tmp_path / "assets",
        visible_hand_region=None,
        native_frames=True,
    )
    requested_categories: list[frozenset[str] | None] = []

    def active_layers(
        _view_id: str,
        _canvas_size: tuple[int, int],
        *,
        categories: frozenset[str] | None = None,
        **_options: object,
    ) -> tuple[()]:
        requested_categories.append(categories)
        return ()

    def no_base_clear(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Native character artwork must preserve its authored pixels")

    monkeypatch.setattr(overlay, "_active_layers", active_layers)
    monkeypatch.setattr(overlay, "_base_clear_regions", no_base_clear)

    source = QPixmap(8, 8)
    source.fill(QColor("blue"))
    appearance = overlay.apply_appearance(QPixmap(source), "front-crossed")

    assert appearance.toImage().pixelColor(4, 4) == QColor("blue")
    assert requested_categories == []

    static = overlay.apply(QPixmap(source), "front-crossed", eye_state="half")
    animated = overlay.apply_animated(
        QPixmap(source),
        "front-crossed",
        lambda frame: frame.fill(QColor("green")),
        appearance_options=AppearanceRenderOptions(eye_state="closed"),
    )

    assert static.toImage().pixelColor(4, 4) == QColor("blue")
    assert animated.toImage().pixelColor(4, 4) == QColor("green")
    assert requested_categories == [frozenset({"makeup"}), frozenset({"makeup"})]
