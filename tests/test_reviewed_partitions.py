"""Batch acceptance must bind reviews and preserve every native RGBA pixel."""
from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path
lazy import struct
lazy import zlib

lazy import numpy as np
lazy from PIL import Image
lazy import pytest

lazy from tools.art_pipeline import reviewed_partitions as subject


def fixture_batch(root: Path) -> tuple[Path, dict, np.ndarray]:
    source = np.full((5, 7, 4), [73, 29, 17, 128], dtype=np.uint8)
    source[0, 0] = [19, 23, 41, 0]  # Preserve even invisible RGB.
    Image.fromarray(source).save(root / "source.png")
    digest = hashlib.sha256((root / "source.png").read_bytes()).hexdigest()
    parts = []
    for index, role in enumerate(["visible_core_hair", "visible_upper_garment"]):
        mask = np.zeros(source.shape[:2], dtype=np.uint8)
        mask[index + 1, 1:4] = 255
        name = f"mask{index}.png"
        Image.fromarray(mask).save(root / name)
        mask_digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        parts.append({"role": role, "mask": {"path": name, "sha256": mask_digest},
                      "review": {"decision": "accept_visible_partition", "reviewer": "root",
                                 "source_sha256": digest, "mask_sha256": mask_digest}})
    spec = {"schema": subject.SCHEMA, "entries": [{"id": "front-eureka",
            "source": {"path": "source.png", "sha256": digest}, "parts": parts}]}
    manifest = root / "batch.json"
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    return manifest, spec, source


@pytest.mark.parametrize("roles", [
    ("visible_core_hair", "visible_upper_garment"),
    ("visible_left_hand", "visible_right_hand"),
])
def test_multi_component_native_reconstruction(tmp_path, roles):
    manifest, spec, source = fixture_batch(tmp_path)
    for part, role in zip(spec["entries"][0]["parts"], roles, strict=True):
        part["role"] = role
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    output = tmp_path / "output"
    receipt = subject.integrate_batch(manifest, output)
    directory = output / "front-eureka"
    names = [*roles, "remaining_foreground"]
    arrays = [np.array(Image.open(directory / f"{name}.png")) for name in names]
    assert np.array_equal(np.sum(arrays, axis=0, dtype=np.uint16), source)
    assert not np.any(np.sum([a[:, :, 3] > 0 for a in arrays], axis=0) > 1)
    assert receipt["production_runtime_ready"] is False
    assert receipt["complete_24_600"] is False


