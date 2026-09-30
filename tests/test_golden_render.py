"""Golden-render governance and one-pixel failure evidence."""

from __future__ import annotations

lazy import hashlib
lazy import io
lazy import json
lazy import os
lazy import shutil
lazy import subprocess
lazy import uuid
lazy import zipfile
lazy from pathlib import Path

lazy import pytest
lazy from PIL import Image

lazy from tools.golden_render import (
    APPROVAL_SCHEMA,
    MANIFEST_PATH,
    GIT_REVISION_LENGTH,
    ROOT,
    SCHEMA,
    compare_manifest,
    matrix_cells,
    render_matrix,
    pixel_sha256,
    main,
    validate_approval,
)
lazy from PySide6.QtGui import QImage

SHA256_HEX_LENGTH = 64
OPAQUE_ALPHA = 255
CHANNEL_MIDPOINT = 128
ARGUMENT_ERROR_EXIT_CODE = 2


def test_manifest_covers_the_complete_matrix() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    cells = matrix_cells()
    assert manifest["schema"] == SCHEMA
    assert manifest["pixel_tolerance"] == 0
    assert manifest["matrix"] == {
        "full_body_cells": 52,
        "half_body_cells": 300,
        "total_cells": 352,
    }
    assert [cell["id"] for cell in manifest["cells"]] == sorted(cell.cell_id for cell in cells)
    assert all(
        len(cell["pixel_sha256"]) == SHA256_HEX_LENGTH
        for cell in manifest["cells"]
    )
    assert all("png_sha256" not in cell for cell in manifest["cells"])
    assert len(manifest["source_revision"]) == GIT_REVISION_LENGTH
    approval = ROOT / manifest["approval"]["path"]
    assert hashlib.sha256(approval.read_bytes()).hexdigest() == manifest["approval"]["sha256"]
    validate_approval(approval, frozenset(cell.cell_id for cell in cells))
    source = manifest["harness"]["source"].encode("utf-8")
    assert hashlib.sha256(source).hexdigest() == manifest["harness"]["sha256"]


