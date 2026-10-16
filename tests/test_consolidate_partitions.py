"""Completed partial batches combine disjoint roles with verified current inputs."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image
lazy import pytest

lazy from tools.art_pipeline.consolidate_partitions import consolidate_batches
lazy from tools.art_pipeline.reviewed_partitions import SCHEMA, integrate_batch


def make_batch(folder: Path, role: str, row: int = 1, color: int = 73) -> tuple[Path, Path]:
    folder.mkdir()
    source = np.full((6, 8, 4), [color, 29, 17, 128], dtype=np.uint8)
    source[0, 0] = [19, 23, 41, 0]
    Image.fromarray(source).save(folder / "source.png")
    mask = np.zeros(source.shape[:2], dtype=np.uint8)
    mask[row, 1:4] = 255
    Image.fromarray(mask).save(folder / "mask.png")
    (folder / "review.txt").write_bytes(b"reviewed source-specific garment")

    def record(name):
        return {"path": name, "sha256": hashlib.sha256((folder / name).read_bytes()).hexdigest()}

    src, selected, evidence = record("source.png"), record("mask.png"), record("review.txt")
    part = {"role": role, "mask": selected,
            "review": {"decision": "accept_visible_partition", "reviewer": "root",
                       "source_sha256": src["sha256"], "mask_sha256": selected["sha256"],
                       "evidence": evidence["path"], "evidence_sha256": evidence["sha256"]}}
    spec = {"schema": SCHEMA, "entries": [{"id": "yaw-165", "source": src, "parts": [part]}]}
    manifest, output = folder / "manifest.json", folder / "batch"
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    integrate_batch(manifest, output)
    return manifest, output


def test_split_view_rebuilds_one_exact_remainder_with_relative_evidence(tmp_path):
    upper = make_batch(tmp_path / "upper", "visible_upper_garment", row=1)
    shorts = make_batch(tmp_path / "shorts", "visible_shorts", row=2)
    output = tmp_path / "combined"
    receipt = consolidate_batches([upper, shorts], tmp_path / "combined.json", output)
    assert len(receipt["entries"]) == 1
    entry = receipt["entries"][0]
    assert {part["role"] for part in entry["parts"]} == {"visible_upper_garment", "visible_shorts"}
    assert receipt["production_runtime_ready"] is False
    assert receipt["complete_24_600"] is False
    layers = [np.array(Image.open(output / "yaw-165" / name)) for name in
              ["visible_upper_garment.png", "visible_shorts.png", "remaining_foreground.png"]]
    source = np.array(Image.open(tmp_path / "upper/source.png"))
    assert np.array_equal(np.sum(layers, axis=0, dtype=np.uint16), source)
    assert not np.any(np.sum([layer[:, :, 3] > 0 for layer in layers], axis=0) > 1)
    assert all(Path(part["review"]["evidence"]).is_absolute() for part in entry["parts"])


@pytest.mark.parametrize("failure", ["source_conflict", "duplicate_role", "overlap",
                                     "incomplete", "output_drift", "manifest_drift", "source_alias_drift"])
def test_invalid_batch_combination_never_creates_export(tmp_path, failure):
    first = make_batch(tmp_path / "first", "visible_upper_garment")
    second = make_batch(tmp_path / "second",
                        "visible_upper_garment" if failure == "duplicate_role" else "visible_shorts",
                        row=1 if failure == "overlap" else 2,
                        color=81 if failure == "source_conflict" else 73)
    if failure == "incomplete":
        (second[1] / "receipt.json").unlink()
    elif failure == "output_drift":
        (second[1] / "yaw-165/remaining_foreground.png").write_bytes(b"corrupt")
    elif failure == "manifest_drift":
        second[0].write_text(second[0].read_text(encoding="utf-8") + " ", encoding="utf-8")
    elif failure == "source_alias_drift":
        (tmp_path / "second/source.png").write_bytes(b"changed source alias")
    with pytest.raises((ValueError, OSError)):
        consolidate_batches([first, second], tmp_path / "combined.json", tmp_path / "combined")
    assert not (tmp_path / "combined").exists()


def test_existing_consolidation_is_never_overwritten(tmp_path):
    batch = make_batch(tmp_path / "input", "visible_shorts")
    manifest = tmp_path / "existing.json"
    manifest.write_bytes(b"previous reviewed manifest")
    with pytest.raises(ValueError):
        consolidate_batches([batch], manifest, tmp_path / "output")
    assert manifest.read_bytes() == b"previous reviewed manifest"
    assert not (tmp_path / "output").exists()