def test_overlapping_hands_are_rejected_before_export(tmp_path):
    manifest, spec, _ = fixture_batch(tmp_path)
    left, right = spec["entries"][0]["parts"]
    left["role"] = "visible_left_hand"
    right["role"] = "visible_right_hand"
    right["mask"] = dict(left["mask"])
    right["review"]["mask_sha256"] = left["mask"]["sha256"]
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError, match="overlap"):
        subject.integrate_batch(manifest, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("failure", ["stale_review", "stale_file", "overlap", "duplicate",
                                     "traversal", "empty", "background", "nonbinary"])
def test_invalid_batch_publishes_nothing(tmp_path, failure):
    manifest, spec, _ = fixture_batch(tmp_path)
    entry = spec["entries"][0]
    part = entry["parts"][0]
    if failure == "stale_review":
        part["review"]["source_sha256"] = "0" * 64
    elif failure == "stale_file":
        (tmp_path / "source.png").write_bytes(b"changed")
    elif failure == "overlap":
        entry["parts"][1]["mask"] = dict(part["mask"])
        entry["parts"][1]["review"]["mask_sha256"] = part["mask"]["sha256"]
    elif failure == "duplicate":
        spec["entries"].append(entry)
    elif failure == "traversal":
        entry["id"] = "../escape"
    elif failure == "empty":
        spec["entries"] = []
    else:
        mask = np.array(Image.open(tmp_path / "mask0.png"))
        mask[0, 0] = 255 if failure == "background" else 127
        Image.fromarray(mask).save(tmp_path / "mask0.png")
        digest = hashlib.sha256((tmp_path / "mask0.png").read_bytes()).hexdigest()
        part["mask"]["sha256"] = digest
        part["review"]["mask_sha256"] = digest
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError):
        subject.integrate_batch(manifest, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_existing_batch_is_never_overwritten(tmp_path):
    manifest, _, _ = fixture_batch(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    sentinel = output / "receipt.json"
    sentinel.write_bytes(b"previous verified batch")
    with pytest.raises(ValueError):
        subject.integrate_batch(manifest, output)
    assert sentinel.read_bytes() == b"previous verified batch"


def test_native_16bit_rgba_is_rejected_before_lossy_decode(tmp_path):
    manifest, spec, source = fixture_batch(tmp_path)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    height, width = source.shape[:2]
    samples = source.astype(np.uint16) * 256 + 37
    samples[:, :, 3] = 32768
    scanlines = b"".join(b"\x00" + row.astype(">u2").tobytes() for row in samples)
    payload = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 16, 6, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b""))
    (tmp_path / "source.png").write_bytes(payload)
    # Pillow reports RGBA while silently dropping each channel's low byte.
    with Image.open(tmp_path / "source.png") as image:
        assert image.mode == "RGBA"
        assert np.array(image).dtype == np.uint8
    digest = hashlib.sha256(payload).hexdigest()
    entry = spec["entries"][0]
    entry["source"]["sha256"] = digest
    for part in entry["parts"]:
        part["review"]["source_sha256"] = digest
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError, match="8-bit"):
        subject.integrate_batch(manifest, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_input_change_during_encoding_is_rejected(tmp_path, monkeypatch):
    manifest, _, _ = fixture_batch(tmp_path)
    original = subject._png

    def changed(array):
        result = original(array)
        (tmp_path / "source.png").write_bytes(b"concurrent replacement")
        return result

    monkeypatch.setattr(subject, "_png", changed)
    with pytest.raises(ValueError, match="changed before"):
        subject.integrate_batch(manifest, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("kind", ["evidence", "trace"])
@pytest.mark.parametrize("failure", ["stale", "missing_path", "blank_path"])
def test_bound_review_artifact_failure_publishes_nothing(tmp_path, kind, failure):
    manifest, spec, _ = fixture_batch(tmp_path)
    proof = tmp_path / "review-proof.txt"
    proof.write_bytes(b"reviewed candidate boundary")
    review = spec["entries"][0]["parts"][0]["review"]
    review[kind] = proof.name
    review[f"{kind}_sha256"] = hashlib.sha256(proof.read_bytes()).hexdigest()
    if failure == "stale":
        proof.write_bytes(b"different candidate boundary")
    elif failure == "missing_path":
        del review[kind]
    else:
        review[kind] = ""
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError):
        subject.integrate_batch(manifest, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_review_artifact_change_during_encoding_is_rejected(tmp_path, monkeypatch):
    manifest, spec, _ = fixture_batch(tmp_path)
    proof = tmp_path / "trace.json"
    proof.write_bytes(b'{"reviewed": true}')
    review = spec["entries"][0]["parts"][0]["review"]
    review["trace"] = proof.name
    review["trace_sha256"] = hashlib.sha256(proof.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    original = subject._png

    def changed(array):
        result = original(array)
        proof.write_bytes(b'{"replacement": true}')
        return result

    monkeypatch.setattr(subject, "_png", changed)
    with pytest.raises(ValueError, match="changed before"):
        subject.integrate_batch(manifest, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_bound_evidence_and_legacy_review_notes_remain_supported(tmp_path):
    manifest, spec, _ = fixture_batch(tmp_path)
    proof = tmp_path / "review.txt"
    proof.write_bytes(b"same reviewed source and mask")
    first, second = spec["entries"][0]["parts"]
    first["review"].update(evidence=proof.name,
                           evidence_sha256=hashlib.sha256(proof.read_bytes()).hexdigest())
    second["review"]["evidence"] = "Legacy descriptive review note without a file binding"
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    receipt = subject.integrate_batch(manifest, tmp_path / "output")
    assert receipt["entries"][0]["rgba_reconstruction_exact"] is True
    assert receipt["entries"][0]["parts"] == spec["entries"][0]["parts"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
