"""Synthetic PNG fixtures for the read-only body-pack reader."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import logging
lazy import zipfile
lazy from io import BytesIO
lazy from pathlib import Path

lazy import pytest
lazy from PIL import Image

lazy from domain.body_pack import (
    BodyPackMismatchError,
    compute_body_pack_fingerprint,
    parse_body_pack_reference,
)
lazy from domain.character_pack.validation import (
    compute_package_hash,
    validate_character_pack,
)
lazy from domain.character_pose import canonical_view_id
lazy from infrastructure.body_pack_reader import BodyPackReader, resolve_body_pack
lazy from infrastructure.character_pack_files import CharacterPackReadError
lazy from infrastructure.character_source_pack import CharacterPackReader
lazy from tests.character_pack_fixtures import FAKE_CHARACTER_ID, build_fake_character_pack

PACK_ID = "synthetic.body"
PACK_VERSION = "1.0.0"
FULL_SIZE = (12, 18)
HALF_SIZE = (10, 8)
CHARACTER_LAYER_PATH = (
    f"assets/characters/{FAKE_CHARACTER_ID}/layers/front.png"
)


def _png(size: tuple[int, int], color: tuple[int, int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGBA", size, color).save(output, format="PNG")
    return output.getvalue()


def _file(path: str, payload: bytes) -> dict[str, str]:
    return {"path": path, "sha256": hashlib.sha256(payload).hexdigest()}


def _manifest() -> tuple[dict[str, object], dict[str, bytes]]:
    full_frame = _png(FULL_SIZE, (40, 60, 80, 255))
    full_blink = _png(FULL_SIZE, (40, 60, 80, 200))
    half_frame = _png(HALF_SIZE, (10, 20, 30, 255))
    face_core = _png(FULL_SIZE, (255, 255, 255, 255))
    files = {
        "frames/full/front-rest.png": full_frame,
        "frames/full/front-blink.png": full_blink,
        "frames/half/portrait-rest.png": half_frame,
        "masks/front.png": face_core,
    }
    manifest: dict[str, object] = {
        "schema": "mohan.body-pack.v1",
        "id": PACK_ID,
        "version": PACK_VERSION,
        "license": "CC-BY-NC-ND-4.0",
        "full_body": {
            "front": {
                "rest": _file("frames/full/front-rest.png", full_frame),
                "blink": _file("frames/full/front-blink.png", full_blink),
            },
        },
        "half_body": {
            "portrait": _file("frames/half/portrait-rest.png", half_frame),
        },
        "face_core_masks": {
            "front": _file("masks/front.png", face_core),
        },
    }
    manifest["fingerprint"] = compute_body_pack_fingerprint(manifest)
    return manifest, files


def _write_pack(
    base: Path,
    *,
    version: str = PACK_VERSION,
    overwrite: dict[str, bytes] | None = None,
) -> tuple[Path, object]:
    manifest, files = _manifest()
    manifest["version"] = version
    pack_root = base / PACK_ID
    pack_root.mkdir(parents=True)
    for relative, payload in files.items():
        path = pack_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    for relative, payload in (overwrite or {}).items():
        (pack_root / relative).write_bytes(payload)
    (pack_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    reference = parse_body_pack_reference(
        {
            "id": PACK_ID,
            "version": PACK_VERSION,
            "fingerprint": manifest["fingerprint"],
        }
    )
    return pack_root, reference


def test_reader_exposes_hash_verified_frames_and_canvases(tmp_path: Path) -> None:
    root = tmp_path / "body-packs"
    root.mkdir()
    pack_root, reference = _write_pack(root)

    reader = resolve_body_pack(reference, [root])

    assert isinstance(reader, BodyPackReader)
    assert reader.manifest.id == PACK_ID
    assert reader.fullbody_canvas == FULL_SIZE
    assert reader.halfbody_canvas == HALF_SIZE
    assert reader.frame_keys("front") == ("rest", "blink")
    assert reader.frame_keys("portrait", halfbody=True) == ("rest",)
    assert reader.load_frame("front", "rest") == (pack_root / "frames/full/front-rest.png").read_bytes()
    assert reader.load_frame("portrait", "rest", halfbody=True) == (
        pack_root / "frames/half/portrait-rest.png"
    ).read_bytes()
    assert reader.load_face_core("front") == (pack_root / "masks/front.png").read_bytes()
    assert reader.load_face_core("portrait") is None


def test_missing_body_pack_is_a_logged_mismatch(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    manifest, _ = _manifest()
    reference = parse_body_pack_reference(
        {
            "id": PACK_ID,
            "version": PACK_VERSION,
            "fingerprint": manifest["fingerprint"],
        }
    )

    with caplog.at_level(logging.ERROR), pytest.raises(BodyPackMismatchError) as error:
        resolve_body_pack(reference, [tmp_path / "missing-root"])

    assert error.value.code == "body_pack_missing"
    assert "body_pack_rejected code=body_pack_missing" in caplog.text


def test_version_mismatch_does_not_select_a_later_pack(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    _write_pack(first_root, version="2.0.0")
    _write_pack(second_root)
    manifest, _ = _manifest()
    reference = parse_body_pack_reference(
        {
            "id": PACK_ID,
            "version": PACK_VERSION,
            "fingerprint": manifest["fingerprint"],
        }
    )

    with pytest.raises(BodyPackMismatchError) as error:
        resolve_body_pack(reference, [first_root, second_root])

    assert error.value.code == "version_mismatch"


def test_fingerprint_mismatch_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "body-packs"
    root.mkdir()
    _write_pack(root)
    reference = parse_body_pack_reference(
        {"id": PACK_ID, "version": PACK_VERSION, "fingerprint": "0" * 64}
    )

    with pytest.raises(BodyPackMismatchError) as error:
        resolve_body_pack(reference, [root])

    assert error.value.code == "fingerprint_mismatch"


def test_payload_hash_mismatch_is_rejected_and_logged(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    root = tmp_path / "body-packs"
    root.mkdir()
    replacement = _png(FULL_SIZE, (200, 10, 20, 255))
    _write_pack(root, overwrite={"frames/full/front-rest.png": replacement})
    manifest, _ = _manifest()
    reference = parse_body_pack_reference(
        {
            "id": PACK_ID,
            "version": PACK_VERSION,
            "fingerprint": manifest["fingerprint"],
        }
    )

    with caplog.at_level(logging.ERROR), pytest.raises(BodyPackMismatchError) as error:
        resolve_body_pack(reference, [root])

    assert error.value.code == "file_hash_mismatch"
    assert error.value.path == "frames/full/front-rest.png"
    assert "body_pack_rejected code=file_hash_mismatch" in caplog.text


def test_missing_declared_image_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "body-packs"
    root.mkdir()
    pack_root, reference = _write_pack(root)
    (pack_root / "frames/full/front-rest.png").unlink()

    with pytest.raises(BodyPackMismatchError) as error:
        resolve_body_pack(reference, [root])

    assert error.value.code == "missing_file"
    assert error.value.path == "frames/full/front-rest.png"


def test_mixed_fullbody_dimensions_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "body-packs"
    root.mkdir()
    manifest, files = _manifest()
    extra = _png((FULL_SIZE[0] + 1, FULL_SIZE[1]), (1, 2, 3, 255))
    files["frames/full/side.png"] = extra
    manifest["full_body"]["side"] = {  # type: ignore[index]
        "rest": _file("frames/full/side.png", extra),
    }
    manifest["fingerprint"] = compute_body_pack_fingerprint(manifest)
    pack_root = root / PACK_ID
    pack_root.mkdir()
    for relative, payload in files.items():
        path = pack_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    (pack_root / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8", newline="\n"
    )
    reference = parse_body_pack_reference(
        {
            "id": PACK_ID,
            "version": PACK_VERSION,
            "fingerprint": manifest["fingerprint"],
        }
    )

    with pytest.raises(BodyPackMismatchError) as error:
        resolve_body_pack(reference, [root])

    assert error.value.code == "image_dimensions_mismatch"


def _character_dependency_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, str, bytes]:
    archive_path = build_fake_character_pack(tmp_path)
    character_root = tmp_path / "character-pack"
    character_root.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(character_root)

    manifest_path = character_root / "manifest.json"
    character_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rig_path = (
        character_root
        / "assets"
        / "characters"
        / FAKE_CHARACTER_ID
        / "rig"
        / "rig-manifest.json"
    )
    rig = json.loads(rig_path.read_text(encoding="utf-8"))
    full_size = (rig["full_body"]["canvas"]["width"], rig["full_body"]["canvas"]["height"])
    half_size = (
        rig["half_body"]["asset_canvas"]["width"], rig["half_body"]["asset_canvas"]["height"],
    )
    view_ids = tuple(
        canonical_view_id(yaw)
        for yaw in rig["full_body"]["view_ring"]["yaws"]
    )

    body_root = tmp_path / "body-packs"
    pack_root = body_root / "tests.synthetic-body"
    full_frame = _png(full_size, (40, 60, 80, 255))
    half_frame = _png(half_size, (20, 30, 40, 255))
    face_core = _png(full_size, (255, 255, 255, 255))
    body_files = {
        "frames/full.png": full_frame,
        "frames/half.png": half_frame,
        "masks/front.png": face_core,
    }
    for relative, payload in body_files.items():
        path = pack_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    body_manifest: dict[str, object] = {
        "schema": "mohan.body-pack.v1",
        "id": "tests.synthetic-body",
        "version": "1.0.0",
        "license": "Synthetic test-only",
        "full_body": dict.fromkeys(
            view_ids,
            _file("frames/full.png", full_frame),
        ),
        "half_body": {
            "portrait": _file("frames/half.png", half_frame),
        },
        "face_core_masks": {
            view_ids[0]: _file("masks/front.png", face_core),
        },
    }
    body_manifest["fingerprint"] = compute_body_pack_fingerprint(body_manifest)
    (pack_root / "manifest.json").write_text(
        json.dumps(body_manifest, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    layer_payload = _png(full_size, (200, 100, 30, 200))
    layer_path = character_root / CHARACTER_LAYER_PATH
    layer_path.parent.mkdir(parents=True, exist_ok=True)
    layer_path.write_bytes(layer_payload)
    layer_digest = hashlib.sha256(layer_payload).hexdigest()
    character_manifest["files"].append(
        {
            "path": CHARACTER_LAYER_PATH,
            "sha256": layer_digest,
            "bytes": len(layer_payload),
            "media_type": "image/png",
            "license_component": "character_art",
        }
    )
    character_manifest["body_pack"] = {
        "id": body_manifest["id"],
        "version": body_manifest["version"],
        "fingerprint": body_manifest["fingerprint"],
    }
    character_manifest["layer_views"] = {
        view_ids[0]: {
            "layers": [
                {
                    "kind": "garment",
                    "path": CHARACTER_LAYER_PATH,
                    "sha256": layer_digest,
                    "anchor": [0, 0],
                }
            ],
        }
    }
    character_manifest["package_hash"] = compute_package_hash(character_manifest)
    manifest_path.write_text(
        json.dumps(character_manifest, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return character_root, body_root, view_ids[0], layer_payload


def test_character_reader_resolves_declared_body_pack_and_layers(
    tmp_path: Path,
) -> None:
    character_root, body_root, view_id, layer_payload = (
        _character_dependency_fixture(tmp_path)
    )

    reader = CharacterPackReader(
        character_root,
        engine_version="4.6.0",
        body_pack_roots=[body_root],
    )

    assert reader.resolved_body_pack is not None
    assert reader.resolved_body_pack.manifest.id == "tests.synthetic-body"
    assert reader.manifest.body_pack == reader.resolved_body_pack.reference
    assert reader.character_layer_views[view_id].layers[0].path == CHARACTER_LAYER_PATH
    assert reader.load_character_layer(
        reader.character_layer_views[view_id].layers[0]
    ) == layer_payload
    assert reader.resolved_body_pack.load_face_core(view_id) is not None


def test_character_reader_rejects_missing_declared_body_pack(
    tmp_path: Path,
) -> None:
    character_root, _, _, _ = _character_dependency_fixture(tmp_path)

    with pytest.raises(BodyPackMismatchError) as error:
        CharacterPackReader(
            character_root,
            engine_version="4.6.0",
            body_pack_roots=[tmp_path / "missing-body-packs"],
        )

    assert error.value.code == "body_pack_missing"


def test_character_layer_hash_must_match_character_file_inventory(
    tmp_path: Path,
) -> None:
    character_root, _, view_id, _ = _character_dependency_fixture(tmp_path)
    manifest_path = character_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["layer_views"][view_id]["layers"][0]["sha256"] = "0" * 64
    manifest["package_hash"] = compute_package_hash(manifest)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    result = validate_character_pack(character_root, engine_version="4.6.0")

    assert not result.valid
    assert result.issues[0].code == "reference_hash_mismatch"
    assert result.issues[0].path == CHARACTER_LAYER_PATH


def test_character_layer_changed_after_validation_raises(tmp_path: Path) -> None:
    character_root, body_root, view_id, _ = _character_dependency_fixture(tmp_path)
    reader = CharacterPackReader(
        character_root, engine_version="4.6.0", body_pack_roots=[body_root],
    )
    layer = reader.character_layer_views[view_id].layers[0]
    path = character_root / layer.path
    changed = bytearray(path.read_bytes())
    changed[-1] ^= 1
    path.write_bytes(changed)
    with pytest.raises(CharacterPackReadError) as error:
        reader.load_character_layer(layer)
    assert error.value.code == "file_hash_mismatch"
