"""Golden-render governance and one-pixel failure evidence."""

from __future__ import annotations

lazy import hashlib
lazy import io
lazy import json
lazy import shutil
lazy import subprocess
lazy import zipfile
lazy from dataclasses import asdict, replace
lazy from itertools import product
lazy from importlib import import_module
lazy from pathlib import Path

lazy import pytest
lazy from PIL import Image

lazy from tools.golden_render import (
    APPROVAL_SCHEMA,
    DEFAULT_CHARACTER_SETTINGS,
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


def test_default_character_settings_preserve_the_approved_matrix() -> None:
    from domain.companion_animation_contract import EXPRESSION_IMAGE_ASSETS, EXPRESSION_POSES
    from domain.constants import POSE_ATLAS_LAYERED_ROOT_NAME, POSE_ATLAS_ROOT_NAME

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    settings = DEFAULT_CHARACTER_SETTINGS
    assert settings.character_id == "flameblade.mohan"
    assert settings.manifest_schema == SCHEMA
    assert settings.approval_schema == APPROVAL_SCHEMA
    assert settings.makeups == ("none", "light", "classic", "glamorous")
    assert settings.half_size == (465, 465)
    assert settings.full_size == (1024, 1536)
    # Runtime speech assets come from a frozenset, so their order varies with
    # the interpreter hash seed. The character config fixes a stable order.
    assert len(settings.expression_assets) == len(EXPRESSION_IMAGE_ASSETS)
    assert frozenset(settings.expression_assets) == frozenset(EXPRESSION_IMAGE_ASSETS)
    assert settings.expression_pose_map() == {
        "idle": "cheek", "idle_lean": "lean", "idle_front": "front", **EXPRESSION_POSES,
    }
    assert settings.full_layered_root == f"assets/pose-atlas/{POSE_ATLAS_LAYERED_ROOT_NAME}"
    assert settings.full_authority_root == f"assets/pose-atlas/{POSE_ATLAS_ROOT_NAME}"
    assert sorted(cell.cell_id for cell in matrix_cells(settings)) == [
        cell["id"] for cell in manifest["cells"]
    ]


def test_fake_character_settings_drive_catalogs_and_asset_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from tools import golden_render

    settings = replace(
        DEFAULT_CHARACTER_SETTINGS,
        character_id="example.test-character",
        manifest_schema="example.golden-render.v1",
        makeups=("bare",),
        eye_states=("rest",),
        half_expressions=(),
        expression_poses=(),
        expression_assets=(),
        full_body_views=("profile-left",),
        full_size=(7, 9),
        official_pack_root="characters/example/appearance",
        half_expression_root="characters/example/portraits",
        half_layered_root="characters/example/half-layers",
        half_detachable_root="characters/example/detachable",
        full_layered_root="characters/example/full-layers",
        full_authority_root="characters/example/full-authority",
    )
    observed = {}

    class FakePixmap:
        def isNull(self):
            return False

        def width(self):
            return 7

        def height(self):
            return 9

    class FakeFullRenderer:
        def __init__(self, manifest, *, outfit_overlay, authority_root):
            observed["manifest"] = manifest
            observed["authority_root"] = authority_root

        def render_view(self, view_id, _motion):
            observed["view_id"] = view_id
            return FakePixmap()

    def fake_load(path):
        observed["layered_root"] = path
        return "fake-manifest"

    monkeypatch.setattr(golden_render, "_prepare_store", lambda *_args: None)
    monkeypatch.setattr(golden_render, "ActiveOutfitOverlay", lambda *_args: object())
    monkeypatch.setattr(golden_render, "load_layered_full_body_assets", fake_load)
    monkeypatch.setattr(golden_render, "LayeredFullBodyRenderer", FakeFullRenderer)
    monkeypatch.setattr(
        golden_render,
        "_save_pixmap",
        lambda _pixmap, _path: {
            "width": 7,
            "height": 9,
            "mode": "RGBA",
            "pixel_sha256": "0" * SHA256_HEX_LENGTH,
            "png_sha256": "1" * SHA256_HEX_LENGTH,
        },
    )
    asset_root = tmp_path / "fake-pack"
    rendered = render_matrix(
        tmp_path / "rendered",
        asset_root=asset_root,
        settings=settings,
    )

    assert rendered["schema"] == "example.golden-render.v1"
    assert rendered["matrix"] == {
        "full_body_cells": 1,
        "half_body_cells": 0,
        "total_cells": 1,
    }
    assert rendered["cells"][0]["id"] == "full__profile-left__bare__rest"
    assert observed == {
        "manifest": "fake-manifest",
        "authority_root": (asset_root / "characters/example/full-authority").resolve(),
        "view_id": "profile-left",
        "layered_root": (asset_root / "characters/example/full-layers").resolve(),
    }


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


def test_settings_json_roundtrip_and_cli_use_explicit_character(tmp_path, monkeypatch):
    from tools import golden_render

    settings = replace(
        DEFAULT_CHARACTER_SETTINGS,
        character_id="example.test", half_expressions=("sample",),
        expression_poses=(("sample", "front"),), expression_assets=("sample",),
        makeups=("bare",), bare_makeup="bare", eye_states=("rest",),
        full_body_views=(),
    )
    path = tmp_path / "character.json"
    path.write_text(json.dumps(asdict(settings)), encoding="utf-8")
    assert golden_render.load_character_settings(path) == settings
    observed = {}

    def capture(output, *, asset_root, settings):
        observed.update(output=output, asset_root=asset_root, settings=settings)
        return {"matrix": {"total_cells": 0}, "elapsed_seconds": 0.0, "cells": []}

    monkeypatch.setattr(golden_render, "render_matrix", capture)
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"cells": []}', encoding="utf-8")
    output = tmp_path / "output"
    root = tmp_path / "character-pack"
    assert main(("--character-settings", str(path), "--asset-root", str(root),
                 "--manifest", str(manifest), "--output", str(output))) == 0
    assert observed == {"output": output, "asset_root": root, "settings": settings}
    with pytest.raises(SystemExit) as failure:
        main(("--character-settings", str(path)))
    assert failure.value.code == ARGUMENT_ERROR_EXIT_CODE