def test_update_requires_an_exact_owner_approval(tmp_path: Path) -> None:
    cell_ids = frozenset(cell.cell_id for cell in matrix_cells())
    approval = tmp_path / "approval.json"
    approval.write_text(json.dumps({
        "schema": APPROVAL_SCHEMA,
        "owner": "owner",
        "date": "2026-09-30",
        "quote": "approved",
        "cells": [next(iter(cell_ids))],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="核准涵蓋不完整"):
        validate_approval(approval, cell_ids)
    approval.write_text(json.dumps({
        "schema": APPROVAL_SCHEMA,
        "owner": "owner",
        "date": "2026-09-30",
        "quote": "approved",
        "cells": "*",
    }), encoding="utf-8")
    assert validate_approval(approval, cell_ids)["owner"] == "owner"


def test_update_without_approval_exits_before_rendering(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("existing baseline", encoding="utf-8")
    with pytest.raises(SystemExit) as failure:
        main(("--update", "--manifest", str(manifest)))
    assert failure.value.code == ARGUMENT_ERROR_EXIT_CODE
    assert manifest.read_text(encoding="utf-8") == "existing baseline"


def test_png_encoding_differences_keep_exact_rgba_contract(tmp_path: Path) -> None:
    original = tmp_path / "original.png"
    reencoded = tmp_path / "reencoded.png"
    image = Image.new("RGBA", (8, 8), (23, 45, 67, OPAQUE_ALPHA))
    image.save(original, compress_level=0)
    image.save(reencoded, compress_level=9)
    assert original.read_bytes() != reencoded.read_bytes()
    assert pixel_sha256(QImage(str(original))) == pixel_sha256(QImage(str(reencoded)))


def test_alpha_only_change_is_visible_in_diff(tmp_path: Path) -> None:
    from tools.golden_render import _write_diff

    original = tmp_path / "original.png"
    new = tmp_path / "new.png"
    Image.new("RGBA", (8, 8), (23, 45, 67, OPAQUE_ALPHA)).save(original)
    Image.new("RGBA", (8, 8), (23, 45, 67, OPAQUE_ALPHA - 1)).save(new)
    _write_diff(original, new, tmp_path / "diff")
    assert Image.open(tmp_path / "diff" / "difference.png").getbbox() is not None


def test_capture_resets_existing_makeup_intensities(tmp_path: Path) -> None:
    from domain.outfit_pack_makeup import (
        DEFAULT_MAKEUP_INTENSITY,
        DEFAULT_SLOT_INTENSITIES_V2,
        read_makeup_intensity,
        read_makeup_slot_intensities,
        write_makeup_intensity,
        write_makeup_slot_intensity,
    )
    from tools.golden_render import _prepare_store

    write_makeup_intensity(tmp_path, 0.2)
    for slot in DEFAULT_SLOT_INTENSITIES_V2:
        write_makeup_slot_intensity(tmp_path, slot, 0.3)
    _prepare_store(tmp_path, "none")
    assert read_makeup_intensity(tmp_path) == DEFAULT_MAKEUP_INTENSITY
    assert read_makeup_slot_intensities(
        tmp_path, slots=frozenset(DEFAULT_SLOT_INTENSITIES_V2),
    ) == DEFAULT_SLOT_INTENSITIES_V2


def _clone_assets_for_mutation(target_root: Path) -> None:
    def clone(source: str, target: str) -> str:
        if source.endswith("mohan.makeup.builtin.mohan-outfit"):
            return shutil.copy2(source, target)
        os.link(source, target)
        return target

    shutil.copytree(ROOT / "assets", target_root / "assets", copy_function=clone)


@pytest.fixture
def mutable_asset_root():
    temporary_parent = (ROOT / ".quality-tmp" / "golden-mutation-tests").resolve()
    asset_root = (temporary_parent / uuid.uuid4().hex).resolve()
    assert asset_root.is_relative_to(temporary_parent)
    temporary_parent.mkdir(parents=True, exist_ok=True)
    _clone_assets_for_mutation(asset_root)
    try:
        yield asset_root
    finally:
        assert asset_root.is_relative_to(temporary_parent)
        shutil.rmtree(asset_root)


def _replace_hash(value: object, member: str, digest: str) -> None:
    if isinstance(value, dict):
        if value.get("path") == member and "sha256" in value:
            value["sha256"] = digest
        for child in value.values():
            _replace_hash(child, member, digest)
    elif isinstance(value, list):
        for child in value:
            _replace_hash(child, member, digest)


def _mutate_one_makeup_pixel(archive_path: Path) -> None:
    member = "assets/classic-rest-yaw+000-pitch+00-lips.png"
    with zipfile.ZipFile(archive_path, "r") as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    image = Image.open(io.BytesIO(members[member])).convert("RGBA")
    opaque = [
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if image.getpixel((x, y))[3] == OPAQUE_ALPHA
    ]
    point = opaque[len(opaque) // 2]
    red, green, blue, alpha = image.getpixel(point)
    image.putpixel(
        point,
        (
            OPAQUE_ALPHA if red < CHANNEL_MIDPOINT else 0,
            OPAQUE_ALPHA if green < CHANNEL_MIDPOINT else 0,
            OPAQUE_ALPHA if blue < CHANNEL_MIDPOINT else 0,
            alpha,
        ),
    )
    encoded = io.BytesIO()
    image.save(encoded, "PNG")
    members[member] = encoded.getvalue()
    manifest = json.loads(members["manifest.json"].decode("utf-8"))
    _replace_hash(manifest, member, hashlib.sha256(members[member]).hexdigest())
    members["manifest.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)


def test_one_makeup_pixel_change_fails_and_writes_three_diff_images(
    tmp_path: Path,
    mutable_asset_root: Path,
) -> None:
    asset_root = mutable_asset_root
    cell = next(
        cell for cell in matrix_cells()
        if cell.cell_id == "full__yaw+000-pitch+00__classic__rest"
    )
    original_output = tmp_path / "original"
    expected = render_matrix(original_output, asset_root=asset_root, cells=(cell,))
    expected["source_revision"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
    ).strip()
    harness_source = (ROOT / "tools" / "golden_render.py").read_bytes()
    expected["harness"] = {
        "source": harness_source.decode("utf-8"),
        "sha256": hashlib.sha256(harness_source).hexdigest(),
    }
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    # A clean CI runner has no approved PNG cache: reconstruct the original
    # from its Git revision while still detecting a mutation of the copied pack.

    archive = asset_root / "assets" / "official-packs" / "mohan.makeup.builtin.mohan-outfit"
    _mutate_one_makeup_pixel(archive)
    changed_output = tmp_path / "changed"
    actual = render_matrix(changed_output, asset_root=asset_root, cells=(cell,))
    diff = ROOT / ".quality-tmp" / "golden-diff" / "mutation-proof" / asset_root.name
    changed = compare_manifest(
        actual,
        expected,
        output=changed_output,
        baseline_dir=baseline,
        diff_dir=diff,
    )
    assert changed == [cell.cell_id]
    assert {path.name for path in (diff / cell.cell_id).iterdir()} == {
        "original.png", "new.png", "difference.png",
    }
    assert Image.open(diff / cell.cell_id / "difference.png").getbbox() is not None
