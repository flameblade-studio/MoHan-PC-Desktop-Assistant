"""Construction-time source binding for explicit full-body blink candidates."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import shutil
lazy import sys
lazy from pathlib import Path
lazy from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import pytest
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication
lazy from domain.face_rig import (
    ExpressionShape,
    EyeState,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from infrastructure.layered_full_body_assets import (
    LayeredFullBodyManifest,
    LayeredFullBodyView,
)
lazy from infrastructure import layered_full_body_renderer as renderer_module
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer

VIEW_ID = "yaw+000-pitch+00"
CANVAS = (32, 32)
SOURCE_POINT = (2, 2)
EYE_POINT = (16, 16)
SOURCE_RGBA = (17, 29, 43, 255)
HALF_RGBA = (221, 47, 63, 255)
CLOSED_RGBA = (42, 83, 219, 255)
REPLACEMENT_RGBA = (233, 191, 31, 255)
RECEIPT_SCHEMA = "mohan.candidate-blink-binding.v1"


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _write_png(
    path: Path,
    color: tuple[int, int, int, int],
    point: tuple[int, int],
    *,
    size: tuple[int, int] = CANVAS,
    transparent: bool = True,
) -> None:
    image = QImage(size[0], size[1], QImage.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0 if transparent else 255))
    image.setPixelColor(*point, QColor(*color))
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path), "PNG")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pixel_rgba(pixmap: QPixmap, point: tuple[int, int]) -> tuple[int, int, int, int]:
    color = pixmap.toImage().pixelColor(*point)
    return color.red(), color.green(), color.blue(), color.alpha()


def _motion(blink: float) -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.CLOSED,
        MouthShape(),
        ExpressionShape(blink=blink),
        breath=0.5,
    )


def _fixture(tmp_path: Path) -> SimpleNamespace:
    authority_root = tmp_path / "authority"
    blink_root = tmp_path / "layers"
    source = authority_root / f"{VIEW_ID}.png"
    half = blink_root / f"{VIEW_ID}_blink_half.png"
    closed = blink_root / f"{VIEW_ID}_blink_closed.png"
    _write_png(source, SOURCE_RGBA, SOURCE_POINT)
    _write_png(half, HALF_RGBA, EYE_POINT)
    _write_png(closed, CLOSED_RGBA, EYE_POINT)
    view = LayeredFullBodyView(
        VIEW_ID,
        {},
        blink_frames={EyeState.HALF: half, EyeState.CLOSED: closed},
    )
    return SimpleNamespace(
        authority_root=authority_root,
        blink_root=blink_root,
        source=source,
        half=half,
        closed=closed,
        view=view,
        manifest=LayeredFullBodyManifest({VIEW_ID: view}),
    )


def _receipt_data(fixture: SimpleNamespace) -> dict:
    return {
        "schema": RECEIPT_SCHEMA,
        "version": 1,
        "view_id": VIEW_ID,
        "canvas": {"width": CANVAS[0], "height": CANVAS[1]},
        "source": {
            "path": str(fixture.source.resolve()),
            "sha256": _sha256(fixture.source),
        },
        "blink": {
            "half": {
                "path": str(fixture.half.resolve()),
                "sha256": _sha256(fixture.half),
            },
            "closed": {
                "path": str(fixture.closed.resolve()),
                "sha256": _sha256(fixture.closed),
            },
        },
    }


def _write_receipt(fixture: SimpleNamespace, data: dict | None = None) -> Path:
    path = fixture.authority_root / f"{VIEW_ID}.blink-binding.json"
    path.write_text(
        json.dumps(data if data is not None else _receipt_data(fixture), indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _portable_receipt_data(fixture: SimpleNamespace) -> dict:
    data = _receipt_data(fixture)
    data.update(schema="mohan.candidate-blink-binding.v2", version=2)
    for record in (data["source"], *data["blink"].values()):
        record["path"] = Path(record["path"]).relative_to(fixture.authority_root.parent).as_posix()
    return data


def test_portable_binding_survives_atlas_relocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    original = _fixture(tmp_path / "original")
    _write_receipt(original, _portable_receipt_data(original))
    relocated = tmp_path / "relocated"
    shutil.copytree(original.authority_root.parent, relocated)
    monkeypatch.chdir(relocated.parent)
    frames = {state: relocated / "layers" / path.name
              for state, path in original.view.blink_frames.items()}
    view = LayeredFullBodyView(VIEW_ID, {}, blink_frames=frames)
    renderer = LayeredFullBodyRenderer(
        LayeredFullBodyManifest({VIEW_ID: view}), authority_root=relocated / "authority",
    )
    for blink, expected in ((0.5, HALF_RGBA), (1.0, CLOSED_RGBA)):
        target = _native_eye_target()
        renderer._paint_dynamic_eye_layers(target, view, _motion(blink))
        assert _pixel_rgba(target, EYE_POINT) == expected
    authority = renderer._view_authority(view, _blank_target())
    assert _pixel_rgba(authority, SOURCE_POINT) == SOURCE_RGBA


@pytest.mark.parametrize("declared", (
    "../outside.png", "/absolute.png", "C:/machine/source.png",
    "C:source.png", "layers\\frame.png", "layers/../frame.png", "layers//frame.png",
))
def test_portable_binding_rejects_nonportable_paths(tmp_path: Path, declared: str) -> None:
    fixture = _fixture(tmp_path)
    data = _portable_receipt_data(fixture)
    data["source"]["path"] = declared
    _write_receipt(fixture, data)
    with pytest.raises(ValueError, match="portable relative path"):
        LayeredFullBodyRenderer(fixture.manifest, authority_root=fixture.authority_root)


def test_portable_binding_rejects_alternate_file_with_matching_digest(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    data = _portable_receipt_data(fixture)
    alternate = fixture.authority_root / "alternate.png"
    shutil.copyfile(fixture.source, alternate)
    data["source"]["path"] = "authority/alternate.png"
    _write_receipt(fixture, data)
    with pytest.raises(ValueError, match="path mismatch"):
        LayeredFullBodyRenderer(fixture.manifest, authority_root=fixture.authority_root)


def _blank_target() -> QPixmap:
    _app()
    target = QPixmap(*CANVAS)
    target.fill(QColor(0, 0, 0, 0))
    return target


def _native_eye_target() -> QPixmap:
    """Blink patches recolor existing skin; the native matte is authoritative."""
    image = _blank_target().toImage()
    image.setPixelColor(*EYE_POINT, QColor(*SOURCE_RGBA))
    return QPixmap.fromImage(image)


def test_explicit_authority_requires_binding_receipt(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    with pytest.raises(FileNotFoundError):
        LayeredFullBodyRenderer(fixture.manifest, authority_root=fixture.authority_root)


@pytest.mark.parametrize(
    "mutation",
    ("missing_source", "missing_half", "missing_closed", "missing_blink", "boolean_version", "wrong_schema", "wrong_half_path"),
)
def test_explicit_authority_rejects_missing_or_malformed_binding(
    tmp_path: Path,
    mutation: str,
) -> None:
    fixture = _fixture(tmp_path)
    data = _receipt_data(fixture)
    if mutation == "missing_source":
        del data["source"]
    elif mutation == "missing_half":
        del data["blink"]["half"]
    elif mutation == "missing_closed":
        del data["blink"]["closed"]
    elif mutation == "missing_blink":
        del data["blink"]
    elif mutation == "boolean_version":
        data["version"] = True
    elif mutation == "wrong_schema":
        data["schema"] = "mohan.candidate-blink-binding.v0"
    elif mutation == "wrong_half_path":
        other = tmp_path / "other-half.png"
        _write_png(other, REPLACEMENT_RGBA, EYE_POINT)
        data["blink"]["half"] = {
            "path": str(other.resolve()),
            "sha256": _sha256(other),
        }
    _write_receipt(fixture, data)

    with pytest.raises(ValueError):
        LayeredFullBodyRenderer(fixture.manifest, authority_root=fixture.authority_root)


@pytest.mark.parametrize("failure", ("wrong_source_root", "wrong_source_sha"))
def test_explicit_authority_rejects_wrong_source_root_or_sha(
    tmp_path: Path,
    failure: str,
) -> None:
    fixture = _fixture(tmp_path)
    data = _receipt_data(fixture)
    if failure == "wrong_source_root":
        other_root = tmp_path / "other-authority"
        other_source = other_root / f"{VIEW_ID}.png"
        _write_png(other_source, REPLACEMENT_RGBA, SOURCE_POINT)
        data["source"] = {
            "path": str(other_source.resolve()),
            "sha256": _sha256(other_source),
        }
    else:
        data["source"]["sha256"] = "0" * 64
    _write_receipt(fixture, data)

    with pytest.raises(ValueError):
        LayeredFullBodyRenderer(fixture.manifest, authority_root=fixture.authority_root)


def test_changed_frame_before_constructor_is_rejected(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _write_receipt(fixture)
    _write_png(fixture.half, REPLACEMENT_RGBA, EYE_POINT)

    with pytest.raises(ValueError):
        LayeredFullBodyRenderer(fixture.manifest, authority_root=fixture.authority_root)


def test_valid_binding_paints_authored_half_and_closed_frames(tmp_path: Path) -> None:
    _app()
    fixture = _fixture(tmp_path)
    _write_receipt(fixture)
    renderer = LayeredFullBodyRenderer(fixture.manifest, authority_root=fixture.authority_root)

    for blink, expected in ((0.5, HALF_RGBA), (1.0, CLOSED_RGBA)):
        target = _native_eye_target()
        renderer._paint_dynamic_eye_layers(target, fixture.view, _motion(blink))
        assert _pixel_rgba(target, EYE_POINT) == expected


def test_constructor_binds_source_and_frames_as_snapshots(tmp_path: Path) -> None:
    _app()
    fixture = _fixture(tmp_path)
    _write_receipt(fixture)
    renderer = LayeredFullBodyRenderer(fixture.manifest, authority_root=fixture.authority_root)

    _write_png(fixture.source, REPLACEMENT_RGBA, SOURCE_POINT)
    _write_png(fixture.half, REPLACEMENT_RGBA, EYE_POINT)
    _write_png(fixture.closed, REPLACEMENT_RGBA, EYE_POINT)

    authority = renderer._view_authority(fixture.view, _blank_target())
    assert _pixel_rgba(authority, SOURCE_POINT) == SOURCE_RGBA
    for blink, expected in ((0.5, HALF_RGBA), (1.0, CLOSED_RGBA)):
        target = _native_eye_target()
        renderer._paint_dynamic_eye_layers(target, fixture.view, _motion(blink))
        assert _pixel_rgba(target, EYE_POINT) == expected


def test_default_legacy_renderer_does_not_require_binding_receipt(tmp_path: Path) -> None:
    _app()
    fixture = _fixture(tmp_path)

    renderer = LayeredFullBodyRenderer(fixture.manifest)

    assert renderer._strict_authority is False
    target = _native_eye_target()
    renderer._paint_dynamic_eye_layers(target, fixture.view, _motion(0.5))
    assert _pixel_rgba(target, EYE_POINT) == HALF_RGBA


def test_lazy_manifest_binds_before_first_view_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    fixture = _fixture(tmp_path)
    _write_receipt(fixture)
    renderer = LayeredFullBodyRenderer(authority_root=fixture.authority_root)
    monkeypatch.setattr(
        renderer_module,
        "load_layered_full_body_assets",
        lambda _root: fixture.manifest,
    )

    renderer._manifest_or_load()
    _write_png(fixture.source, REPLACEMENT_RGBA, SOURCE_POINT)

    authority = renderer._view_authority(fixture.view, _blank_target())
    assert _pixel_rgba(authority, SOURCE_POINT) == SOURCE_RGBA


def test_relative_blink_paths_survive_cwd_change_after_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    fixture = _fixture(tmp_path)
    relative_view = LayeredFullBodyView(
        VIEW_ID,
        {},
        blink_frames={
            EyeState.HALF: Path("layers") / fixture.half.name,
            EyeState.CLOSED: Path("layers") / fixture.closed.name,
        },
    )
    fixture.view = relative_view
    fixture.manifest = LayeredFullBodyManifest({VIEW_ID: relative_view})
    monkeypatch.chdir(tmp_path)
    _write_receipt(fixture)
    renderer = LayeredFullBodyRenderer(
        fixture.manifest,
        authority_root=fixture.authority_root,
    )
    other_cwd = tmp_path / "other-cwd"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    target = _native_eye_target()
    renderer._paint_dynamic_eye_layers(target, fixture.view, _motion(0.5))
    assert _pixel_rgba(target, EYE_POINT) == HALF_RGBA


def test_explicit_authority_rejects_manifest_with_incomplete_pair(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    incomplete_view = LayeredFullBodyView(
        VIEW_ID,
        {},
        blink_frames={EyeState.HALF: fixture.half},
    )
    incomplete_manifest = LayeredFullBodyManifest({VIEW_ID: incomplete_view})
    _write_receipt(fixture)

    with pytest.raises(ValueError, match="Incomplete blink binding pair"):
        LayeredFullBodyRenderer(
            incomplete_manifest,
            authority_root=fixture.authority_root,
        )


def test_explicit_authority_without_authored_pair_needs_no_receipt(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    no_blink_view = LayeredFullBodyView(VIEW_ID, {})
    no_blink_manifest = LayeredFullBodyManifest({VIEW_ID: no_blink_view})

    renderer = LayeredFullBodyRenderer(
        no_blink_manifest,
        authority_root=fixture.authority_root,
    )

    assert renderer._strict_authority is True


@pytest.mark.parametrize("failure", ("source_canvas", "half_canvas", "opaque_half"))
def test_explicit_authority_rejects_invalid_bound_png_contract(
    tmp_path: Path,
    failure: str,
) -> None:
    _app()
    fixture = _fixture(tmp_path)
    if failure == "source_canvas":
        _write_png(fixture.source, REPLACEMENT_RGBA, SOURCE_POINT, size=(31, 32))
    elif failure == "half_canvas":
        _write_png(fixture.half, REPLACEMENT_RGBA, EYE_POINT, size=(31, 32))
    else:
        _write_png(fixture.half, REPLACEMENT_RGBA, EYE_POINT, transparent=False)
    _write_receipt(fixture)

    with pytest.raises(ValueError):
        LayeredFullBodyRenderer(fixture.manifest, authority_root=fixture.authority_root)


def test_bound_blink_reloads_from_snapshot_after_qpixmap_cache_eviction(
    tmp_path: Path,
) -> None:
    _app()
    fixture = _fixture(tmp_path)
    _write_receipt(fixture)
    renderer = LayeredFullBodyRenderer(fixture.manifest, authority_root=fixture.authority_root)
    assert _pixel_rgba(renderer._cached_pixmap(fixture.half), EYE_POINT) == HALF_RGBA

    for index in range(renderer_module.MAX_CACHED_LAYER_PIXMAPS + 1):
        dummy = tmp_path / f"dummy-{index}.png"
        _write_png(dummy, REPLACEMENT_RGBA, EYE_POINT)
        renderer._cached_pixmap(dummy)
    _write_png(fixture.half, REPLACEMENT_RGBA, EYE_POINT)

    assert _pixel_rgba(renderer._cached_pixmap(fixture.half), EYE_POINT) == HALF_RGBA