def test_fake_half_character_reads_its_portraits_layers_and_detachable(tmp_path, monkeypatch):
    from tools import golden_render
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    settings = replace(
        DEFAULT_CHARACTER_SETTINGS, makeups=("none",), eye_states=("rest",),
        half_expressions=("sample",), expression_poses=(("sample", "front"),),
        expression_assets=("sample",), full_body_views=(), half_size=(8, 8),
        half_expression_root="sample/portraits", half_layered_root="sample/layers",
        half_detachable_root="sample/detachable", official_pack_root="sample/packs",
    )
    portraits = tmp_path / "sample/portraits"
    portraits.mkdir(parents=True)
    Image.new("RGBA", (8, 8), (23, 45, 67, OPAQUE_ALPHA)).save(portraits / "sample.png")
    observed = {}

    class HalfRenderer:
        def __init__(self, *, manifest, outfit_overlay, authority_dir, detachable_dir):
            observed.update(manifest=manifest, authority=authority_dir, detachable=detachable_dir)

        def render(self, base, motion, _unused):
            observed["expression"] = motion.expression
            return base

    def load(path):
        observed["layers"] = path
        return "sample-manifest"

    def harness(root, renderer, configuration):
        portrait = golden_render._scaled_expression(root, "sample", configuration)
        observed["portrait_size"] = (portrait.width(), portrait.height())
        return object()

    monkeypatch.setattr(golden_render, "load_layered_face_assets", load)
    monkeypatch.setattr(golden_render, "LayeredParametricFaceRenderer", HalfRenderer)
    monkeypatch.setattr(golden_render, "_BlinkHarness", harness)
    monkeypatch.setattr(golden_render, "_prepare_store", lambda *_args: None)
    monkeypatch.setattr(golden_render, "ActiveOutfitOverlay", lambda *_args: object())
    assert isinstance(golden_render._scaled_expression(tmp_path, "sample", settings), QPixmap)
    result = render_matrix(tmp_path / "render", asset_root=tmp_path, settings=settings)
    assert result["matrix"]["total_cells"] == 1
    assert observed == {
        "manifest": "sample-manifest", "authority": portraits.resolve(),
        "detachable": (tmp_path / "sample/detachable").resolve(),
        "layers": (tmp_path / "sample/layers").resolve(), "expression": "sample",
        "portrait_size": settings.half_size,
    }


