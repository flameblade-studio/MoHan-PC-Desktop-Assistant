"""Consolidation intake must reject stale or semantically inconsistent batches."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image
lazy import pytest

lazy from tools.art_pipeline.consolidate_partitions import consolidate_batches
lazy from tools.art_pipeline.reviewed_partitions import SCHEMA, integrate_batch


def _record(folder: Path, name: str) -> dict[str, str]:
    path = folder / name
    return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _make_batch(folder: Path) -> tuple[Path, Path]:
    folder.mkdir(parents=True)
    source = np.full((6, 8, 4), [73, 29, 17, 128], dtype=np.uint8)
    source[0, 0] = [19, 23, 41, 0]
    Image.fromarray(source).save(folder / "source.png")
    mask = np.zeros(source.shape[:2], dtype=np.uint8)
    mask[1, 1:4] = 255
    Image.fromarray(mask).save(folder / "mask.png")
    (folder / "review.txt").write_bytes(b"reviewed source-specific garment")

    source_record = _record(folder, "source.png")
    mask_record = _record(folder, "mask.png")
    evidence_record = _record(folder, "review.txt")
    part = {
        "role": "visible_shorts",
        "mask": mask_record,
        "review": {
            "decision": "accept_visible_partition",
            "reviewer": "root",
            "source_sha256": source_record["sha256"],
            "mask_sha256": mask_record["sha256"],
            "evidence": evidence_record["path"],
            "evidence_sha256": evidence_record["sha256"],
        },
    }
    spec = {
        "schema": SCHEMA,
        "entries": [{"id": "yaw-165", "source": source_record, "parts": [part]}],
    }
    manifest = folder / "manifest.json"
    output = folder / "batch"
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    integrate_batch(manifest, output)
    return manifest, output


def _rewrite_report(batch: Path, mutate) -> None:
    receipt_path = batch / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    mutate(receipt["entries"][0])
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")


def _rejects_before_export(tmp_path: Path, source_batch: tuple[Path, Path]) -> None:
    target_manifest = tmp_path / "consolidated.json"
    target_output = tmp_path / "consolidated"
    assert not target_output.exists()
    with pytest.raises((ValueError, OSError)):
        consolidate_batches([source_batch], target_manifest, target_output)
    assert not target_output.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dimensions", [999, 999]),
        ("visible_component_pixels", {"visible_shorts": 0}),
        ("remainder_role", "visible_shorts"),
        ("rgba_reconstruction_exact", False),
        ("overlap_pixels", 1),
    ],
)
def test_consolidation_rejects_contradictory_report_fields(
    tmp_path: Path, field: str, value: object,
) -> None:
    source_batch = _make_batch(tmp_path / "input")
    _rewrite_report(source_batch[1], lambda report: report.__setitem__(field, value))
    _rejects_before_export(tmp_path, source_batch)


def test_consolidation_rejects_non_png_even_when_receipt_hash_is_updated(tmp_path: Path) -> None:
    source_batch = _make_batch(tmp_path / "input")
    output_file = source_batch[1] / "yaw-165" / "visible_shorts.png"
    output_file.write_bytes(b"not a PNG")
    _rewrite_report(
        source_batch[1],
        lambda report: report["outputs"].__setitem__(
            "visible_shorts.png", hashlib.sha256(output_file.read_bytes()).hexdigest()
        ),
    )
    _rejects_before_export(tmp_path, source_batch)


def test_consolidation_rejects_changed_pixels_even_when_receipt_hash_is_updated(
    tmp_path: Path,
) -> None:
    source_batch = _make_batch(tmp_path / "input")
    output_file = source_batch[1] / "yaw-165" / "visible_shorts.png"
    with Image.open(output_file) as image:
        changed = np.array(image.convert("RGBA"))
    changed[1, 1, 0] = (int(changed[1, 1, 0]) + 1) % 256
    Image.fromarray(changed, mode="RGBA").save(output_file)
    _rewrite_report(
        source_batch[1],
        lambda report: report["outputs"].__setitem__(
            "visible_shorts.png", hashlib.sha256(output_file.read_bytes()).hexdigest()
        ),
    )
    _rejects_before_export(tmp_path, source_batch)


def test_consolidation_rejects_unlisted_batch_directory_file(tmp_path: Path) -> None:
    source_batch = _make_batch(tmp_path / "input")
    (source_batch[1] / "yaw-165" / "unlisted-extra.bin").write_bytes(b"extra")
    _rejects_before_export(tmp_path, source_batch)


def test_consolidation_rejects_unlisted_batch_root_file(tmp_path: Path) -> None:
    source_batch = _make_batch(tmp_path / "input")
    (source_batch[1] / "unlisted-extra.bin").write_bytes(b"extra")
    _rejects_before_export(tmp_path, source_batch)


def test_consolidation_allows_same_rgba_with_different_png_compression(tmp_path: Path) -> None:
    source_batch = _make_batch(tmp_path / "input")
    output_file = source_batch[1] / "yaw-165" / "visible_shorts.png"
    original_payload = output_file.read_bytes()
    with Image.open(output_file) as image:
        original_pixels = np.array(image.convert("RGBA"))
    Image.fromarray(original_pixels, mode="RGBA").save(
        output_file, format="PNG", compress_level=0,
    )
    compressed_payload = output_file.read_bytes()
    assert compressed_payload != original_payload
    with Image.open(output_file) as image:
        assert np.array_equal(np.array(image.convert("RGBA")), original_pixels)
    _rewrite_report(
        source_batch[1],
        lambda report: report["outputs"].__setitem__(
            "visible_shorts.png", hashlib.sha256(compressed_payload).hexdigest()
        ),
    )
    target_manifest = tmp_path / "consolidated.json"
    target_output = tmp_path / "consolidated"
    receipt = consolidate_batches([source_batch], target_manifest, target_output)
    assert target_output.exists()
    assert receipt["entries"][0]["id"] == "yaw-165"
