"""Contract tests for the owner-approved four-look makeup pack builder."""

from __future__ import annotations

import copy
import json
import shutil
import zipfile
from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage

from domain.outfit_pack import MAKEUP_CANVASES, REQUIRED_SILHOUETTES
from domain.outfit_pack_makeup import FoundationSafeMask, MakeupSafeRegion
from tools.art_pipeline.four_look_makeup_pack import (
    FourLookStageError,
    LOOKS,
    SLOTS,
    STATES,
    _validate_views,
    digest,
    prepare_four_look_pack,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RELATIVE = "assets/official-packs/mohan.makeup.builtin.mohan-outfit"
APPROVAL_SOURCE = ROOT / "scratchpad/halfbody-makeup-consistency-20260913-01/four-look-v4-standard-01/approved-installation-06/owner-approval.json"
APPROVAL_RELATIVE = "scratchpad/approval/owner-approval.json"
EXPECTED_STAGE_RECORDS = 3 * 31 * 4 * 3
EXPECTED_OUTPUT_DECLARATIONS = 744
EXPECTED_ARCHIVE_MEMBERS = EXPECTED_OUTPUT_DECLARATIONS + 1
EXPECTED_SOURCE_PINS = 2


def _write_png(path: Path, size: tuple[int, int], *, visible: bool = False) -> bytes:
    image = QImage(size[0], size[1], QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    if visible:
        image.setPixelColor(0, 0, QColor(220, 30, 40, 255))
    assert image.save(str(path), "PNG")
    return path.read_bytes()


def _copy_pins(root: Path) -> dict[str, dict[str, str]]:
    source = root / SOURCE_RELATIVE
    source.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / SOURCE_RELATIVE, source)
    approval = root / APPROVAL_RELATIVE
    approval.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(APPROVAL_SOURCE, approval)
    return {
        "source_pack": {"path": SOURCE_RELATIVE, "sha256": digest(source.read_bytes())},
        "approval": {"path": APPROVAL_RELATIVE, "sha256": digest(approval.read_bytes())},
    }


def _stage(root: Path) -> Path:
    pins = _copy_pins(root)
    layers = root / "scratchpad/stage"
    layers.mkdir(parents=True, exist_ok=True)
    files = {
        "half": layers / "blank-half.rgba.png",
        "full": layers / "blank-full.rgba.png",
    }
    records = {}
    for kind, path in files.items():
        size = MAKEUP_CANVASES["half-body" if kind == "half" else "full-body"]
        payload = _write_png(path, size)
        relative = path.relative_to(root).as_posix()
        records[kind] = {"path": relative, "sha256": digest(payload), "nonvisible": True}
    views = {}
    for silhouette in REQUIRED_SILHOUETTES:
        kind = "full" if silhouette.startswith("yaw") else "half"
        state_layers = {
            state: {slot: copy.deepcopy(records[kind]) for slot in SLOTS}
            for state in STATES
        }
        views[silhouette] = {
            "variants": {
                look: {"states": copy.deepcopy(state_layers)} for look in LOOKS
            },
        }
    stage = {
        "schema": "mohan.four-look-makeup-stage.v1",
        **pins,
        "views": views,
    }
    path = root / "scratchpad/stage.json"
    path.write_text(json.dumps(stage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _regions() -> dict[str, MakeupSafeRegion]:
    regions = {}
    for silhouette in REQUIRED_SILHOUETTES:
        canvas = MAKEUP_CANVASES["full-body" if silhouette.startswith("yaw") else "half-body"]
        alpha = bytes(canvas[0] * canvas[1])
        masks = {
            state: FoundationSafeMask(
                f"assets/test-{silhouette}-{state}.png",
                "0" * 64,
                canvas,
                (0, 0),
                alpha,
            )
            for state in STATES
        }
        regions[silhouette] = MakeupSafeRegion(
            silhouette,
            canvas,
            "test",
            {slot: () for slot in ("eyes", "cheeks", "lips")},
            masks,
            masks,
        )
    return regions


def test_builds_three_looks_with_canonical_eye_state_slots(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    output = tmp_path / "scratchpad/pack-four-look.mohan-outfit"
    receipt_path = tmp_path / "scratchpad/pack-four-look.receipt.json"
    receipt = prepare_four_look_pack(
        tmp_path,
        stage,
        output,
        receipt_path=receipt_path,
        makeup_regions=_regions(),
    )

    assert output.is_file()
    assert receipt_path.is_file()
    assert receipt["stage_records"] == EXPECTED_STAGE_RECORDS
    assert receipt["output_png_declarations"] == EXPECTED_OUTPUT_DECLARATIONS
    assert receipt["output_pack_sha256"] == digest(output.read_bytes())
    with zipfile.ZipFile(output) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        item = manifest["makeup"][0]
        assert [variant["id"] for variant in item["variants"]] == list(LOOKS)
        paths = []
        for variant in item["variants"]:
            assert set(variant["foundation_silhouettes"]) == set(REQUIRED_SILHOUETTES)
            assert set(variant["poses"]) == set(REQUIRED_SILHOUETTES)
            assert set(variant["eye_states"]) == {"half", "closed"}
            for entries in variant["poses"].values():
                assert {entry["slot"] for entry in entries} == set(SLOTS)
                paths.extend(entry["path"] for entry in entries)
            for state in variant["eye_states"].values():
                for entries in state.values():
                    assert {entry["slot"] for entry in entries} == {"eyes", "foundation"}
                    paths.extend(entry["path"] for entry in entries)
        assert len(paths) == EXPECTED_OUTPUT_DECLARATIONS
        assert len(set(paths)) == EXPECTED_OUTPUT_DECLARATIONS
        assert len(archive.namelist()) == EXPECTED_ARCHIVE_MEMBERS


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("missing_rest_foundation", "must carry all four makeup slots"),
        ("missing_half_foundation", "must carry all four makeup slots"),
        ("missing_glamorous", "must declare light, classic and glamorous"),
    ),
)
def test_missing_stage_material_is_rejected_before_sealing(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    stage_path = _stage(tmp_path)
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    view = stage["views"]["front-crossed"]
    if mutation == "missing_rest_foundation":
        del view["variants"]["light"]["states"]["rest"]["foundation"]
    elif mutation == "missing_half_foundation":
        del view["variants"]["light"]["states"]["half"]["foundation"]
    else:
        del view["variants"]["glamorous"]
    stage_path.write_text(json.dumps(stage), encoding="utf-8")
    output = tmp_path / f"scratchpad/{mutation}.mohan-outfit"

    with pytest.raises(FourLookStageError, match=message):
        prepare_four_look_pack(tmp_path, stage_path, output, makeup_regions=_regions())
    assert not output.exists()


def test_alpha_pin_mismatch_is_rejected(tmp_path: Path) -> None:
    stage_path = _stage(tmp_path)
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    record = stage["views"]["front-crossed"]["variants"]["light"]["states"]["rest"]["eyes"]
    record["nonvisible"] = False
    stage_path.write_text(json.dumps(stage), encoding="utf-8")
    output = tmp_path / "scratchpad/alpha-mismatch.mohan-outfit"

    with pytest.raises(FourLookStageError, match="nonvisible disagrees"):
        prepare_four_look_pack(tmp_path, stage_path, output, makeup_regions=_regions())
    assert not output.exists()


def test_compact_eye_states_are_accepted_but_required_layers_are_not_optional(tmp_path: Path) -> None:
    stage_path = _stage(tmp_path)
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    for view in stage["views"].values():
        for variant in view["variants"].values():
            for state in ("half", "closed"):
                for slot in ("cheeks", "lips"):
                    del variant["states"][state][slot]
    layers, pins, records = _validate_views(tmp_path, stage["views"])
    assert len(layers) == 3 * 31 * 8
    assert len(pins) == EXPECTED_SOURCE_PINS
    assert records == EXPECTED_OUTPUT_DECLARATIONS

    del stage["views"]["front-crossed"]["variants"]["light"]["states"]["half"]["foundation"]
    with pytest.raises(FourLookStageError, match="eyes and foundation"):
        _validate_views(tmp_path, stage["views"])
