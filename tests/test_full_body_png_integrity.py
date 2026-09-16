"""Regression tests for structural PNG checks and deferred layer decoding."""

from __future__ import annotations

lazy import struct
lazy import zlib
lazy import re
lazy from pathlib import Path

lazy import pytest
lazy from PySide6.QtGui import QImage
lazy from PySide6.QtWidgets import QApplication

lazy from domain.constants import FULL_BODY_LAYER_Z_ORDER
lazy from infrastructure import layered_full_body_assets as assets
lazy from infrastructure.layered_full_body_assets import (
    FULL_BODY_DIMENSION_HEIGHT,
    FULL_BODY_DIMENSION_WIDTH,
    LayeredFullBodyManifest,
    LayeredFullBodyView,
    load_layered_full_body_assets,
)
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer

VIEW_ID = "yaw+000-pitch+00"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"
PNG_HEADER_LENGTH = 24


def _png_chunk(
    chunk_type: bytes,
    payload: bytes,
    *,
    crc_override: int | None = None,
) -> bytes:
    crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    if crc_override is not None:
        crc = crc_override
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", crc)
    )


def _structural_png(
    *,
    bit_depth: int = 8,
    color_type: int = 6,
    idat: bytes | None = None,
    bad_ihdr_crc: bool = False,
) -> bytes:
    ihdr_payload = struct.pack(
        ">IIBBBBB",
        FULL_BODY_DIMENSION_WIDTH,
        FULL_BODY_DIMENSION_HEIGHT,
        bit_depth,
        color_type,
        0,
        0,
        0,
    )
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_payload) & 0xFFFFFFFF
    if bad_ihdr_crc:
        ihdr_crc ^= 1
    chunks = [_png_chunk(b"IHDR", ihdr_payload, crc_override=ihdr_crc)]
    if idat is not None:
        chunks.append(_png_chunk(b"IDAT", idat))
    chunks.append(PNG_IEND)
    return PNG_SIGNATURE + b"".join(chunks)


def _write_inventory(root: Path, payload: bytes) -> None:
    for layer in FULL_BODY_LAYER_Z_ORDER:
        (root / f"{VIEW_ID}_{layer}.png").write_bytes(payload)


def _load_one_view(root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(assets, "VIEW_IDS", (VIEW_ID,))
    return load_layered_full_body_assets(root)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _write_transparent_rgba(path: Path) -> None:
    image = QImage(
        FULL_BODY_DIMENSION_WIDTH,
        FULL_BODY_DIMENSION_HEIGHT,
        QImage.Format_RGBA8888,
    )
    image.fill(0)
    assert image.save(str(path), "PNG")


@pytest.mark.parametrize(
    "payload",
    (
        pytest.param(_structural_png()[:PNG_HEADER_LENGTH], id="truncated-24-bytes"),
        pytest.param(_structural_png(color_type=2), id="rgb-8-bit"),
        pytest.param(_structural_png(bit_depth=16), id="rgba-16-bit"),
        pytest.param(_structural_png(bad_ihdr_crc=True), id="bad-ihdr-crc"),
    ),
)
def test_loader_rejects_non_rgba_or_incomplete_png_headers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
) -> None:
    _write_inventory(tmp_path, _structural_png())
    (tmp_path / f"{VIEW_ID}_base.png").write_bytes(payload)

    with pytest.raises(ValueError, match="(invalid|8-bit RGBA)"):
        _load_one_view(tmp_path, monkeypatch)


def test_loader_accepts_transparent_rgba_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "transparent-rgba.png"
    _write_transparent_rgba(source)
    payload = source.read_bytes()
    assert payload[:8] == PNG_SIGNATURE
    assert payload[24:26] == b"\x08\x06"
    _write_inventory(tmp_path, payload)

    manifest = _load_one_view(tmp_path, monkeypatch)

    assert set(manifest.view(VIEW_ID).layers) == set(FULL_BODY_LAYER_Z_ORDER)


def test_structural_loader_defers_bad_idat_to_renderer_decode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_inventory(tmp_path, _structural_png(idat=b"not-zlib-data"))

    manifest = _load_one_view(tmp_path, monkeypatch)
    bad_path = manifest.view(VIEW_ID).path("base")
    assert bad_path is not None

    _app()
    renderer = LayeredFullBodyRenderer(manifest)
    with pytest.raises(ValueError, match="Cannot decode full-body layer PNG"):
        renderer._cached_pixmap(bad_path)


def test_optional_missing_layer_stays_a_null_pixmap(tmp_path: Path) -> None:
    _app()
    body_path = tmp_path / "body.png"
    image = QImage(4, 4, QImage.Format_RGBA8888)
    image.fill(0)
    assert image.save(str(body_path), "PNG")
    view = LayeredFullBodyView(VIEW_ID, {"body": body_path})
    renderer = LayeredFullBodyRenderer(LayeredFullBodyManifest({VIEW_ID: view}))

    assert view.path("base") is None
    assert renderer._cached_pixmap(view.path("base")).isNull()


def test_loader_reports_deleted_required_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_inventory(tmp_path, _structural_png())
    missing_path = tmp_path / f"{VIEW_ID}_body.png"
    missing_path.unlink()

    with pytest.raises(FileNotFoundError, match=re.escape(missing_path.name)):
        _load_one_view(tmp_path, monkeypatch)