@pytest.mark.parametrize("changes", [
    {"half_expression_root": "../escape"}, {"half_expression_root": "C:relative"},
    {"makeups": ("../escape",)}, {"half_size": (True, 10)},
    {"half_size": (10,)}, {"expression_poses": ()},
])
def test_character_settings_reject_unsafe_or_incomplete_input(changes):
    with pytest.raises(ValueError):
        replace(DEFAULT_CHARACTER_SETTINGS, **changes)


def test_custom_baseline_pins_settings_and_uses_separate_cache(tmp_path, monkeypatch):
    from tools import golden_render

    settings = replace(DEFAULT_CHARACTER_SETTINGS, character_id="example.test")
    config = tmp_path / "settings.json"
    config.write_text(json.dumps(asdict(settings)), encoding="utf-8")
    approval = tmp_path / "approval.json"
    approval.write_text(json.dumps({
        "schema": settings.approval_schema, "owner": "example owner",
        "date": "2026-10-06", "quote": "approved", "cells": "*",
    }), encoding="utf-8")
    output = tmp_path / "rendered"
    output.mkdir()
    (output / "sample.png").write_bytes(b"example pixels")
    cell = {"id": "sample", "file": "sample.png", "png_sha256": "unused"}
    rendered = {"cells": [cell], "matrix": {"total_cells": 1}, "elapsed_seconds": 0.0}
    monkeypatch.setattr(golden_render, "ROOT", tmp_path)
    monkeypatch.setattr(golden_render, "_require_committed_render_sources", lambda _settings: None)
    monkeypatch.setattr(import_module("subprocess"), "check_output", lambda *_args, **_kwargs: "a" * GIT_REVISION_LENGTH)
    monkeypatch.setattr(golden_render, "render_matrix", lambda *_args, **_kwargs: rendered)
    manifest = tmp_path / "manifest.json"
    assert main(("--character-settings", str(config), "--asset-root", str(tmp_path),
                 "--manifest", str(manifest), "--output", str(output),
                 "--update", "--approval", str(approval))) == 0
    pinned = json.loads(manifest.read_text(encoding="utf-8"))
    assert golden_render.load_character_settings(config) == settings
    assert pinned["character_settings"] == json.loads(config.read_text(encoding="utf-8"))
    assert (output / "baseline/sample.png").read_bytes() == b"example pixels"


def test_update_rejects_unreconstructable_external_asset_root(tmp_path):
    with pytest.raises(SystemExit) as failure:
        main(("--update", "--approval", str(tmp_path / "approval.json"),
              "--asset-root", str(tmp_path)))
    assert failure.value.code == ARGUMENT_ERROR_EXIT_CODE


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
    # Copies support pytest temporary roots on another volume and keep any
    # fixture mutation isolated from the approved production assets.
    shutil.copytree(ROOT / "assets", target_root / "assets")


@pytest.fixture
def mutable_asset_root(tmp_path):
    asset_root = tmp_path / "mutable-assets"
    _clone_assets_for_mutation(asset_root)
    return asset_root


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
        for y, x in product(range(image.height), range(image.width))
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
    diff = tmp_path / "diff"
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
